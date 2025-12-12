"""Link triggers to user actions via UUID foreign key

Revision ID: link_triggers_to_actions
Revises: add_user_trigger_actions
Create Date: 2025-12-11 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'link_triggers_to_actions'
down_revision = 'add_user_trigger_actions'
branch_labels = None
depends_on = None


def upgrade():
    # Add new action_uuid column (nullable for now)
    op.add_column('triggers', sa.Column('action_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add index on action_uuid for performance
    op.create_index('idx_trigger_action_uuid', 'triggers', ['action_uuid'])
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_trigger_action_uuid',
        'triggers',
        'user_trigger_actions',
        ['action_uuid'],
        ['uuid'],
        ondelete='SET NULL'  # If action is deleted, set trigger's action_uuid to NULL
    )
    
    # Note: The old 'action' column is kept for backward compatibility
    # Applications can gradually migrate to using action_uuid


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_trigger_action_uuid', 'triggers', type_='foreignkey')
    
    # Drop index
    op.drop_index('idx_trigger_action_uuid', table_name='triggers')
    
    # Drop action_uuid column
    op.drop_column('triggers', 'action_uuid')
