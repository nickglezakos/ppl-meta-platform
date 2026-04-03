"""Add per-camera MVR periodic scheduler fields

Revision ID: add_mvr_periodic_scheduler
Revises: increase_model_serial_number
Create Date: 2026-04-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_mvr_periodic_scheduler'
down_revision = 'increase_model_serial_number'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'cameras',
        sa.Column(
            'mvr_periodic_scheduler_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'cameras',
        sa.Column(
            'mvr_periodic_scheduler_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.70',
        ),
    )
    op.add_column(
        'cameras',
        sa.Column(
            'mvr_periodic_scheduler_frequency_seconds',
            sa.Integer(),
            nullable=False,
            server_default='300',
        ),
    )


def downgrade() -> None:
    op.drop_column('cameras', 'mvr_periodic_scheduler_frequency_seconds')
    op.drop_column('cameras', 'mvr_periodic_scheduler_threshold')
    op.drop_column('cameras', 'mvr_periodic_scheduler_enabled')
