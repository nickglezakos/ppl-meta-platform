"""add_left_object_trigger_fields

Adds left_object trigger configuration columns for stationary / abandoned object mode.

Revision ID: add_left_object_trigger_fields
Revises: add_velocity_trigger_fields
Create Date: 2026-09-10

"""
from alembic import op
import sqlalchemy as sa


revision = "add_left_object_trigger_fields"
down_revision = "add_velocity_trigger_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_class_allowlist",
            sa.Text(),
            nullable=True,
            comment='JSON array of COCO class labels (e.g. ["backpack","handbag","suitcase","bottle"])',
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_roi",
            sa.Text(),
            nullable=True,
            comment="JSON polygon of normalized viewport coords [[x,y],...] in 0-1; null = full frame",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_t_stable_seconds",
            sa.Integer(),
            nullable=True,
            server_default="60",
            comment="Seconds of low motion before track is STABLE",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_t_abandon_seconds",
            sa.Integer(),
            nullable=True,
            server_default="30",
            comment="Seconds without nearby person before ABANDONED (V2)",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_min_box_area_px",
            sa.Integer(),
            nullable=True,
            server_default="400",
            comment="Minimum bbox area in pixels",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_require_person_left",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
            comment="When true, fire only after ATTENDED then ABANDONED (V2)",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_proximity_px",
            sa.Float(),
            nullable=True,
            server_default="120",
            comment="Max body-object center distance in pixels for ATTENDED (V2)",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "left_object_iou_threshold",
            sa.Float(),
            nullable=True,
            server_default="0.3",
            comment="Minimum bbox IoU to continue an object track across cycles",
        ),
    )


def downgrade() -> None:
    op.drop_column("triggers", "left_object_iou_threshold")
    op.drop_column("triggers", "left_object_proximity_px")
    op.drop_column("triggers", "left_object_require_person_left")
    op.drop_column("triggers", "left_object_min_box_area_px")
    op.drop_column("triggers", "left_object_t_abandon_seconds")
    op.drop_column("triggers", "left_object_t_stable_seconds")
    op.drop_column("triggers", "left_object_roi")
    op.drop_column("triggers", "left_object_class_allowlist")
