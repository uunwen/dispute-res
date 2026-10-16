"""End-to-end demo of the multi-agent resolution pipeline.

Resolves one route-deviation dispute and one no-show dispute (the official
golden cases DISP-001 / DISP-002 when imported, otherwise the first seeded
dispute of each category) and prints each dispute's ruling and agent timeline.

Run from the backend folder:

    uv run python scripts/demo.py

Requires the database to be migrated and cases imported (see README).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.db import models
from app.db.enums import DisputeCategory
from app.db.session import async_session_factory
from app.orchestrator.pipeline import resolve_dispute


async def _find_dispute(session, *, external_id=None, category=None):
    if external_id is not None:
        dispute = (
            await session.execute(
                select(models.Dispute).where(models.Dispute.external_id == external_id)
            )
        ).scalars().first()
        if dispute is not None:
            return dispute
    if category is not None:
        return (
            await session.execute(
                select(models.Dispute)
                .where(models.Dispute.category == category)
                .order_by(models.Dispute.id)
            )
        ).scalars().first()
    return None


async def _reset_dispute(dispute_id: int) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id))
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id))
        dispute = await session.get(models.Dispute, dispute_id)
        if dispute is not None:
            dispute.status = "open"
        await session.commit()


async def _run_demo(dispute: models.Dispute) -> None:
    await _reset_dispute(dispute.id)

    print("\n" + "=" * 72)
    print(f"DISPUTE #{dispute.id}  ·  {dispute.category.value}")
    print(f"claim: {dispute.claim_text}")
    print("=" * 72)

    ruling = await resolve_dispute(dispute.id)

    print("final ruling")
    print(f"  outcome      : {ruling.outcome.value}")
    print(f"  refund       : ${ruling.refund_amount:.2f}")
    print(f"  confidence   : {ruling.confidence:.2f}")
    print(f"  escalated    : {ruling.escalated}")
    print(f"  llm_degraded : {ruling.llm_degraded}")

    async with async_session_factory() as session:
        messages = (
            await session.execute(
                select(models.AgentMessage)
                .where(models.AgentMessage.dispute_id == dispute.id)
                .order_by(models.AgentMessage.created_at)
            )
        ).scalars().all()

    print("agent timeline")
    for message in messages:
        round_ = (message.content or {}).get("round", "")
        print(f"  - {message.sender:15s} [{message.message_type}] round={round_}")
    if not messages:
        print("  (no agent messages produced)")


async def main() -> None:
    async with async_session_factory() as session:
        route = await _find_dispute(
            session, external_id="DISP-001", category=DisputeCategory.route_deviation
        )
        no_show = await _find_dispute(
            session, external_id="DISP-002", category=DisputeCategory.no_show
        )

    if route is None:
        print("No route-deviation dispute found — run scripts/seed.py or scripts/import_cases.py first.")
    else:
        await _run_demo(route)

    if no_show is None:
        print("No no-show dispute found — run scripts/seed.py or scripts/import_cases.py first.")
    else:
        await _run_demo(no_show)


if __name__ == "__main__":
    asyncio.run(main())
