"""Add demographic fields to triggers table

Revision ID: 321a0601fef9
Revises: 7dd97e47324f
Create Date: 2025-12-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '321a0601fef9'
down_revision = '7dd97e47324f'
branch_labels = None
depends_on = None


def upgrade():
    """Add demographic trigger fields to triggers table."""
    
    # Add demographic condition fields
    op.add_column('triggers', sa.Column(
        'enable_demographic_conditions',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='Enable demographic-based trigger evaluation (percent_male, percent_female, etc.)'
    ))
    
    op.add_column('triggers', sa.Column(
        'demographic_conditions',
        sa.Text(),
        nullable=True,
        comment='JSON array of demographic conditions: [{"field": "percent_male", "operator": "gte", "value": 60}]'
    ))
    
    op.add_column('triggers', sa.Column(
        'signage_device_ids',
        sa.Text(),
        nullable=True,
        comment='JSON array of signage device UUIDs for playback control: ["device-uuid-1", "device-uuid-2"]'
    ))
    
    op.add_column('triggers', sa.Column(
        'signage_playlist_id',
        sa.String(255),
        nullable=True,
        comment='Playlist UUID to play when trigger fires'
    ))
    
    op.add_column('triggers', sa.Column(
        'signage_transition_mode',
        sa.String(50),
        nullable=False,
        server_default='immediate',
        comment='Playlist transition mode: immediate | after_current | fade'
    ))
    
    op.add_column('triggers', sa.Column(
        'signage_fade_duration_ms',
        sa.Integer(),
        nullable=False,
        server_default='2000',
        comment='Fade duration in milliseconds for fade transition mode'
    ))
    
    op.add_column('triggers', sa.Column(
        'cooldown_seconds',
        sa.Integer(),
        nullable=False,
        server_default='60',
        comment='Minimum seconds between trigger firings to prevent spam'
    ))
    
    op.add_column('triggers', sa.Column(
        'last_fired_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Timestamp of last trigger firing'
    ))
    
    # Create indexes for performance
    op.create_index('idx_trigger_demographic_enabled', 'triggers', ['enable_demographic_conditions'], unique=False)
    op.create_index('idx_trigger_cooldown', 'triggers', ['last_fired_at'], unique=False)
    
    print("✅ Added demographic fields to triggers table")


def downgrade():
    """Remove demographic trigger fields."""
    
    # Drop indexes
    op.drop_index('idx_trigger_cooldown', table_name='triggers')
    op.drop_index('idx_trigger_demographic_enabled', table_name='triggers')
    
    # Drop columns
    op.drop_column('triggers', 'last_fired_at')
    op.drop_column('triggers', 'cooldown_seconds')
    op.drop_column('triggers', 'signage_fade_duration_ms')
    op.drop_column('triggers', 'signage_transition_mode')
    op.drop_column('triggers', 'signage_playlist_id')
    op.drop_column('triggers', 'signage_device_ids')
    op.drop_column('triggers', 'demographic_conditions')
    op.drop_column('triggers', 'enable_demographic_conditions')
    
    print("✅ Removed demographic fields from triggers table")
