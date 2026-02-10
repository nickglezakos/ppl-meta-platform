"""Add unique constraint to collection name

Revision ID: add_unique_collection_name
Revises: rename_media_source_uuid
Create Date: 2026-02-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_collection_name'
down_revision = ('d1fe7ad7ecfa', 'refactor_demographic_2026_01_14')  # Merge both heads
branch_labels = None
depends_on = None


def upgrade():
    """
    Add unique constraint to collection names.
    
    This ensures that each collection (which represents a camera's recordings)
    has a unique name across the platform.
    """
    # First, check for and resolve any existing duplicate names
    # This adds a suffix to duplicates before applying the constraint
    op.execute("""
        WITH duplicates AS (
            SELECT 
                name,
                ROW_NUMBER() OVER (PARTITION BY name ORDER BY created_at) as rn,
                id
            FROM media_collections
            WHERE name IN (
                SELECT name 
                FROM media_collections 
                GROUP BY name 
                HAVING COUNT(*) > 1
            )
        )
        UPDATE media_collections mc
        SET name = d.name || ' (' || d.rn || ')'
        FROM duplicates d
        WHERE mc.id = d.id AND d.rn > 1;
    """)
    
    # Now add the unique constraint
    op.create_unique_constraint(
        'unique_collection_name',
        'media_collections',
        ['name']
    )


def downgrade():
    """Remove unique constraint from collection names."""
    op.drop_constraint('unique_collection_name', 'media_collections', type_='unique')
