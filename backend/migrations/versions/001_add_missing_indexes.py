"""Add indexes for simulation_events and reports.share_token

Revision ID: 001_add_indexes
Revises:
Create Date: 2026-03-23
"""
from alembic import op

revision = "001_add_indexes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SECURITY/PERFORMANCE: Event log and public share lookups
    op.create_index(
        "ix_simulation_events_simulation_id",
        "simulation_events",
        ["simulation_id"],
        unique=False,
    )
    op.create_index(
        "ix_reports_share_token",
        "reports",
        ["share_token"],
        unique=True,
    )
    op.create_index(
        "ix_simulation_events_sim_id_id_desc",
        "simulation_events",
        ["simulation_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_simulation_events_sim_id_id_desc", table_name="simulation_events")
    op.drop_index("ix_reports_share_token", table_name="reports")
    op.drop_index("ix_simulation_events_simulation_id", table_name="simulation_events")
