"""add attachments table

Revision ID: f1e2d3c4b5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-10-16
"""

import sqlalchemy as sa
from alembic import op

revision = "f1e2d3c4b5a6"
down_revision = "a9b8c7d6e5f4"
branch_labels = None
depends_on = None

ATTACHMENT_KIND_ENUM = sa.Enum(
    "photo", "receipt", "chat_log", "other", name="attachment_kind"
)


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dispute_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("kind", ATTACHMENT_KIND_ENUM, nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("analysis", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attachments_dispute_id", "attachments", ["dispute_id"])


def downgrade() -> None:
    op.drop_index("ix_attachments_dispute_id", table_name="attachments")
    op.drop_table("attachments")
    ATTACHMENT_KIND_ENUM.drop(op.get_bind(), checkfirst=True)
