import contextvars
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class StageStats:
    seconds: float = 0.0
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Profiler:
    def __init__(self) -> None:
        self._stages: dict[str, StageStats] = {}
        self._order: list[str] = []
        self._policy_tokens: dict[str, list[int]] = {}

    def record(
        self,
        stage: str,
        seconds: float,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        calls: int = 1,
    ) -> None:
        stats = self._stages.get(stage)
        if stats is None:
            stats = StageStats()
            self._stages[stage] = stats
            self._order.append(stage)
        stats.seconds += seconds
        stats.calls += calls
        stats.prompt_tokens += prompt_tokens
        stats.completion_tokens += completion_tokens

    def record_policy_tokens(self, agent: str, tokens: int) -> None:
        self._policy_tokens.setdefault(agent, []).append(tokens)

    def policy_token_averages(self) -> dict[str, float]:
        return {
            agent: sum(vals) / len(vals)
            for agent, vals in self._policy_tokens.items()
            if vals
        }

    def reset(self) -> None:
        self._stages.clear()
        self._order.clear()
        self._policy_tokens.clear()

    def snapshot(self) -> list[tuple[str, StageStats]]:
        return [(name, self._stages[name]) for name in self._order]


profiler = Profiler()

# The LLM client reads this to attribute a call to the stage set by the caller
# (e.g. "llm_advocate_rebuttal") without changing the public chat/structured API.
current_stage: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_stage", default=None
)


@asynccontextmanager
async def stage_scope(stage: str):
    token = current_stage.set(stage)
    try:
        yield
    finally:
        current_stage.reset(token)


def estimate_tokens(text: str) -> int:
    """Rough token estimate for reporting (approx 4 chars/token)."""
    return max(1, len(text) // 4)


class Timer:
    """Measure wall-clock time for a synchronous or awaited block."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self._start = time.perf_counter()

    def stop(self, *, prompt_tokens: int = 0, completion_tokens: int = 0, calls: int = 1) -> None:
        profiler.record(
            self.stage,
            time.perf_counter() - self._start,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            calls=calls,
        )


def format_table(snapshot: list[tuple[str, StageStats]]) -> str:
    rows = [
        ("stage", "seconds", "calls", "prompt_tokens", "completion_tokens"),
    ]
    for name, stats in snapshot:
        rows.append(
            (
                name,
                f"{stats.seconds:.3f}",
                str(stats.calls),
                str(stats.prompt_tokens),
                str(stats.completion_tokens),
            )
        )

    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    lines = []
    for i, row in enumerate(rows):
        line = "  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row))
        lines.append(line)
        if i == 0:
            lines.append("  ".join("-" * widths[j] for j in range(5)))
    return "\n".join(lines)
