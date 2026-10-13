"""enforce embedding dimension and track provider/model on policy_chunks

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # policy_chunks is derived data rebuilt by scripts/ingest_policies.py, so a
    # dimension change can safely wipe it instead of attempting an invalid cast.
    op.execute("TRUNCATE TABLE policy_chunks")
    op.execute(
        f"ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector({settings.embedding_dim})"
    )
    op.add_column(
        "policy_chunks",
        sa.Column("embedding_provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "policy_chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_chunks", "embedding_model")
    op.drop_column("policy_chunks", "embedding_provider")
    op.execute("ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector")
