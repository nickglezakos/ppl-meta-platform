"""add_search_trigger_fields

Revision ID: add_search_trigger_fields
Revises: add_storage_locations
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_search_trigger_fields'
down_revision = 'add_storage_locations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add search trigger columns to triggers table
    op.add_column('triggers', sa.Column(
        'search_camera_device_ids', sa.Text(), nullable=True,
        comment='JSON array of camera device IDs for search trigger mode'
    ))
    op.add_column('triggers', sa.Column(
        'search_interval_seconds', sa.Integer(), nullable=True, server_default='300',
        comment='How often (in seconds) a search trigger executes. Minimum 30.'
    ))

    # Add search trigger columns to trigger_execution_logs table
    op.add_column('trigger_execution_logs', sa.Column(
        'search_cameras_queried', sa.Text(), nullable=True,
        comment='JSON array of camera device IDs queried by search trigger'
    ))
    op.add_column('trigger_execution_logs', sa.Column(
        'search_session_uuid', sa.String(length=255), nullable=True,
        comment='Search session UUID returned by vmeta camera-search'
    ))
    op.create_index(
        'ix_trigger_execution_logs_search_session_uuid',
        'trigger_execution_logs',
        ['search_session_uuid']
    )


def downgrade() -> None:
    op.drop_index('ix_trigger_execution_logs_search_session_uuid', table_name='trigger_execution_logs')
    op.drop_column('trigger_execution_logs', 'search_session_uuid')
    op.drop_column('trigger_execution_logs', 'search_cameras_queried')
    op.drop_column('triggers', 'search_interval_seconds')
    op.drop_column('triggers', 'search_camera_device_ids')
