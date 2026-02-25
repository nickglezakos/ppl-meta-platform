-- Migration: Increase model and serial_number column sizes for Android devices
-- Reason: Android devices (like TrebleDroid) have extremely long model strings and serial numbers
-- Example Android serial: google/lineage_arm64_bgN/tdgsi_arm64_ab:14/UQ1A.240205.004/eng.crossg.20260126.103446:userdebug/release-keys (130+ chars)

-- Increase model column from VARCHAR(100) to VARCHAR(500)
ALTER TABLE cameras ALTER COLUMN model TYPE varchar(500);

-- Increase serial_number column from VARCHAR(100) to VARCHAR(500)
ALTER TABLE cameras ALTER COLUMN serial_number TYPE varchar(500);
