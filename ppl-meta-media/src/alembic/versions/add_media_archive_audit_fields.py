"""Add archive audit fields to media table

Revision ID: add_media_archive_audit_fields
Revises: add_camera_device_id_to_collections
Create Date: 2026-03-01 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_media_archive_audit_fields"
down_revision = "add_camera_device_id_to_collections"
branch_labels = None
depends_on = None


def upgrade():
    """Add archive audit columns and index to media table."""
    op.add_column("media", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("media", sa.Column("archived_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("media", sa.Column("archive_source", sa.String(length=100), nullable=True))
    op.add_column("media", sa.Column("archive_reason", sa.Text(), nullable=True))
    op.create_index(
        "ix_media_archived_by_user_id",
        "media",
        ["archived_by_user_id"],
        unique=False,
    )


def downgrade():
    """Remove archive audit columns and index from media table."""
    op.drop_index("ix_media_archived_by_user_id", table_name="media")
    op.drop_column("media", "archive_reason")
    op.drop_column("media", "archive_source")
    op.drop_column("media", "archived_by_user_id")
    op.drop_column("media", "archived_at")
