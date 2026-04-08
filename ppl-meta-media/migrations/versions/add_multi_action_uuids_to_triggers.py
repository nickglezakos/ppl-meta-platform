"""add_multi_action_uuids_to_triggers

Adds action_uuids (JSON text) column to triggers table for multi-action support.
Migrates existing action_uuid values into action_uuids array.

Revision ID: add_multi_action_uuids
Revises: add_search_trigger_fields
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_multi_action_uuids'
down_revision = 'add_search_trigger_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add action_uuids column
    op.add_column(
        'triggers',
        sa.Column(
            'action_uuids',
            sa.Text(),
            nullable=True,
            comment='JSON array of action UUIDs assigned to this trigger'
        )
    )

    # Migrate existing action_uuid values into action_uuids as single-element JSON arrays
    op.execute(
        """
        UPDATE triggers
        SET action_uuids = '["' || action_uuid::text || '"]'
        WHERE action_uuid IS NOT NULL
          AND action_uuids IS NULL
        """
    )


def downgrade():
    op.drop_column('triggers', 'action_uuids')
