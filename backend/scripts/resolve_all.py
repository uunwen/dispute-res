import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.db import models
from app.db.session import async_session_factory
from app.orchestrator.pipeline import resolve_dispute


async def _clear_dispute(dispute_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id)
        )
        await session.execute(
            delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id)
        )
        await session.execute(
            delete(models.DisputeReview).where(models.DisputeReview.dispute_id == dispute_id)
        )
        await session.commit()


async def _resolve_one(dispute_id: int, force: bool) -> dict:
    if force:
        await _clear_dispute(dispute_id)
    start = time.perf_counter()
    ruling = await resolve_dispute(dispute_id)
    return {
        "id": dispute_id,
        "outcome": ruling.outcome.value,
        "llm_degraded": ruling.llm_degraded,
        "seconds": time.perf_counter() - start,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve disputes through the agent pipeline.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete prior rulings/messages/reviews for a dispute before re-resolving.",
    )
    parser.add_argument(
        "dispute_ids",
        nargs="*",
        type=int,
        help="Specific dispute ids to resolve. If omitted, all open disputes are resolved.",
    )
    args = parser.parse_args()

    if args.dispute_ids:
        ids = args.dispute_ids
    else:
        async with async_session_factory() as session:
            ids = (
                await session.execute(
                    select(models.Dispute.id).where(models.Dispute.status == "open")
                )
            ).scalars().all()

    print(f"Resolving {len(ids)} dispute(s) (force={args.force})...", flush=True)
    rows = []
    for dispute_id in ids:
        try:
            row = await _resolve_one(dispute_id, args.force)
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"  dispute {dispute_id}: FAILED: {exc}", flush=True)
            rows.append({"id": dispute_id, "outcome": "ERROR", "llm_degraded": None, "seconds": 0.0})

    print("\nid | outcome | llm_degraded | seconds")
    for row in rows:
        print(f"{row['id']} | {row['outcome']} | {row['llm_degraded']} | {row['seconds']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
