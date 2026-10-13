"""initial tables

Revision ID: b1e2a3c4d5f6
Revises:
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from pgvector.sqlalchemy import Vector

from app.config import settings

revision = "b1e2a3c4d5f6"
down_revision = None
branch_labels = None
depends_on = None

account_role = postgresql.ENUM(
    "rider", "driver", name="account_role", create_type=False
)
dispute_category = postgresql.ENUM(
    "fare_dispute",
    "route_deviation",
    "surge_pricing",
    "cancellation_fee",
    "service_quality",
    "other",
    name="dispute_category",
    create_type=False,
)
ruling_outcome = postgresql.ENUM(
    "full_refund",
    "partial_refund",
    "no_refund",
    "favor_rider",
    "favor_driver",
    name="ruling_outcome",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    account_role.create(op.get_bind(), checkfirst=True)
    dispute_category.create(op.get_bind(), checkfirst=True)
    ruling_outcome.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role", account_role, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("age_band", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rider_id", sa.BigInteger(), nullable=False),
        sa.Column("driver_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("pickup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dropoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_fare", sa.Float(), nullable=False),
        sa.Column("actual_fare", sa.Float(), nullable=False),
        sa.Column("surge_multiplier", sa.Float(), nullable=False),
        sa.Column("promo_code", sa.String(length=100), nullable=True),
        sa.Column("promo_discount", sa.Float(), nullable=False),
        sa.Column("base_fare", sa.Float(), nullable=False),
        sa.Column("per_km_rate", sa.Float(), nullable=False),
        sa.Column("per_min_rate", sa.Float(), nullable=False),
        sa.Column("cancellation_fee", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("estimated_distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_duration_min", sa.Float(), nullable=False),
        sa.Column(
            "optimal_route_polyline",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["driver_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["rider_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_driver_id", "trips", ["driver_id"], unique=False)
    op.create_index("ix_trips_rider_id", "trips", ["rider_id"], unique=False)

    op.create_table(
        "gps_points",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.BigInteger(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("speed_kmh", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gps_points_trip_id", "gps_points", ["trip_id"], unique=False)
    op.create_index(
        "ix_gps_points_trip_id_ts", "gps_points", ["trip_id", "ts"], unique=False
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"], unique=False)
    op.create_index("ix_chat_messages_trip_id", "chat_messages", ["trip_id"], unique=False)
    op.create_index(
        "ix_chat_messages_trip_id_ts", "chat_messages", ["trip_id", "ts"], unique=False
    )

    op.create_table(
        "disputes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.BigInteger(), nullable=False),
        sa.Column("filed_by", sa.BigInteger(), nullable=False),
        sa.Column("category", dispute_category, nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["filed_by"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_disputes_filed_by", "disputes", ["filed_by"], unique=False)
    op.create_index("ix_disputes_trip_id", "disputes", ["trip_id"], unique=False)

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dispute_id", sa.BigInteger(), nullable=False),
        sa.Column("sender", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=50), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_messages_dispute_id", "agent_messages", ["dispute_id"], unique=False
    )

    op.create_table(
        "rulings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dispute_id", sa.BigInteger(), nullable=False),
        sa.Column("outcome", ruling_outcome, nullable=False),
        sa.Column("refund_amount", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("rule_outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("escalated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rulings_dispute_id", "rulings", ["dispute_id"], unique=False)

    op.create_table(
        "policy_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(settings.embedding_dim), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("policy_chunks")
    op.drop_table("rulings")
    op.drop_table("agent_messages")
    op.drop_table("disputes")
    op.drop_table("chat_messages")
    op.drop_table("gps_points")
    op.drop_table("trips")
    op.drop_table("accounts")

    ruling_outcome.drop(op.get_bind(), checkfirst=True)
    dispute_category.drop(op.get_bind(), checkfirst=True)
    account_role.drop(op.get_bind(), checkfirst=True)
