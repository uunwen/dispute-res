import json
import logging
from dataclasses import dataclass, field

from app.agents.base import _format_evidence, _format_policy
from app.agents.prompts import load_prompt
from app.config import settings
from app.db import models
from app.db.enums import RulingOutcome
from app.db.session import async_session_factory
from app.llm.client import client as llm_client, model_for_role
from app.messaging import dispute_channel, publish_message
from app.profiling import estimate_tokens, profiler, stage_scope
from app.rules.engine import evaluate
from app.rules.models import RuleResult
from app.schemas.case_brief import CaseBrief
from app.schemas.evidence import EvidenceItem
from app.schemas.fraud import FraudSignal
from app.schemas.ruling import HumanReviewSummary, LLMRuling

logger = logging.getLogger(__name__)

_OUTCOME_TO_RULING = {
    "no_action": RulingOutcome.no_refund,
    "partial_refund": RulingOutcome.partial_refund,
    "full_refund": RulingOutcome.full_refund,
}

_VALID_OUTCOMES = {"no_action", "partial_refund", "full_refund"}

_AGE_HINTS = {
    "18-24": "We know a timely resolution matters to you.",
    "55+": "We took extra care reviewing every detail.",
}


@dataclass
class JudgeContext:
    dispute_id: int
    trip_id: int
    category: str
    claim_text: str
    rider_brief: CaseBrief
    driver_brief: CaseBrief
    evidence: list[EvidenceItem] = field(default_factory=list)
    policy: list[dict] = field(default_factory=list)
    rider_history: dict | None = None
    driver_history: dict | None = None
    fraud_signal: FraudSignal | None = None
    rule_result: RuleResult | None = None
    tone: str = "neutral"
    age_band: str | None = None


def reconcile(rule_result: RuleResult, llm_ruling: LLMRuling) -> dict:
    """Reconcile the LLM ruling against the deterministic rule result.

    The rule amount is the ceiling: the LLM may reduce the refund but never exceed
    it. The final amount is ``min(rule_amount, max(llm_amount, 0))`` and the final
    outcome is derived from the final amount. A disagreement is flagged when the
    LLM's outcome differs from the rule's outcome.
    """
    rule_amount = rule_result.refund_amount
    llm_amount = llm_ruling.refund_amount

    final_amount = round(min(rule_amount, max(llm_amount, 0.0)), 2)

    if final_amount <= 0.0:
        final_outcome = "no_action"
    elif final_amount >= rule_amount - 0.01 and rule_result.outcome == "full_refund":
        final_outcome = "full_refund"
    else:
        final_outcome = "partial_refund"

    return {
        "outcome": final_outcome,
        "amount": final_amount,
        "disagreement": llm_ruling.outcome != rule_result.outcome,
        "amount_clamped": llm_amount > rule_amount + 0.01,
    }


def compute_confidence(agreement: float, evidence_strength: float, citation_validity: float, history_risk: float) -> float:
    """Documented confidence formula (not LLM self-reported).

    confidence = 0.35 * agreement
               + 0.30 * evidence_strength
               + 0.20 * citation_validity
               + 0.15 * history_risk

    All components are in [0, 1]. ``agreement`` is 1.0 when the LLM and rules
    agree on the outcome (0.3 otherwise). ``evidence_strength`` is the mean
    strength of the cited evidence. ``citation_validity`` is the fraction of cited
    evidence ids that actually exist. ``history_risk`` is the maximum abuse-risk
    score across the two parties.
    """
    value = (
        0.35 * agreement
        + 0.30 * evidence_strength
        + 0.20 * citation_validity
        + 0.15 * history_risk
    )
    return round(min(max(value, 0.0), 1.0), 3)


def _evidence_strength(evidence: list[EvidenceItem], cited_ids: list[str]) -> float:
    by_id = {e.id: e for e in evidence}
    strengths = [by_id[i].strength for i in cited_ids if i in by_id]
    return sum(strengths) / len(strengths) if strengths else 0.0


def _citation_validity(evidence: list[EvidenceItem], cited_ids: list[str]) -> float:
    if not cited_ids:
        return 0.0
    valid_ids = {e.id for e in evidence}
    valid = sum(1 for i in cited_ids if i in valid_ids)
    return valid / len(cited_ids)


def _history_risk(rider_history: dict | None, driver_history: dict | None) -> float:
    rider = (rider_history or {}).get("abuse_risk_score", 0.0)
    driver = (driver_history or {}).get("abuse_risk_score", 0.0)
    return max(rider, driver)


class Judge:
    name = "Judge"

    async def decide(self, context: JudgeContext) -> dict:
        rule_result = context.rule_result or evaluate(context.category, context.evidence)
        llm_ruling = await self._call_llm(context, rule_result)

        final = reconcile(rule_result, llm_ruling)

        valid_ids = {e.id for e in context.evidence}
        deciding_ids = [i for i in llm_ruling.deciding_evidence_ids if i in valid_ids]

        agreement = 1.0 if not final["disagreement"] else 0.3
        ev_strength = _evidence_strength(context.evidence, deciding_ids)
        citation = _citation_validity(context.evidence, llm_ruling.deciding_evidence_ids)
        history = _history_risk(context.rider_history, context.driver_history)
        confidence = compute_confidence(agreement, ev_strength, citation, history)
        fraud_penalty = self._fraud_penalty(final["outcome"], context.fraud_signal)
        confidence = round(min(max(confidence - fraud_penalty, 0.0), 1.0), 3)

        rider_explanation = self._explanation("rider", final, context.tone, context.age_band)
        driver_explanation = self._explanation("driver", final, context.tone, context.age_band)

        return {
            "outcome": final["outcome"],
            "amount": final["amount"],
            "confidence": confidence,
            "reasoning": llm_ruling.reasoning,
            "disagreement": final["disagreement"],
            "deciding_evidence_ids": deciding_ids,
            "deciding_policy_sections": llm_ruling.deciding_policy_sections,
            "rejected_claims": [rc.model_dump() for rc in llm_ruling.rejected_claims],
            "rider_explanation": rider_explanation,
            "driver_explanation": driver_explanation,
            "confidence_components": {
                "agreement": round(agreement, 3),
                "evidence_strength": round(ev_strength, 3),
                "citation_validity": round(citation, 3),
                "history_risk": round(history, 3),
                "fraud_penalty": round(fraud_penalty, 3),
            },
            "rule": {
                "outcome": rule_result.outcome,
                "refund_amount": rule_result.refund_amount,
                "matched_rule_ids": rule_result.matched_rule_ids,
            },
            "llm": {"outcome": llm_ruling.outcome, "refund_amount": llm_ruling.refund_amount},
        }

    async def run(self, context: JudgeContext) -> models.Ruling:
        decision = await self.decide(context)
        escalate, reason = self._should_escalate(context, decision)
        summary = self._build_human_review_summary(context, decision, reason) if escalate else None
        return await self._persist(context, decision, escalate, summary)

    async def _call_llm(self, context: JudgeContext, rule_result: RuleResult) -> LLMRuling:
        system = load_prompt("judge")
        user = self._ruling_user_message(context, rule_result)
        try:
            async with stage_scope("llm_judge"):
                ruling = await llm_client.structured(system, user, LLMRuling, role="judge")
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM ruling failed: %s", exc)
            ruling = None

        if ruling is None or ruling.outcome not in _VALID_OUTCOMES:
            ruling = LLMRuling(
                outcome=rule_result.outcome,
                refund_amount=rule_result.refund_amount,
                reasoning="LLM unavailable or returned an unrecognized outcome; "
                "falling back to the rule-based outcome.",
            )
        return ruling

    async def _persist(
        self, context: JudgeContext, decision: dict, escalate: bool, summary: HumanReviewSummary | None
    ) -> models.Ruling:
        summary_dict = summary.model_dump(mode="json") if summary is not None else None
        model_info = {
            "advocate": model_for_role("advocate"),
            "judge": model_for_role("judge"),
            "tools": model_for_role("tools"),
        }
        error_info = getattr(llm_client, "error_info", None)
        if error_info:
            model_info["error"] = error_info
        async with async_session_factory() as session:
            ruling = models.Ruling(
                dispute_id=context.dispute_id,
                outcome=_OUTCOME_TO_RULING[decision["outcome"]],
                refund_amount=decision["amount"],
                confidence=decision["confidence"],
                reasoning=decision["reasoning"],
                rule_outcome={
                    "rule": decision["rule"],
                    "llm": decision["llm"],
                    "disagreement": decision["disagreement"],
                    "deciding_evidence_ids": decision["deciding_evidence_ids"],
                    "deciding_policy_sections": decision["deciding_policy_sections"],
                    "rejected_claims": decision["rejected_claims"],
                    "rider_explanation": decision["rider_explanation"],
                    "driver_explanation": decision["driver_explanation"],
                    "tone": context.tone,
                    "confidence_components": decision["confidence_components"],
                },
                evidence_ids=decision["deciding_evidence_ids"],
                escalated=escalate,
                human_review_summary=summary_dict,
                llm_degraded=getattr(llm_client, "degraded", False),
                model_info=model_info,
            )
            session.add(ruling)

            dispute = await session.get(models.Dispute, context.dispute_id)
            if dispute is not None:
                dispute.status = "needs_human_review" if escalate else "resolved"

            escalation_message = None
            if escalate and summary_dict is not None:
                escalation_message = models.AgentMessage(
                    dispute_id=context.dispute_id,
                    sender="Judge",
                    recipient="HumanReviewer",
                    message_type="escalation",
                    content=summary_dict,
                )
                session.add(escalation_message)

            await session.commit()
            await session.refresh(ruling)
            if escalation_message is not None:
                await session.refresh(escalation_message)

        if escalate and escalation_message is not None:
            await publish_message(
                dispute_channel(context.dispute_id),
                {
                    "id": escalation_message.id,
                    "dispute_id": context.dispute_id,
                    "type": "agent_message",
                    "sender": "Judge",
                    "recipient": "HumanReviewer",
                    "message_type": "escalation",
                    "content": summary_dict,
                    "created_at": escalation_message.created_at.isoformat()
                    if escalation_message.created_at
                    else None,
                },
            )

        return ruling

    def _should_escalate(self, context: JudgeContext, decision: dict) -> tuple[bool, str | None]:
        if not settings.escalation_enabled:
            return False, None
        reasons = []
        if context.category == "safety_incident":
            reasons.append("safety_incident")
        if context.category == "route_deviation":
            for e in context.evidence:
                ek = e.data.get("extra_distance_km")
                if ek is not None and ek > settings.route_escalate_km:
                    reasons.append("route_deviation_over_2km")
                    break
        if decision["disagreement"]:
            reasons.append("rule_llm_disagreement")
        if decision["confidence"] < settings.escalation_threshold:
            reasons.append("low_confidence")
        if reasons:
            return True, ", ".join(reasons)
        return False, None

    def _fraud_penalty(self, outcome: str, signal: FraudSignal | None) -> float:
        """Reduce confidence when the favored side has a high fraud risk.

        The fraud signal is advisory only: it never changes the outcome, but it
        lowers confidence when the side being favored (rider for refunds, driver
        for no_action) has risk at or above ``fraud_penalty_threshold``.
        """
        if signal is None:
            return 0.0
        favored = "rider" if outcome in ("full_refund", "partial_refund") else "driver"
        risk = signal.rider_risk if favored == "rider" else signal.driver_risk
        if risk >= settings.fraud_penalty_threshold:
            return round(settings.fraud_penalty_weight * risk, 3)
        return 0.0

    def _build_human_review_summary(
        self, context: JudgeContext, decision: dict, reason: str | None
    ) -> HumanReviewSummary:
        return HumanReviewSummary(
            dispute=f"#{context.dispute_id} ({context.category}): {context.claim_text}",
            rider_brief=self._summarize_brief(context.rider_brief),
            driver_brief=self._summarize_brief(context.driver_brief),
            key_evidence_ids=decision["deciding_evidence_ids"],
            ruling=(
                f"{decision['outcome']} — refund {decision['amount']:.2f} "
                f"(confidence {decision['confidence']:.2f})"
            ),
            escalation_reason=reason or "",
            recommended_action="Review the evidence and confirm or override the provisional ruling.",
        )

    @staticmethod
    def _summarize_brief(brief: CaseBrief) -> str:
        summary = brief.argument_summary or brief.position
        lines = [line.strip() for line in summary.strip().splitlines() if line.strip()]
        return " ".join(lines[:2]) or brief.position

    def _judge_policy(self, context: JudgeContext) -> list[dict]:
        """Policy sections cited by the advocates plus the top-2 retrieved chunks.

        Only these sections are passed to the Judge, rather than the whole
        retrieval set, to keep the ruling prompt small and focused.
        """
        cited_ids: set[str] = set()
        for brief in (context.rider_brief, context.driver_brief):
            for claim in brief.claims:
                cited_ids.update(claim.policy_section_ids)

        by_key = {f"{p['source']}#{p['section']}": p for p in context.policy}
        selected: list[dict] = []
        seen: set[str] = set()

        for cid in cited_ids:
            chunk = by_key.get(cid)
            if chunk is not None and cid not in seen:
                selected.append(chunk)
                seen.add(cid)

        for chunk in context.policy[:2]:
            key = f"{chunk['source']}#{chunk['section']}"
            if key not in seen:
                selected.append(chunk)
                seen.add(key)

        return selected

    def _ruling_user_message(self, context: JudgeContext, rule_result: RuleResult) -> str:
        policy_text = _format_policy(self._judge_policy(context))
        profiler.record_policy_tokens("Judge", estimate_tokens(policy_text))
        return "\n".join(
            [
                f"Dispute id: {context.dispute_id}",
                f"Category: {context.category}",
                f"Claim: {context.claim_text}",
                "",
                "Rule-based outcome (source of truth for the amount):",
                f"  outcome={rule_result.outcome} refund={rule_result.refund_amount} rules={rule_result.matched_rule_ids}",
                "",
                "Rider brief:",
                context.rider_brief.model_dump_json(),
                "",
                "Driver brief:",
                context.driver_brief.model_dump_json(),
                "",
                "Evidence:",
                _format_evidence(context.evidence),
                "",
                "Policy:",
                policy_text,
                "",
                "History:",
                f"  rider={json.dumps(context.rider_history or {})}",
                f"  driver={json.dumps(context.driver_history or {})}",
                "",
                "Produce your ruling.",
            ]
        )

    def _explanation(self, audience: str, final: dict, tone: str, age_band: str | None) -> str:
        tone = tone if tone in ("empathetic", "neutral") else "neutral"
        amount = final["amount"]
        outcome = final["outcome"]

        if outcome == "no_action":
            decision = "No refund will be issued for this trip."
        elif outcome == "full_refund":
            decision = f"A full refund of {amount:.2f} will be issued."
        else:
            decision = f"A partial refund of {amount:.2f} will be issued."

        if tone == "empathetic":
            opener = (
                "We're sorry this experience was difficult for you."
                if audience == "rider"
                else "We appreciate your patience while we reviewed this."
            )
            closer = " We hope this feels fair."
        else:
            opener = (
                "Your dispute has been reviewed."
                if audience == "rider"
                else "This dispute has been reviewed."
            )
            closer = ""

        age_hint = _AGE_HINTS.get(age_band, "") if age_band else ""
        if age_hint:
            decision = f"{decision} {age_hint}"

        return f"{opener} {decision}{closer}"
