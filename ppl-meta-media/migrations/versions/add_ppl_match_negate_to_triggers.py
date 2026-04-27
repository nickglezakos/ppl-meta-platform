"""add_ppl_match_negate_to_triggers

Adds ppl_match_negate boolean column to triggers table.
When True, ppl_match and search triggers fire when NO group members are matched (NOT mode).

Revision ID: add_ppl_match_negate
Revises: add_multi_action_uuids
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ppl_match_negate'
down_revision = 'add_multi_action_uuids'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'triggers',
        sa.Column(
            'ppl_match_negate',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment='When True, trigger fires when NO group members are matched (NOT mode)',
        ),
    )


def downgrade() -> None:
    op.drop_column('triggers', 'ppl_match_negate')
