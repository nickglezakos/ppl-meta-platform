"""split_tracking_duration_into_number_and_unit

Revision ID: 7dd97e47324f
Revises: add_tracking_duration
Create Date: 2025-12-11 10:42:42.923972

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7dd97e47324f'
down_revision = 'add_tracking_duration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column('triggers', sa.Column('tracking_number', sa.Integer(), nullable=True, comment='Number value for tracking duration'))
    op.add_column('triggers', sa.Column('tracking_unit', sa.String(20), nullable=True, comment='Unit for tracking duration (seconds, minutes, hours, days, months)'))
    
    # Parse existing tracking_duration values and populate new columns
    # Default: "10 minutes" -> tracking_number=10, tracking_unit="minutes"
    op.execute("""
        UPDATE triggers 
        SET 
            tracking_number = CAST(SPLIT_PART(tracking_duration, ' ', 1) AS INTEGER),
            tracking_unit = CASE 
                WHEN tracking_duration LIKE '% second%' THEN 'seconds'
                WHEN tracking_duration LIKE '% minute%' THEN 'minutes'
                WHEN tracking_duration LIKE '% hour%' THEN 'hours'
                WHEN tracking_duration LIKE '% day%' THEN 'days'
                WHEN tracking_duration LIKE '% month%' THEN 'months'
                ELSE 'minutes'
            END
        WHERE tracking_duration IS NOT NULL
    """)
    
    # Set default values for any nulls
    op.execute("UPDATE triggers SET tracking_number = 10 WHERE tracking_number IS NULL")
    op.execute("UPDATE triggers SET tracking_unit = 'minutes' WHERE tracking_unit IS NULL")
    
    # Make columns non-nullable with defaults
    op.alter_column('triggers', 'tracking_number', nullable=False, server_default='10')
    op.alter_column('triggers', 'tracking_unit', nullable=False, server_default='minutes')
    
    # Create indexes
    op.create_index('idx_trigger_tracking_number', 'triggers', ['tracking_number'])
    op.create_index('idx_trigger_tracking_unit', 'triggers', ['tracking_unit'])
    
    # Drop old tracking_duration column
    op.drop_index('idx_trigger_tracking_duration', table_name='triggers')
    op.drop_column('triggers', 'tracking_duration')


def downgrade() -> None:
    # Recreate tracking_duration column
    op.add_column('triggers', sa.Column('tracking_duration', sa.String(50), nullable=True, comment='Time window for MVR search'))
    
    # Reconstruct tracking_duration from tracking_number and tracking_unit
    op.execute("""
        UPDATE triggers 
        SET tracking_duration = CONCAT(
            tracking_number::text, 
            ' ', 
            CASE 
                WHEN tracking_number = 1 THEN RTRIM(tracking_unit, 's')
                ELSE tracking_unit
            END
        )
    """)
    
    # Set default and make non-nullable
    op.execute("UPDATE triggers SET tracking_duration = '10 minutes' WHERE tracking_duration IS NULL")
    op.alter_column('triggers', 'tracking_duration', nullable=False, server_default='10 minutes')
    op.create_index('idx_trigger_tracking_duration', 'triggers', ['tracking_duration'])
    
    # Drop new columns
    op.drop_index('idx_trigger_tracking_unit', table_name='triggers')
    op.drop_index('idx_trigger_tracking_number', table_name='triggers')
    op.drop_column('triggers', 'tracking_unit')
    op.drop_column('triggers', 'tracking_number')
