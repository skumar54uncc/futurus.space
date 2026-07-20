"""Add last_heartbeat_at for lease-based simulation recovery

Revision ID: 004_add_last_heartbeat
Revises: 003_add_cascade_and_tz
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_last_heartbeat"
down_revision = "003_add_cascade_and_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "last_heartbeat_at")
