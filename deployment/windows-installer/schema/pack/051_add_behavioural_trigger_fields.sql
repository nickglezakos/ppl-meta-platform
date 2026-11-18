-- Behavioural trigger mode: flush lookback + intent metric conditions
ALTER TABLE triggers
  ADD COLUMN IF NOT EXISTS behavioural_lookback_flushes INTEGER DEFAULT 6,
  ADD COLUMN IF NOT EXISTS behavioural_conditions TEXT,
  ADD COLUMN IF NOT EXISTS behavioural_condition_logic VARCHAR(8) DEFAULT 'and';
