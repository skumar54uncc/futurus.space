"""Add notify_on_complete column to simulations

Revision ID: 002_add_notify_on_complete
Revises: 001_add_indexes
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_notify_on_complete"
down_revision = "001_add_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("notify_on_complete", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("simulations", "notify_on_complete")
