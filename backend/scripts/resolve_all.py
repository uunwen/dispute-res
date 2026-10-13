import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import models
from app.db.session import async_session_factory
from app.orchestrator.pipeline import resolve_dispute


async def main() -> None:
    async with async_session_factory() as session:
        ids = (
            await session.execute(
                select(models.Dispute.id).where(models.Dispute.status == "open")
            )
        ).scalars().all()

    for dispute_id in ids:
        print(f"Resolving dispute {dispute_id}...", flush=True)
        try:
            await resolve_dispute(dispute_id)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {exc}", flush=True)

    print(f"Resolved {len(ids)} open dispute(s).")


if __name__ == "__main__":
    asyncio.run(main())
