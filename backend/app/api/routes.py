import hashlib
import json
import re
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import models
from app.db.enums import AttachmentKind
from app.db.session import get_session
from app.formulas import FORMULAS
from app.messaging import dispute_channel
from app.orchestrator.pipeline import _gather_trip_evidence, resolve_dispute
from app.policies import load_policy_sections
from app.queue.queue import enqueue_dispute, list_queue, remove_dispute
from app.rules.engine import load_rules
from app.schemas.api import (
    AccountItem,
    AttachmentResponse,
    CategoryMeta,
    ChatMessageItem,
    ConfigEntry,
    DisputeCreate,
    DisputeListItem,
    DisputeResponse,
    DisputeReviewCreate,
    DisputeReviewResponse,
    GpsPointItem,
    MessageResponse,
    ModelAssignment,
    PolicySection,
    QueueItem,
    RuleItem,
    RulingResponse,
    SettingsResponse,
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


def _review_dict(r: models.DisputeReview) -> dict:
    return {
        "id": r.id,
        "dispute_id": r.dispute_id,
        "action": r.action,
        "note": r.note,
        "actor": r.actor,
        "created_at": r.created_at,
    }


def _attachment_dict(a: models.Attachment) -> dict:
    return {
        "id": a.id,
        "dispute_id": a.dispute_id,
        "filename": a.filename,
        "mime": a.mime,
        "size_bytes": a.size_bytes,
        "kind": a.kind.value,
        "sha256": a.sha256,
        "created_at": a.created_at,
        "analysis": a.analysis,
    }


_ALLOWED_ATTACHMENT_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
    "application/json",
}

_ATTACHMENT_KINDS = {"photo", "receipt", "chat_log", "other"}


def _sanitize_filename(name: str | None) -> str:
    base = Path(name or "attachment").name
    base = re.sub(r"[^\w.\- ]", "_", base)
    base = base.strip(" .")[:200]
    return base or "attachment"


def _uploads_root() -> Path:
    root = Path(settings.attachments_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / settings.attachments_dir
    return root


@router.post(
    "/disputes",
    response_model=DisputeResponse,
    status_code=201,
    tags=["Disputes"],
    summary="File a new dispute",
    description="Create a dispute against a trip and enqueue it for autonomous resolution.",
)
async def create_dispute(payload: DisputeCreate, session: AsyncSession = Depends(get_session)):
    trip = await session.get(models.Trip, payload.trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    if payload.filed_by is not None:
        if payload.filed_by not in (trip.rider_id, trip.driver_id):
            raise HTTPException(
                status_code=400,
                detail="filed_by account does not belong to this trip",
            )
        filed_by = payload.filed_by
    else:
        filed_by = trip.rider_id if payload.filed_by_role == "rider" else trip.driver_id

    dispute = models.Dispute(
        trip_id=payload.trip_id,
        filed_by=filed_by,
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


@router.post(
    "/disputes/{dispute_id}/resolve",
    tags=["Disputes"],
    summary="Resolve a dispute",
    description=(
        "Run the multi-agent resolution pipeline (Rider Advocate, Driver Advocate, "
        "Judge) for a dispute. When `force` is true, any prior messages/rulings are "
        "deleted first. Resolution runs as a background task."
    ),
)
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


@router.get(
    "/disputes/{dispute_id}",
    response_model=DisputeResponse,
    tags=["Disputes"],
    summary="Get a dispute",
)
async def get_dispute(dispute_id: int, session: AsyncSession = Depends(get_session)):
    dispute = await session.get(models.Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="dispute not found")
    return _dispute_dict(dispute)


@router.get(
    "/disputes/{dispute_id}/messages",
    response_model=list[MessageResponse],
    tags=["Disputes"],
    summary="List inter-agent messages",
    description="Return the observable communication log between agents for a dispute.",
)
async def get_messages(dispute_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(models.AgentMessage)
            .where(models.AgentMessage.dispute_id == dispute_id)
            .order_by(models.AgentMessage.created_at)
        )
    ).scalars().all()
    return [_message_dict(m) for m in rows]


@router.get(
    "/disputes/{dispute_id}/ruling",
    response_model=RulingResponse,
    tags=["Disputes"],
    summary="Get the latest ruling",
    description="Return the most recent ruling (outcome, refund, confidence, reasoning) for a dispute.",
)
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


@router.post(
    "/disputes/{dispute_id}/review",
    response_model=DisputeReviewResponse,
    status_code=201,
    tags=["Disputes"],
    summary="Record a review action",
    description=(
        "Record a human review action (confirm, appeal or assign) against a dispute. "
        "The action is written to the dispute audit log and updates the dispute status."
    ),
)
async def review_dispute(
    dispute_id: int,
    payload: DisputeReviewCreate,
    session: AsyncSession = Depends(get_session),
):
    dispute = await session.get(models.Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="dispute not found")

    if payload.action == "confirm":
        dispute.status = "resolved"
    elif payload.action == "appeal":
        dispute.status = "needs_human_review"
    elif payload.action == "assign":
        dispute.status = "needs_human_review"

    review = models.DisputeReview(
        dispute_id=dispute_id,
        action=payload.action,
        note=payload.note,
        actor="ops",
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return _review_dict(review)


@router.get(
    "/disputes/{dispute_id}/reviews",
    response_model=list[DisputeReviewResponse],
    tags=["Disputes"],
    summary="List review actions",
    description="Return the audit log of human review actions for a dispute.",
)
async def list_reviews(dispute_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(models.DisputeReview)
            .where(models.DisputeReview.dispute_id == dispute_id)
            .order_by(models.DisputeReview.created_at)
        )
    ).scalars().all()
    return [_review_dict(r) for r in rows]


@router.get(
    "/accounts",
    response_model=list[AccountItem],
    tags=["Trips"],
    summary="List accounts",
    description="Return the rider and driver accounts (id, name, role) available in the system.",
)
async def list_accounts(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(select(models.Account).order_by(models.Account.id))
    ).scalars().all()
    return [{"id": a.id, "name": a.name, "role": a.role.value} for a in rows]


@router.post(
    "/disputes/{dispute_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
    tags=["Disputes"],
    summary="Upload an evidence attachment",
    description=(
        "Upload a user-supplied evidence file for a dispute. Accepted mime types: "
        "image/jpeg, image/png, image/webp, application/pdf, text/plain, "
        "application/json. Max 5 MB per file and 5 files per dispute."
    ),
)
async def upload_attachment(
    dispute_id: int,
    file: UploadFile = File(...),
    kind: str = Form("other"),
    session: AsyncSession = Depends(get_session),
):
    dispute = await session.get(models.Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="dispute not found")

    if kind not in _ATTACHMENT_KINDS:
        raise HTTPException(status_code=400, detail=f"invalid kind {kind!r}")

    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime not in _ALLOWED_ATTACHMENT_MIME:
        raise HTTPException(status_code=415, detail=f"unsupported media type {mime or '(none)'}")

    content = await file.read()
    if len(content) > settings.attachment_max_size_bytes:
        raise HTTPException(status_code=413, detail="file exceeds 5 MB limit")

    existing_count = (
        await session.execute(
            select(func.count()).select_from(models.Attachment).where(
                models.Attachment.dispute_id == dispute_id
            )
        )
    ).scalar_one()
    if existing_count >= settings.attachment_max_files:
        raise HTTPException(status_code=400, detail="attachment limit reached (5 per dispute)")

    sha256 = hashlib.sha256(content).hexdigest()
    duplicate = (
        await session.execute(
            select(models.Attachment.id).where(
                models.Attachment.dispute_id == dispute_id,
                models.Attachment.sha256 == sha256,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="duplicate attachment (same file already uploaded)")

    filename = _sanitize_filename(file.filename)
    uploads_dir = _uploads_root() / str(dispute_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    storage_path = uploads_dir / f"{sha256[:16]}_{filename}"
    storage_path.write_bytes(content)

    attachment = models.Attachment(
        dispute_id=dispute_id,
        filename=filename,
        mime=mime,
        size_bytes=len(content),
        kind=AttachmentKind(kind),
        storage_path=str(storage_path),
        sha256=sha256,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return _attachment_dict(attachment)


@router.get(
    "/disputes/{dispute_id}/attachments",
    response_model=list[AttachmentResponse],
    tags=["Disputes"],
    summary="List evidence attachments",
    description="Return the user-supplied evidence files attached to a dispute.",
)
async def list_attachments(dispute_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(models.Attachment)
            .where(models.Attachment.dispute_id == dispute_id)
            .order_by(models.Attachment.created_at)
        )
    ).scalars().all()
    return [_attachment_dict(a) for a in rows]


@router.get(
    "/disputes/{dispute_id}/stream",
    tags=["Disputes"],
    summary="Stream dispute events (SSE)",
    description="Server-Sent Events stream of agent messages and resolution events for a dispute.",
)
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


@router.get(
    "/trips/{trip_id}/evidence",
    response_model=list[EvidenceItem],
    tags=["Trips"],
    summary="Compute evidence for a trip",
    description="Run all deterministic evidence analyzers (route, fare, no-show, chat) for a trip.",
)
async def get_trip_evidence(trip_id: int):
    return await _gather_trip_evidence(trip_id)


@router.get(
    "/disputes",
    response_model=list[DisputeListItem],
    tags=["Disputes"],
    summary="List disputes",
    description="Return all disputes with their latest ruling outcome and refund amount.",
)
async def list_disputes(
    account_id: int | None = None,
    include_synthetic: bool = False,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(models.Dispute).order_by(models.Dispute.created_at.desc())

    if account_id is not None:
        stmt = (
            stmt.join(models.Trip, models.Trip.id == models.Dispute.trip_id)
            .where(
                or_(
                    models.Dispute.filed_by == account_id,
                    models.Trip.rider_id == account_id,
                    models.Trip.driver_id == account_id,
                )
            )
        )

    if not include_synthetic:
        stmt = stmt.where(
            models.Dispute.external_id.is_not(None),
            ~models.Dispute.external_id.like("VAR-%"),
        )

    disputes = (await session.execute(stmt)).scalars().all()
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
                "external_id": d.external_id,
                "outcome": r.outcome.value if r else None,
                "refund_amount": r.refund_amount if r else None,
                "llm_degraded": r.llm_degraded if r else None,
                "confidence": r.confidence if r else None,
                "ruling_created_at": r.created_at if r else None,
            }
        )
    return result


@router.get(
    "/trips",
    response_model=list[TripListItem],
    tags=["Trips"],
    summary="List trips",
)
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


@router.get(
    "/trips/{trip_id}/chat",
    response_model=list[ChatMessageItem],
    tags=["Trips"],
    summary="Get a trip's chat log",
)
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


@router.get(
    "/trips/{trip_id}/gps",
    response_model=TripGpsResponse,
    tags=["Trips"],
    summary="Get a trip's GPS trace",
    description="Return the optimal route polyline and the ordered GPS points for a trip.",
)
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


@router.get(
    "/queue",
    response_model=list[QueueItem],
    tags=["Queue"],
    summary="Inspect the priority queue",
    description="Return queued disputes ordered by priority, with wait time and SLA-breach status.",
)
async def get_queue(session: AsyncSession = Depends(get_session)):
    return await list_queue(session=session)


@router.get(
    "/meta/categories",
    response_model=list[CategoryMeta],
    tags=["Meta"],
    summary="List dispute categories",
    description="Return the dispute categories the system supports, with example claims.",
)
async def get_categories():
    return _CATEGORY_META


@router.get(
    "/meta/formulas",
    response_model=list[dict],
    tags=["Meta"],
    summary="List deterministic formulas",
    description=(
        "Return every deterministic calculation the system uses (confidence, refund "
        "reconciliation, abuse risk, fare, route deviation, no-show, fraud, queue "
        "priority, sentiment) with its source location."
    ),
)
async def get_formulas():
    return [f.model_dump() for f in FORMULAS]


@router.get(
    "/meta/policies",
    response_model=list[PolicySection],
    tags=["Meta"],
    summary="List policy sections",
    description=(
        "Return the sections parsed from backend/policies/*.md, each with its id, "
        "title, body text and source file. Precedent rulings are tagged 'precedent'."
    ),
)
async def get_policies():
    return load_policy_sections()


@router.get(
    "/meta/rules",
    response_model=list[RuleItem],
    tags=["Meta"],
    summary="List deterministic rules",
    description=(
        "Return the parsed rules/rules.yaml entries: id, category, policy section "
        "citation, conditions expression, outcome and refund amount formula."
    ),
)
async def get_rules():
    return [r.model_dump() for r in load_rules()]


def _fmt_money(value: float) -> str:
    return f"${value:.2f}"


@router.get(
    "/meta/settings",
    response_model=SettingsResponse,
    tags=["Meta"],
    summary="Effective non-secret configuration",
    description=(
        "Return the effective, non-secret runtime configuration: model per agent "
        "role, the LLM mock flag, and the policy thresholds and escalation values. "
        "API keys, base URLs and other credentials are never included."
    ),
)
async def get_settings():
    advocate = settings.llm_model_advocate or settings.llm_model
    judge = settings.llm_model_judge or settings.llm_model
    return {
        "models": [
            ModelAssignment(agent="RiderAdvocate", model=advocate, purpose="Presents the rider's case"),
            ModelAssignment(agent="DriverAdvocate", model=advocate, purpose="Presents the driver's defense"),
            ModelAssignment(agent="Judge", model=judge, purpose="Evaluates evidence and applies policy"),
        ],
        "llm_mock": settings.llm_mock,
        "policy_version": settings.policy_version,
        "policy_numbers": [
            ConfigEntry(key="noshow_cancellation_fee", label="Cancellation fee", value=_fmt_money(settings.noshow_cancellation_fee), source="no_show_fee.md §2.2"),
            ConfigEntry(key="noshow_goodwill_credit", label="Goodwill credit", value=_fmt_money(settings.noshow_goodwill_credit), source="no_show_fee.md §2.4"),
            ConfigEntry(key="noshow_min_wait_min", label="Free wait time", value=f"{settings.noshow_min_wait_min:g} minutes", source="no_show_fee.md §2.1"),
            ConfigEntry(key="noshow_proximity_m", label="Arrival radius", value=f"{settings.noshow_proximity_m:g} m", source="no_show_fee.md §2.1"),
            ConfigEntry(key="route_buffer_m", label="Off-route buffer", value=f"{settings.route_buffer_m:g} m", source="route_deviation.md §1.3"),
            ConfigEntry(key="route_escalate_km", label="Major detour threshold", value=f"{settings.route_escalate_km:g} km extra", source="route_deviation.md §1.3"),
            ConfigEntry(key="fare_tolerance_pct", label="Fare tolerance", value=f"{settings.fare_tolerance_pct * 100:g}%", source="fare_surge_promo.md §3.3"),
        ],
        "thresholds": [
            ConfigEntry(key="abuse_risk_threshold", label="Abuse-risk threshold", value=f"{settings.abuse_risk_threshold:g}", source="app/config.py"),
            ConfigEntry(key="fraud_dispute_frequency_days", label="Fraud window", value=f"{settings.fraud_dispute_frequency_days} days", source="app/config.py"),
            ConfigEntry(key="fraud_dispute_frequency_threshold", label="Fraud dispute threshold", value=f"{settings.fraud_dispute_frequency_threshold}", source="app/config.py"),
            ConfigEntry(key="fraud_win_rate_threshold", label="Fraud win-rate threshold", value=f"{settings.fraud_win_rate_threshold:g}", source="app/config.py"),
            ConfigEntry(key="fraud_repeat_deviation_threshold", label="Repeat-deviation threshold", value=f"{settings.fraud_repeat_deviation_threshold}", source="app/config.py"),
            ConfigEntry(key="fraud_account_age_days", label="Young-account window", value=f"{settings.fraud_account_age_days} days", source="app/config.py"),
            ConfigEntry(key="fraud_penalty_threshold", label="Fraud penalty threshold", value=f"{settings.fraud_penalty_threshold:g}", source="app/config.py"),
            ConfigEntry(key="fraud_penalty_weight", label="Fraud penalty weight", value=f"{settings.fraud_penalty_weight:g}", source="app/config.py"),
        ],
        "escalation": [
            ConfigEntry(key="escalation_enabled", label="Escalation enabled", value="true" if settings.escalation_enabled else "false", source="app/config.py"),
            ConfigEntry(key="escalation_low_value", label="Low-value threshold", value=_fmt_money(settings.escalation_low_value), source="app/config.py"),
            ConfigEntry(key="escalation_high_value", label="High-value threshold", value=_fmt_money(settings.escalation_high_value), source="app/config.py"),
            ConfigEntry(key="escalation_threshold", label="Confidence threshold", value=f"{settings.escalation_threshold:g}", source="app/config.py"),
            ConfigEntry(key="escalation_fraud_threshold", label="Fraud confidence threshold", value=f"{settings.escalation_fraud_threshold:g}", source="app/config.py"),
        ],
    }
