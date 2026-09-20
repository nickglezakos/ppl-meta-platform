-- Orchestrator workflow_settings key/value store (people counters, MVR merge knobs).
-- Not the same as cameras.* workflow columns in 041_add_workflow_settings.sql.

CREATE TABLE IF NOT EXISTS workflow_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value DOUBLE PRECISION NOT NULL,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_workflow_settings_key ON workflow_settings(setting_key);

INSERT INTO workflow_settings (setting_key, setting_value, min_value, max_value, description, updated_by)
VALUES
  ('velocity_sensitivity', 20.0, 5.0, 50.0, 'Face tracking tolerance percentage', 'system'),
  ('people_counters_enabled', 0.0, 0.0, 1.0, 'Master switch for people counters', 'system'),
  ('people_counters_batch_seconds', 3600.0, 900.0, 86400.0, 'Batch window seconds', 'system'),
  ('people_counters_workers', 2.0, 1.0, 16.0, 'Worker count', 'system'),
  ('people_counters_quiet_workers', 4.0, 1.0, 32.0, 'Quiet-hours workers', 'system'),
  ('people_counters_max_cpu_pct', 60.0, 10.0, 100.0, 'Max CPU percent', 'system'),
  ('people_counters_max_inflight', 5.0, 1.0, 100.0, 'Max inflight jobs', 'system'),
  ('people_counters_backoff_seconds', 60.0, 5.0, 600.0, 'Backoff seconds', 'system'),
  ('people_counters_per_batch_timeout_seconds', 300.0, 30.0, 3600.0, 'Per-batch timeout', 'system'),
  ('people_counters_max_attempts', 3.0, 1.0, 10.0, 'Max attempts', 'system'),
  ('people_counters_backfill_daily_budget', 200.0, 0.0, 10000.0, 'Daily backfill budget', 'system'),
  ('people_counters_quiet_hours_start', 1.0, 0.0, 23.0, 'Quiet hours start', 'system'),
  ('people_counters_quiet_hours_end', 6.0, 0.0, 23.0, 'Quiet hours end', 'system')
ON CONFLICT (setting_key) DO NOTHING;
