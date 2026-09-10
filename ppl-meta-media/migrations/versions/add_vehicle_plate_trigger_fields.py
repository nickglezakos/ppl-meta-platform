"""add_vehicle_plate_trigger_fields

Adds vehicle_plate trigger configuration columns.

Revision ID: add_vehicle_plate_trigger_fields
Revises: add_left_object_trigger_fields
Create Date: 2026-09-10

"""
from alembic import op
import sqlalchemy as sa


revision = "add_vehicle_plate_trigger_fields"
down_revision = "add_left_object_trigger_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_class_allowlist",
            sa.Text(),
            nullable=True,
            comment='JSON array of COCO vehicle labels (e.g. ["car","motorcycle","bicycle"])',
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_roi",
            sa.Text(),
            nullable=True,
            comment="JSON polygon of normalized viewport coords [[x,y],...] in 0-1; null = full frame",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_t_stable_seconds",
            sa.Integer(),
            nullable=True,
            server_default="15",
            comment="Seconds of low motion before vehicle track is STABLE",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_min_box_area_px",
            sa.Integer(),
            nullable=True,
            server_default="800",
            comment="Minimum vehicle bbox area in pixels",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_plate_ocr_enabled",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("true"),
            comment="When true, attempt plate OCR on vehicle crops (V2)",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_plate_ocr_every_n_cycles",
            sa.Integer(),
            nullable=True,
            server_default="2",
            comment="Run plate OCR every N instant cycles",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "vehicle_iou_threshold",
            sa.Float(),
            nullable=True,
            server_default="0.3",
            comment="Minimum bbox IoU to continue a vehicle track across cycles",
        ),
    )


def downgrade() -> None:
    op.drop_column("triggers", "vehicle_iou_threshold")
    op.drop_column("triggers", "vehicle_plate_ocr_every_n_cycles")
    op.drop_column("triggers", "vehicle_plate_ocr_enabled")
    op.drop_column("triggers", "vehicle_min_box_area_px")
    op.drop_column("triggers", "vehicle_t_stable_seconds")
    op.drop_column("triggers", "vehicle_roi")
    op.drop_column("triggers", "vehicle_class_allowlist")
