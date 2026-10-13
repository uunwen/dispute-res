import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.orchestrator.pipeline import resolve_dispute
from app.queue.queue import pop_dispute


async def main() -> None:
    while True:
        dispute_id, score = await pop_dispute()
        if dispute_id is None:
            await asyncio.sleep(1)
            continue
        print(f"Resolving dispute {dispute_id} (priority {score})", flush=True)
        try:
            await resolve_dispute(dispute_id)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to resolve dispute {dispute_id}: {exc}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
