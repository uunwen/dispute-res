import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.orchestrator.pipeline import resolve_dispute
from app.profiling import format_table, profiler

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


async def main() -> None:
    ground_truth = json.loads((DATA_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    route = next(e for e in ground_truth if e["label"] == "route_deviation")
    no_show = next(e for e in ground_truth if e["label"] == "driver_no_show")

    profiler.reset()
    overall = time.perf_counter()
    await resolve_dispute(route["dispute_id"])
    await resolve_dispute(no_show["dispute_id"])
    total = time.perf_counter() - overall

    snapshot = profiler.snapshot()
    print(format_table(snapshot))
    print(f"\noverall wall-clock: {total:.3f}s for 2 disputes ({route['dispute_id']}, {no_show['dispute_id']})")

    ranked = sorted(snapshot, key=lambda item: item[1].seconds, reverse=True)
    print("\ntop contributors by seconds:")
    for name, stats in ranked[:3]:
        print(f"  {name}: {stats.seconds:.3f}s ({stats.calls} calls)")

    print("\naverage policy-text tokens injected per agent (estimated, chars/4):")
    for agent, avg in profiler.policy_token_averages().items():
        print(f"  {agent}: {avg:.0f}")


if __name__ == "__main__":
    asyncio.run(main())
