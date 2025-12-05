"""add_triggers_table

Revision ID: add_triggers_table
Revises: 
Create Date: 2025-12-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'add_triggers_table'
down_revision = 'add_signage_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create triggers table."""
    op.create_table(
        'triggers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False),
        sa.Column('person_count_operator', sa.Enum('less_than', 'more_than', 'equals', 'between', name='personcountoperator'), nullable=False),
        sa.Column('person_count_value', sa.String(length=50), nullable=False),
        sa.Column('age_range', sa.Enum('underage', 'adults', 'seniors', 'all', name='agerange'), nullable=False),
        sa.Column('gender_filter', sa.String(length=50), nullable=True),
        sa.Column('time_span', sa.String(length=100), nullable=False),
        sa.Column('media_source_uuid', UUID(as_uuid=True), nullable=False),
        sa.Column('media_source_name', sa.String(length=255), nullable=True),
        sa.Column('action', sa.Enum('alert', 'email', 'webhook', 'log', name='triggeraction'), nullable=False),
        sa.Column('action_config', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_triggers_uuid'), 'triggers', ['uuid'], unique=True)
    op.create_index(op.f('ix_triggers_is_active'), 'triggers', ['is_active'], unique=False)
    op.create_index(op.f('ix_triggers_media_source_uuid'), 'triggers', ['media_source_uuid'], unique=False)


def downgrade() -> None:
    """Drop triggers table."""
    op.drop_index(op.f('ix_triggers_media_source_uuid'), table_name='triggers')
    op.drop_index(op.f('ix_triggers_is_active'), table_name='triggers')
    op.drop_index(op.f('ix_triggers_uuid'), table_name='triggers')
    op.drop_table('triggers')
    
    # Drop enums (PostgreSQL specific)
    op.execute('DROP TYPE IF EXISTS triggeraction')
    op.execute('DROP TYPE IF EXISTS agerange')
    op.execute('DROP TYPE IF EXISTS personcountoperator')
