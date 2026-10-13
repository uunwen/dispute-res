import json

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import models
from app.db.session import get_session
from app.messaging import dispute_channel
from app.orchestrator.pipeline import _gather_trip_evidence, resolve_dispute
from app.queue.queue import enqueue_dispute, list_queue, remove_dispute
from app.schemas.api import (
    CategoryMeta,
    ChatMessageItem,
    DisputeCreate,
    DisputeListItem,
    DisputeResponse,
    GpsPointItem,
    MessageResponse,
    QueueItem,
    RulingResponse,
    TripGpsResponse,
    TripListItem,
)
from app.schemas.evidence import EvidenceItem

router = APIRouter()

_CATEGORY_META = [
    {
        "value": "route_deviation",
        "label": "Route deviation",
        "example_claim": "The driver took a long detour off the optimal route.",
        "supported": True,
    },
    {
        "value": "no_show",
        "label": "No-show",
        "example_claim": "The driver never arrived at the pickup point and I was charged a fee.",
        "supported": True,
    },
    {
        "value": "fare_dispute",
        "label": "Fare dispute",
        "example_claim": "I was charged a surge fare that did not match my booking.",
        "supported": True,
    },
    {
        "value": "property_damage",
        "label": "Property damage",
        "example_claim": "My property was damaged during the trip.",
        "supported": False,
    },
    {
        "value": "safety_incident",
        "label": "Safety incident",
        "example_claim": "I felt unsafe during the trip.",
        "supported": False,
    },
]


def _dispute_dict(d: models.Dispute) -> dict:
    return {
        "id": d.id,
        "trip_id": d.trip_id,
        "filed_by": d.filed_by,
        "category": d.category.value,
        "claim_text": d.claim_text,
        "status": d.status,
        "priority": d.priority,
        "created_at": d.created_at,
    }


def _message_dict(m: models.AgentMessage) -> dict:
    return {
        "id": m.id,
        "dispute_id": m.dispute_id,
        "sender": m.sender,
        "recipient": m.recipient,
        "message_type": m.message_type,
        "content": m.content,
        "created_at": m.created_at,
    }


def _ruling_dict(r: models.Ruling) -> dict:
    return {
        "id": r.id,
        "dispute_id": r.dispute_id,
        "outcome": r.outcome.value,
        "refund_amount": r.refund_amount,
        "confidence": r.confidence,
        "reasoning": r.reasoning,
        "rule_outcome": r.rule_outcome,
        "evidence_ids": r.evidence_ids,
        "escalated": r.escalated,
        "human_review_summary": r.human_review_summary,
        "llm_degraded": r.llm_degraded,
        "model_info": r.model_info,
        "created_at": r.created_at,
    }


@router.post("/disputes", response_model=DisputeResponse, status_code=201)
async def create_dispute(payload: DisputeCreate, session: AsyncSession = Depends(get_session)):
    dispute = models.Dispute(
        trip_id=payload.trip_id,
        filed_by=payload.filed_by,
        category=payload.category,
        claim_text=payload.claim_text,
        status="open",
        priority="medium",
    )
    session.add(dispute)
    await session.commit()
    await session.refresh(dispute)
    await enqueue_dispute(dispute.id)
    return _dispute_dict(dispute)


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute_endpoint(
    dispute_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(models.Dispute, dispute_id) is None:
        raise HTTPException(status_code=404, detail="dispute not found")

    if force:
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id))
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id))
        await session.commit()

    await remove_dispute(dispute_id)
    background_tasks.add_task(resolve_dispute, dispute_id)
    return {"dispute_id": dispute_id, "status": "started"}


@router.get("/disputes/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(dispute_id: int, session: AsyncSession = Depends(get_session)):
    dispute = await session.get(models.Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="dispute not found")
    return _dispute_dict(dispute)


@router.get("/disputes/{dispute_id}/messages", response_model=list[MessageResponse])
async def get_messages(dispute_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(models.AgentMessage)
            .where(models.AgentMessage.dispute_id == dispute_id)
            .order_by(models.AgentMessage.created_at)
        )
    ).scalars().all()
    return [_message_dict(m) for m in rows]


@router.get("/disputes/{dispute_id}/ruling", response_model=RulingResponse)
async def get_ruling(dispute_id: int, session: AsyncSession = Depends(get_session)):
    ruling = (
        await session.execute(
            select(models.Ruling)
            .where(models.Ruling.dispute_id == dispute_id)
            .order_by(models.Ruling.created_at.desc())
        )
    ).scalars().first()
    if ruling is None:
        raise HTTPException(status_code=404, detail="ruling not found")
    return _ruling_dict(ruling)


@router.get("/disputes/{dispute_id}/stream")
async def stream_dispute(dispute_id: int):
    async def gen():
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(dispute_channel(dispute_id))
            yield f"data: {json.dumps({'type': 'connected', 'dispute_id': dispute_id})}\n\n"
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    yield f"data: {message['data']}\n\n"
        finally:
            await pubsub.aclose()
            await client.aclose()

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/trips/{trip_id}/evidence", response_model=list[EvidenceItem])
async def get_trip_evidence(trip_id: int):
    return await _gather_trip_evidence(trip_id)


@router.get("/disputes", response_model=list[DisputeListItem])
async def list_disputes(session: AsyncSession = Depends(get_session)):
    disputes = (
        await session.execute(select(models.Dispute).order_by(models.Dispute.created_at.desc()))
    ).scalars().all()
    if not disputes:
        return []

    ids = [d.id for d in disputes]
    rulings = (
        await session.execute(
            select(models.Ruling)
            .where(models.Ruling.dispute_id.in_(ids))
            .order_by(models.Ruling.created_at.desc())
        )
    ).scalars().all()
    latest: dict[int, models.Ruling] = {}
    for ruling in rulings:
        latest.setdefault(ruling.dispute_id, ruling)

    result = []
    for d in disputes:
        r = latest.get(d.id)
        result.append(
            {
                "id": d.id,
                "trip_id": d.trip_id,
                "category": d.category.value,
                "status": d.status,
                "priority": d.priority,
                "claim_text": d.claim_text,
                "created_at": d.created_at,
                "outcome": r.outcome.value if r else None,
                "refund_amount": r.refund_amount if r else None,
                "llm_degraded": r.llm_degraded if r else None,
            }
        )
    return result


@router.get("/trips", response_model=list[TripListItem])
async def list_trips(limit: int = 50, session: AsyncSession = Depends(get_session)):
    trips = (
        await session.execute(
            select(models.Trip).order_by(models.Trip.requested_at.desc()).limit(limit)
        )
    ).scalars().all()
    if not trips:
        return []

    trip_ids = [t.id for t in trips]
    account_ids = {t.rider_id for t in trips} | {t.driver_id for t in trips}
    accounts = (
        await session.execute(select(models.Account).where(models.Account.id.in_(account_ids)))
    ).scalars().all()
    name_map = {a.id: a.name for a in accounts}

    disputes = (
        await session.execute(select(models.Dispute).where(models.Dispute.trip_id.in_(trip_ids)))
    ).scalars().all()
    scenario_map = {d.trip_id: d.category.value for d in disputes}

    return [
        {
            "id": t.id,
            "rider_id": t.rider_id,
            "driver_id": t.driver_id,
            "rider": name_map.get(t.rider_id, "unknown"),
            "driver": name_map.get(t.driver_id, "unknown"),
            "fare": t.actual_fare,
            "scenario": scenario_map.get(t.id, "normal"),
        }
        for t in trips
    ]


@router.get("/trips/{trip_id}/chat", response_model=list[ChatMessageItem])
async def get_trip_chat(trip_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(models.ChatMessage)
            .where(models.ChatMessage.trip_id == trip_id)
            .order_by(models.ChatMessage.ts)
        )
    ).scalars().all()
    if not rows:
        return []

    sender_ids = {m.sender_id for m in rows}
    accounts = (
        await session.execute(select(models.Account).where(models.Account.id.in_(sender_ids)))
    ).scalars().all()
    name_map = {a.id: a.name for a in accounts}

    return [
        {
            "id": m.id,
            "trip_id": m.trip_id,
            "sender_id": m.sender_id,
            "sender": name_map.get(m.sender_id, "unknown"),
            "text": m.text,
            "ts": m.ts,
        }
        for m in rows
    ]


@router.get("/trips/{trip_id}/gps", response_model=TripGpsResponse)
async def get_trip_gps(trip_id: int, session: AsyncSession = Depends(get_session)):
    trip = await session.get(models.Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    points = (
        await session.execute(
            select(models.GpsPoint)
            .where(models.GpsPoint.trip_id == trip_id)
            .order_by(models.GpsPoint.ts)
        )
    ).scalars().all()

    return {
        "optimal_route": trip.optimal_route_polyline or [],
        "points": [
            {"lat": g.lat, "lng": g.lng, "ts": g.ts, "speed_kmh": g.speed_kmh} for g in points
        ],
    }


@router.get("/queue", response_model=list[QueueItem])
async def get_queue(session: AsyncSession = Depends(get_session)):
    return await list_queue(session=session)


@router.get("/meta/categories", response_model=list[CategoryMeta])
async def get_categories():
    return _CATEGORY_META
