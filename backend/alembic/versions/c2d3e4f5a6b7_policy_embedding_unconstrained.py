"""make policy_chunks.embedding unconstrained

Revision ID: c2d3e4f5a6b7
Revises: b1e2a3c4d5f6
Create Date: 2026-10-09
"""

from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1e2a3c4d5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector")


def downgrade() -> None:
    op.execute("ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector(1536)")
