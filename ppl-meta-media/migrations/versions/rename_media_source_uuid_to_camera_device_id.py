"""Rename media_source_uuid to camera_device_id and change type to String

Revision ID: rename_media_source_uuid
Revises: update_trigger_schema_for_operators
Create Date: 2025-12-10 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'rename_media_source_uuid'
down_revision = 'update_trigger_schema_operators'
branch_labels = None
depends_on = None


def upgrade():
    """
    Rename media_source_uuid to camera_device_id and change from UUID to String.
    This aligns with the Camera service's device_id field (e.g., 'usb_camera_0', 'rtsp_192.168.1.76_554').
    """
    
    # Step 1: Add new camera_device_id column
    op.add_column('triggers', 
        sa.Column('camera_device_id', sa.String(255), nullable=True, index=True,
                  comment="Device ID of the camera (e.g., 'usb_camera_0')")
    )
    
    # Step 2: Rename media_source_name to camera_name
    op.alter_column('triggers', 'media_source_name', new_column_name='camera_name')
    
    # Step 3: Migrate existing data - cast UUID to string if any exist
    # Note: Existing data may have fake UUIDs, so we'll set them to a placeholder
    op.execute("""
        UPDATE triggers 
        SET camera_device_id = 'usb_camera_0'
        WHERE media_source_uuid IS NOT NULL
    """)
    
    # Step 4: Make camera_device_id NOT NULL
    op.alter_column('triggers', 'camera_device_id', nullable=False)
    
    # Step 5: Drop the old index
    op.drop_index('ix_triggers_media_source_uuid', table_name='triggers')
    
    # Step 6: Drop the old column
    op.drop_column('triggers', 'media_source_uuid')
    
    print("✅ Renamed media_source_uuid to camera_device_id (UUID → String)")


def downgrade():
    """Revert back to media_source_uuid as UUID."""
    
    # Add back media_source_uuid as UUID
    op.add_column('triggers',
        sa.Column('media_source_uuid', UUID(as_uuid=True), nullable=True, index=True)
    )
    
    # Try to convert camera_device_id back to UUID (will fail for non-UUID values)
    # For downgrade, we'll just set a dummy UUID
    op.execute("""
        UPDATE triggers 
        SET media_source_uuid = '123e4567-e89b-12d3-a456-426614174000'::uuid
        WHERE camera_device_id IS NOT NULL
    """)
    
    op.alter_column('triggers', 'media_source_uuid', nullable=False)
    op.create_index('ix_triggers_media_source_uuid', 'triggers', ['media_source_uuid'])
    op.drop_column('triggers', 'camera_device_id')
    
    # Rename camera_name back to media_source_name
    op.alter_column('triggers', 'camera_name', new_column_name='media_source_name')
    
    print("⚠️  Reverted to media_source_uuid (String → UUID)")
