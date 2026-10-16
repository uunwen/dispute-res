"""add dispute_reviews audit log

Revision ID: a9b8c7d6e5f4
Revises: c9d0e1f2a3b4
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "a9b8c7d6e5f4"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispute_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dispute_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=50), nullable=False, server_default=sa.text("'ops'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dispute_reviews_dispute_id", "dispute_reviews", ["dispute_id"])


def downgrade() -> None:
    op.drop_index("ix_dispute_reviews_dispute_id", table_name="dispute_reviews")
    op.drop_table("dispute_reviews")
