"""add_body_posture_trigger_fields

Adds body posture trigger configuration columns for body_posture mode.

Revision ID: add_body_posture_trigger_fields
Revises: add_vprofile_match_fields
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa


revision = "add_body_posture_trigger_fields"
down_revision = "add_vprofile_match_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "body_posture_target",
            sa.String(length=32),
            nullable=True,
            server_default="horizontal",
            comment="Target posture for body_posture mode: horizontal | upright | either",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "body_posture_window_size",
            sa.Integer(),
            nullable=True,
            server_default="4",
            comment="Consecutive instant-body scans used for voting (3-4)",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "body_posture_min_matches",
            sa.Integer(),
            nullable=True,
            server_default="3",
            comment="Minimum matching scans in the window required to fire",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "body_posture_min_confidence",
            sa.Float(),
            nullable=True,
            server_default="0.5",
            comment="Minimum posture_confidence for a scan label to count",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "body_posture_iou_threshold",
            sa.Float(),
            nullable=True,
            server_default="0.3",
            comment="Minimum bbox IoU to continue a body track across cycles",
        ),
    )


def downgrade() -> None:
    op.drop_column("triggers", "body_posture_iou_threshold")
    op.drop_column("triggers", "body_posture_min_confidence")
    op.drop_column("triggers", "body_posture_min_matches")
    op.drop_column("triggers", "body_posture_window_size")
    op.drop_column("triggers", "body_posture_target")
