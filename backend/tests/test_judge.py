from app.agents.judge import Judge, JudgeContext, compute_confidence, reconcile
from app.rules.models import RuleResult
from app.schemas.case_brief import CaseBrief
from app.schemas.evidence import EvidenceItem
from app.schemas.ruling import LLMRuling, RejectedClaim


def _rule(outcome="partial_refund", amount=5.0):
    return RuleResult(outcome=outcome, refund_amount=amount, matched_rule_ids=["r1"], explanation="")


def _brief(position):
    return CaseBrief(position=position, argument_summary="x", requested_outcome="refund")


def test_reconcile_llm_cannot_exceed_rule_amount():
    final = reconcile(_rule("partial_refund", 2.0), LLMRuling(outcome="full_refund", refund_amount=10.0))
    assert final["amount"] == 2.0
    assert final["outcome"] == "partial_refund"
    assert final["disagreement"] is True
    assert final["amount_clamped"] is True


def test_reconcile_llm_reduces_within_bounds():
    final = reconcile(_rule("full_refund", 6.0), LLMRuling(outcome="partial_refund", refund_amount=3.0))
    assert final["amount"] == 3.0
    assert final["outcome"] == "partial_refund"
    assert final["disagreement"] is True


def test_reconcile_no_action_is_a_floor():
    final = reconcile(_rule("no_action", 0.0), LLMRuling(outcome="full_refund", refund_amount=6.0))
    assert final["amount"] == 0.0
    assert final["outcome"] == "no_action"
    assert final["disagreement"] is True


def test_reconcile_agreement():
    final = reconcile(_rule("partial_refund", 5.0), LLMRuling(outcome="partial_refund", refund_amount=5.0))
    assert final["amount"] == 5.0
    assert final["outcome"] == "partial_refund"
    assert final["disagreement"] is False


def test_compute_confidence_formula():
    assert compute_confidence(1.0, 0.5, 1.0, 0.4) == 0.76
    assert compute_confidence(0.0, 0.0, 0.0, 0.0) == 0.0
    assert compute_confidence(1.0, 1.0, 1.0, 1.0) == 1.0
    assert 0.0 <= compute_confidence(1.0, 0.7, 0.3, 0.9) <= 1.0


class _FakeLLM:
    def __init__(self, ruling):
        self.ruling = ruling

    async def structured(self, system, user, schema, role="judge"):
        return self.ruling


def _context(**overrides):
    defaults = dict(
        dispute_id=1,
        trip_id=1,
        category="route_deviation",
        claim_text="driver deviated",
        rider_brief=_brief("rider"),
        driver_brief=_brief("driver"),
        rule_result=_rule("partial_refund", 5.0),
    )
    defaults.update(overrides)
    return JudgeContext(**defaults)


async def test_ruling_unchanged_when_tone_or_age_band_changes(monkeypatch):
    ruling = LLMRuling(outcome="partial_refund", refund_amount=3.0, reasoning="reduced refund")
    monkeypatch.setattr("app.agents.judge.llm_client", _FakeLLM(ruling))

    judge = Judge()
    empathetic = await judge.decide(_context(tone="empathetic", age_band="18-24"))
    neutral = await judge.decide(_context(tone="neutral", age_band=None))
    senior = await judge.decide(_context(tone="empathetic", age_band="55+"))

    for decision in (empathetic, neutral, senior):
        assert decision["outcome"] == "partial_refund"
        assert decision["amount"] == 3.0
        assert decision["confidence"] == empathetic["confidence"]

    assert empathetic["rider_explanation"] != neutral["rider_explanation"]
    assert empathetic["rider_explanation"] != senior["rider_explanation"]


async def test_decide_flags_disagreement_and_rejects_hallucinated_ids(monkeypatch):
    ruling = LLMRuling(
        outcome="full_refund",
        refund_amount=50.0,
        reasoning="rider should get everything",
        deciding_evidence_ids=["route_deviation:1", "ghost:999"],
        deciding_policy_sections=["route_deviation#4"],
        rejected_claims=[RejectedClaim(advocate="driver", claim_text="no deviation", reason="contradicted by evidence")],
    )
    monkeypatch.setattr("app.agents.judge.llm_client", _FakeLLM(ruling))

    evidence = [
        EvidenceItem(id="route_deviation:1", type="route_deviation", trip_id=1, summary="dev", data={}, supports="rider", strength=0.9)
    ]
    decision = await Judge().decide(_context(rule_result=_rule("partial_refund", 5.0), evidence=evidence))
    assert decision["amount"] == 5.0  # capped at rule amount
    assert decision["disagreement"] is True
    assert decision["deciding_evidence_ids"] == ["route_deviation:1"]  # hallucinated id stripped
    assert decision["rejected_claims"][0]["advocate"] == "driver"


async def test_run_persists_ruling(seeded_session, ground_truth, monkeypatch):
    from sqlalchemy import select

    from app.db import models
    from app.db.session import async_session_factory

    ruling = LLMRuling(
        outcome="partial_refund", refund_amount=3.0, reasoning="reduced refund", deciding_evidence_ids=["e1"]
    )
    monkeypatch.setattr("app.agents.judge.llm_client", _FakeLLM(ruling))

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    ctx = JudgeContext(
        dispute_id=entry["dispute_id"],
        trip_id=entry["trip_id"],
        category="route_deviation",
        claim_text="driver deviated",
        rider_brief=_brief("rider"),
        driver_brief=_brief("driver"),
        evidence=[
            EvidenceItem(
                id="e1", type="route_deviation", trip_id=entry["trip_id"], summary="dev", data={}, supports="rider", strength=1.0
            )
        ],
        rider_history={"abuse_risk_score": 1.0},
        driver_history={"abuse_risk_score": 1.0},
        rule_result=_rule("partial_refund", 5.0),
        tone="empathetic",
    )
    saved = await Judge().run(ctx)

    assert saved.id is not None
    assert saved.outcome.value == "partial_refund"
    assert saved.refund_amount == 3.0
    assert saved.escalated is False
    assert saved.human_review_summary is None
    assert saved.llm_degraded is False
    assert saved.model_info is not None
    assert saved.model_info["judge"]
    assert saved.model_info["advocate"]
    assert saved.model_info["tools"]

    async with async_session_factory() as session:
        row = (
            await session.execute(select(models.Ruling).where(models.Ruling.id == saved.id))
        ).scalar_one_or_none()
    assert row is not None
    assert row.dispute_id == entry["dispute_id"]
    assert "rider_explanation" in row.rule_outcome


async def test_llm_degraded_flag(seeded_session, ground_truth, monkeypatch):
    class DegradedLLM:
        degraded = True
        error_info = {"class": "HTTPStatusError", "status": 429}

        async def structured(self, system, user, schema, role="judge"):
            raise RuntimeError("llm down")

    monkeypatch.setattr("app.agents.judge.llm_client", DegradedLLM())

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    ctx = _context(dispute_id=entry["dispute_id"], trip_id=entry["trip_id"])
    saved = await Judge().run(ctx)
    assert saved.llm_degraded is True
    assert saved.model_info["error"] == {"class": "HTTPStatusError", "status": 429}
