from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.db.enums import DisputeCategory


class DisputeCreate(BaseModel):
    trip_id: int
    category: DisputeCategory
    claim_text: str
    filed_by: int

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, v):
        aliases = {
            "cancellation_fee": "no_show",
            "surge_pricing": "fare_dispute",
            "fare": "fare_dispute",
        }
        if isinstance(v, str) and v in aliases:
            return aliases[v]
        return v


class DisputeResponse(BaseModel):
    id: int
    trip_id: int
    filed_by: int
    category: str
    claim_text: str
    status: str
    priority: str
    created_at: datetime


class MessageResponse(BaseModel):
    id: int
    dispute_id: int
    sender: str
    recipient: str
    message_type: str
    content: dict[str, Any]
    created_at: datetime


class RulingResponse(BaseModel):
    id: int
    dispute_id: int
    outcome: str
    refund_amount: float
    confidence: float
    reasoning: str
    rule_outcome: dict[str, Any]
    evidence_ids: list[str]
    escalated: bool
    human_review_summary: dict[str, Any] | None = None
    llm_degraded: bool = False
    model_info: dict[str, Any] | None = None
    created_at: datetime


class DisputeListItem(BaseModel):
    id: int
    trip_id: int
    category: str
    status: str
    priority: str
    claim_text: str
    created_at: datetime
    outcome: str | None = None
    refund_amount: float | None = None
    llm_degraded: bool | None = None


class TripListItem(BaseModel):
    id: int
    rider_id: int
    driver_id: int
    rider: str
    driver: str
    fare: float
    scenario: str


class ChatMessageItem(BaseModel):
    id: int
    trip_id: int
    sender_id: int
    sender: str
    text: str
    ts: datetime


class GpsPointItem(BaseModel):
    lat: float
    lng: float
    ts: datetime
    speed_kmh: float | None


class TripGpsResponse(BaseModel):
    optimal_route: list[list[float]]
    points: list[GpsPointItem]


class QueueItem(BaseModel):
    dispute_id: int
    category: str
    amount: float
    priority: float
    wait_time_seconds: float
    sla_seconds: int
    breached: bool


class CategoryMeta(BaseModel):
    value: str
    label: str
    example_claim: str
    supported: bool
