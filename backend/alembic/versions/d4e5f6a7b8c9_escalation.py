"""escalation: human_review_summary column + safety_incident category

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rulings",
        sa.Column("human_review_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute("ALTER TYPE dispute_category ADD VALUE IF NOT EXISTS 'safety_incident'")


def downgrade() -> None:
    op.drop_column("rulings", "human_review_summary")
    # Postgres does not support removing an enum value; safety_incident is left in place.
