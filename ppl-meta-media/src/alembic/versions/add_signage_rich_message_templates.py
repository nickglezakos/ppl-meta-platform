"""Add signage rich message templates table

Revision ID: add_signage_rich_message_templates
Revises: add_trigger_execution_logs_table
Create Date: 2026-10-01

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "add_signage_rich_message_templates"
down_revision = "add_trigger_execution_logs_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "signage_rich_message_templates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("title_font_size", sa.Integer(), nullable=False, server_default="48"),
        sa.Column(
            "message_font_size", sa.Integer(), nullable=False, server_default="28"
        ),
        sa.Column(
            "title_color", sa.String(32), nullable=False, server_default="#FFFFFF"
        ),
        sa.Column(
            "message_color", sa.String(32), nullable=False, server_default="#F0F0F0"
        ),
        sa.Column(
            "background_color",
            sa.String(32),
            nullable=False,
            server_default="#000000",
        ),
        sa.Column("opacity", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("layout", sa.String(50), nullable=False, server_default="card"),
        sa.Column(
            "media_id",
            sa.Integer(),
            sa.ForeignKey("media.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sound_media_id",
            sa.Integer(),
            sa.ForeignKey("media.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "default_duration_ms", sa.Integer(), nullable=False, server_default="15000"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_signage_rich_message_templates_user_id",
        "signage_rich_message_templates",
        ["user_id"],
    )
    op.create_index(
        "ix_signage_rich_message_templates_is_active",
        "signage_rich_message_templates",
        ["is_active"],
    )


def downgrade():
    op.drop_index(
        "ix_signage_rich_message_templates_is_active",
        table_name="signage_rich_message_templates",
    )
    op.drop_index(
        "ix_signage_rich_message_templates_user_id",
        table_name="signage_rich_message_templates",
    )
    op.drop_table("signage_rich_message_templates")
