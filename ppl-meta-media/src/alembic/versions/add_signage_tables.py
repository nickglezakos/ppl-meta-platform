"""Add signage simple player tables

Revision ID: add_signage_tables
Revises: add_collection_storage_mgmt
Create Date: 2025-12-02 10:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_signage_tables"
down_revision = "add_collection_storage_mgmt"
branch_labels = None
depends_on = None


def upgrade():
    """Create signage simple player tables."""

    # Create video_lists table
    op.create_table(
        "video_lists",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        # Basic information
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        # Ownership
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        # Playback configuration
        sa.Column("loop_mode", sa.String(50), default="continuous", nullable=False),
        sa.Column("transition_duration", sa.Integer(), default=0, nullable=False),
        # Status flags
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False, index=True),
        sa.Column("is_published", sa.Boolean(), default=False, nullable=False),
        # Metadata
        sa.Column("total_duration_ms", sa.Integer(), default=0),
        sa.Column("video_count", sa.Integer(), default=0),
        sa.Column("last_modified_by", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )

    # Create video_list_items table
    op.create_table(
        "video_list_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        # References
        sa.Column(
            "video_list_id",
            sa.Integer(),
            sa.ForeignKey("video_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("media_collections.id"),
            nullable=False,
        ),
        sa.Column(
            "video_id",
            sa.Integer(),
            sa.ForeignKey("media.id"),
            nullable=False,
        ),
        # Ordering
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        # Optional overrides
        sa.Column("duration_override", sa.Integer(), nullable=True),
        sa.Column("title_override", sa.String(255), nullable=True),
        sa.Column("transition_override", sa.Integer(), nullable=True),
        # Cached metadata
        sa.Column("video_filename", sa.String(255), nullable=True),
        sa.Column("video_file_path", sa.String(500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        # Status
        sa.Column("is_available", sa.Boolean(), default=True, nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )

    # Create index on video_list_id and sequence_order for efficient ordering
    op.create_index(
        "ix_video_list_items_list_sequence",
        "video_list_items",
        ["video_list_id", "sequence_order"],
    )

    # Create signage_devices table
    op.create_table(
        "signage_devices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        # Device identification
        sa.Column("device_id", UUID(as_uuid=True), unique=True, nullable=False, index=True),
        sa.Column("device_name", sa.String(255), nullable=False),
        sa.Column("device_hostname", sa.String(255), nullable=True),
        # Network information
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("mac_address", sa.String(17), nullable=True),
        # Device characteristics
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("android_version", sa.String(50), nullable=True),
        sa.Column("screen_resolution", sa.String(20), nullable=True),
        sa.Column("screen_size_inches", sa.Integer(), nullable=True),
        # Software information
        sa.Column("app_version", sa.String(50), nullable=True),
        sa.Column("last_app_update", sa.DateTime(timezone=True), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_online", sa.Boolean(), default=False, nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        # Current playback
        sa.Column(
            "current_video_list_id",
            sa.Integer(),
            sa.ForeignKey("video_lists.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("playback_state", sa.String(20), nullable=True),
        # Ownership
        sa.Column("registered_by", UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=True),
        # Capabilities
        sa.Column("supports_hd", sa.Boolean(), default=True),
        sa.Column("supports_4k", sa.Boolean(), default=False),
        sa.Column("max_storage_gb", sa.Integer(), default=10),
        # Metadata
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )

    # Create video_list_sync_history table
    op.create_table(
        "video_list_sync_history",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        # References
        sa.Column(
            "video_list_id",
            sa.Integer(),
            sa.ForeignKey("video_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signage_device_id", UUID(as_uuid=True), nullable=False, index=True),
        # Sync details
        sa.Column("sync_status", sa.String(50), default="pending", nullable=False),
        sa.Column("sync_mode", sa.String(20), nullable=False),
        # Statistics
        sa.Column("videos_synced", sa.Integer(), default=0),
        sa.Column("videos_failed", sa.Integer(), default=0),
        sa.Column("total_videos", sa.Integer(), nullable=True),
        sa.Column("data_transferred_bytes", sa.Integer(), default=0),
        # Timing
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_duration_ms", sa.Integer(), nullable=True),
        # Error handling
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        # Metadata
        sa.Column("initiated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("device_ip_address", sa.String(45), nullable=True),
        sa.Column("device_hostname", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_video_list_sync_history_list_device",
        "video_list_sync_history",
        ["video_list_id", "signage_device_id"],
    )
    op.create_index(
        "ix_video_list_sync_history_status",
        "video_list_sync_history",
        ["sync_status"],
    )


def downgrade():
    """Drop signage simple player tables."""

    # Drop tables in reverse order of creation (respecting foreign keys)
    op.drop_table("video_list_sync_history")
    op.drop_table("signage_devices")
    op.drop_table("video_list_items")
    op.drop_table("video_lists")
