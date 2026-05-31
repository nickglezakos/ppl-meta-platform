"""presence decision history table

Revision ID: 20260530_0003
Revises: 20260530_0002
Create Date: 2026-05-30 15:58:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260530_0003"
down_revision = "20260530_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presence_decision_history",
        sa.Column("decision_uuid", sa.String(length=64), primary_key=True),
        sa.Column("session_uuid", sa.String(length=64), nullable=False),
        sa.Column("user_uuid", sa.String(length=64), nullable=False),
        sa.Column("device_uuid", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_presence_decision_history_session_uuid", "presence_decision_history", ["session_uuid"])
    op.create_index("ix_presence_decision_history_user_uuid", "presence_decision_history", ["user_uuid"])
    op.create_index("ix_presence_decision_history_device_uuid", "presence_decision_history", ["device_uuid"])
    op.create_index("ix_presence_decision_history_decision", "presence_decision_history", ["decision"])


def downgrade() -> None:
    op.drop_index("ix_presence_decision_history_decision", table_name="presence_decision_history")
    op.drop_index("ix_presence_decision_history_device_uuid", table_name="presence_decision_history")
    op.drop_index("ix_presence_decision_history_user_uuid", table_name="presence_decision_history")
    op.drop_index("ix_presence_decision_history_session_uuid", table_name="presence_decision_history")
    op.drop_table("presence_decision_history")