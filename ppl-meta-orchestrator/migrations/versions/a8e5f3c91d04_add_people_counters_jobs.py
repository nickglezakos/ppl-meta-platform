"""Add people_counters_jobs table and default settings

Revision ID: a8e5f3c91d04
Revises: f19a0d4c2b11
Create Date: 2026-05-09 12:00:00.000000

People Counters automation — see docs/proposals/people-counters.md

This migration creates the durable job queue used by the orchestrator's
people-counters worker (§5.5.1) and seeds default values for the worker
configuration into the existing workflow_settings table (§5.8).

The table is intentionally simple: it is the orchestrator's record of
"work that needs to be done" — the *result* of a successful batch lives
in vmeta's mvr_search_sessions (rows with batch_key IS NOT NULL).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'a8e5f3c91d04'
down_revision = 'f19a0d4c2b11'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'people_counters_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        # Deterministic identifier shared with vmeta's mvr_search_sessions.batch_key:
        # "{camera_id}|{batch_start_utc}|{batch_end_utc}".
        sa.Column('batch_key', sa.String(255), nullable=False, unique=True),
        sa.Column('camera_id', sa.String(100), nullable=False),
        sa.Column('batch_start_utc', sa.DateTime(), nullable=False),
        sa.Column('batch_end_utc', sa.DateTime(), nullable=False),
        # State machine: pending -> running -> success | failed -> dead_letter
        sa.Column(
            'status', sa.String(20), nullable=False, server_default='pending'
        ),
        # Tier ordering for the backlog selection query (§5.5.2).
        # 0 = today, 1 = yesterday, 2 = stale refresh, 3 = older backfill.
        sa.Column(
            'priority_tier', sa.Integer(), nullable=False, server_default='3'
        ),
        # TRUE when this row was queued as a refresh of a stale batch
        # (vs. filling a never-computed window).
        sa.Column(
            'is_stale_refresh', sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        # Heartbeat written by the worker every ~30s; used by the startup
        # recovery pass to reset orphaned 'running' rows whose worker died.
        sa.Column('heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        # vmeta search_session_uuid that holds the result_payload (set on success).
        sa.Column('search_session_uuid', sa.String(36), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Backlog selection: pull the next pending row in tier order, newest first.
    op.create_index(
        'idx_pcj_dispatch',
        'people_counters_jobs',
        ['status', 'priority_tier', 'batch_start_utc'],
    )
    # Per-camera diagnostics + Settings UI "Cameras" tab.
    op.create_index(
        'idx_pcj_camera_window',
        'people_counters_jobs',
        ['camera_id', 'batch_start_utc'],
    )
    # Recovery pass scans 'running' rows by stale heartbeat.
    op.create_index(
        'idx_pcj_running_heartbeat',
        'people_counters_jobs',
        ['status', 'heartbeat_at'],
    )

    # Seed default people-counters config into workflow_settings.
    # All values are float-encoded (the workflow_settings table is float-only);
    # boolean settings use 0.0 / 1.0.
    op.execute(text("""
        INSERT INTO workflow_settings
            (setting_key, setting_value, min_value, max_value, description, updated_by)
        VALUES
            ('people_counters_enabled',
             0.0, 0.0, 1.0,
             'Master switch for the People Counters automation worker (0=off, 1=on)',
             'system'),
            ('people_counters_batch_seconds',
             3600.0, 900.0, 86400.0,
             'Batch window size in seconds (default 1 hour)',
             'system'),
            ('people_counters_workers',
             2.0, 1.0, 16.0,
             'Concurrent low-priority worker count',
             'system'),
            ('people_counters_quiet_workers',
             4.0, 1.0, 32.0,
             'Concurrent worker count during quiet hours',
             'system'),
            ('people_counters_max_cpu_pct',
             60.0, 10.0, 100.0,
             'Skip dispatching new batches if vmeta CPU exceeds this percentage',
             'system'),
            ('people_counters_max_inflight',
             5.0, 1.0, 100.0,
             'Skip dispatching if vmeta active-request count exceeds this',
             'system'),
            ('people_counters_backoff_seconds',
             60.0, 5.0, 600.0,
             'Sleep duration when system-load gate trips',
             'system'),
            ('people_counters_per_batch_timeout_seconds',
             300.0, 30.0, 3600.0,
             'HTTP timeout for a single /persisted-merge-session call',
             'system'),
            ('people_counters_max_attempts',
             3.0, 1.0, 10.0,
             'Retry budget per batch before dead-lettering',
             'system'),
            ('people_counters_backfill_daily_budget',
             200.0, 0.0, 10000.0,
             'Cap on tier-3 (older backfill) batches dispatched per 24h window',
             'system'),
            ('people_counters_quiet_hours_start',
             1.0, 0.0, 23.0,
             'Quiet hours start (local hour, 0-23). Set equal to end to disable.',
             'system'),
            ('people_counters_quiet_hours_end',
             6.0, 0.0, 23.0,
             'Quiet hours end (local hour, 0-23). Set equal to start to disable.',
             'system')
        ON CONFLICT (setting_key) DO NOTHING
    """))


def downgrade():
    op.execute(text("""
        DELETE FROM workflow_settings
         WHERE setting_key LIKE 'people_counters_%'
    """))
    op.drop_index('idx_pcj_running_heartbeat', table_name='people_counters_jobs')
    op.drop_index('idx_pcj_camera_window', table_name='people_counters_jobs')
    op.drop_index('idx_pcj_dispatch', table_name='people_counters_jobs')
    op.drop_table('people_counters_jobs')
