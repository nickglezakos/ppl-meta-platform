"""initial presence tables

Revision ID: 20260530_0001
Revises: 
Create Date: 2026-05-30 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presence_sessions",
        sa.Column("session_uuid", sa.String(length=64), primary_key=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "presence_attempts",
        sa.Column("attempt_uuid", sa.String(length=64), primary_key=True),
        sa.Column("session_uuid", sa.String(length=64), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_presence_attempts_session_uuid", "presence_attempts", ["session_uuid"])
    op.create_table(
        "presence_resources",
        sa.Column("resource_uuid", sa.String(length=64), primary_key=True),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_presence_resources_resource_type", "presence_resources", ["resource_type"])


def downgrade() -> None:
    op.drop_index("ix_presence_resources_resource_type", table_name="presence_resources")
    op.drop_table("presence_resources")
    op.drop_index("ix_presence_attempts_session_uuid", table_name="presence_attempts")
    op.drop_table("presence_attempts")
    op.drop_table("presence_sessions")
