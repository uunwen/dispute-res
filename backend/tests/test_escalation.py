from sqlalchemy import delete, select

from app.agents.judge import Judge, JudgeContext
from app.config import settings
from app.db import models
from app.db.enums import DisputeCategory
from app.db.session import async_session_factory
from app.rules.models import RuleResult
from app.schemas.case_brief import CaseBrief
from app.schemas.evidence import EvidenceItem
from app.schemas.ruling import LLMRuling


class _FakeLLM:
    def __init__(self, ruling):
        self.ruling = ruling

    async def structured(self, system, user, schema, role="judge"):
        return self.ruling


def _brief(position):
    return CaseBrief(position=position, argument_summary=f"{position} argument", requested_outcome="no_action")


def _context(dispute_id, trip_id, category, rule, evidence=None, rider_history=None, driver_history=None):
    return JudgeContext(
        dispute_id=dispute_id,
        trip_id=trip_id,
        category=category,
        claim_text="test claim",
        rider_brief=_brief("rider"),
        driver_brief=_brief("driver"),
        evidence=evidence or [],
        rider_history=rider_history,
        driver_history=driver_history,
        rule_result=rule,
    )


async def _route_entry(ground_truth, index):
    entries = [e for e in ground_truth if e["label"] == "route_deviation"]
    return entries[index]


async def _dispute_status(dispute_id):
    async with async_session_factory() as session:
        d = await session.get(models.Dispute, dispute_id)
        return d.status if d else None


async def _escalation_messages(dispute_id):
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(models.AgentMessage).where(
                    models.AgentMessage.dispute_id == dispute_id,
                    models.AgentMessage.message_type == "escalation",
                )
            )
        ).scalars().all()
        return rows


async def _create_safety_dispute(trip_id):
    async with async_session_factory() as session:
        d = models.Dispute(
            trip_id=trip_id,
            filed_by=1,
            category=DisputeCategory.safety_incident,
            claim_text="rider was threatened",
            status="open",
            priority="high",
        )
        session.add(d)
        await session.commit()
        await session.refresh(d)
        return d.id


async def _cleanup_dispute(dispute_id):
    async with async_session_factory() as session:
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id))
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id))
        await session.execute(delete(models.Dispute).where(models.Dispute.id == dispute_id))
        await session.commit()


async def test_low_confidence_escalates(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="no_action", refund_amount=0.0, reasoning="disagree")),
    )
    entry = await _route_entry(ground_truth, 0)
    rule = RuleResult(outcome="full_refund", refund_amount=6.0, matched_rule_ids=["r"], explanation="")
    ctx = _context(entry["dispute_id"], entry["trip_id"], "route_deviation", rule)

    ruling = await Judge().run(ctx)

    assert ruling.escalated is True
    assert ruling.human_review_summary is not None
    assert "low_confidence" in ruling.human_review_summary["escalation_reason"]
    assert await _dispute_status(entry["dispute_id"]) == "needs_human_review"
    assert len(await _escalation_messages(entry["dispute_id"])) >= 1


async def test_high_confidence_does_not_escalate(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="partial_refund", refund_amount=5.0, deciding_evidence_ids=["e1"], reasoning="agree")),
    )
    entry = await _route_entry(ground_truth, 1)
    rule = RuleResult(outcome="partial_refund", refund_amount=5.0, matched_rule_ids=["r"], explanation="")
    evidence = [EvidenceItem(id="e1", type="route_deviation", trip_id=entry["trip_id"], summary="dev", data={}, supports="rider", strength=1.0)]
    ctx = _context(
        entry["dispute_id"],
        entry["trip_id"],
        "route_deviation",
        rule,
        evidence=evidence,
        rider_history={"abuse_risk_score": 1.0},
        driver_history={"abuse_risk_score": 1.0},
    )

    ruling = await Judge().run(ctx)

    assert ruling.escalated is False
    assert ruling.human_review_summary is None
    assert await _dispute_status(entry["dispute_id"]) == "resolved"
    assert await _escalation_messages(entry["dispute_id"]) == []


async def test_safety_incident_always_escalates(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="no_action", refund_amount=0.0, reasoning="agree")),
    )
    entry = await _route_entry(ground_truth, 2)
    dispute_id = await _create_safety_dispute(entry["trip_id"])
    try:
        rule = RuleResult(outcome="no_action", refund_amount=0.0, matched_rule_ids=[], explanation="")
        ctx = _context(dispute_id, entry["trip_id"], "safety_incident", rule)

        ruling = await Judge().run(ctx)

        assert ruling.escalated is True
        assert "safety_incident" in ruling.human_review_summary["escalation_reason"]
        assert await _dispute_status(dispute_id) == "needs_human_review"
        assert len(await _escalation_messages(dispute_id)) >= 1
    finally:
        await _cleanup_dispute(dispute_id)


async def test_escalation_disabled_never_escalates(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(settings, "escalation_enabled", False)
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="no_action", refund_amount=0.0, reasoning="disagree")),
    )
    entry = await _route_entry(ground_truth, 3)
    rule = RuleResult(outcome="full_refund", refund_amount=6.0, matched_rule_ids=["r"], explanation="")
    ctx = _context(entry["dispute_id"], entry["trip_id"], "route_deviation", rule)

    ruling = await Judge().run(ctx)

    assert ruling.escalated is False
    assert ruling.human_review_summary is None
    assert await _dispute_status(entry["dispute_id"]) == "resolved"
