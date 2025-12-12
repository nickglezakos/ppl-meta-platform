"""Add tracking_duration field to triggers

Revision ID: add_tracking_duration
Revises: link_triggers_to_actions
Create Date: 2025-12-11 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_tracking_duration'
down_revision = 'link_triggers_to_actions'
branch_labels = None
depends_on = None


def upgrade():
    # Add tracking_duration column with default value
    op.add_column('triggers', sa.Column(
        'tracking_duration',
        sa.String(50),
        nullable=False,
        server_default='10 minutes',
        comment='Time window for MVR search (e.g., "5 seconds", "10 minutes", "2 hours", "1 day", "3 months")'
    ))
    
    # Add index for performance
    op.create_index('idx_trigger_tracking_duration', 'triggers', ['tracking_duration'])


def downgrade():
    # Drop index
    op.drop_index('idx_trigger_tracking_duration', table_name='triggers')
    
    # Drop column
    op.drop_column('triggers', 'tracking_duration')
