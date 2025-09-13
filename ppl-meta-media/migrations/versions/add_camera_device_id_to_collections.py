"""Add camera_device_id to media_collections table

Revision ID: add_camera_device_id_to_collections
Revises: add_collection_storage_mgmt
Create Date: 2025-09-13 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_camera_device_id"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add camera_device_id column to media_collections table."""

    # Add camera_device_id column to media_collections table
    op.add_column(
        "media_collections",
        sa.Column("camera_device_id", sa.String(255), nullable=True),
    )

    # Create index on camera_device_id for efficient lookups
    op.create_index(
        "idx_media_collections_camera_device_id",
        "media_collections",
        ["camera_device_id"],
    )


def downgrade():
    """Remove camera_device_id column from media_collections table."""

    # Drop index first
    op.drop_index("idx_media_collections_camera_device_id", "media_collections")

    # Drop column
    op.drop_column("media_collections", "camera_device_id")
