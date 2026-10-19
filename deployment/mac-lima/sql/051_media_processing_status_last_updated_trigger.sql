-- media_processing_status has last_updated, not updated_at.
-- Lab symptom: UPDATEs fail when the trigger still calls update_updated_at_column()
--   (NEW.updated_at) — record "has no field updated_at".

CREATE OR REPLACE FUNCTION update_media_processing_status_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_media_processing_status_updated_at ON media_processing_status;
CREATE TRIGGER trigger_media_processing_status_updated_at
    BEFORE UPDATE ON media_processing_status
    FOR EACH ROW
    EXECUTE FUNCTION update_media_processing_status_last_updated();
