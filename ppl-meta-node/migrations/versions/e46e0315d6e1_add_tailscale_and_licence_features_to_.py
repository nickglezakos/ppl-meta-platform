"""add_tailscale_and_licence_features_to_installation_info

Revision ID: e46e0315d6e1
Revises: 08daff9f9e2a
Create Date: 2026-06-29 19:21:52.571674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e46e0315d6e1'
down_revision = '08daff9f9e2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('installation_info', sa.Column('tailscale_ip', sa.String(45), nullable=True))
    op.add_column('installation_info', sa.Column('tailscale_enrolled', sa.Boolean(), server_default=sa.text('false'), nullable=True))
    op.add_column('installation_info', sa.Column('tailscale_tags', sa.JSON(), nullable=True))
    op.add_column('installation_info', sa.Column('tailscale_enrolled_at', sa.DateTime(), nullable=True))
    op.add_column('installation_info', sa.Column('authority_licence_features', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('installation_info', 'authority_licence_features')
    op.drop_column('installation_info', 'tailscale_enrolled_at')
    op.drop_column('installation_info', 'tailscale_tags')
    op.drop_column('installation_info', 'tailscale_enrolled')
    op.drop_column('installation_info', 'tailscale_ip')
