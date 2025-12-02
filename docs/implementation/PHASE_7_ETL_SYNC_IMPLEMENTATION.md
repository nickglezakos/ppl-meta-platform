# Phase 7: ETL Sync & History Implementation

## Overview

Phase 7 implements the ETL (Extract, Transform, Load) synchronization system for pushing video playlists from the PPL Meta Media service to signage devices. This includes batch processing, job queuing, retry logic, and comprehensive sync history tracking.

## Architecture

### Components

1. **SignageETLWorker** (`services/signage_etl_worker.py`)
   - Background worker with async job processing
   - Configurable worker pool (default: 5 workers)
   - Job queue with priority support
   - Automatic retry with exponential backoff
   - Controlled concurrency per job (max 3 devices simultaneously)

2. **BatchSyncManager** (`services/signage_etl_worker.py`)
   - High-level batch sync operations
   - One-to-many: Sync one playlist to multiple devices
   - Many-to-one: Sync multiple playlists to one device
   - Many-to-many: Sync multiple playlists to multiple devices
   - Broadcast: Sync to all online devices

3. **API Endpoints** (`api/v1/signage.py`)
   - Individual sync: POST `/api/v1/signage/etl/sync`
   - Batch sync: POST `/api/v1/signage/etl/batch-sync`
   - Broadcast: POST `/api/v1/signage/etl/sync-to-all`
   - Job status: GET `/api/v1/signage/etl/job-status/{job_id}`
   - Sync history: GET `/api/v1/signage/etl/sync-history`

## Implementation Details

### ETL Worker Lifecycle

```python
# Startup (in main.py lifespan)
await start_etl_worker()

# Shutdown (in main.py lifespan)
await stop_etl_worker()
```

The worker automatically:
- Creates worker pool on startup
- Processes jobs from queue
- Handles errors and retries
- Cleans up completed jobs (24h retention)
- Graceful shutdown on stop

### Job Processing Flow

```
1. Job Enqueued
   ├─ Assigned unique job_id (UUID)
   ├─ Added to active_jobs dict
   └─ Pushed to asyncio.Queue

2. Worker Picks Up Job
   ├─ Status: "pending" → "in_progress"
   ├─ Get video list with all items
   ├─ Get device information
   └─ Process sync to each device

3. Parallel Device Sync
   ├─ Semaphore (max 3 concurrent)
   ├─ Prepare video list payload
   ├─ HTTP POST to device /api/v1/sync
   └─ Record sync history per device

4. Job Completion
   ├─ Status: "in_progress" → "completed"/"failed"
   ├─ Move to completed_jobs dict
   └─ Result includes success/failure counts
```

### Sync Job Structure

```python
{
    "job_id": "uuid",
    "video_list_id": 123,
    "device_ids": ["uuid1", "uuid2", ...],
    "sync_mode": "full" | "incremental",
    "user_id": "uuid",
    "force_update": bool,
    "priority": int,
    "status": "pending" | "in_progress" | "completed" | "failed",
    "created_at": "timestamp",
    "result": {
        "total_devices": 5,
        "successful_devices": 4,
        "failed_devices": 1,
        "sync_mode": "full",
        "video_list_id": 123,
        "video_list_name": "Store Playlist",
        "video_count": 10
    }
}
```

### Video List Payload

Data sent to each device:

```json
{
    "video_list": {
        "id": "uuid",
        "name": "Playlist Name",
        "description": "Optional description",
        "loop_mode": "continuous",
        "transition_duration": 1000,
        "videos": [
            {
                "id": "video-uuid",
                "video_id": 123,
                "sequence_order": 1,
                "filename": "video.mp4",
                "file_path": "/path/to/video.mp4",
                "duration_ms": 30000,
                "title": "Video Title",
                "thumbnail_url": "http://..."
            }
        ]
    },
    "sync_mode": "full",
    "force_update": false
}
```

## API Usage Examples

### 1. Individual Sync

Sync one playlist to one or more devices:

```bash
curl -X POST http://localhost:8000/api/v1/signage/etl/sync \
  -H "Content-Type: application/json" \
  -d '{
    "video_list_id": "550e8400-e29b-41d4-a716-446655440000",
    "target_devices": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ],
    "sync_mode": "full",
    "force_update": false
  }'
```

Response:
```json
{
    "sync_job_id": "660e8400-e29b-41d4-a716-446655440003",
    "status": "pending",
    "target_device_count": 2,
    "message": "Sync initiated for 2 device(s)"
}
```

### 2. Batch Sync

Sync multiple playlists to multiple devices:

```bash
curl -X POST http://localhost:8000/api/v1/signage/etl/batch-sync \
  -H "Content-Type: application/json" \
  -d '{
    "video_list_ids": [1, 2, 3],
    "device_ids": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ],
    "sync_mode": "full",
    "force_update": false
  }'
```

Response:
```json
{
    "status": "accepted",
    "job_count": 3,
    "job_ids": [
        "660e8400-...",
        "660e8401-...",
        "660e8402-..."
    ],
    "video_list_count": 3,
    "device_count": 2,
    "message": "Queued 3 sync job(s)"
}
```

### 3. Broadcast Sync

Sync one playlist to all online devices:

```bash
curl -X POST http://localhost:8000/api/v1/signage/etl/sync-to-all \
  -H "Content-Type: application/json" \
  -d '{
    "video_list_id": 1,
    "sync_mode": "full",
    "force_update": false
  }'
```

Response:
```json
{
    "status": "accepted",
    "job_id": "660e8400-e29b-41d4-a716-446655440004",
    "message": "Sync job queued for all online devices"
}
```

### 4. Check Job Status

```bash
curl http://localhost:8000/api/v1/signage/etl/job-status/660e8400-e29b-41d4-a716-446655440003
```

Response:
```json
{
    "job_id": "660e8400-e29b-41d4-a716-446655440003",
    "status": "completed",
    "video_list_id": 1,
    "device_count": 2,
    "created_at": "2024-12-02T10:30:00Z",
    "result": {
        "total_devices": 2,
        "successful_devices": 2,
        "failed_devices": 0,
        "sync_mode": "full",
        "video_list_id": 1,
        "video_list_name": "Store Playlist",
        "video_count": 10
    }
}
```

### 5. Get Sync History

```bash
# All history
curl http://localhost:8000/api/v1/signage/etl/sync-history

# Filter by video list
curl "http://localhost:8000/api/v1/signage/etl/sync-history?video_list_id=1"

# Filter by device
curl "http://localhost:8000/api/v1/signage/etl/sync-history?device_id=550e8400-..."

# Pagination
curl "http://localhost:8000/api/v1/signage/etl/sync-history?page=2&page_size=20"
```

Response:
```json
{
    "total_count": 45,
    "page": 1,
    "page_size": 50,
    "results": [
        {
            "id": 1,
            "uuid": "770e8400-...",
            "video_list_id": 1,
            "signage_device_id": "550e8400-...",
            "sync_mode": "full",
            "sync_status": "completed",
            "videos_synced": 10,
            "videos_failed": 0,
            "sync_started_at": "2024-12-02T10:30:00Z",
            "sync_completed_at": "2024-12-02T10:30:15Z",
            "duration_seconds": 15,
            "device_ip_address": "192.168.1.100",
            "device_hostname": "signage-lobby",
            "initiated_by": "user-uuid"
        }
    ]
}
```

## Database Schema

### VideoListSyncHistory Table

```sql
CREATE TABLE video_list_sync_history (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL,
    video_list_id INTEGER REFERENCES video_lists(id) ON DELETE CASCADE,
    signage_device_id UUID NOT NULL,
    sync_mode VARCHAR(50) NOT NULL,
    sync_status VARCHAR(50) NOT NULL,
    videos_synced INTEGER DEFAULT 0,
    videos_failed INTEGER DEFAULT 0,
    error_message TEXT,
    sync_started_at TIMESTAMP WITH TIME ZONE,
    sync_completed_at TIMESTAMP WITH TIME ZONE,
    device_ip_address VARCHAR(50),
    device_hostname VARCHAR(255),
    initiated_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sync_history_list_device ON video_list_sync_history(video_list_id, signage_device_id);
CREATE INDEX idx_sync_history_status ON video_list_sync_history(sync_status);
CREATE INDEX idx_sync_history_created ON video_list_sync_history(created_at DESC);
```

## Performance Characteristics

### Worker Configuration

- **Worker Pool Size**: 5 workers (configurable)
- **Concurrent Device Sync**: 3 per job (controlled by semaphore)
- **Max Retries**: 3 attempts per device
- **HTTP Timeout**: 30 seconds for sync, 10 seconds for control
- **Job Retention**: 24 hours for completed jobs

### Throughput

With default configuration:
- **Per Worker**: ~3 devices simultaneously
- **Total Capacity**: 15 devices simultaneously (5 workers × 3 devices)
- **Average Sync Time**: 5-10 seconds per device (depends on playlist size)
- **Batch Processing**: Unlimited jobs queued (memory permitting)

### Scaling Recommendations

For high-volume deployments:

```python
# Increase worker pool
worker = SignageETLWorker(max_workers=10, max_retries=5)

# Increase concurrent device syncs per job
semaphore = asyncio.Semaphore(5)  # Allow 5 concurrent devices per job
```

## Error Handling

### Retry Logic

The worker automatically retries failed syncs with exponential backoff:

1. **First Attempt**: Immediate
2. **Retry 1**: Wait 2 seconds
3. **Retry 2**: Wait 4 seconds
4. **Retry 3**: Wait 8 seconds
5. **Final Failure**: Record in sync history

### Error Types

- **Device Offline**: Marked as failed immediately (no retry)
- **Network Timeout**: Retries with backoff
- **HTTP 4xx**: Client error, no retry (recorded as failed)
- **HTTP 5xx**: Server error, retries with backoff
- **Unknown Error**: Retries with backoff

### Sync History Status Values

- **pending**: Job queued, not started
- **in_progress**: Currently syncing
- **completed**: All devices synced successfully
- **partial**: Some devices failed
- **failed**: All devices failed or job error

## Frontend Integration

The frontend can now:

1. **Create Playlists**: POST `/api/v1/signage/video-lists`
2. **Sync to Devices**: POST `/api/v1/signage/etl/sync`
3. **Check Progress**: GET `/api/v1/signage/etl/job-status/{job_id}`
4. **View History**: GET `/api/v1/signage/etl/sync-history`

Example workflow:

```javascript
// 1. Create playlist
const playlist = await createPlaylist({
    name: "Store Playlist",
    collection_ids: [1, 2, 3],
    loop_mode: "continuous"
});

// 2. Sync to device
const syncJob = await syncToDevice({
    video_list_id: playlist.uuid,
    target_devices: [deviceId],
    sync_mode: "full"
});

// 3. Poll for completion
const checkStatus = setInterval(async () => {
    const status = await getJobStatus(syncJob.sync_job_id);
    
    if (status.status === "completed") {
        console.log("Sync completed!", status.result);
        clearInterval(checkStatus);
    } else if (status.status === "failed") {
        console.error("Sync failed!", status.result);
        clearInterval(checkStatus);
    }
}, 2000); // Check every 2 seconds
```

## Testing

### Manual Testing

```bash
# 1. Start the media service
cd ppl-meta-media
source venv/bin/activate
python src/main.py

# 2. Create a video list
curl -X POST http://localhost:8000/api/v1/signage/video-lists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Playlist",
    "collection_ids": [1],
    "loop_mode": "continuous",
    "transition_duration": 1000
  }'

# 3. Register a device (or use existing from discovery)
curl -X POST http://localhost:8000/api/v1/signage/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440001",
    "device_name": "Test Device",
    "ip_address": "192.168.1.100",
    "port": 8009
  }'

# 4. Sync playlist to device
curl -X POST http://localhost:8000/api/v1/signage/etl/sync \
  -H "Content-Type: application/json" \
  -d '{
    "video_list_id": "playlist-uuid",
    "target_devices": ["550e8400-e29b-41d4-a716-446655440001"],
    "sync_mode": "full"
  }'

# 5. Check job status
curl http://localhost:8000/api/v1/signage/etl/job-status/{job_id}

# 6. View sync history
curl http://localhost:8000/api/v1/signage/etl/sync-history
```

## Monitoring

### Logs

The ETL worker logs detailed information:

```
INFO - Starting ETL worker with 5 workers
INFO - Worker 0 started
INFO - Enqueued sync job abc-123 for video list 1 to 2 device(s)
INFO - Worker 0 processing job abc-123
INFO - Successfully synced video list 'Store Playlist' to device 'signage-lobby'
INFO - Worker 0 completed job abc-123: 2/2 devices synced
```

### Metrics (Future Enhancement)

Consider adding Prometheus metrics:
- `signage_etl_jobs_queued`
- `signage_etl_jobs_completed`
- `signage_etl_jobs_failed`
- `signage_etl_sync_duration_seconds`
- `signage_etl_devices_synced_total`

## Next Steps

### Phase 8: Scheduling (Future)

- Schedule playlist changes at specific times
- Recurring sync schedules (daily, weekly)
- Calendar-based content rotation
- Holiday/event-based playlists

### Phase 9: Analytics (Future)

- Playback analytics per device
- Content performance metrics
- Device uptime tracking
- Audience engagement metrics

## Troubleshooting

### Worker Not Starting

```
ERROR - Failed to start ETL worker: ...
```

**Solution**: Check that the database is accessible and signage tables exist.

### Sync Jobs Stuck in "pending"

**Causes**:
- Worker not running
- Queue full
- Worker threads crashed

**Solution**: Restart the media service to restart the worker.

### Devices Not Receiving Updates

**Causes**:
- Device offline
- Device HTTP server not responding
- Network firewall blocking
- Incorrect device IP/port

**Solution**: Check device connectivity and logs.

### High Memory Usage

**Cause**: Too many completed jobs retained.

**Solution**: The worker automatically cleans up jobs older than 24 hours. For more aggressive cleanup:

```python
await worker.cleanup_old_jobs(max_age_hours=1)  # Keep only 1 hour
```

---

**Implementation Status**: ✅ Complete  
**Last Updated**: December 2, 2024  
**Version**: 1.0
