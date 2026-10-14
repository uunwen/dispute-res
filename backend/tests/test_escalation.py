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


def _context(dispute_id, trip_id, category, rule, evidence=None, rider_history=None, driver_history=None,
             amount=20.0, fraud_flags=0, claim_text="test claim"):
    return JudgeContext(
        dispute_id=dispute_id,
        trip_id=trip_id,
        category=category,
        claim_text=claim_text,
        rider_brief=_brief("rider"),
        driver_brief=_brief("driver"),
        evidence=evidence or [],
        rider_history=rider_history,
        driver_history=driver_history,
        rule_result=rule,
        dispute_amount=amount,
        fraud_flags=fraud_flags,
    )


def _route_entry(ground_truth, index):
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


# --- Sec 6 threshold logic (tested directly against _should_escalate) ---


def _decision(confidence=0.9, disagreement=False):
    return {"confidence": confidence, "disagreement": disagreement}


def _judge_ctx(**kwargs):
    return _context(1, 1, kwargs.pop("category", "route_deviation"),
                    RuleResult(outcome="no_action", refund_amount=0.0, matched_rule_ids=[], explanation=""),
                    **kwargs)


def test_under_10_final_at_any_confidence():
    judge = Judge()
    escalated, _ = judge._should_escalate(
        _judge_ctx(category="fare_dispute", amount=5.0), _decision(confidence=0.05)
    )
    assert escalated is False


def test_route_deviation_confidence_applies_under_10():
    judge = Judge()
    escalated, reason = judge._should_escalate(_judge_ctx(amount=5.0), _decision(confidence=0.50))
    assert escalated is True
    assert "low_confidence" in reason


def test_mid_band_low_confidence_escalates():
    judge = Judge()
    escalated, reason = judge._should_escalate(_judge_ctx(amount=20.0), _decision(confidence=0.50))
    assert escalated is True
    assert "low_confidence" in reason


def test_mid_band_high_confidence_does_not_escalate():
    judge = Judge()
    escalated, _ = judge._should_escalate(_judge_ctx(amount=20.0), _decision(confidence=0.90))
    assert escalated is False


def test_over_50_always_escalates():
    judge = Judge()
    escalated, reason = judge._should_escalate(_judge_ctx(amount=60.0), _decision(confidence=0.99))
    assert escalated is True
    assert "amount_over_50" in reason


def test_fraud_flag_raises_threshold():
    judge = Judge()
    escalated, reason = judge._should_escalate(_judge_ctx(amount=20.0, fraud_flags=1), _decision(confidence=0.90))
    assert escalated is True
    assert "low_confidence" in reason
    escalated2, _ = judge._should_escalate(_judge_ctx(amount=20.0, fraud_flags=1), _decision(confidence=0.96))
    assert escalated2 is False


def test_fraud_flag_applies_even_under_10():
    judge = Judge()
    escalated, _ = judge._should_escalate(_judge_ctx(amount=5.0, fraud_flags=1), _decision(confidence=0.90))
    assert escalated is True


def test_route_deviation_over_2km_escalates():
    judge = Judge()
    evidence = [EvidenceItem(id="e1", type="case_facts", trip_id=1, summary="s",
                             data={"deviation_km": 3.0}, supports="neutral", strength=1.0)]
    escalated, reason = judge._should_escalate(_judge_ctx(amount=5.0, evidence=evidence), _decision(confidence=0.99))
    assert escalated is True
    assert "route_deviation_over_2km" in reason


def test_safety_category_always_escalates():
    judge = Judge()
    escalated, reason = judge._should_escalate(_judge_ctx(category="safety_incident", amount=5.0), _decision(confidence=0.99))
    assert escalated is True
    assert "safety" in reason


def test_safety_keyword_escalates_regardless_of_category():
    judge = Judge()
    escalated, reason = judge._should_escalate(
        _judge_ctx(category="no_show", amount=5.0, claim_text="the driver threatened me"), _decision(confidence=0.99)
    )
    assert escalated is True
    assert "safety" in reason


def test_escalation_disabled_never_escalates(monkeypatch):
    monkeypatch.setattr(settings, "escalation_enabled", False)
    judge = Judge()
    escalated, _ = judge._should_escalate(_judge_ctx(amount=60.0), _decision(confidence=0.99))
    assert escalated is False


# --- Safety escalation produces a case file only (Sec 5.2) ---


async def test_safety_incident_always_escalates(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="no_action", refund_amount=0.0, reasoning="agree")),
    )
    entry = _route_entry(ground_truth, 0)
    dispute_id = await _create_safety_dispute(entry["trip_id"])
    try:
        rule = RuleResult(outcome="no_action", refund_amount=0.0, matched_rule_ids=[], explanation="")
        ctx = _context(dispute_id, entry["trip_id"], "safety_incident", rule)
        ruling = await Judge().run(ctx)
        assert ruling.escalated is True
        assert "safety" in ruling.human_review_summary["escalation_reason"]
        assert await _dispute_status(dispute_id) == "needs_human_review"
        assert len(await _escalation_messages(dispute_id)) >= 1
    finally:
        await _cleanup_dispute(dispute_id)


async def test_safety_escalation_has_no_outcome_or_refund(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="full_refund", refund_amount=10.0, reasoning="agree")),
    )
    entry = _route_entry(ground_truth, 1)
    dispute_id = await _create_safety_dispute(entry["trip_id"])
    try:
        rule = RuleResult(outcome="full_refund", refund_amount=10.0, matched_rule_ids=["r"], explanation="")
        ctx = _context(dispute_id, entry["trip_id"], "safety_incident", rule)
        ruling = await Judge().run(ctx)
        assert ruling.escalated is True
        assert ruling.outcome.value == "no_refund"
        assert ruling.refund_amount == 0.0
        assert ruling.human_review_summary["recommended_action"] == ""
        assert "No automated ruling" in ruling.human_review_summary["ruling"]
    finally:
        await _cleanup_dispute(dispute_id)


async def test_high_confidence_mid_band_does_not_escalate(seeded_session, ground_truth, monkeypatch):
    monkeypatch.setattr(
        "app.agents.judge.llm_client",
        _FakeLLM(LLMRuling(outcome="partial_refund", refund_amount=5.0, deciding_evidence_ids=["e1"], reasoning="agree")),
    )
    entry = _route_entry(ground_truth, 2)
    rule = RuleResult(outcome="partial_refund", refund_amount=5.0, matched_rule_ids=["r"], explanation="")
    evidence = [EvidenceItem(id="e1", type="route_deviation", trip_id=entry["trip_id"], summary="dev",
                             data={"deviation_km": 1.0}, supports="rider", strength=1.0)]
    ctx = _context(entry["dispute_id"], entry["trip_id"], "route_deviation", rule, evidence=evidence,
                   rider_history={"abuse_risk_score": 0.0}, driver_history={"abuse_risk_score": 0.0},
                   amount=20.0)
    ruling = await Judge().run(ctx)
    assert ruling.escalated is False
    assert ruling.human_review_summary is None
    assert await _dispute_status(entry["dispute_id"]) == "resolved"
