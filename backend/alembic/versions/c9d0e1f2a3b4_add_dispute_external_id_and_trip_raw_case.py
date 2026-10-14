"""add dispute external_id and trip raw_case

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-15
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "disputes",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint("uq_disputes_external_id", "disputes", ["external_id"])
    op.add_column(
        "trips",
        sa.Column("raw_case", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trips", "raw_case")
    op.drop_constraint("uq_disputes_external_id", "disputes", type_="unique")
    op.drop_column("disputes", "external_id")
