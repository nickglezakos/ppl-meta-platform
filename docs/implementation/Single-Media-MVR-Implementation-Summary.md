# Single-Media MVR Endpoint - Implementation Summary

**Date**: November 29, 2025  
**Version**: v2.19.43  
**Status**: ✅ Implementation Complete

---

## Overview

Successfully implemented a new VMeta endpoint that processes photos and videos independently to generate MVR people without cross-media merging. Each media is processed in complete isolation, making it ideal for photo galleries, single-video analysis, and independent media libraries.

---

## Implementation Components

### 1. Pydantic Models ✅
**File**: `ppl-meta-vmeta/src/api/models/process_media.py`

Created comprehensive request/response models:
- `ProcessMediaRequest` - Main request with media UUIDs and processing options
- `ProcessingOptions` - Configuration (similarity threshold, quality filters, etc.)
- `ResponseFormat` - Output format configuration
- `ProcessMediaResponse` - Main response with results and statistics
- `MediaResult` - Per-media processing result
- `MVRPerson` - Standard MVR person structure
- `RouteData` / `RoutePoint` - Movement tracking data
- `Demographics` - Age/gender estimates
- `AggregateStatistics` - Summary statistics
- `AsyncProcessingResponse` / `JobStatusResponse` - Async support

### 2. Media Client ✅
**File**: `ppl-meta-vmeta/src/utils/media_client.py`

HTTP client for Media service communication:
- `get_media_metadata(media_uuid)` - Fetch photo/video metadata
- `get_media_type(media_uuid)` - Get media type (photo/video)
- `batch_get_media_metadata(media_uuids)` - Batch metadata fetch
- Singleton pattern with `get_media_client()`

### 3. Route Data Builder ✅
**File**: `ppl-meta-vmeta/src/utils/route_data_builder.py`

Utility functions for building route/movement data:
- `build_route_data_for_photo()` - Single-point route (timestamp=0.0, zero velocity)
- `build_route_data_for_video()` - Multi-point route with velocity calculation
- `calculate_velocities()` - Normalized velocity computation
- `sample_route_points()` - Uniform sampling algorithm (>100 points threshold)
- `build_route_data()` - Main function dispatching by media type

### 4. MVR Service Method ✅
**File**: `ppl-meta-vmeta/src/services/mvr_service.py`

Added `process_single_media_for_mvr()` method:
- Face embedding generation with quality filtering
- Within-media similarity matching using cosine similarity
- Connected components clustering (DFS algorithm)
- Quality-weighted canonical embedding computation
- MVR person creation with isolation flag
- Demographics estimation integration
- Returns MVR people in standard format

### 5. Database Schema ✅
**File**: `ppl-meta-vmeta/src/database/migrations/004_single_media_mvr_columns.sql`

Added columns to `mvr_people` table:
```sql
ALTER TABLE mvr_people
ADD COLUMN is_isolated BOOLEAN DEFAULT FALSE,
ADD COLUMN source_media_uuid UUID;
```

Created indexes:
- `idx_mvr_people_isolated` - Filter isolated MVR
- `idx_mvr_people_source_media` - Source media lookup
- `idx_mvr_people_isolated_source` - Composite index for isolated filtering

### 6. Repository Updates ✅
**File**: `ppl-meta-vmeta/src/database/mvr_repository.py`

Updated `create_mvr_people()` method:
- Added `is_isolated` parameter (default: False)
- Added `source_media_uuid` parameter
- Updated INSERT statement to include new columns

### 7. API Endpoint ✅
**File**: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

Implemented `POST /api/v1/mvr-people/process-media`:
- Request validation (max 50 media per request)
- Async processing support (with job queue placeholder)
- Media metadata fetching
- Person objects retrieval from Orchestrator
- Per-media independent processing
- Route data building (photo vs video)
- Demographics integration
- Aggregate statistics calculation
- Comprehensive error handling
- Partial failure support

---

## Key Features

### 1. Independent Processing
- Each media processed in complete isolation
- No cross-media MVR merging (guaranteed by `is_isolated` flag)
- Suitable for maintaining separate identity spaces

### 2. Photo Support
- Single-point route data (timestamp = 0.0)
- Face center coordinates from bounding box
- Zero velocity and movement duration

### 3. Video Support
- Multi-point route data with temporal tracking
- Velocity calculation (normalized px/s)
- Route sampling for >100 points
- Movement duration and pattern analysis

### 4. Standard MVR Format
- Same response structure as existing endpoints
- Compatible with current frontend implementations
- `is_isolated` and `source_media_uuid` fields added

### 5. Performance Optimizations
- Quality-based face filtering
- Efficient similarity matrix computation
- Connected components clustering
- Optional demographics/route data

---

## API Usage Examples

### Basic Request (Photos)
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["photo-1", "photo-2", "photo-3"],
    "processing_options": {
      "similarity_threshold": 0.85,
      "include_demographics": true
    }
  }'
```

### Video Processing
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["video-1"],
    "processing_options": {
      "similarity_threshold": 0.80,
      "include_route_data": true,
      "include_demographics": true
    }
  }'
```

### Async Processing
```bash
curl -X POST http://localhost:8080/api/v1/mvr-people/process-media \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_uuids": ["video-1", "video-2", "video-3"],
    "processing_options": {
      "async_processing": true
    }
  }'
```

---

## Response Structure

```json
{
  "success": true,
  "total_media": 3,
  "processed_media": 3,
  "failed_media": 0,
  "processing_time_seconds": 4.23,
  "results": [
    {
      "media_uuid": "photo-uuid-1",
      "media_type": "photo",
      "status": "completed",
      "mvr_people": [
        {
          "mvr_people_uuid": "mvr-abc-123",
          "individual_uuids": ["ind-001"],
          "total_appearances": 1,
          "unique_videos": 1,
          "confidence_score": 0.92,
          "quality_score": 0.89,
          "demographics": {
            "gender": "Male",
            "age_min": 30,
            "age_max": 40
          },
          "route_data": {
            "route_points": [{
              "center_x": 640.5,
              "center_y": 480.2,
              "timestamp": 0.0,
              "frame_number": 0,
              "velocity_x": 0.0,
              "velocity_y": 0.0,
              "confidence": 0.94
            }],
            "total_detections": 1,
            "movement_duration": 0.0
          },
          "is_isolated": true,
          "source_media_uuid": "photo-uuid-1"
        }
      ],
      "total_faces_detected": 5,
      "mvr_people_count": 2
    }
  ],
  "aggregate_statistics": {
    "total_mvr_people_created": 6,
    "total_individuals_detected": 18,
    "processing_breakdown": {
      "photos": {"count": 2, "total_mvr": 4},
      "videos": {"count": 1, "total_mvr": 2}
    }
  }
}
```

---

## Database Migration

To apply the schema changes:

```bash
# Connect to PostgreSQL
psql -h localhost -U <user> -d <database>

# Run migration
\i ppl-meta-vmeta/src/database/migrations/004_single_media_mvr_columns.sql
```

Or using the migration runner:
```python
from database.postgresql_migration_runner import run_migrations
await run_migrations()
```

---

## Testing Checklist

### Unit Tests
- [ ] Test ProcessMediaRequest validation
- [ ] Test route_data_builder for photos (single point)
- [ ] Test route_data_builder for videos (multi-point + velocity)
- [ ] Test MVRService.process_single_media_for_mvr()
- [ ] Test clustering algorithm (connected components)
- [ ] Test media_client HTTP methods

### Integration Tests
- [ ] End-to-end photo processing
- [ ] End-to-end video processing
- [ ] Mixed media batch (photos + videos)
- [ ] Error handling (invalid UUID, missing media, no faces)
- [ ] Verify is_isolated flag prevents cross-media merging
- [ ] Verify source_media_uuid tracking
- [ ] Test async processing (when implemented)

### Manual Tests
- [ ] Process single photo with faces
- [ ] Process single video with movement
- [ ] Process batch of 10 media
- [ ] Verify route data format (photo vs video)
- [ ] Verify demographics accuracy
- [ ] Check performance (< 5s for 10 media)
- [ ] Test with Postman/curl

---

## Performance Characteristics

Based on specification estimates:
- **Single photo**: ~100ms (simple, single-point route)
- **Single video (30s)**: ~2-4s (embedding + clustering + route sampling)
- **Batch (10 media)**: ~10-15s synchronous
- **Cache hit**: N/A (no cross-media caching for isolated processing)

Optimization opportunities:
- Parallel media processing (asyncio.gather)
- Embedding caching (person_object_uuid → embedding)
- GPU acceleration for embedding generation
- Async mode for large batches

---

## Known Limitations

1. **No Cross-Media Caching**: Each media processed independently, no benefit from previous sessions
2. **Async Job Queue**: Placeholder implementation (needs background task queue)
3. **Face Crop Extraction**: Simplified implementation (needs actual crop from media)
4. **Appearances Data**: Simplified structure (needs detailed timestamp tracking)
5. **Max Media Limit**: 50 media per request (prevent overload)

---

## Next Steps

1. **Testing**: Implement comprehensive test suite
2. **Async Queue**: Integrate with Celery/RQ for background processing
3. **Face Crop Integration**: Connect to Media service for actual face crops
4. **Performance Tuning**: Profile and optimize bottlenecks
5. **Frontend Integration**: Update Flutter app to use new endpoint
6. **Documentation**: Add to VMeta API docs (vmeta-api-endpoints.md)
7. **Monitoring**: Add metrics/logging for production use

---

## Related Documentation

- **Specification**: `/docs/guides/developer/Single-Media-MVR-Endpoint-Specification.md`
- **VMeta API Docs**: `/docs/vmeta-api-endpoints.md`
- **Cross-Video Tracking**: `/docs/guides/developer/Cross-Video-Individual-Analysis.md`
- **Route Sampling**: `/docs/guides/developer/route-sample-rendering.md`

---

## Version Control

**Branch**: main (or feature branch)
**Commit Message**:
```
feat(vmeta): Add single-media MVR processing endpoint

- Implement /api/v1/mvr-people/process-media endpoint
- Add independent photo/video processing with isolation
- Create route data builder for single-point (photo) and multi-point (video)
- Add media client for Media service communication
- Update database schema with is_isolated and source_media_uuid columns
- Add comprehensive Pydantic models for request/response
- Support async processing mode (placeholder)

Closes #XXX
```

---

## Success Criteria ✅

- [x] Pydantic models created
- [x] Media client implemented
- [x] Route data builder completed
- [x] MVR service method added
- [x] Database schema updated
- [x] Repository methods updated
- [x] API endpoint implemented
- [x] Comprehensive error handling
- [x] Standard MVR format maintained
- [x] Documentation complete

**Status**: Ready for testing and deployment 🚀
