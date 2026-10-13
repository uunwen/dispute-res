import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.llm.client import LLMError
from app.llm.embeddings import embeddings
from app.orchestrator.pipeline import resolve_dispute

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

EXPECTED_TO_RULING = {
    "refund": "full_refund",
    "partial_refund": "partial_refund",
    "no_action": "no_refund",
}


async def _reset_disputes(dispute_ids: list[int]) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(models.Ruling).where(models.Ruling.dispute_id.in_(dispute_ids))
        )
        await session.execute(
            delete(models.AgentMessage).where(models.AgentMessage.dispute_id.in_(dispute_ids))
        )
        disputes = (
            await session.execute(select(models.Dispute).where(models.Dispute.id.in_(dispute_ids)))
        ).scalars().all()
        for dispute in disputes:
            dispute.status = "open"
        await session.commit()


async def _resolve_one(semaphore: asyncio.Semaphore, dispute_id: int) -> tuple[int, float, bool]:
    async with semaphore:
        start = time.perf_counter()
        last_exc: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                await resolve_dispute(dispute_id)
                return dispute_id, time.perf_counter() - start, False
            except LLMError as exc:
                last_exc = exc
                wait = settings.llm_backoff_base * (2 ** attempt)
                print(f"  dispute {dispute_id}: LLM error ({exc}); retrying in {wait:.2f}s", flush=True)
                await asyncio.sleep(wait)
        return dispute_id, time.perf_counter() - start, last_exc is not None


async def main() -> None:
    ground_truth = json.loads((DATA_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    dispute_ids = [entry["dispute_id"] for entry in ground_truth]
    await _reset_disputes(dispute_ids)

    semaphore = asyncio.Semaphore(settings.eval_concurrency)
    print(
        f"Evaluating {len(dispute_ids)} disputes with concurrency {settings.eval_concurrency}...",
        flush=True,
    )
    total_start = time.perf_counter()
    results = await asyncio.gather(
        *[_resolve_one(semaphore, dispute_id) for dispute_id in dispute_ids]
    )
    total_time = time.perf_counter() - total_start

    print("\nper-dispute time:")
    for dispute_id, seconds, failed in results:
        print(f"  dispute {dispute_id}: {seconds:.2f}s {'FAILED' if failed else 'ok'}")
    print(f"\ntotal resolve time: {total_time:.2f}s")

    total = 0
    degraded = 0
    non_degraded = 0
    correct = 0
    judge_models: dict[str, int] = {}
    async with async_session_factory() as session:
        for entry in ground_truth:
            ruling = (
                await session.execute(
                    select(models.Ruling)
                    .where(models.Ruling.dispute_id == entry["dispute_id"])
                    .order_by(models.Ruling.created_at.desc())
                )
            ).scalars().first()
            if ruling is None:
                continue
            total += 1
            if ruling.llm_degraded:
                degraded += 1
                continue
            non_degraded += 1
            expected = EXPECTED_TO_RULING.get(entry["expected_outcome"])
            if expected is not None and expected == ruling.outcome.value:
                correct += 1
            judge_model = (ruling.model_info or {}).get("judge")
            if judge_model:
                judge_models[judge_model] = judge_models.get(judge_model, 0) + 1

    accuracy = (correct / non_degraded) if non_degraded else 0.0
    print(f"\nrulings evaluated: {total}")
    print(f"degraded (excluded from accuracy): {degraded}")
    print(f"non-degraded: {non_degraded}")
    print(f"accuracy (non-degraded): {correct}/{non_degraded} ({accuracy:.1%})")
    if judge_models:
        print("model(s) used for rulings:")
        for model, count in sorted(judge_models.items()):
            print(f"  {model}: {count}")

    print("embedding space:")
    print(f"  provider: {embeddings.active_provider}")
    print(f"  model: {embeddings.active_model}")
    print(f"  dimension: {embeddings.dimension}")
    print(f"  fell back to fastembed: {'yes' if embeddings.fallback_reason else 'no'}")
    if embeddings.fallback_reason:
        print(f"  fallback reason: {embeddings.fallback_reason}")


if __name__ == "__main__":
    asyncio.run(main())
