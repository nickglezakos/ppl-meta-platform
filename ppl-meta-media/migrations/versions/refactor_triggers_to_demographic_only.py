"""refactor triggers to demographic only

Revision ID: refactor_demographic_2026_01_14
Revises: 321a0601fef9
Create Date: 2026-01-14

This migration refactors the triggers table to:
1. Make demographic_conditions required (not nullable)
2. Remove redundant fields (person_count_*, age_range_*, gender_filter, action, action_config)
3. Remove signage-specific fields (moved to user actions)
4. Keep core fields: demographic_conditions, time_span, camera_device_id, action_uuid, tracking_duration, cooldown_seconds

IMPORTANT: Before running this migration, ensure you've backed up your database!
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'refactor_demographic_2026_01_14'
down_revision = '321a0601fef9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade database schema to refactored trigger structure.
    
    WARNING: This will:
    1. Migrate old triggers to new demographic_conditions format
    2. Drop columns: person_count_*, age_range_*, gender_filter, action, action_config,
       enable_demographic_conditions, signage_*
    """
    
    # Step 1: Migrate existing triggers to demographic_conditions format
    # For triggers without demographic_conditions, create from old fields
    op.execute("""
        UPDATE triggers
        SET demographic_conditions = 
            CASE 
                WHEN demographic_conditions IS NULL OR demographic_conditions = '' THEN
                    -- Convert old person_count fields to demographic condition
                    '[{"field": "people_count", "operator": "' || 
                    CASE person_count_operator
                        WHEN 'more_than' THEN 'gt'
                        WHEN 'less_than' THEN 'lt'
                        WHEN 'equals' THEN 'eq'
                        WHEN 'between' THEN 'gte'
                        ELSE 'gte'
                    END || 
                    '", "value": ' || 
                    CASE person_count_operator
                        WHEN 'between' THEN split_part(person_count_value, '-', 1)
                        ELSE person_count_value
                    END ||
                    '}]'
                ELSE demographic_conditions
            END
        WHERE demographic_conditions IS NULL OR demographic_conditions = ''
    """)
    
    # Step 2: Make demographic_conditions NOT NULL
    op.alter_column('triggers', 'demographic_conditions',
                    existing_type=sa.Text(),
                    nullable=False,
                    comment='JSON array of demographic conditions: [{"field": "people_count|percent_male|percent_age_18_24|...", "operator": "gt|gte|lt|lte|eq", "value": number}]')
    
    # Step 3: Drop removed columns
    op.drop_column('triggers', 'person_count_operator')
    op.drop_column('triggers', 'person_count_value')
    op.drop_column('triggers', 'age_range_operator')
    op.drop_column('triggers', 'age_range_value')
    op.drop_column('triggers', 'gender_filter')
    op.drop_column('triggers', 'action')
    op.drop_column('triggers', 'action_config')
    op.drop_column('triggers', 'enable_demographic_conditions')
    op.drop_column('triggers', 'signage_device_ids')
    op.drop_column('triggers', 'signage_playlist_id')
    op.drop_column('triggers', 'signage_transition_mode')
    op.drop_column('triggers', 'signage_fade_duration_ms')
    
    print("✅ Migration complete!")
    print("ℹ️  Old signage configurations should be recreated as 'digital_signage' user actions")


def downgrade():
    """
    Downgrade database schema to old trigger structure.
    
    WARNING: This will restore old columns but data loss may occur!
    """
    
    # Re-add removed columns
    op.add_column('triggers', sa.Column('person_count_operator', sa.String(50), nullable=True, server_default='more_than'))
    op.add_column('triggers', sa.Column('person_count_value', sa.String(50), nullable=True, server_default='1'))
    op.add_column('triggers', sa.Column('age_range_operator', sa.String(50), nullable=True))
    op.add_column('triggers', sa.Column('age_range_value', sa.String(50), nullable=True))
    op.add_column('triggers', sa.Column('gender_filter', sa.String(50), nullable=True, server_default='any'))
    op.add_column('triggers', sa.Column('action', sa.String(50), nullable=True, server_default='alert'))
    op.add_column('triggers', sa.Column('action_config', sa.String(500), nullable=True))
    op.add_column('triggers', sa.Column('enable_demographic_conditions', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('triggers', sa.Column('signage_device_ids', sa.Text(), nullable=True))
    op.add_column('triggers', sa.Column('signage_playlist_id', sa.String(255), nullable=True))
    op.add_column('triggers', sa.Column('signage_transition_mode', sa.String(50), nullable=True, server_default='immediate'))
    op.add_column('triggers', sa.Column('signage_fade_duration_ms', sa.Integer(), nullable=True, server_default='2000'))
    
    # Attempt to extract person_count from demographic_conditions (limited reverse migration)
    op.execute("""
        UPDATE triggers
        SET 
            person_count_operator = 'more_than',
            person_count_value = '1',
            enable_demographic_conditions = true
        WHERE demographic_conditions IS NOT NULL
    """)
    
    # Make demographic_conditions nullable again
    op.alter_column('triggers', 'demographic_conditions',
                    existing_type=sa.Text(),
                    nullable=True)
    
    print("⚠️  Downgrade complete, but some data may have been lost!")
