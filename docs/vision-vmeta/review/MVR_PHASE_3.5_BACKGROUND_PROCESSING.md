# Phase 3.5: Background Processing - Implementation Complete

## Overview

Phase 3.5 implements **automatic background processing** for MVR-People creation and matching when new Individuals are created. This ensures that MVR-People records are created automatically without blocking Individual creation, and duplicate people are intelligently merged based on face similarity.

## Components Created

### 1. MVRBackgroundProcessor (`background/mvr_background_processor.py`)
**Purpose:** Core background task processor with retry logic and statistics tracking.

**Key Features:**
- **Asynchronous Processing:** Non-blocking background tasks using `asyncio.create_task()`
- **Retry Logic:** Automatic retry with exponential backoff (configurable retries + delay)
- **Task Tracking:** Monitors pending, completed, and failed tasks
- **Statistics:** Success rates, processing times, merge counts
- **Pipeline Stages:**
  1. Create MVR-People from Individual
  2. Match against existing MVR-People
  3. Merge if high-confidence match found
  4. Log results and update statistics

**API:**
```python
async def process_new_individual(
    individual_uuid: UUID,
    session_uuid: Optional[UUID] = None,
    auto_match: bool = True
) -> Dict  # Returns task status

async def get_task_status(individual_uuid: UUID) -> Dict
async def get_statistics() -> Dict
async def get_all_pending_tasks() -> Dict
async def cleanup_old_tasks(max_age_hours: int = 24) -> int
```

### 2. MVRIntegrationHook (`background/mvr_integration_hook.py`)
**Purpose:** Clean integration point for Individual lifecycle events.

**Key Features:**
- **Lifecycle Hook:** `on_individual_created()` called after Individual creation
- **Enable/Disable:** Runtime control of automatic processing
- **Error Isolation:** Failures don't break Individual creation

**API:**
```python
async def on_individual_created(
    individual_uuid: UUID,
    session_uuid: Optional[UUID] = None,
    auto_match: bool = True
) -> None

def enable() -> None
def disable() -> None
def is_enabled() -> bool
```

### 3. MVR Helper Module (`background/mvr_helper.py`)
**Purpose:** Global access utility for easy integration.

**Key Features:**
- **Global Hook Registry:** Singleton pattern for hook access
- **Convenience Functions:** Simple one-line integration
- **Availability Checks:** Safely handle MVR not available

**API:**
```python
def set_mvr_integration_hook(hook) -> None  # Called on startup
def get_mvr_integration_hook() -> Optional[MVRIntegrationHook]

async def trigger_mvr_creation(
    individual_uuid: UUID,
    session_uuid: Optional[UUID] = None,
    auto_match: bool = True
) -> bool  # Main integration point

def is_mvr_enabled() -> bool
```

### 4. Integration Example (`background/integration_example.py`)
**Purpose:** Complete documentation and code examples for integration.

**Contents:**
- Step-by-step integration guide
- Example code snippets
- Monitoring examples
- Configuration documentation

## Integration into Application

### Main Application (`src/main.py`)
Updated application startup to initialize MVR background processing:

```python
# Initialize MVR-People services
mvr_repository = MVRRepository(connection_pool=mvr_pool)
ml_processor = MVRProcessor()
mvr_service = MVRService(repository=mvr_repository, ml_processor=ml_processor)
mvr_matcher = MVRMatcher(repository=mvr_repository, ml_processor=ml_processor)

# Initialize background processor
mvr_background_processor = MVRBackgroundProcessor(
    mvr_service=mvr_service,
    mvr_matcher=mvr_matcher,
    max_retries=3,
    retry_delay=5.0
)

# Initialize integration hook
mvr_integration_hook = MVRIntegrationHook(
    background_processor=mvr_background_processor
)

# Register globally
mvr_helper.set_mvr_integration_hook(mvr_integration_hook)
```

## Usage in Individual Creation

### Simple Integration (Recommended)
Add to `database/repository.py` in `create_individual()` method:

```python
async def create_individual(
    self,
    session_id: UUID,
    first_appearance: VideoAppearance,
    confidence_score: float
) -> UUID:
    # ... existing Individual creation code ...
    
    # Trigger automatic MVR-People creation (ONE LINE!)
    from background.mvr_helper import trigger_mvr_creation
    
    await trigger_mvr_creation(
        individual_uuid=individual_uuid,
        session_uuid=session_id,
        auto_match=True
    )
    
    return individual_uuid
```

### Manual Integration (Advanced)
Direct hook access for more control:

```python
from background import mvr_helper

hook = mvr_helper.get_mvr_integration_hook()
if hook and hook.is_enabled():
    await hook.on_individual_created(
        individual_uuid=individual_uuid,
        session_uuid=session_id,
        auto_match=True
    )
```

## Background Processing Workflow

### Complete Pipeline
1. **Individual Created** → Trigger background task (non-blocking)
2. **Background Task Starts** → Fetch person objects from Orchestrator
3. **Quality Selection** → Select best quality face from all appearances
4. **ML Processing** → Extract face embedding (512D), age, gender
5. **MVR Creation** → Create MVR-People record in database
6. **Linking** → Link Individual to MVR-People
7. **Similarity Search** → Find similar MVR-People using pgvector
8. **Match Selection** → Select best match above threshold (default 0.85)
9. **Quality Comparison** → Compare quality scores of matched MVR
10. **Merge Execution** → Orphan loser, reassign Individuals, update audit
11. **Statistics Update** → Track success/failure, processing time

### Error Handling
- **Retries:** Automatic retry up to 3 times with 5-second delay
- **Isolation:** Errors don't affect Individual creation
- **Logging:** All errors logged with context
- **Tracking:** Failed tasks stored for analysis

## Monitoring & Statistics

### Get Task Status
```python
from background import mvr_helper

hook = mvr_helper.get_mvr_integration_hook()
status = await hook.background_processor.get_task_status(individual_uuid)

# Returns:
{
    "task_id": "uuid",
    "status": "processing|completed|failed|not_found",
    "mvr_uuid": "uuid",  # if completed
    "merge_result": {...},  # if completed
    "processing_time_seconds": 2.5,
    "retry_count": 0,
    "completed_at": "2025-10-31T12:34:56"
}
```

### Get Statistics
```python
stats = await hook.background_processor.get_statistics()

# Returns:
{
    "pending": 5,
    "completed": 100,
    "failed": 2,
    "success_rate_percent": 98.04,
    "average_processing_time_seconds": 2.3,
    "merged_count": 25,
    "unique_individuals_count": 75
}
```

### Get Pending Tasks
```python
pending = await hook.background_processor.get_all_pending_tasks()

# Returns:
{
    "pending_count": 5,
    "task_ids": ["uuid1", "uuid2", ...]
}
```

### Cleanup Old Tasks
```python
# Clean up tasks older than 24 hours
cleaned = await hook.background_processor.cleanup_old_tasks(max_age_hours=24)
logger.info(f"Cleaned up {cleaned} old tasks")
```

## Configuration

### Background Processor Settings
- **max_retries:** 3 (number of retry attempts on failure)
- **retry_delay:** 5.0 seconds (delay between retries)

### MVR Matching Settings
Controlled via `mvr_matching_config` table:
- **similarity_threshold:** 0.85 (minimum similarity for match)
- **auto_merge_enabled:** True (enable automatic merging)
- **max_candidates_to_check:** 50 (limit similarity search)

### Enable/Disable at Runtime
```python
from background import mvr_helper

hook = mvr_helper.get_mvr_integration_hook()

# Disable
hook.disable()

# Enable
hook.enable()

# Check status
is_enabled = hook.is_enabled()
```

## Testing

### Test Script
Created `test_background_processing.py` to demonstrate:
1. Service initialization
2. Background task triggering
3. Status checking
4. Statistics retrieval
5. Enable/disable control
6. Pending task monitoring

### Run Test
```bash
cd ppl-meta-vmeta/src
source ../venv/bin/activate
python test_background_processing.py
```

## Benefits

### 1. Non-Blocking Performance
- Individual creation completes immediately
- MVR processing happens asynchronously
- No waiting for ML model inference

### 2. Automatic Intelligence
- No manual MVR creation needed
- Automatic duplicate detection
- Quality-based merging decisions

### 3. Reliability
- Retry logic handles transient failures
- Error isolation protects main workflow
- Complete audit trail

### 4. Scalability
- Parallel processing of multiple Individuals
- Configurable resource limits (max retries, delays)
- Background task cleanup

### 5. Observability
- Real-time task status tracking
- Comprehensive statistics
- Success rate monitoring
- Processing time metrics

## Next Steps

### Phase 3.6: Testing Phase 3 Components
- Unit tests for background processor
- Integration tests for complete pipeline
- Performance testing with real data
- Error scenario testing

### Phase 4: API Implementation
- REST endpoints for MVR-People CRUD
- Background task status endpoints
- Statistics and monitoring endpoints
- Configuration management endpoints

## Files Modified/Created

### Created Files
1. `src/background/__init__.py` - Module exports
2. `src/background/mvr_background_processor.py` - Core processor (500+ lines)
3. `src/background/mvr_integration_hook.py` - Integration hook (90 lines)
4. `src/background/mvr_helper.py` - Global access utility (90 lines)
5. `src/background/integration_example.py` - Documentation + examples (140 lines)
6. `src/test_background_processing.py` - Test script (180 lines)

### Modified Files
1. `src/main.py` - Added MVR services initialization

### Total Lines Added
~1,100 lines of production code + documentation

## Status

✅ **Phase 3.5 COMPLETE**

All background processing infrastructure is implemented and ready for integration.
The system is designed for easy integration (one line of code), reliable operation
(retry logic, error isolation), and comprehensive monitoring (statistics, status tracking).

---

**Implementation Date:** October 31, 2025  
**Author:** PPL Meta Platform Team  
**Status:** Complete - Ready for Phase 3.6 Testing
