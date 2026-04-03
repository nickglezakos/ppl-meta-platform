"""Add default workflow settings for MVR merge rule and threshold

Revision ID: f19a0d4c2b11
Revises: c3d45e8bf729
Create Date: 2026-04-03 13:30:00.000000

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'f19a0d4c2b11'
down_revision = 'c3d45e8bf729'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        text(
            """
            INSERT INTO workflow_settings
                (setting_key, setting_value, min_value, max_value, description, updated_by)
            VALUES
                ('mvr_merge_rule', 1.0, 0.0, 2.0, 'MVR merge mode: 0=none, 1=semi, 2=auto', 'system')
            ON CONFLICT (setting_key) DO NOTHING
            """
        )
    )

    op.execute(
        text(
            """
            INSERT INTO workflow_settings
                (setting_key, setting_value, min_value, max_value, description, updated_by)
            VALUES
                ('mvr_merge_threshold', 0.70, 0.30, 0.95, 'Default threshold for MVR merge operations', 'system')
            ON CONFLICT (setting_key) DO NOTHING
            """
        )
    )


def downgrade():
    op.execute(
        text(
            """
            DELETE FROM workflow_settings
            WHERE setting_key IN ('mvr_merge_rule', 'mvr_merge_threshold')
            """
        )
    )
