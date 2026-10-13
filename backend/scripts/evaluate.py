import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import models
from app.db.session import async_session_factory
from app.llm.embeddings import embeddings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

EXPECTED_TO_RULING = {
    "refund": "full_refund",
    "partial_refund": "partial_refund",
    "no_action": "no_refund",
}


async def main() -> None:
    ground_truth = json.loads((DATA_DIR / "ground_truth.json").read_text(encoding="utf-8"))

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
    print(f"rulings evaluated: {total}")
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
