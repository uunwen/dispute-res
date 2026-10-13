import asyncio
import logging
from dataclasses import replace

from sqlalchemy import select

from app.agents.base import AgentContext
from app.agents.driver_advocate import DriverAdvocate
from app.agents.fraud import analyze_fraud, publish_fraud_signal
from app.agents.judge import Judge, JudgeContext
from app.agents.rider_advocate import RiderAdvocate
from app.db import models
from app.db.session import async_session_factory
from app.evidence import chat as chat_evidence
from app.evidence import fare as fare_evidence
from app.evidence import noshow as noshow_evidence
from app.evidence import route as route_evidence
from app.evidence.history import compute_history_profile_db
from app.llm.client import client as llm_client
from app.messaging import publish_dispute_event
from app.rag.retrieve import retrieve_policy
from app.rules.engine import evaluate
from app.schemas.case_brief import CaseBrief

logger = logging.getLogger(__name__)


async def _gather_trip_evidence(trip_id: int) -> list:
    results = await asyncio.gather(
        route_evidence.analyze_route_deviation(trip_id),
        fare_evidence.validate_fare(trip_id),
        noshow_evidence.analyze_noshow(trip_id),
        chat_evidence.analyze_chat(trip_id),
        return_exceptions=True,
    )
    return [r for r in results if not isinstance(r, BaseException)]


async def resolve_dispute(dispute_id: int, *, rebuttal: bool = True, tone: str = "neutral") -> models.Ruling:
    llm_client.degraded = False
    llm_client.error_info = None

    async with async_session_factory() as session:
        dispute = (
            await session.execute(select(models.Dispute).where(models.Dispute.id == dispute_id))
        ).scalar_one_or_none()
        if dispute is None:
            raise ValueError(f"dispute {dispute_id} not found")

        trip = (
            await session.execute(select(models.Trip).where(models.Trip.id == dispute.trip_id))
        ).scalar_one_or_none()
        rider = (
            await session.execute(select(models.Account).where(models.Account.id == trip.rider_id))
        ).scalar_one_or_none()
        rider_id = trip.rider_id
        driver_id = trip.driver_id

    await publish_dispute_event(dispute_id, "resolving", {"status": dispute.status})

    rider_history = (await compute_history_profile_db(rider_id)).data
    driver_history = (await compute_history_profile_db(driver_id)).data

    evidence = await _gather_trip_evidence(dispute.trip_id)
    policy = await retrieve_policy(dispute.claim_text, category=None, k=4)
    rule_result = evaluate(dispute.category.value, evidence)

    ctx = AgentContext(
        dispute_id=dispute_id,
        trip_id=dispute.trip_id,
        category=dispute.category.value,
        claim_text=dispute.claim_text,
    )

    rider_msg, driver_msg, fraud_signal = await asyncio.gather(
        RiderAdvocate().run(ctx),
        DriverAdvocate().run(ctx),
        analyze_fraud(dispute.trip_id),
    )
    await publish_fraud_signal(dispute_id, fraud_signal)

    rider_brief = CaseBrief(**rider_msg.content["brief"])
    driver_brief = CaseBrief(**driver_msg.content["brief"])

    if rebuttal:
        rider_msg, driver_msg = await asyncio.gather(
            RiderAdvocate().run(replace(ctx, opponent_brief=driver_brief, round="rebuttal")),
            DriverAdvocate().run(replace(ctx, opponent_brief=rider_brief, round="rebuttal")),
        )
        rider_brief = CaseBrief(**rider_msg.content["brief"])
        driver_brief = CaseBrief(**driver_msg.content["brief"])

    await publish_dispute_event(dispute_id, "advocates_done", {})

    judge_ctx = JudgeContext(
        dispute_id=dispute_id,
        trip_id=dispute.trip_id,
        category=dispute.category.value,
        claim_text=dispute.claim_text,
        rider_brief=rider_brief,
        driver_brief=driver_brief,
        evidence=evidence,
        policy=policy,
        rider_history=rider_history,
        driver_history=driver_history,
        fraud_signal=fraud_signal,
        rule_result=rule_result,
        tone=tone,
        age_band=rider.age_band if rider else None,
    )
    ruling = await Judge().run(judge_ctx)

    await publish_dispute_event(dispute_id, "ruling_ready", {"ruling_id": ruling.id})

    return ruling
