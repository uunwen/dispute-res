import datetime as dt
import logging

import redis.asyncio as aioredis
from sqlalchemy import select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

QUEUE_KEY = "dispute_queue"

# Priority weights (documented). A dispute's score is the sum of:
#   safety category  -> SAFETY_WEIGHT  (dominates everything else)
#   disputed amount  -> amount * AMOUNT_WEIGHT  (higher amount first)
#   age in seconds   -> age * AGE_WEIGHT  (older first, as a tiebreaker)
# The weights are chosen so safety > amount > age for realistic fares and ages.
SAFETY_WEIGHT = 1e15
AMOUNT_WEIGHT = 1e8
AGE_WEIGHT = 1.0


def _redis():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def priority_score(*, category: str, amount: float, created_at: dt.datetime, now: dt.datetime) -> float:
    safety = 1.0 if category == "safety_incident" else 0.0
    age = max(0.0, (now - created_at).total_seconds())
    return safety * SAFETY_WEIGHT + amount * AMOUNT_WEIGHT + age * AGE_WEIGHT


def _sla_seconds(category: str) -> int:
    return settings.sla_safety_seconds if category == "safety_incident" else settings.sla_default_seconds


async def enqueue_dispute(dispute_id: int, *, session=None, now: dt.datetime | None = None) -> float:
    now = now or dt.datetime.now(dt.timezone.utc)

    async def _load(s):
        dispute = await s.get(models.Dispute, dispute_id)
        if dispute is None:
            raise ValueError(f"dispute {dispute_id} not found")
        trip = await s.get(models.Trip, dispute.trip_id)
        amount = trip.actual_fare if trip else 0.0
        return dispute.category.value, amount, dispute.created_at

    if session is not None:
        category, amount, created_at = await _load(session)
    else:
        async with async_session_factory() as s:
            category, amount, created_at = await _load(s)

    score = priority_score(category=category, amount=amount, created_at=created_at, now=now)
    try:
        client = _redis()
        await client.zadd(QUEUE_KEY, {str(dispute_id): score})
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to enqueue dispute %s: %s", dispute_id, exc)
    return score


async def pop_dispute() -> tuple[int | None, float | None]:
    try:
        client = _redis()
        result = await client.zpopmax(QUEUE_KEY)
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to pop from queue: %s", exc)
        return None, None
    if not result:
        return None, None
    member, score = result[0]
    return int(member), float(score)


async def remove_dispute(dispute_id: int) -> None:
    try:
        client = _redis()
        await client.zrem(QUEUE_KEY, str(dispute_id))
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to remove dispute %s from queue: %s", dispute_id, exc)


async def clear_queue() -> None:
    try:
        client = _redis()
        await client.delete(QUEUE_KEY)
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to clear queue: %s", exc)


async def list_queue(session=None) -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)
    try:
        client = _redis()
        raw = await client.zrevrange(QUEUE_KEY, 0, -1, withscores=True)
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to read queue: %s", exc)
        return []

    async def _run(s):
        ids = [int(member) for member, _ in raw]
        disputes = (
            await s.execute(select(models.Dispute).where(models.Dispute.id.in_(ids)))
        ).scalars().all() if ids else []
        dmap = {d.id: d for d in disputes}
        trips = (
            await s.execute(select(models.Trip).where(models.Trip.id.in_([d.trip_id for d in disputes])))
        ).scalars().all()
        tmap = {t.id: t for t in trips}

        result = []
        for member, score in raw:
            dispute_id = int(member)
            dispute = dmap.get(dispute_id)
            if dispute is None:
                continue
            trip = tmap.get(dispute.trip_id)
            category = dispute.category.value
            amount = trip.actual_fare if trip else 0.0
            wait = max(0.0, (now - dispute.created_at).total_seconds())
            sla = _sla_seconds(category)
            result.append(
                {
                    "dispute_id": dispute_id,
                    "category": category,
                    "amount": amount,
                    "priority": float(score),
                    "wait_time_seconds": round(wait, 1),
                    "sla_seconds": sla,
                    "breached": wait > sla,
                }
            )
        return result

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
