-- ============================================================================
-- Migration: Add Demographics to Individuals Table
-- ============================================================================
-- Description: Add age and gender estimate columns to individuals table
--              for demographic analytics and reporting
-- Created: 2025-12-07
-- ============================================================================

-- Add gender estimate column
ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS gender_estimate VARCHAR(20);

COMMENT ON COLUMN individuals.gender_estimate IS 'Estimated gender (male, female, unknown)';

-- Add age estimate column
ALTER TABLE individuals
ADD COLUMN IF NOT EXISTS age_estimate INTEGER;

COMMENT ON COLUMN individuals.age_estimate IS 'Estimated age in years';

-- Add constraint to ensure valid gender values
ALTER TABLE individuals
ADD CONSTRAINT IF NOT EXISTS valid_gender_estimate 
CHECK (gender_estimate IS NULL OR gender_estimate IN ('male', 'female', 'unknown'));

-- Add constraint to ensure valid age range
ALTER TABLE individuals
ADD CONSTRAINT IF NOT EXISTS valid_age_estimate 
CHECK (age_estimate IS NULL OR (age_estimate >= 0 AND age_estimate <= 120));

-- Create index for demographic queries
CREATE INDEX IF NOT EXISTS idx_individuals_demographics 
ON individuals(gender_estimate, age_estimate) 
WHERE gender_estimate IS NOT NULL AND age_estimate IS NOT NULL;

-- ============================================================================
-- Migration Complete
-- ============================================================================
