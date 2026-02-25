"""Increase model and serial_number column sizes for Android devices

Revision ID: increase_model_serial_number
Revises: 
Create Date: 2026-02-24 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'increase_model_serial_number'
down_revision = 'add_unique_camera_name'
branch_labels = None
depends_on = None


def upgrade():
    """
    Increase column sizes for model and serial_number in cameras table.
    
    Android devices can have extremely long model strings and serial numbers.
    For example, TrebleDroid devices have serial numbers like:
    'google/lineage_arm64_bgN/tdgsi_arm64_ab:14/UQ1A.240205.004/eng.crossg.20260126.103446:userdebug/release-keys'
    
    This migration extends model from VARCHAR(100) to VARCHAR(500) and
    serial_number from VARCHAR(100) to VARCHAR(500) to accommodate these long values.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'cameras' not in inspector.get_table_names():
        return
    
    table_columns = {col['name']: col for col in inspector.get_columns('cameras')}
    
    # Alter model column if it exists and is still VARCHAR(100)
    if 'model' in table_columns:
        old_type = table_columns['model']['type']
        if hasattr(old_type, 'length') and old_type.length == 100:
            # Using ALTER COLUMN for PostgreSQL compatibility
            op.alter_column(
                'cameras',
                'model',
                type_=sa.String(500),
                existing_type=sa.String(100)
            )
    
    # Alter serial_number column if it exists and is still VARCHAR(100)
    if 'serial_number' in table_columns:
        old_type = table_columns['serial_number']['type']
        if hasattr(old_type, 'length') and old_type.length == 100:
            op.alter_column(
                'cameras',
                'serial_number',
                type_=sa.String(500),
                existing_type=sa.String(100)
            )


def downgrade():
    """
    Revert column sizes back to VARCHAR(100).
    
    WARNING: This may fail if any existing data exceeds 100 characters.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'cameras' not in inspector.get_table_names():
        return
    
    table_columns = {col['name']: col for col in inspector.get_columns('cameras')}
    
    # Revert model column if it exists
    if 'model' in table_columns:
        old_type = table_columns['model']['type']
        if hasattr(old_type, 'length') and old_type.length == 500:
            op.alter_column(
                'cameras',
                'model',
                type_=sa.String(100),
                existing_type=sa.String(500)
            )
    
    # Revert serial_number column if it exists
    if 'serial_number' in table_columns:
        old_type = table_columns['serial_number']['type']
        if hasattr(old_type, 'length') and old_type.length == 500:
            op.alter_column(
                'cameras',
                'serial_number',
                type_=sa.String(100),
                existing_type=sa.String(500)
            )
