from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.db.enums import DisputeCategory


class DisputeCreate(BaseModel):
    trip_id: int = Field(..., description="ID of the trip being disputed.")
    category: DisputeCategory = Field(
        ...,
        description="Dispute category. Aliases `cancellation_fee`, `surge_pricing` and `fare` are accepted.",
    )
    claim_text: str = Field(..., description="The claimant's natural-language claim.")
    filed_by: int | None = Field(
        None,
        description="Account ID of the party filing the dispute. If omitted, derived from ``filed_by_role``.",
    )
    filed_by_role: Literal["rider", "driver"] = Field(
        "rider",
        description="Which trip party files the dispute when ``filed_by`` is omitted.",
    )

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
    outcome: str = Field(..., description="Final outcome: `full_refund`, `partial_refund` or `no_refund`.")
    refund_amount: float = Field(..., description="Refund amount in currency units (0 for no refund).")
    confidence: float = Field(..., description="Judge confidence score in [0, 1].")
    reasoning: str = Field(..., description="Natural-language reasoning summary.")
    rule_outcome: dict[str, Any] = Field(..., description="Deterministic rule result, LLM ruling and reconciliation details.")
    evidence_ids: list[str] = Field(..., description="Evidence ids the ruling is based on.")
    escalated: bool = Field(..., description="Whether the ruling was escalated to human review.")
    human_review_summary: dict[str, Any] | None = Field(None, description="Case summary for the human reviewer (if escalated).")
    llm_degraded: bool = Field(False, description="Whether the LLM was unavailable and rule fallback was used.")
    model_info: dict[str, Any] | None = Field(None, description="Models used per agent role.")
    created_at: datetime


class DisputeListItem(BaseModel):
    id: int
    trip_id: int
    category: str
    status: str
    priority: str
    claim_text: str
    created_at: datetime
    external_id: str | None = None
    outcome: str | None = None
    refund_amount: float | None = None
    llm_degraded: bool | None = None
    confidence: float | None = None
    ruling_created_at: datetime | None = None


class DisputeReviewCreate(BaseModel):
    action: Literal["confirm", "appeal", "assign"] = Field(
        ..., description="Review action to record."
    )
    note: str | None = Field(None, description="Optional free-text note.")


class DisputeReviewResponse(BaseModel):
    id: int
    dispute_id: int
    action: str
    note: str | None
    actor: str
    created_at: datetime


class AccountItem(BaseModel):
    id: int
    name: str
    role: str


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


class PolicySection(BaseModel):
    id: str
    title: str
    text: str
    source: str
    tag: str | None = None


class RuleItem(BaseModel):
    id: str
    category: str
    citation: str
    conditions: str
    outcome: str
    amount: str


class ModelAssignment(BaseModel):
    agent: str
    model: str
    purpose: str


class ConfigEntry(BaseModel):
    key: str
    label: str
    value: str
    source: str


class SettingsResponse(BaseModel):
    models: list[ModelAssignment]
    llm_mock: bool
    policy_version: str
    policy_numbers: list[ConfigEntry]
    thresholds: list[ConfigEntry]
    escalation: list[ConfigEntry]
