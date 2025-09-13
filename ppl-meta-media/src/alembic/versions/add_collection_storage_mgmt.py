"""Add collection storage management tables

Revision ID: add_collection_storage_mgmt
Revises:
Create Date: 2025-09-13 10:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_collection_storage_mgmt"
down_revision = None  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Create collection storage management tables."""

    # Create collection_storage_configs table
    op.create_table(
        "collection_storage_configs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("media_collections.id"),
            unique=True,
            nullable=False,
        ),
        # Storage configuration
        sa.Column("total_size_gb", sa.Float(), default=50.0, nullable=False),
        sa.Column("live_portion_percentage", sa.Float(), default=70.0, nullable=False),
        sa.Column(
            "archive_portion_percentage", sa.Float(), default=30.0, nullable=False
        ),
        # Monitoring thresholds
        sa.Column(
            "warning_threshold_percentage", sa.Float(), default=80.0, nullable=False
        ),
        sa.Column(
            "critical_threshold_percentage", sa.Float(), default=95.0, nullable=False
        ),
        # Auto-archival settings
        sa.Column("auto_archive_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("min_age_for_archive_days", sa.Integer(), default=7, nullable=False),
        # Storage policies
        sa.Column("auto_delete_enabled", sa.Boolean(), default=False, nullable=False),
        sa.Column("auto_delete_after_days", sa.Integer(), default=365, nullable=False),
        # Metadata
        sa.Column("notes", sa.Text()),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create collection_storage_usage table
    op.create_table(
        "collection_storage_usage",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("media_collections.id"),
            unique=True,
            nullable=False,
        ),
        # Current usage tracking (in bytes)
        sa.Column("total_used_bytes", sa.Integer(), default=0, nullable=False),
        sa.Column("live_portion_used_bytes", sa.Integer(), default=0, nullable=False),
        sa.Column(
            "archive_portion_used_bytes", sa.Integer(), default=0, nullable=False
        ),
        # Media counts
        sa.Column("total_media_count", sa.Integer(), default=0, nullable=False),
        sa.Column("live_media_count", sa.Integer(), default=0, nullable=False),
        sa.Column("archived_media_count", sa.Integer(), default=0, nullable=False),
        # Storage status flags
        sa.Column("is_near_capacity", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_at_capacity", sa.Boolean(), default=False, nullable=False),
        sa.Column("requires_cleanup", sa.Boolean(), default=False, nullable=False),
        # Activity tracking
        sa.Column("last_archival_run", sa.DateTime()),
        sa.Column("last_cleanup_run", sa.DateTime()),
        sa.Column("last_notification_sent", sa.DateTime()),
        # Performance metrics
        sa.Column("avg_file_size_bytes", sa.Integer(), default=0),
        sa.Column("largest_file_size_bytes", sa.Integer(), default=0),
        sa.Column("oldest_media_date", sa.DateTime()),
        sa.Column("newest_media_date", sa.DateTime()),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create media_archive_status table
    op.create_table(
        "media_archive_status",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        sa.Column(
            "media_id",
            sa.Integer(),
            sa.ForeignKey("media.id"),
            unique=True,
            nullable=False,
        ),
        # Archive status
        sa.Column("is_archived", sa.Boolean(), default=False, nullable=False),
        sa.Column("archived_at", sa.DateTime()),
        sa.Column("archive_reason", sa.String(100)),
        # Storage locations
        sa.Column("live_storage_path", sa.String(500)),
        sa.Column("archive_storage_path", sa.String(500)),
        # Access characteristics
        sa.Column("can_stream_immediately", sa.Boolean(), default=True, nullable=False),
        sa.Column("requires_retrieval", sa.Boolean(), default=False, nullable=False),
        sa.Column("estimated_retrieval_time_seconds", sa.Integer(), default=0),
        # Archive metadata
        sa.Column("original_file_size_bytes", sa.Integer()),
        sa.Column("compressed_file_size_bytes", sa.Integer()),
        sa.Column("compression_ratio", sa.Float()),
        sa.Column("checksum", sa.String(64)),
        # Access tracking
        sa.Column("last_accessed", sa.DateTime()),
        sa.Column("access_count", sa.Integer(), default=0),
        sa.Column("retrieval_count", sa.Integer(), default=0),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create user_storage_preferences table
    op.create_table(
        "user_storage_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        sa.Column(
            "user_id", UUID(as_uuid=True), unique=True, nullable=False, index=True
        ),
        # Default collection settings
        sa.Column(
            "default_collection_size_gb", sa.Float(), default=50.0, nullable=False
        ),
        sa.Column(
            "default_live_portion_percentage", sa.Float(), default=70.0, nullable=False
        ),
        sa.Column(
            "default_auto_archive_enabled", sa.Boolean(), default=True, nullable=False
        ),
        sa.Column(
            "default_min_age_for_archive_days", sa.Integer(), default=7, nullable=False
        ),
        # Notification preferences
        sa.Column(
            "enable_storage_notifications", sa.Boolean(), default=True, nullable=False
        ),
        sa.Column(
            "notification_threshold_percentage",
            sa.Float(),
            default=80.0,
            nullable=False,
        ),
        sa.Column(
            "email_notifications_enabled", sa.Boolean(), default=True, nullable=False
        ),
        sa.Column(
            "push_notifications_enabled", sa.Boolean(), default=True, nullable=False
        ),
        # Auto-management preferences
        sa.Column(
            "auto_delete_old_archives_enabled",
            sa.Boolean(),
            default=False,
            nullable=False,
        ),
        sa.Column("auto_delete_after_days", sa.Integer(), default=365, nullable=False),
        sa.Column(
            "auto_increase_quota_enabled", sa.Boolean(), default=False, nullable=False
        ),
        sa.Column("max_auto_quota_increase_gb", sa.Float(), default=100.0),
        # Advanced settings
        sa.Column(
            "preferred_compression_enabled", sa.Boolean(), default=True, nullable=False
        ),
        sa.Column("preferred_video_quality", sa.String(20), default="medium"),
        sa.Column(
            "enable_redundant_storage", sa.Boolean(), default=False, nullable=False
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for better query performance
    op.create_index(
        "idx_collection_storage_config_collection_id",
        "collection_storage_configs",
        ["collection_id"],
    )
    op.create_index(
        "idx_collection_storage_usage_collection_id",
        "collection_storage_usage",
        ["collection_id"],
    )
    op.create_index(
        "idx_collection_storage_usage_near_capacity",
        "collection_storage_usage",
        ["is_near_capacity"],
    )
    op.create_index(
        "idx_media_archive_status_media_id", "media_archive_status", ["media_id"]
    )
    op.create_index(
        "idx_media_archive_status_archived", "media_archive_status", ["is_archived"]
    )
    op.create_index(
        "idx_user_storage_preferences_user_id", "user_storage_preferences", ["user_id"]
    )


def downgrade():
    """Drop collection storage management tables."""

    # Drop indexes
    op.drop_index("idx_user_storage_preferences_user_id")
    op.drop_index("idx_media_archive_status_archived")
    op.drop_index("idx_media_archive_status_media_id")
    op.drop_index("idx_collection_storage_usage_near_capacity")
    op.drop_index("idx_collection_storage_usage_collection_id")
    op.drop_index("idx_collection_storage_config_collection_id")

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table("user_storage_preferences")
    op.drop_table("media_archive_status")
    op.drop_table("collection_storage_usage")
    op.drop_table("collection_storage_configs")
