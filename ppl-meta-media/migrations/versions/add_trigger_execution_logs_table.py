"""Add trigger execution logs table

Revision ID: add_trigger_execution_logs_table
Revises: add_ppl_match_fields_to_triggers
Create Date: 2026-02-28 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_trigger_execution_logs_table'
down_revision = 'add_ppl_match_fields_to_triggers'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'trigger_execution_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('trigger_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger_id', sa.Integer(), nullable=True),
        sa.Column('trigger_name', sa.String(length=255), nullable=True),
        sa.Column('trigger_mode', sa.String(length=30), nullable=False, server_default='demographic'),
        sa.Column('camera_device_id', sa.String(length=255), nullable=False),

        sa.Column('source_mvr_uuid', sa.String(length=255), nullable=True),
        sa.Column('matched_group_id', sa.String(length=255), nullable=True),
        sa.Column('matched_member_uuid', sa.String(length=255), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('match_details_json', sa.Text(), nullable=True),

        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('action_executed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),

        sa.ForeignKeyConstraint(['trigger_id'], ['triggers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_trigger_execution_logs_trigger_uuid', 'trigger_execution_logs', ['trigger_uuid'])
    op.create_index('idx_trigger_execution_logs_trigger_id', 'trigger_execution_logs', ['trigger_id'])
    op.create_index('idx_trigger_execution_logs_trigger_mode', 'trigger_execution_logs', ['trigger_mode'])
    op.create_index('idx_trigger_execution_logs_camera_device_id', 'trigger_execution_logs', ['camera_device_id'])
    op.create_index('idx_trigger_execution_logs_source_mvr_uuid', 'trigger_execution_logs', ['source_mvr_uuid'])
    op.create_index('idx_trigger_execution_logs_matched_group_id', 'trigger_execution_logs', ['matched_group_id'])
    op.create_index('idx_trigger_execution_logs_matched_member_uuid', 'trigger_execution_logs', ['matched_member_uuid'])
    op.create_index('idx_trigger_execution_logs_passed', 'trigger_execution_logs', ['passed'])
    op.create_index('idx_trigger_execution_logs_evaluated_at', 'trigger_execution_logs', ['evaluated_at'])


def downgrade():
    op.drop_index('idx_trigger_execution_logs_evaluated_at', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_passed', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_matched_member_uuid', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_matched_group_id', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_source_mvr_uuid', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_camera_device_id', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_trigger_mode', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_trigger_id', table_name='trigger_execution_logs')
    op.drop_index('idx_trigger_execution_logs_trigger_uuid', table_name='trigger_execution_logs')

    op.drop_table('trigger_execution_logs')
