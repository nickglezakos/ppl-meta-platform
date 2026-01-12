# MVR Queue Architecture Refactor
**PPL Meta Platform - vmeta Service**  
**Date:** January 9, 2026  
**Version:** 2.22.4  
**Status:** Implementation Ready

---

## 🎯 Problem Statement

### Current Issue
The continuous pipeline for RTSP camera recordings has a critical flaw:
- **Video discovery via polling** sometimes misses videos (timing issues)
- **Individual creation** is queued (Queue A) ✅
- **MVR creation** runs synchronously INSIDE Queue A ❌
- If polling discovers 0 videos → No individuals → No MVR people

### Evidence from Production
**Session Analysis (January 6, 2026):**

| Session ID | Time | Videos Found | Individuals | MVR People | Result |
|------------|------|--------------|-------------|------------|--------|
| dbd02649 | 12:03-12:04 | 0 (polling miss) | 0 | 0 | ❌ FAILED |
| c921551c | 12:26-12:27 | 2 | 1 | 0 | ⚠️ Single-individual bug |
| 84555d11 | 12:39-12:40 | 5 + 0 | 2 | 2 | ✅ SUCCESS |
| b68eb7a4 | 19:15-19:16 | 0 (polling miss) | 0 | 0 | ❌ FAILED |

**Key Observations:**
1. Session 84555d11 worked perfectly when polling found videos
2. Sessions dbd02649 and b68eb7a4 failed at video discovery stage
3. Polling is unreliable for short recordings (~60 seconds)

---

## 🏗️ Proposed Architecture

### Three-Queue System

```
┌─────────────────────────────────────────────────────────────┐
│                    RECORDING SESSION                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ QUEUE A: Video Discovery → Individual Creation              │
│ - Polling discovers videos (batch of 5)                     │
│ - Background task: process_tracking_session()               │
│ - Creates individuals from person_objects                   │
│ - Status: ✅ ALREADY IMPLEMENTED                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ QUEUE B: Individual → MVR People Creation (NEW!)            │
│ - Separate background task per session                      │
│ - Runs embedding-based merge (Facenet512)                   │
│ - Creates MVR people from individuals                       │
│ - Decoupled from video discovery                            │
│ - Can be retried independently                              │
│ - Status: 🆕 TO BE IMPLEMENTED                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ QUEUE C: MVR People → Super-Individuals (SCHEDULED)         │
│ - Hierarchical merger across batches                        │
│ - Finds duplicate MVR people from different batches         │
│ - Merges into super-individuals                             │
│ - Runs: After recording OR Periodic (every N minutes)       │
│ - Status: 🆕 TO BE IMPLEMENTED                              │
└─────────────────────────────────────────────────────────────┘
```

### Before vs After

**BEFORE (Current):**
```python
process_tracking_session():
    videos = discover_videos()  # Polling-dependent
    if len(videos) == 0:
        return  # ❌ No individuals, no MVR people
    
    individuals = create_individuals(videos)
    mvr_people = merge_individuals_by_similarity(individuals)  # Synchronous
    # ❌ If discovery fails, entire pipeline stops
```

**AFTER (New):**
```python
# Queue A: Video → Individuals
process_tracking_session():
    videos = discover_videos()
    if len(videos) == 0:
        return  # Still no individuals, but...
    
    individuals = create_individuals(videos)
    # ✅ Queue MVR creation instead of running synchronously
    mvr_background_processor.queue_session_mvr_creation(
        session_uuid=session_uuid,
        individual_uuids=individuals
    )
    return  # Complete immediately

# Queue B: Individuals → MVR People (NEW background task)
async def _process_session_mvr_creation():
    individuals_data = fetch_individuals_from_db(session_uuid)
    await merge_individuals_by_similarity(individuals_data)
    
    # ✅ Queue hierarchical merge
    hierarchical_merger_scheduler.queue_merge(
        session_uuid=session_uuid,
        mvr_uuids=created_mvr_uuids
    )

# Queue C: MVR People → Super-Individuals (NEW scheduler)
async def _run_hierarchical_merge():
    recent_mvr = get_mvr_created_in_last_N_minutes()
    await hierarchical_merger.merge_hierarchical(recent_mvr)
```

---

## 📋 Implementation Plan

### Phase 1: Queue B - Separate MVR Creation ⭐ Priority

#### 1.1 Extend `MVRBackgroundProcessor`
**File:** `ppl-meta-vmeta/src/background/mvr_background_processor.py`

Add new method:
```python
async def queue_session_mvr_creation(
    self,
    session_uuid: UUID,
    individual_uuids: List[UUID],
    auth_token: Optional[str] = None
) -> Dict:
    """
    Queue MVR creation for all individuals in a session.
    Creates background task that runs embedding-based merge.
    
    Returns immediately with task ID for status tracking.
    """
```

Add internal pipeline:
```python
async def _process_session_mvr_pipeline(
    self,
    session_uuid: UUID,
    individual_uuids: List[UUID],
    auth_token: Optional[str]
):
    """
    Internal: Fetch individuals from DB and call merge function.
    This becomes the background queue for MVR creation.
    """
```

#### 1.2 Modify `process_tracking_session()`
**File:** `ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`

**Current (Line ~3020):**
```python
merged_count = await merge_individuals_by_similarity(
    db_client=db_client,
    session_uuid=session_uuid,
    matched_individuals=all_matched_individuals,
    auth_token=auth_token,
    similarity_threshold=0.70
)
```

**Change to:**
```python
# Queue MVR creation in background (don't wait)
mvr_background_processor = get_mvr_background_processor()
await mvr_background_processor.queue_session_mvr_creation(
    session_uuid=session_uuid,
    individual_uuids=created_individual_uuids,
    auth_token=auth_token
)
logger.info(f"✅ MVR creation queued for {len(created_individual_uuids)} individuals")
```

#### 1.3 Update Session Status Tracking
Add new session status: `mvr_processing`, `mvr_complete`, `mvr_failed`

Update tracking_sessions table query to show:
- Individual creation status (existing)
- MVR creation status (new)
- Hierarchical merge status (new)

#### 1.4 Add Status Endpoint
**New endpoint:** `GET /api/v1/cross-video/sessions/{session_uuid}/mvr-status`

Returns:
```json
{
  "session_uuid": "...",
  "individual_creation": "completed",
  "mvr_creation": "processing",
  "hierarchical_merge": "pending",
  "individuals_count": 6,
  "mvr_people_count": 4,
  "super_individuals_count": null
}
```

---

### Phase 2: Queue C - Scheduled Hierarchical Merger

#### 2.1 Create Hierarchical Merger Scheduler
**New File:** `ppl-meta-vmeta/src/background/hierarchical_merge_scheduler.py`

```python
class HierarchicalMergeScheduler:
    """
    Background scheduler for hierarchical MVR merging.
    
    Runs in two modes:
    1. Post-Session: After recording session MVR creation completes
    2. Periodic: Every N minutes for recent MVR people
    """
    
    async def queue_post_session_merge(
        self,
        session_uuid: UUID,
        mvr_uuids: List[UUID]
    ):
        """Queue merge after session MVR creation completes."""
    
    async def start_periodic_merge(
        self,
        interval_minutes: int = 30,
        lookback_minutes: int = 60
    ):
        """Start periodic merger for recent MVR people."""
```

#### 2.2 Integrate with MVR Background Processor
Call hierarchical merger after Queue B completes:

```python
# In _process_session_mvr_pipeline():
mvr_uuids = [created mvr people]

# Queue hierarchical merge
hierarchical_scheduler.queue_post_session_merge(
    session_uuid=session_uuid,
    mvr_uuids=mvr_uuids
)
```

#### 2.3 Add Periodic Background Task
**File:** `ppl-meta-vmeta/src/main.py`

Start scheduler on service initialization:
```python
hierarchical_merge_scheduler = HierarchicalMergeScheduler(...)
await hierarchical_merge_scheduler.start_periodic_merge(
    interval_minutes=30,  # Every 30 minutes
    lookback_minutes=120  # Merge MVR created in last 2 hours
)
```

---

### Phase 3: Reconciliation Safety Net (Bonus)

#### 3.1 Add Post-Recording Reconciliation
**File:** `ppl-meta-vmeta/src/services/batch_timeout_manager.py`

In `stop_recording()` method, add:
```python
# After final batch is triggered:
await self._reconcile_missed_videos(
    collection_id=collection_id,
    recording_start_time=recording_info['started_at'],
    recording_stop_time=datetime.utcnow()
)
```

#### 3.2 Reconciliation Logic
```python
async def _reconcile_missed_videos(self, ...):
    """
    Query database for ALL videos created during recording.
    Compare against what polling discovered.
    Trigger batch for any missed videos.
    """
    # Query Media service for videos in time range
    all_videos = await query_media_service(
        collection_id=collection_id,
        start_time=recording_start_time,
        end_time=recording_stop_time
    )
    
    # Compare against processed videos
    missed_videos = [v for v in all_videos if v.uuid not in self._processed_videos]
    
    if missed_videos:
        logger.warning(f"🔍 Reconciliation found {len(missed_videos)} missed videos!")
        await self._trigger_batch_processing(
            videos_to_process=missed_videos,
            is_final=True
        )
```

---

## 🎯 Benefits

### 1. Reliability
- ✅ MVR creation no longer depends on perfect video discovery timing
- ✅ Individuals can be processed into MVR people even if created later
- ✅ Reconciliation catches any videos polling missed

### 2. Performance
- ✅ Queue A completes faster (doesn't wait for MVR merge)
- ✅ Parallel processing: Multiple sessions can process MVR simultaneously
- ✅ Non-blocking: Recording session marked complete immediately

### 3. Maintainability
- ✅ Clear separation of concerns (discovery → individuals → MVR → super-individuals)
- ✅ Each queue can be monitored independently
- ✅ Easy to retry failed stages without reprocessing entire pipeline

### 4. Flexibility
- ✅ Can manually trigger MVR creation for old sessions
- ✅ Can adjust merge thresholds without reprocessing videos
- ✅ Hierarchical merger can run on-demand or scheduled

---

## 📊 Testing Strategy

### Unit Tests
1. Queue B: MVR creation from individuals
2. Queue C: Hierarchical merger scheduling
3. Reconciliation: Missed video detection

### Integration Tests
1. Full pipeline: Recording → Individuals → MVR → Super-Individuals
2. Polling miss scenario: Reconciliation triggers Queue A → Queue B
3. Multi-session scenario: Multiple recordings processed in parallel

### Production Validation
1. Re-test January 6 scenarios with new architecture
2. Monitor Queue B/C task completion rates
3. Compare MVR creation rates before/after

---

## 🚀 Rollout Plan

### Stage 1: Implementation (This Session)
- Implement Queue B (separate MVR creation)
- Add session MVR status tracking
- Update logging for visibility

### Stage 2: Testing & Validation
- Deploy to development environment
- Test with RTSP camera recordings
- Verify all 3 queues work correctly

### Stage 3: Production Deployment
- Deploy Queue B to production
- Monitor for 24 hours
- Deploy Queue C (hierarchical scheduler)
- Monitor for 48 hours

### Stage 4: Reconciliation (Optional)
- Add reconciliation safety net
- Test in production with monitoring
- Enable by default after validation

---

## 📝 Migration Notes

### Database Changes
None required! All existing tables support the new architecture.

### API Changes
- New endpoint: `GET /sessions/{uuid}/mvr-status` (non-breaking)
- Existing endpoints unchanged (backward compatible)

### Configuration
Add to vmeta config:
```yaml
mvr_background_processor:
  enabled: true
  max_retries: 3
  retry_delay_seconds: 5

hierarchical_merge_scheduler:
  enabled: true
  periodic_interval_minutes: 30
  lookback_minutes: 120
  post_session_delay_seconds: 30
```

---

## ✅ Success Criteria

1. **Zero polling misses cause MVR people loss**
   - Reconciliation catches all missed videos
   - Queue B processes individuals regardless of discovery timing

2. **100% MVR creation rate for valid individuals**
   - All individuals with valid embeddings get MVR people
   - Failed MVR creation can be retried independently

3. **Automatic duplicate detection**
   - Queue C merges MVR people across batches
   - Same person detected in multiple recordings → 1 super-individual

4. **Observable pipeline**
   - Clear logs for each queue stage
   - Status endpoint shows progress through pipeline
   - Failed tasks can be identified and retried

---

## 🎓 Technical Debt Resolved

1. ❌ **Old:** MVR creation coupled with video discovery
   ✅ **New:** Decoupled, can run independently

2. ❌ **Old:** Polling misses = permanent data loss
   ✅ **New:** Reconciliation + manual retry capability

3. ❌ **Old:** Same person in multiple batches = duplicate MVR people
   ✅ **New:** Hierarchical merger consolidates duplicates

4. ❌ **Old:** Failed MVR creation requires reprocessing entire session
   ✅ **New:** Retry only Queue B, keep individuals from Queue A

---

**Document Version:** 1.0  
**Author:** GitHub Copilot + User Collaboration  
**Next Steps:** Begin Phase 1 Implementation
