"""Update trigger schema with age/gender operators

Revision ID: update_trigger_schema_operators
Revises: add_camera_device_id
Create Date: 2025-12-10 12:00:00.000000

This migration updates the triggers table to support more flexible
age and gender filtering:
- Splits age_range into age_range_operator and age_range_value
- Changes gender_filter from String to Enum
- Updates to support numeric age thresholds instead of categories

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "update_trigger_schema_operators"
down_revision = "add_camera_device_id"
branch_labels = None
depends_on = None


def upgrade():
    """Apply trigger schema updates."""
    
    connection = op.get_bind()
    
    # Drop existing enum types if they exist (from failed migrations)
    op.execute("DROP TYPE IF EXISTS agerangeoperator")
    op.execute("DROP TYPE IF EXISTS genderfilter")
    
    # Create new enum types
    op.execute("CREATE TYPE agerangeoperator AS ENUM ('less_than', 'more_than', 'between', 'any')")
    op.execute("CREATE TYPE genderfilter AS ENUM ('male', 'female', 'any')")
    
    # Create SQLAlchemy enum references
    age_range_operator_enum = postgresql.ENUM(
        'less_than', 'more_than', 'between', 'any',
        name='agerangeoperator',
        create_type=False  # Already created above
    )
    
    gender_filter_enum = postgresql.ENUM(
        'male', 'female', 'any',
        name='genderfilter',
        create_type=False  # Already created above
    )
    
    # Add new columns for age range operator/value
    op.add_column(
        'triggers',
        sa.Column('age_range_operator', age_range_operator_enum, nullable=True)
    )
    op.add_column(
        'triggers',
        sa.Column('age_range_value', sa.String(50), nullable=True)
    )
    
    # Migrate existing age_range data
    # Old values: 'underage', 'adults', 'seniors', 'all'
    # Map to new format:
    # - 'underage' -> operator='less_than', value='18'
    # - 'adults' -> operator='between', value='18-65'
    # - 'seniors' -> operator='more_than', value='65'
    # - 'all' -> operator='any', value=NULL
    
    # Use CAST to properly convert string to enum type
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range_operator = CAST('less_than' AS agerangeoperator), 
            age_range_value = '18'
        WHERE age_range::text = 'underage'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range_operator = CAST('between' AS agerangeoperator), 
            age_range_value = '18-65'
        WHERE age_range::text = 'adults'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range_operator = CAST('more_than' AS agerangeoperator), 
            age_range_value = '65'
        WHERE age_range::text = 'seniors'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range_operator = CAST('any' AS agerangeoperator), 
            age_range_value = NULL
        WHERE age_range::text = 'all'
    """))
    
    # Drop old age_range column (this will also drop the old agerange enum if not used elsewhere)
    op.drop_column('triggers', 'age_range')
    
    # Drop the old agerange enum type
    op.execute("DROP TYPE IF EXISTS agerange")
    
    # Update gender_filter to use enum
    # First, ensure all existing values are valid
    connection.execute(sa.text("""
        UPDATE triggers 
        SET gender_filter = 'any'
        WHERE gender_filter IS NULL 
           OR gender_filter NOT IN ('male', 'female', 'any')
    """))
    
    # Alter column to use enum type
    op.execute("""
        ALTER TABLE triggers 
        ALTER COLUMN gender_filter 
        TYPE genderfilter 
        USING gender_filter::genderfilter
    """)


def downgrade():
    """Revert trigger schema updates."""
    
    # Create old age_range enum if needed
    old_age_range_enum = postgresql.ENUM(
        'underage', 'adults', 'seniors', 'all',
        name='agerange',
        create_type=True
    )
    
    # Add back old age_range column
    op.add_column(
        'triggers',
        sa.Column('age_range', old_age_range_enum, nullable=True)
    )
    
    # Migrate data back to old format
    connection = op.get_bind()
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range = 'underage'
        WHERE age_range_operator = 'less_than' AND age_range_value = '18'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range = 'seniors'
        WHERE age_range_operator = 'more_than' AND age_range_value = '65'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range = 'adults'
        WHERE age_range_operator = 'between' AND age_range_value = '18-65'
    """))
    
    connection.execute(sa.text("""
        UPDATE triggers 
        SET age_range = 'all'
        WHERE age_range_operator = 'any' OR age_range_operator IS NULL
    """))
    
    # Drop new columns
    op.drop_column('triggers', 'age_range_value')
    op.drop_column('triggers', 'age_range_operator')
    
    # Revert gender_filter to String
    op.execute("""
        ALTER TABLE triggers 
        ALTER COLUMN gender_filter 
        TYPE VARCHAR(50) 
        USING gender_filter::text
    """)
    
    # Drop new enum types
    op.execute("DROP TYPE IF EXISTS agerangeoperator")
    op.execute("DROP TYPE IF EXISTS genderfilter")
