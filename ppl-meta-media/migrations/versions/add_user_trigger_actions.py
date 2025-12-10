"""add_user_trigger_actions_table

Revision ID: add_user_trigger_actions
Revises: rename_media_source_uuid
Create Date: 2025-12-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_user_trigger_actions'
down_revision = 'rename_media_source_uuid'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create user_trigger_actions table."""
    op.create_table(
        'user_trigger_actions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_config', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_user_trigger_action_id', 'user_trigger_actions', ['id'])
    op.create_index('idx_user_trigger_action_uuid', 'user_trigger_actions', ['uuid'], unique=True)
    op.create_index('idx_user_trigger_action_is_active', 'user_trigger_actions', ['is_active'])
    op.create_index('idx_user_trigger_action_type', 'user_trigger_actions', ['action_type'])
    
    print("✅ user_trigger_actions table created successfully")


def downgrade() -> None:
    """Drop user_trigger_actions table."""
    op.drop_index('idx_user_trigger_action_type', table_name='user_trigger_actions')
    op.drop_index('idx_user_trigger_action_is_active', table_name='user_trigger_actions')
    op.drop_index('idx_user_trigger_action_uuid', table_name='user_trigger_actions')
    op.drop_index('idx_user_trigger_action_id', table_name='user_trigger_actions')
    op.drop_table('user_trigger_actions')
    
    print("✅ user_trigger_actions table dropped successfully")
