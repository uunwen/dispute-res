import datetime as dt
import logging

from sqlalchemy import func, select

from app.config import settings
from app.db import models
from app.db.enums import DisputeCategory
from app.db.session import async_session_factory
from app.evidence import fare as fare_evidence
from app.evidence import noshow as noshow_evidence
from app.evidence import route as route_evidence
from app.evidence.history import compute_history_profile_db
from app.messaging import dispute_channel, publish_message
from app.schemas.fraud import FraudReason, FraudSignal

logger = logging.getLogger(__name__)

# Risk contribution per rule. Each rule adds its weight to the relevant side's
# risk (rider or driver) when it fires; the total is clamped to [0, 1].
_WEIGHTS = {
    "dispute_frequency": 0.3,
    "win_rate_anomaly": 0.2,
    "repeat_deviation": 0.4,
    "young_account": 0.2,
    "claim_evidence_contradiction": 0.3,
}


def compute_fraud_signal(facts: dict) -> FraudSignal:
    """Rule-based fraud scoring (no LLM). Each rule is documented below.

    Rules (thresholds are configurable via settings):

    1. dispute frequency — filed >= threshold disputes within the last N days.
    2. win rate anomaly — rider win rate below the threshold (proxy for below-average).
    3. repeat deviation — driver involved in >= threshold route-deviation disputes.
    4. young account — account age below N days.
    5. claim-vs-evidence contradiction — the claim is contradicted by the
       deterministic evidence.

    This signal is advisory only; it is never used to auto-deny a dispute.
    """
    reasons: list[FraudReason] = []
    rider_risk = 0.0
    driver_risk = 0.0

    if facts["rider_disputes"] >= facts["dispute_frequency_threshold"]:
        rider_risk += _WEIGHTS["dispute_frequency"]
        reasons.append(
            FraudReason(
                code="dispute_frequency",
                description=(
                    f"rider filed {facts['rider_disputes']} disputes in the last "
                    f"{facts['dispute_frequency_days']} days"
                ),
                evidence_id=facts["rider_history_id"],
            )
        )

    if facts["driver_disputes"] >= facts["dispute_frequency_threshold"]:
        driver_risk += _WEIGHTS["dispute_frequency"]
        reasons.append(
            FraudReason(
                code="dispute_frequency",
                description=(
                    f"driver filed {facts['driver_disputes']} disputes in the last "
                    f"{facts['dispute_frequency_days']} days"
                ),
                evidence_id=facts["driver_history_id"],
            )
        )

    if facts["rider_win_rate"] < facts["win_rate_threshold"]:
        rider_risk += _WEIGHTS["win_rate_anomaly"]
        reasons.append(
            FraudReason(
                code="win_rate_anomaly",
                description=(
                    f"rider win rate {facts['rider_win_rate']:.2f} is below "
                    f"threshold {facts['win_rate_threshold']:.2f}"
                ),
                evidence_id=facts["rider_history_id"],
            )
        )

    if facts["driver_deviation_count"] >= facts["repeat_deviation_threshold"]:
        driver_risk += _WEIGHTS["repeat_deviation"]
        reasons.append(
            FraudReason(
                code="repeat_deviation",
                description=(
                    f"driver involved in {facts['driver_deviation_count']} "
                    "route-deviation disputes"
                ),
                evidence_id=facts["driver_history_id"],
            )
        )

    if facts["rider_account_age_days"] < facts["account_age_days"]:
        rider_risk += _WEIGHTS["young_account"]
        reasons.append(
            FraudReason(
                code="young_account",
                description=f"rider account is only {facts['rider_account_age_days']} days old",
                evidence_id=facts["rider_history_id"],
            )
        )

    if facts["driver_account_age_days"] < facts["account_age_days"]:
        driver_risk += _WEIGHTS["young_account"]
        reasons.append(
            FraudReason(
                code="young_account",
                description=f"driver account is only {facts['driver_account_age_days']} days old",
                evidence_id=facts["driver_history_id"],
            )
        )

    if facts["contradiction"]:
        rider_risk += _WEIGHTS["claim_evidence_contradiction"]
        reasons.append(
            FraudReason(
                code="claim_evidence_contradiction",
                description="the dispute claim is contradicted by the deterministic evidence",
                evidence_id=facts["contradiction_evidence_id"],
            )
        )

    return FraudSignal(
        trip_id=facts["trip_id"],
        rider_risk=round(min(rider_risk, 1.0), 3),
        driver_risk=round(min(driver_risk, 1.0), 3),
        reasons=reasons,
    )


def _detect_contradiction(dispute, evidence) -> tuple[bool, str | None]:
    if dispute is None:
        return False, None
    category = dispute.category.value if hasattr(dispute.category, "value") else str(dispute.category)
    if category != "route_deviation":
        return False, None
    route = next((e for e in evidence if e.type == "route_deviation"), None)
    if route is None:
        return False, None
    if not route.data.get("bad_faith_deviation", False):
        return True, route.id
    return False, None


async def analyze_fraud(trip_id: int, session=None) -> FraudSignal:
    async def _run(s):
        trip = (
            await s.execute(select(models.Trip).where(models.Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None:
            raise ValueError(f"trip {trip_id} not found")

        dispute = (
            await s.execute(select(models.Dispute).where(models.Dispute.trip_id == trip_id))
        ).scalars().first()

        rider_history = (await compute_history_profile_db(trip.rider_id, session=s)).data
        driver_history = (await compute_history_profile_db(trip.driver_id, session=s)).data

        reference = dispute.created_at if dispute else trip.requested_at
        cutoff = reference - dt.timedelta(days=settings.fraud_dispute_frequency_days)

        rider_disputes = (
            await s.execute(
                select(func.count())
                .select_from(models.Dispute)
                .where(
                    models.Dispute.filed_by == trip.rider_id,
                    models.Dispute.created_at >= cutoff,
                )
            )
        ).scalar_one()

        driver_disputes = (
            await s.execute(
                select(func.count())
                .select_from(models.Dispute)
                .where(
                    models.Dispute.filed_by == trip.driver_id,
                    models.Dispute.created_at >= cutoff,
                )
            )
        ).scalar_one()

        driver_deviation_count = (
            await s.execute(
                select(func.count())
                .select_from(models.Dispute)
                .join(models.Trip, models.Trip.id == models.Dispute.trip_id)
                .where(
                    models.Trip.driver_id == trip.driver_id,
                    models.Dispute.category == DisputeCategory.route_deviation,
                )
            )
        ).scalar_one()

        evidence = []
        for fn in (
            route_evidence.analyze_route_deviation,
            fare_evidence.validate_fare,
            noshow_evidence.analyze_noshow,
        ):
            try:
                evidence.append(await fn(trip_id, session=s))
            except Exception as exc:  # noqa: BLE001
                logger.warning("fraud evidence step failed: %s", exc)

        contradiction, contradiction_evidence_id = _detect_contradiction(dispute, evidence)

        facts = {
            "trip_id": trip_id,
            "rider_disputes": rider_disputes,
            "driver_disputes": driver_disputes,
            "rider_win_rate": rider_history.get("win_rate", 0.5),
            "driver_win_rate": driver_history.get("win_rate", 0.5),
            "driver_deviation_count": driver_deviation_count,
            "rider_account_age_days": rider_history.get("account_age_days", 0),
            "driver_account_age_days": driver_history.get("account_age_days", 0),
            "contradiction": contradiction,
            "contradiction_evidence_id": contradiction_evidence_id or "",
            "rider_history_id": f"history_profile:{trip.rider_id}",
            "driver_history_id": f"history_profile:{trip.driver_id}",
            "dispute_frequency_days": settings.fraud_dispute_frequency_days,
            "dispute_frequency_threshold": settings.fraud_dispute_frequency_threshold,
            "win_rate_threshold": settings.fraud_win_rate_threshold,
            "repeat_deviation_threshold": settings.fraud_repeat_deviation_threshold,
            "account_age_days": settings.fraud_account_age_days,
        }
        return compute_fraud_signal(facts)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)


async def publish_fraud_signal(dispute_id: int, signal: FraudSignal) -> models.AgentMessage:
    content = signal.model_dump(mode="json")
    async with async_session_factory() as session:
        message = models.AgentMessage(
            dispute_id=dispute_id,
            sender="Fraud",
            recipient="Judge",
            message_type="fraud_signal",
            content=content,
        )
        session.add(message)
        await session.commit()
        await session.refresh(message)

    await publish_message(
        dispute_channel(dispute_id),
        {
            "id": message.id,
            "dispute_id": dispute_id,
            "type": "agent_message",
            "sender": "Fraud",
            "recipient": "Judge",
            "message_type": "fraud_signal",
            "content": content,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        },
    )
    return message
