"""add_ppl_match_fields_to_triggers

Revision ID: add_ppl_match_fields_to_triggers
Revises: add_user_trigger_actions
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ppl_match_fields_to_triggers'
down_revision = 'add_user_trigger_actions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('triggers', sa.Column('trigger_mode', sa.String(length=30), nullable=False, server_default='demographic'))
    op.add_column('triggers', sa.Column('ppl_match_group_id', sa.String(length=255), nullable=True))
    op.add_column('triggers', sa.Column('ppl_match_similarity_threshold', sa.Float(), nullable=False, server_default='0.75'))
    op.add_column('triggers', sa.Column('ppl_match_top_k', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('triggers', sa.Column('last_match_info', sa.Text(), nullable=True))
    op.add_column('triggers', sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('idx_triggers_trigger_mode', 'triggers', ['trigger_mode'])
    op.create_index('idx_triggers_ppl_match_group_id', 'triggers', ['ppl_match_group_id'])
    op.create_index('idx_triggers_last_matched_at', 'triggers', ['last_matched_at'])


def downgrade() -> None:
    op.drop_index('idx_triggers_last_matched_at', table_name='triggers')
    op.drop_index('idx_triggers_ppl_match_group_id', table_name='triggers')
    op.drop_index('idx_triggers_trigger_mode', table_name='triggers')

    op.drop_column('triggers', 'last_matched_at')
    op.drop_column('triggers', 'last_match_info')
    op.drop_column('triggers', 'ppl_match_top_k')
    op.drop_column('triggers', 'ppl_match_similarity_threshold')
    op.drop_column('triggers', 'ppl_match_group_id')
    op.drop_column('triggers', 'trigger_mode')
