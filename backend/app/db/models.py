import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.base import Base
from app.db.enums import AccountRole, DisputeCategory, RulingOutcome

ACCOUNT_ROLE_ENUM = Enum(
    AccountRole,
    name="account_role",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
)
DISPUTE_CATEGORY_ENUM = Enum(
    DisputeCategory,
    name="dispute_category",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
)
RULING_OUTCOME_ENUM = Enum(
    RulingOutcome,
    name="ruling_outcome",
    native_enum=True,
    values_callable=lambda e: [m.value for m in e],
)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role: Mapped[AccountRole] = mapped_column(ACCOUNT_ROLE_ENUM, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    age_band: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rider_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=False, index=True
    )
    driver_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=False, index=True
    )
    requested_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    pickup_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dropoff_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_fare: Mapped[float] = mapped_column(Float, nullable=False)
    actual_fare: Mapped[float] = mapped_column(Float, nullable=False)
    surge_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    promo_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    promo_discount: Mapped[float] = mapped_column(Float, nullable=False)
    base_fare: Mapped[float] = mapped_column(Float, nullable=False)
    per_km_rate: Mapped[float] = mapped_column(Float, nullable=False)
    per_min_rate: Mapped[float] = mapped_column(Float, nullable=False)
    cancellation_fee: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration_min: Mapped[float] = mapped_column(Float, nullable=False)
    optimal_route_polyline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class GpsPoint(Base):
    __tablename__ = "gps_points"
    __table_args__ = (Index("ix_gps_points_trip_id_ts", "trip_id", "ts"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trips.id"), nullable=False, index=True
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_trip_id_ts", "trip_id", "ts"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trips.id"), nullable=False, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trips.id"), nullable=False, index=True
    )
    filed_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=False, index=True
    )
    category: Mapped[DisputeCategory] = mapped_column(DISPUTE_CATEGORY_ENUM, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dispute_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("disputes.id"), nullable=False, index=True
    )
    sender: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(50), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Ruling(Base):
    __tablename__ = "rulings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dispute_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("disputes.id"), nullable=False, index=True
    )
    outcome: Mapped[RulingOutcome] = mapped_column(RULING_OUTCOME_ENUM, nullable=False)
    refund_amount: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    rule_outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    escalated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    human_review_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_degraded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    model_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dim), nullable=False
    )
    embedding_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
