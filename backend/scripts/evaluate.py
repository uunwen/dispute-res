import asyncio
import json
import statistics
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

DATASET_LABEL = "synthetic variants of organizer samples"


async def _dispute_id_by_external(session, external_id: str) -> int | None:
    return (
        await session.execute(
            select(models.Dispute.id).where(models.Dispute.external_id == external_id)
        )
    ).scalar_one_or_none()


async def _reset_disputes(dispute_ids: list[int]) -> None:
    if not dispute_ids:
        return
    async with async_session_factory() as session:
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id.in_(dispute_ids)))
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id.in_(dispute_ids)))
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


async def _latest_ruling(session, dispute_id: int) -> models.Ruling | None:
    return (
        await session.execute(
            select(models.Ruling)
            .where(models.Ruling.dispute_id == dispute_id)
            .order_by(models.Ruling.created_at.desc())
        )
    ).scalars().first()


async def main() -> None:
    expected = json.loads((DATA_DIR / "eval" / "expected.json").read_text(encoding="utf-8"))

    entries: list[tuple[dict, int]] = []
    async with async_session_factory() as session:
        for entry in expected:
            dispute_id = await _dispute_id_by_external(session, entry["external_id"])
            if dispute_id is None:
                print(f"  warning: no dispute for external_id {entry['external_id']}; run generate_variants.py / import_cases.py", flush=True)
                continue
            entries.append((entry, dispute_id))

    dispute_ids = [dispute_id for _, dispute_id in entries]
    await _reset_disputes(dispute_ids)

    semaphore = asyncio.Semaphore(settings.eval_concurrency)
    print(
        f"Evaluating {len(dispute_ids)} disputes ({DATASET_LABEL}) "
        f"with concurrency {settings.eval_concurrency}...",
        flush=True,
    )
    total_start = time.perf_counter()
    results = await asyncio.gather(*[_resolve_one(semaphore, dispute_id) for _, dispute_id in entries])
    total_time = time.perf_counter() - total_start

    seconds_by_id = {dispute_id: seconds for dispute_id, seconds, _failed in results}
    failed_ids = {dispute_id for dispute_id, _seconds, failed in results if failed}

    total = 0
    degraded = 0
    correct = 0
    refund_errors: list[float] = []
    tp = fp = fn = tn = 0
    per_section: dict[str, dict[str, int]] = {}
    judge_models: dict[str, int] = {}

    async with async_session_factory() as session:
        for entry, dispute_id in entries:
            ruling = await _latest_ruling(session, dispute_id)
            if ruling is None:
                continue
            total += 1
            if ruling.llm_degraded:
                degraded += 1
                continue

            section = entry.get("section", "?")
            bucket = per_section.setdefault(section, {"correct": 0, "total": 0})
            bucket["total"] += 1

            if ruling.outcome.value == entry["outcome"]:
                correct += 1
                bucket["correct"] += 1

            refund_errors.append(abs(ruling.refund_amount - entry["refund_amount"]))

            expected_esc = bool(entry["escalate"])
            actual_esc = bool(ruling.escalated)
            if expected_esc and actual_esc:
                tp += 1
            elif expected_esc and not actual_esc:
                fn += 1
            elif not expected_esc and actual_esc:
                fp += 1
            else:
                tn += 1

            judge_model = (ruling.model_info or {}).get("judge")
            if judge_model:
                judge_models[judge_model] = judge_models.get(judge_model, 0) + 1

    non_degraded = total - degraded
    accuracy = (correct / non_degraded) if non_degraded else 0.0
    precision = (tp / (tp + fp)) if (tp + fp) else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) else 0.0

    print(f"\n=== evaluation report ({DATASET_LABEL}) ===")
    print(f"disputes resolved: {total}")
    print(f"degraded (excluded from metrics): {degraded}")
    if failed_ids:
        print(f"failed to resolve: {len(failed_ids)}")
    print(f"\noutcome accuracy (non-degraded): {correct}/{non_degraded} ({accuracy:.1%})")
    if refund_errors:
        print(
            f"refund error (mean |actual - expected|): {statistics.mean(refund_errors):.3f} "
            f"(max {max(refund_errors):.3f})"
        )
    print(
        f"escalation precision: {tp}/{tp + fp} ({precision:.1%})   "
        f"recall: {tp}/{tp + fn} ({recall:.1%})"
    )
    print("  (escalation ground truth covers deterministic triggers only: safety, "
          "dispute value > $50, route deviation > 2km, fraud flag; the confidence-based "
          "Sec 6.1/6.2 escalation the system also applies is not predicted)")
    print("\nper-section accuracy:")
    for section in sorted(per_section):
        bucket = per_section[section]
        acc = (bucket["correct"] / bucket["total"]) if bucket["total"] else 0.0
        print(f"  Sec {section}: {bucket['correct']}/{bucket['total']} ({acc:.1%})")

    times = list(seconds_by_id.values())
    if times:
        print(
            f"\ntime per dispute: mean {statistics.mean(times):.2f}s "
            f"median {statistics.median(times):.2f}s max {max(times):.2f}s "
            f"(total {total_time:.2f}s)"
        )

    if judge_models:
        print("model(s) used for rulings:")
        for model, count in sorted(judge_models.items()):
            print(f"  {model}: {count}")

    print("embedding space:")
    print(f"  provider: {embeddings.active_provider}")
    print(f"  model: {embeddings.active_model}")
    print(f"  dimension: {embeddings.dimension}")
    print(f"  fell back to fastembed: {'yes' if embeddings.fallback_reason else 'no'}")


if __name__ == "__main__":
    asyncio.run(main())
