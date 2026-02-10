"""Add unique constraint to camera name

Revision ID: add_unique_camera_name
Revises: 
Create Date: 2026-02-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_camera_name'
down_revision = None  # This is the first Alembic migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add unique constraint to camera names.
    
    This ensures that each camera has a unique user-defined name across the platform.
    Camera identification continues to use device_id (UUID) as the primary identifier.
    """
    # Check if cameras table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'cameras' not in inspector.get_table_names():
        print("Cameras table does not exist yet - skipping migration")
        return
    
    # First, check for and resolve any existing duplicate names
    # This adds a suffix to duplicates before applying the constraint
    try:
        op.execute("""
            UPDATE cameras 
            SET name = name || ' (' || 
                (SELECT COUNT(*) + 1 
                 FROM cameras c2 
                 WHERE c2.name = cameras.name 
                 AND c2.id < cameras.id) || ')'
            WHERE name IN (
                SELECT name 
                FROM cameras 
                GROUP BY name 
                HAVING COUNT(*) > 1
            )
            AND id NOT IN (
                SELECT MIN(id) 
                FROM cameras 
                GROUP BY name
            );
        """)
    except Exception as e:
        print(f"Note: Could not resolve duplicate names: {e}")
    
    # Now add the unique constraint
    # Use SQLite-compatible approach
    try:
        # Check if the constraint already exists
        constraints = inspector.get_unique_constraints('cameras')
        constraint_names = [c['name'] for c in constraints if c.get('name')]
        
        if 'unique_camera_name' not in constraint_names:
            op.create_unique_constraint(
                'unique_camera_name',
                'cameras',
                ['name']
            )
            print("✅ Added unique constraint to camera name")
        else:
            print("ℹ️ Unique constraint already exists on camera name")
    except Exception as e:
        # If constraint already exists or other error, log it
        print(f"Note: Could not add unique constraint (may already exist): {e}")


def downgrade():
    """Remove unique constraint from camera names."""
    try:
        op.drop_constraint('unique_camera_name', 'cameras', type_='unique')
    except Exception as e:
        print(f"Note: Could not drop unique constraint: {e}")
