"""consolidate dispute_category to handbook values

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-10
"""

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_TARGET_VALUES = (
    "'route_deviation', 'no_show', 'fare_dispute', 'property_damage', 'safety_incident'"
)
_LEGACY_VALUES = (
    "'fare_dispute', 'route_deviation', 'surge_pricing', 'cancellation_fee', "
    "'service_quality', 'other', 'safety_incident'"
)


def upgrade() -> None:
    # Create the target enum type, then migrate data as plain text (so the old
    # enum constraint does not block new values), then cast to the target type.
    op.execute(f"CREATE TYPE dispute_category_tmp AS ENUM ({_TARGET_VALUES})")
    op.execute("ALTER TABLE disputes ALTER COLUMN category TYPE text")
    op.execute("UPDATE disputes SET category = 'fare_dispute' WHERE category = 'surge_pricing'")
    op.execute("UPDATE disputes SET category = 'no_show' WHERE category = 'cancellation_fee'")
    op.execute(
        "UPDATE disputes SET category = 'route_deviation' WHERE category IN ('service_quality', 'other')"
    )
    op.execute(
        "ALTER TABLE disputes ALTER COLUMN category TYPE dispute_category_tmp "
        "USING category::dispute_category_tmp"
    )
    op.execute("DROP TYPE dispute_category")
    op.execute("ALTER TYPE dispute_category_tmp RENAME TO dispute_category")


def downgrade() -> None:
    # Restore the legacy enum type. The merge of surge_pricing into fare_dispute
    # is not reversible, so data is mapped back on a best-effort basis.
    op.execute(f"CREATE TYPE dispute_category_tmp AS ENUM ({_LEGACY_VALUES})")
    op.execute("ALTER TABLE disputes ALTER COLUMN category TYPE text")
    op.execute("UPDATE disputes SET category = 'cancellation_fee' WHERE category = 'no_show'")
    op.execute("UPDATE disputes SET category = 'other' WHERE category = 'property_damage'")
    op.execute(
        "ALTER TABLE disputes ALTER COLUMN category TYPE dispute_category_tmp "
        "USING category::dispute_category_tmp"
    )
    op.execute("DROP TYPE dispute_category")
    op.execute("ALTER TYPE dispute_category_tmp RENAME TO dispute_category")
