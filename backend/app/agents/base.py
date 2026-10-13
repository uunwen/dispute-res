import json
import logging
from dataclasses import dataclass

from sqlalchemy import select

from app.agents.prompts import load_prompt
from app.db import models
from app.db.session import async_session_factory
from app.evidence import registry
from app.llm.client import client as llm_client
from app.messaging import dispute_channel, publish_message
from app.rag.retrieve import retrieve_policy
from app.schemas.case_brief import CaseBrief
from app.schemas.evidence import EvidenceItem

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 5


@dataclass
class AgentContext:
    dispute_id: int
    trip_id: int
    category: str
    claim_text: str
    recipient: str = "Judge"
    opponent_brief: CaseBrief | None = None
    round: str = "opening"


def validate_case_brief(brief: CaseBrief, valid_evidence_ids: set[str]) -> CaseBrief:
    """Strip any claim citation whose evidence id does not exist.

    Claims that are left with no valid evidence citations are dropped entirely so
    advocates cannot rest an argument on hallucinated evidence.
    """
    kept = []
    for claim in brief.claims:
        claim.evidence_ids = [eid for eid in claim.evidence_ids if eid in valid_evidence_ids]
        if claim.evidence_ids:
            kept.append(claim)
    brief.claims = kept
    return brief


def _format_policy(policy: list[dict]) -> str:
    if not policy:
        return "(none)"
    return "\n".join(f"[{p['source']}#{p['section']}] {p['text']}" for p in policy)


def _format_evidence(evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "(none)"
    return "\n".join(
        f"[{e.id}] type={e.type} supports={e.supports} strength={e.strength} summary={e.summary}"
        for e in evidence
    )


class Agent:
    name: str = "agent"
    position: str = "neutral"
    prompt_file: str = ""

    async def run(self, context: AgentContext) -> models.AgentMessage:
        async with async_session_factory() as session:
            trip = (
                await session.execute(select(models.Trip).where(models.Trip.id == context.trip_id))
            ).scalar_one_or_none()
        rider_id = trip.rider_id if trip else None
        driver_id = trip.driver_id if trip else None

        policy = await retrieve_policy(context.claim_text, category=context.category, k=4)

        evidence, tool_calls = await self._gather_evidence(context, policy, rider_id, driver_id)

        brief = await self._build_brief(context, policy, evidence)
        brief = validate_case_brief(brief, {e.id for e in evidence})

        return await self._persist(context, brief, evidence, tool_calls)

    async def _gather_evidence(
        self, context: AgentContext, policy: list[dict], rider_id, driver_id
    ) -> tuple[list[EvidenceItem], int]:
        system = load_prompt(self.prompt_file)
        user = self._tool_phase_message(context, policy, rider_id, driver_id)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        evidence: list[EvidenceItem] = []
        tool_calls = 0
        for _ in range(MAX_TOOL_CALLS):
            try:
                result = await llm_client.chat(
                    messages, tools=registry.tool_specs(), tool_choice="auto", role="tools"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM chat failed during evidence gathering: %s", exc)
                break

            if not result.tool_calls:
                break

            messages.append(self._assistant_message(result))
            for tc in result.tool_calls:
                if tool_calls >= MAX_TOOL_CALLS:
                    break
                tool = registry.get_tool(tc.name)
                if tool is None:
                    messages.append(self._tool_error(tc.id, f"unknown tool {tc.name}"))
                    continue
                try:
                    output = await tool.func(**tc.arguments)
                except Exception as exc:  # noqa: BLE001
                    messages.append(self._tool_error(tc.id, str(exc)))
                    continue

                tool_calls += 1
                if isinstance(output, EvidenceItem):
                    evidence.append(output)
                    content = json.dumps(output.model_dump(mode="json"), default=str)
                else:
                    content = json.dumps(output, default=str)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": content})

        return evidence, tool_calls

    async def _build_brief(self, context: AgentContext, policy: list[dict], evidence: list[EvidenceItem]) -> CaseBrief:
        system = load_prompt(self.prompt_file)
        user = self._brief_message(context, policy, evidence)
        try:
            brief = await llm_client.structured(system, user, CaseBrief, role="advocate")
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM structured output failed for %s: %s", self.name, exc)
            brief = None

        if brief is None:
            brief = CaseBrief(
                position=self.position,
                argument_summary="No brief produced (LLM unavailable).",
                claims=[],
                requested_outcome="no_action",
                weaknesses=[],
            )
        return brief

    async def _persist(self, context: AgentContext, brief: CaseBrief, evidence: list[EvidenceItem], tool_calls: int) -> models.AgentMessage:
        content = {
            "brief": brief.model_dump(mode="json"),
            "evidence_ids": [e.id for e in evidence],
            "evidence": [e.model_dump(mode="json") for e in evidence],
            "tool_calls": tool_calls,
            "round": context.round,
        }
        async with async_session_factory() as session:
            message = models.AgentMessage(
                dispute_id=context.dispute_id,
                sender=self.name,
                recipient=context.recipient,
                message_type="case_brief",
                content=content,
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)

        await publish_message(
            dispute_channel(context.dispute_id),
            {
                "id": message.id,
                "dispute_id": context.dispute_id,
                "type": "agent_message",
                "sender": self.name,
                "recipient": context.recipient,
                "message_type": "case_brief",
                "content": content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            },
        )
        return message

    def _tool_phase_message(self, context: AgentContext, policy: list[dict], rider_id, driver_id) -> str:
        return "\n".join(
            [
                f"Dispute id: {context.dispute_id}",
                f"Trip id: {context.trip_id}",
                f"Category: {context.category}",
                f"Claim: {context.claim_text}",
                f"Rider account id: {rider_id}",
                f"Driver account id: {driver_id}",
                "",
                "Relevant policy:",
                _format_policy(policy),
                "",
                "Use the available tools to gather evidence, then produce your case brief.",
            ]
        )

    def _brief_message(self, context: AgentContext, policy: list[dict], evidence: list[EvidenceItem]) -> str:
        parts = [
            f"Dispute id: {context.dispute_id}",
            f"Category: {context.category}",
            f"Claim: {context.claim_text}",
            "",
            "Policy sections:",
            _format_policy(policy),
            "",
            "Gathered evidence:",
            _format_evidence(evidence),
        ]
        if context.opponent_brief is not None:
            parts += [
                "",
                "Opposing advocate's brief (rebut it):",
                context.opponent_brief.model_dump_json(),
            ]
        parts += [
            "",
            "Produce your case brief arguing for the position described in your instructions.",
        ]
        return "\n".join(parts)

    def _assistant_message(self, result) -> dict:
        return {
            "role": "assistant",
            "content": result.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    **tc.extra_content,
                }
                for tc in result.tool_calls
            ],
        }

    def _tool_error(self, tool_call_id: str, error: str) -> dict:
        return {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps({"error": error})}
