from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.evidence import chat, case_facts, fare, history, noshow, route


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Awaitable[Any]]


def _trip_parameters():
    return {
        "type": "object",
        "properties": {"trip_id": {"type": "integer"}},
        "required": ["trip_id"],
    }


def _account_parameters():
    return {
        "type": "object",
        "properties": {"account_id": {"type": "integer"}},
        "required": ["account_id"],
    }


TOOLS: dict[str, Tool] = {
    "analyze_route_deviation": Tool(
        name="analyze_route_deviation",
        description="Compare GPS fixes against the optimal route and flag bad-faith deviations.",
        parameters=_trip_parameters(),
        func=route.analyze_route_deviation,
    ),
    "validate_fare": Tool(
        name="validate_fare",
        description="Recompute the expected fare and report any discrepancy vs the charged amount.",
        parameters=_trip_parameters(),
        func=fare.validate_fare,
    ),
    "analyze_noshow": Tool(
        name="analyze_noshow",
        description="Determine driver/rider no-show and whether a cancellation fee is valid.",
        parameters=_trip_parameters(),
        func=noshow.analyze_noshow,
    ),
    "compute_history_profile": Tool(
        name="compute_history_profile",
        description="Compute an account's dispute count, win rate and abuse-risk score.",
        parameters=_account_parameters(),
        func=history.compute_history_profile_db,
    ),
    "analyze_chat": Tool(
        name="analyze_chat",
        description="Extract threats, admissions and sentiment from the trip chat log.",
        parameters=_trip_parameters(),
        func=chat.analyze_chat,
    ),
    "analyze_case_facts": Tool(
        name="analyze_case_facts",
        description="Extract deterministic case facts (contact attempts, wait, surge notification, deviation notification) from the trip's raw case.",
        parameters=_trip_parameters(),
        func=case_facts.analyze_case_facts,
    ),
}


def get_tool(name: str) -> Tool | None:
    return TOOLS.get(name)


def tool_specs() -> list[dict[str, Any]]:
    """Return OpenAI-style function tool specs for LLM tool calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOLS.values()
    ]
