"""Add CASCADE to simulation FK columns and convert to TIMESTAMPTZ

Revision ID: 003_add_cascade_and_tz
Create Date: 2026-03-27
"""
from alembic import op

revision = "003_add_cascade_and_tz"
down_revision = "002_add_notify_on_complete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop and recreate FK with CASCADE on simulation_events
    op.drop_constraint(
        "simulation_events_simulation_id_fkey",
        "simulation_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "simulation_events_simulation_id_fkey",
        "simulation_events", "simulations",
        ["simulation_id"], ["id"],
        ondelete="CASCADE",
    )

    # Drop and recreate FK with CASCADE on reports
    op.drop_constraint(
        "reports_simulation_id_fkey",
        "reports",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "reports_simulation_id_fkey",
        "reports", "simulations",
        ["simulation_id"], ["id"],
        ondelete="CASCADE",
    )

    # Convert DateTime columns to TIMESTAMPTZ (timezone-aware)
    op.execute(
        "ALTER TABLE simulations ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE simulations ALTER COLUMN started_at TYPE TIMESTAMPTZ "
        "USING started_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE simulations ALTER COLUMN completed_at TYPE TIMESTAMPTZ "
        "USING completed_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE simulation_events ALTER COLUMN timestamp TYPE TIMESTAMPTZ "
        "USING timestamp AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN last_active_at TYPE TIMESTAMPTZ "
        "USING last_active_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN billing_period_start TYPE TIMESTAMPTZ "
        "USING billing_period_start AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN subscription_period_end TYPE TIMESTAMPTZ "
        "USING subscription_period_end AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE reports ALTER COLUMN created_at TYPE TIMESTAMPTZ "
        "USING created_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    # Reverse CASCADE removal
    op.drop_constraint(
        "simulation_events_simulation_id_fkey",
        "simulation_events",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "simulation_events_simulation_id_fkey",
        "simulation_events", "simulations",
        ["simulation_id"], ["id"],
    )
    op.drop_constraint(
        "reports_simulation_id_fkey",
        "reports",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "reports_simulation_id_fkey",
        "reports", "simulations",
        ["simulation_id"], ["id"],
    )

    # Reverse TIMESTAMPTZ to TIMESTAMP
    for table, col in [
        ("simulations", "created_at"),
        ("simulations", "started_at"),
        ("simulations", "completed_at"),
        ("simulation_events", "timestamp"),
        ("users", "created_at"),
        ("users", "last_active_at"),
        ("users", "billing_period_start"),
        ("users", "subscription_period_end"),
        ("reports", "created_at"),
    ]:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP "
            f"USING {col} AT TIME ZONE 'UTC'"
        )
