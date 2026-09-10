"""add_velocity_trigger_fields

Adds velocity trigger configuration columns for velocity mode.

Revision ID: add_velocity_trigger_fields
Revises: add_body_posture_trigger_fields
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


revision = "add_velocity_trigger_fields"
down_revision = "add_body_posture_trigger_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "velocity_scope",
            sa.String(length=16),
            nullable=True,
            server_default="crowd",
            comment="Velocity trigger scope: crowd | single",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "velocity_band",
            sa.String(length=32),
            nullable=True,
            server_default="walking",
            comment="Gait band floor: walking | light_running | running | fast_running",
        ),
    )


def downgrade() -> None:
    op.drop_column("triggers", "velocity_band")
    op.drop_column("triggers", "velocity_scope")
