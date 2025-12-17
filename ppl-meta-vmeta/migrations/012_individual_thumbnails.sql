-- Migration: Add thumbnail caching for individuals
-- Date: 2025-12-17
-- Description: Stores generated thumbnails with size variants and metadata

-- Create thumbnails table
CREATE TABLE IF NOT EXISTS individual_thumbnails (
    individual_uuid UUID NOT NULL,
    size VARCHAR(20) NOT NULL CHECK (size IN ('small', 'medium', 'large')),
    thumbnail_data TEXT NOT NULL, -- Base64-encoded image data
    source_video_uuid UUID, -- Video the thumbnail was extracted from
    source_frame_number INTEGER, -- Frame number in the video
    quality_score DOUBLE PRECISION, -- Quality score of the source frame
    generated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    file_size INTEGER, -- Size in bytes (calculated from base64)
    PRIMARY KEY (individual_uuid, size),
    FOREIGN KEY (individual_uuid) REFERENCES individuals(individual_uuid) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_thumbnails_individual ON individual_thumbnails(individual_uuid);
CREATE INDEX idx_thumbnails_generated_at ON individual_thumbnails(generated_at DESC);
CREATE INDEX idx_thumbnails_quality ON individual_thumbnails(quality_score DESC);

-- Function to calculate file size from base64 data
CREATE OR REPLACE FUNCTION calculate_thumbnail_size()
RETURNS TRIGGER AS $$
BEGIN
    -- Base64 size is approximately 4/3 of binary size
    -- Remove data URI prefix if present
    IF NEW.thumbnail_data LIKE 'data:image%' THEN
        NEW.file_size := (LENGTH(SPLIT_PART(NEW.thumbnail_data, ',', 2)) * 3) / 4;
    ELSE
        NEW.file_size := (LENGTH(NEW.thumbnail_data) * 3) / 4;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate file size
CREATE TRIGGER trigger_calculate_thumbnail_size
    BEFORE INSERT OR UPDATE ON individual_thumbnails
    FOR EACH ROW
    EXECUTE FUNCTION calculate_thumbnail_size();

-- Create view for thumbnail summary
CREATE OR REPLACE VIEW individual_thumbnail_summary AS
SELECT 
    i.individual_uuid,
    i.individual_id,
    EXISTS(SELECT 1 FROM individual_thumbnails t WHERE t.individual_uuid = i.individual_uuid) as has_thumbnail,
    MAX(t.generated_at) as thumbnail_updated_at,
    MAX(t.quality_score) as best_thumbnail_quality,
    COUNT(t.size) as available_sizes,
    ARRAY_AGG(t.size ORDER BY t.size) FILTER (WHERE t.size IS NOT NULL) as sizes,
    SUM(t.file_size) as total_size_bytes
FROM individuals i
LEFT JOIN individual_thumbnails t ON i.individual_uuid = t.individual_uuid
GROUP BY i.individual_uuid, i.individual_id;

-- Comments for documentation
COMMENT ON TABLE individual_thumbnails IS 'Caches generated thumbnails for individuals in multiple sizes';
COMMENT ON COLUMN individual_thumbnails.thumbnail_data IS 'Base64-encoded JPEG image data with optional data URI prefix';
COMMENT ON COLUMN individual_thumbnails.quality_score IS 'Quality score from the source frame (0.0-1.0)';
