"""add_motion_trigger_fields

Rename velocity trigger mode to motion and add demographic-style
motion_conditions / motion_condition_logic / motion_roi. Backfill existing
velocity rows into a single speed_band condition.

Revision ID: add_motion_trigger_fields
Revises: add_vehicle_plate_trigger_fields
Create Date: 2026-10-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision = "add_motion_trigger_fields"
down_revision = "add_vehicle_plate_trigger_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "triggers",
        sa.Column(
            "motion_scope",
            sa.String(length=16),
            nullable=True,
            server_default="crowd",
            comment="Motion trigger speed scope: crowd | single",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "motion_conditions",
            sa.Text(),
            nullable=True,
            comment='JSON array: [{"field":"speed_band|motion_class|roi_transit","operator":"...","value":...}]',
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "motion_condition_logic",
            sa.String(length=8),
            nullable=True,
            server_default="and",
            comment="Combine motion_conditions with and | or",
        ),
    )
    op.add_column(
        "triggers",
        sa.Column(
            "motion_roi",
            sa.Text(),
            nullable=True,
            comment="JSON polygon of normalized viewport coords [[x,y],...] in 0-1",
        ),
    )

    conn = op.get_bind()

    # Copy scope from legacy velocity_scope
    conn.execute(
        text(
            """
            UPDATE triggers
            SET motion_scope = COALESCE(velocity_scope, 'crowd')
            WHERE trigger_mode IN ('velocity', 'motion')
               OR velocity_scope IS NOT NULL
            """
        )
    )

    # Backfill motion_conditions from velocity_band for velocity rows
    rows = conn.execute(
        text(
            """
            SELECT id, velocity_band, motion_conditions
            FROM triggers
            WHERE trigger_mode = 'velocity'
            """
        )
    ).fetchall()
    for row in rows:
        trigger_id, band, existing = row[0], row[1], row[2]
        if existing:
            continue
        band_value = (band or "walking").strip().lower() or "walking"
        conditions_json = (
            '[{"field":"speed_band","operator":"gte","value":"%s"}]' % band_value
        )
        conn.execute(
            text(
                """
                UPDATE triggers
                SET motion_conditions = :conds,
                    motion_condition_logic = COALESCE(motion_condition_logic, 'and')
                WHERE id = :id
                """
            ),
            {"conds": conditions_json, "id": trigger_id},
        )

    # Rename trigger_mode velocity → motion
    conn.execute(
        text(
            """
            UPDATE triggers
            SET trigger_mode = 'motion'
            WHERE trigger_mode = 'velocity'
            """
        )
    )

    # Synthetic camera_device_id sentinel
    conn.execute(
        text(
            """
            UPDATE triggers
            SET camera_device_id = 'motion'
            WHERE camera_device_id = 'velocity'
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        text(
            """
            UPDATE triggers
            SET camera_device_id = 'velocity'
            WHERE camera_device_id = 'motion'
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE triggers
            SET trigger_mode = 'velocity'
            WHERE trigger_mode = 'motion'
            """
        )
    )
    # Best-effort restore velocity_band from first speed_band condition
    conn.execute(
        text(
            """
            UPDATE triggers
            SET velocity_scope = COALESCE(motion_scope, velocity_scope, 'crowd')
            WHERE trigger_mode = 'velocity'
            """
        )
    )

    op.drop_column("triggers", "motion_roi")
    op.drop_column("triggers", "motion_condition_logic")
    op.drop_column("triggers", "motion_conditions")
    op.drop_column("triggers", "motion_scope")
