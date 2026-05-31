"""profiles and analytics tables

Revision ID: 20260530_0002
Revises: 20260530_0001
Create Date: 2026-05-30 14:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0002"
down_revision = "20260530_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presence_profiles",
        sa.Column("presence_profile_uuid", sa.String(length=64), primary_key=True),
        sa.Column("profile_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_presence_profiles_profile_type", "presence_profiles", ["profile_type"])
    op.create_table(
        "presence_analytics_events",
        sa.Column("event_uuid", sa.String(length=64), primary_key=True),
        sa.Column("session_uuid", sa.String(length=64), nullable=False),
        sa.Column("user_uuid", sa.String(length=64), nullable=False),
        sa.Column("device_uuid", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_presence_analytics_events_session_uuid", "presence_analytics_events", ["session_uuid"])
    op.create_index("ix_presence_analytics_events_user_uuid", "presence_analytics_events", ["user_uuid"])
    op.create_index("ix_presence_analytics_events_device_uuid", "presence_analytics_events", ["device_uuid"])
    op.create_index("ix_presence_analytics_events_outcome", "presence_analytics_events", ["outcome"])


def downgrade() -> None:
    op.drop_index("ix_presence_analytics_events_outcome", table_name="presence_analytics_events")
    op.drop_index("ix_presence_analytics_events_device_uuid", table_name="presence_analytics_events")
    op.drop_index("ix_presence_analytics_events_user_uuid", table_name="presence_analytics_events")
    op.drop_index("ix_presence_analytics_events_session_uuid", table_name="presence_analytics_events")
    op.drop_table("presence_analytics_events")
    op.drop_index("ix_presence_profiles_profile_type", table_name="presence_profiles")
    op.drop_table("presence_profiles")