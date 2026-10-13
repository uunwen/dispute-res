from types import SimpleNamespace

from sqlalchemy import select

from app.agents import AgentContext, RiderAdvocate
from app.agents.base import validate_case_brief
from app.agents.prompts import load_prompt
from app.db import models
from app.db.session import async_session_factory
from app.llm.client import ChatResult, LLMClient, ToolCall
from app.schemas.case_brief import CaseBrief, CaseClaim
from app.schemas.evidence import EvidenceItem


def test_validate_case_brief_strips_invalid_ids():
    brief = CaseBrief(
        position="rider",
        argument_summary="x",
        requested_outcome="refund",
        claims=[
            CaseClaim(
                text="c1",
                evidence_ids=["a:1", "ghost:99"],
                policy_section_ids=["route_deviation#1"],
            ),
            CaseClaim(text="c2", evidence_ids=["ghost:99"], policy_section_ids=[]),
        ],
    )
    result = validate_case_brief(brief, {"a:1"})
    assert len(result.claims) == 1
    assert result.claims[0].evidence_ids == ["a:1"]


def test_load_prompts():
    rider = load_prompt("rider_advocate")
    driver = load_prompt("driver_advocate")
    assert "Rider" in rider
    assert "Driver" in driver
    assert rider != driver
    assert "evidence" in rider


async def test_gather_evidence_executes_tool_calls(monkeypatch):
    evidence = EvidenceItem(
        id="route_deviation:1",
        type="route_deviation",
        trip_id=1,
        summary="deviation",
        data={},
        supports="rider",
        strength=0.9,
    )
    called = {"n": 0}

    async def fake_tool(trip_id=1):
        called["n"] += 1
        return evidence

    class FakeRegistry:
        def tool_specs(self):
            return []

        def get_tool(self, name):
            return SimpleNamespace(name=name, func=fake_tool)

    class FakeLLM:
        def __init__(self):
            self.results = iter(
                [
                    ChatResult(
                        content=None,
                        tool_calls=[ToolCall(id="c1", name="analyze_route_deviation", arguments={"trip_id": 1})],
                    ),
                    ChatResult(content="done", tool_calls=[]),
                ]
            )

        async def chat(self, messages, *, tools=None, tool_choice="auto", temperature=None, role="tools"):
            try:
                return next(self.results)
            except StopIteration:
                return ChatResult(content="done", tool_calls=[])

    monkeypatch.setattr("app.agents.base.llm_client", FakeLLM())
    monkeypatch.setattr("app.agents.base.registry", FakeRegistry())

    agent = RiderAdvocate()
    ctx = AgentContext(dispute_id=1, trip_id=1, category="route_deviation", claim_text="deviation")
    evidence_items, calls = await agent._gather_evidence(ctx, [], None, None)

    assert called["n"] == 1
    assert calls == 1
    assert len(evidence_items) == 1
    assert evidence_items[0].id == "route_deviation:1"


async def test_agent_run_persists_message(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr("app.agents.base.llm_client", LLMClient(mock=True))

    async def fake_retrieve(query, category=None, k=4, session=None):
        return [{"source": category or "route_deviation", "section": "1", "text": "policy text", "similarity": 0.9}]

    monkeypatch.setattr("app.agents.base.retrieve_policy", fake_retrieve)

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    ctx = AgentContext(
        dispute_id=entry["dispute_id"],
        trip_id=entry["trip_id"],
        category="route_deviation",
        claim_text="driver deviated from the route",
    )

    message = await RiderAdvocate().run(ctx)

    assert message.id is not None
    assert message.sender == "RiderAdvocate"
    assert message.message_type == "case_brief"
    assert "brief" in message.content
    assert "evidence_ids" in message.content

    async with async_session_factory() as session:
        saved = (
            await session.execute(select(models.AgentMessage).where(models.AgentMessage.id == message.id))
        ).scalar_one_or_none()
    assert saved is not None
    assert saved.sender == "RiderAdvocate"
