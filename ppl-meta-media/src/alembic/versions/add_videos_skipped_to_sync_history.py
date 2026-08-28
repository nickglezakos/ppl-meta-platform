"""Add videos_skipped to video_list_sync_history

Revision ID: add_videos_skipped_to_sync_history
Revises: add_vprofile_match_fields
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa


revision = "add_videos_skipped_to_sync_history"
down_revision = "add_vprofile_match_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_list_sync_history",
        sa.Column("videos_skipped", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("video_list_sync_history", "videos_skipped")
