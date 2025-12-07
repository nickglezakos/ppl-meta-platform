# PPL Meta Platform Workflows

**Version:** 2.19.70  
**Last Updated:** December 5, 2025  
**Status:** Production Ready

## Overview

The PPL Meta Platform implements a comprehensive workflow orchestration system that manages all person detection, tracking, and analytics processes. All workflows are centrally registered in the **Orchestrator Service** and can be triggered manually, automatically via triggers, or through camera events.

## Table of Contents

- [Workflow Architecture](#workflow-architecture)
- [Workflow Registry](#workflow-registry)
- [Detection Workflows](#detection-workflows)
- [Tracking Workflows](#tracking-workflows)
- [Analytics Workflows](#analytics-workflows)
- [Automation Workflows](#automation-workflows)
- [Lifecycle Workflows](#lifecycle-workflows)
- [API Reference](#api-reference)
- [Integration Guide](#integration-guide)

---

## Workflow Architecture

### Central Registry

All workflows are registered in the **Orchestrator Service** (`ppl-meta-orchestrator` on port 8002) through the Workflows Registry system.

**Key Components:**
- `workflows_registry.py` - Central workflow definitions and metadata
- `workflows_registry_endpoints.py` - REST API for workflow discovery
- Authentication support for unified security and future user-specific workflows

### Workflow Structure

Each workflow contains:

```python
{
  "id": "workflow_identifier",
  "name": "Human-Readable Name",
  "description": "What the workflow does",
  "category": "detection|tracking|analytics|automation|lifecycle",
  "workflow_type": "specific_type",
  "is_active": true,
  "execution_count": 0,
  "success_rate": 95.0,
  "average_duration_seconds": 2.5,
  "parameters": [
    {
      "name": "parameter_name",
      "type": "string|number|boolean|array|object",
      "description": "Parameter description",
      "required": true|false,
      "default": "default_value"
    }
  ],
  "requires_auth": true,
  "supports_batch": true,
  "supports_realtime": false
}
```

---

## Workflow Registry

### Accessing the Registry

**List All Workflows:**
```bash
GET http://localhost:8002/api/v1/workflows/registry
```

**Get Specific Workflow:**
```bash
GET http://localhost:8002/api/v1/workflows/registry/{workflow_id}
```

**Get Workflow Statistics:**
```bash
GET http://localhost:8002/api/v1/workflows/count
```

**List Categories:**
```bash
GET http://localhost:8002/api/v1/workflows/categories
```

### Authentication

All endpoints support optional authentication:
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8002/api/v1/workflows/registry
```

---

## Detection Workflows

### 1. Face Detection Workflow

**ID:** `face_detection`  
**Category:** Detection  
**Success Rate:** 98.5%  
**Avg Duration:** 2.5 seconds

#### Description
Enhanced face detection with distance calculation and embedding generation. This is the primary workflow for detecting faces in media files or camera streams.

#### Features
- Two-stage detection method (Haar Cascade + DNN)
- Real-time distance calculation from camera
- Face embedding generation for recognition
- Session-based result storage
- Support for batch and real-time processing

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID or camera ID to process |
| `confidence_threshold` | number | No | 0.5 | Minimum confidence threshold (0.0-1.0) |
| `enable_distance_calculation` | boolean | No | true | Calculate distance from camera |
| `method` | string | No | "two_stage" | Detection method: two_stage, single_stage, or both |

#### Usage Example

```python
# Via Master Lifecycle
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "source_identifier": "video_001.mp4",
  "source_type": "media",
  "workflow_types": ["face_detection"],
  "config": {
    "confidence_threshold": 0.7,
    "enable_distance_calculation": true,
    "method": "two_stage"
  }
}
```

#### Results
- Face bounding boxes with coordinates
- Confidence scores per detection
- Distance estimates from camera
- Face embeddings (512-dimensional vectors)
- Stored in Vision Service database

---

## Tracking Workflows

### 2. Person Objects Creation

**ID:** `person_objects`  
**Category:** Tracking  
**Success Rate:** 96.2%  
**Avg Duration:** 1.8 seconds

#### Description
Creates and tracks person objects from face detection results. Groups multiple face detections of the same individual across frames into unified person objects.

#### Features
- Face embedding similarity matching
- Automatic person object merging
- Confidence-based grouping
- Cross-video person tracking
- Person object lifecycle management

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID with face detection results |
| `merge_threshold` | number | No | 0.7 | Similarity threshold for merging (0.0-1.0) |

#### Usage Example

```python
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "source_identifier": "video_001.mp4",
  "workflow_types": ["face_detection", "person_objects"],
  "config": {
    "merge_threshold": 0.75
  }
}
```

#### Results
- Unified person objects with UUIDs
- Face detection associations
- Person appearance counts
- Confidence scores
- Stored in Media Service database

---

## Analytics Workflows

### 3. Person Routes Analytics

**ID:** `person_routes`  
**Category:** Analytics  
**Success Rate:** 94.8%  
**Avg Duration:** 3.2 seconds

#### Description
Analyzes person movement patterns and generates route analytics. Creates spatial and temporal analysis of person trajectories through the monitored space.

#### Features
- Movement path reconstruction
- Dwell time analysis
- Entry/exit point detection
- Route pattern recognition
- Heatmap generation

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID with person objects |
| `min_route_length` | number | No | 3 | Minimum frames for valid route |

#### Usage Example

```python
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "workflow_types": ["face_detection", "person_objects", "person_routes"],
  "config": {
    "min_route_length": 5
  }
}
```

#### Results
- Route coordinates and timestamps
- Movement velocity and direction
- Dwell time per location
- Entry/exit statistics
- Route pattern classifications

---

### 4. Advanced Vector Analytics

**ID:** `vector_analytics`  
**Category:** Analytics  
**Success Rate:** 92.1%  
**Avg Duration:** 4.5 seconds

#### Description
Performs advanced vector-based analytics and pattern recognition on face embeddings and person data. Enables clustering, similarity search, and demographic analysis.

#### Features
- Face embedding clustering (DBSCAN, K-means)
- Similarity search across database
- Anomaly detection
- Pattern recognition
- Demographic clustering

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID for analytics |
| `analysis_types` | array | No | ["clustering", "similarity"] | Types of analysis to perform |

#### Usage Example

```python
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "workflow_types": ["vector_analytics"],
  "config": {
    "analysis_types": ["clustering", "similarity", "anomaly"]
  }
}
```

#### Results
- Cluster assignments
- Similarity scores
- Anomaly flags
- Pattern identifications
- Statistical summaries

---

### 5. Age & Gender Detection

**ID:** `age_gender_detection`  
**Category:** Analytics  
**Success Rate:** 89.4%  
**Avg Duration:** 1.9 seconds

#### Description
Detects age range and gender demographics from face detection results. Provides demographic insights for analytics and reporting.

#### Features
- Age group classification (child, teen, adult, senior)
- Gender detection (male, female)
- Confidence scoring per prediction
- Demographic aggregation
- Privacy-preserving analysis

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID with face detection results |
| `age_groups` | array | No | ["child", "teen", "adult", "senior"] | Age classifications |

#### Usage Example

```python
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "workflow_types": ["face_detection", "age_gender_detection"],
  "config": {
    "age_groups": ["child", "teen", "young_adult", "adult", "senior"]
  }
}
```

#### Results
- Age group classifications
- Gender predictions
- Confidence scores
- Demographic statistics
- Aggregate reports

---

## Automation Workflows

### 6. Bulk Media Processing

**ID:** `bulk_processing`  
**Category:** Automation  
**Success Rate:** 97.3%  
**Avg Duration:** 15.0 seconds

#### Description
Processes multiple media files in batch with configurable workflows. Ideal for processing large collections of videos or images with consistent workflow configurations.

#### Features
- Multi-media parallel processing
- Configurable workflow chains
- Progress tracking per media
- Error handling and retry logic
- Batch result aggregation

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `media_ids` | array | Yes | - | List of media IDs to process |
| `workflow_types` | array | Yes | ["face_detection", "person_objects"] | Workflows to execute |

#### Usage Example

```python
POST /api/v1/workflows/bulk-processing
{
  "media_ids": [
    "media-uuid-001",
    "media-uuid-002",
    "media-uuid-003"
  ],
  "workflow_types": [
    "face_detection",
    "person_objects",
    "person_routes"
  ],
  "config": {
    "confidence_threshold": 0.6,
    "merge_threshold": 0.75
  }
}
```

#### Results
- Per-media processing status
- Aggregate success/failure counts
- Total processing time
- Individual workflow results
- Error logs for failed items

---

### 7. Camera-Triggered Workflow

**ID:** `camera_triggered`  
**Category:** Automation  
**Success Rate:** 95.7%  
**Avg Duration:** 2.1 seconds

#### Description
Real-time workflow triggered by camera events and motion detection. Automatically processes camera feeds when motion or scheduled events occur.

#### Features
- Motion-based triggering
- Scheduled execution
- Real-time processing
- Event-driven architecture
- Low-latency response

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `camera_device_id` | string | Yes | - | Camera device identifier |
| `trigger_type` | string | No | "motion" | Event trigger: motion, schedule, manual |

#### Usage Example

```python
POST /api/v1/camera-automation/trigger
{
  "camera_device_id": "camera-uuid-456",
  "trigger_type": "motion",
  "workflow_types": ["face_detection"],
  "config": {
    "confidence_threshold": 0.7,
    "enable_distance_calculation": true
  }
}
```

#### Results
- Real-time detection results
- Event timestamps
- Trigger source information
- Processing metrics
- Alert notifications (if configured)

---

## Lifecycle Workflows

### 8. Master Person Lifecycle

**ID:** `master_lifecycle`  
**Category:** Lifecycle  
**Success Rate:** 96.8%  
**Avg Duration:** 8.5 seconds

#### Description
Complete person detection lifecycle: detection → objects → routes → analytics. This is the comprehensive workflow that executes the entire person tracking pipeline.

#### Features
- End-to-end person tracking pipeline
- Sequential workflow orchestration
- Session-based execution tracking
- Progress monitoring
- Comprehensive result aggregation

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source_id` | string | Yes | - | Media ID or camera ID |
| `workflow_types` | array | No | ["face_detection", "person_objects", "person_routes"] | Sub-workflows |
| `execution_trigger` | string | No | "manual" | Trigger source: manual, scheduled, automated |

#### Usage Example

```python
POST /api/v1/master-lifecycle/start
{
  "source_id": "media-uuid-123",
  "source_identifier": "retail_store_cam1.mp4",
  "source_type": "media",
  "workflow_types": [
    "face_detection",
    "person_objects",
    "person_routes",
    "vector_analytics"
  ],
  "execution_trigger": "manual",
  "config": {
    "confidence_threshold": 0.65,
    "merge_threshold": 0.75,
    "min_route_length": 5
  }
}
```

#### Workflow Stages

1. **Face Detection** (10-30% progress)
   - Detect faces in all frames
   - Generate embeddings
   - Calculate distances

2. **Person Objects** (30-60% progress)
   - Group faces into person objects
   - Merge similar persons
   - Assign unique identifiers

3. **Person Routes** (60-85% progress)
   - Reconstruct movement paths
   - Analyze dwell times
   - Identify entry/exit points

4. **Vector Analytics** (85-100% progress)
   - Cluster similar persons
   - Pattern recognition
   - Generate insights

#### Results
- Complete person tracking data
- Unified results from all sub-workflows
- Execution statistics and timings
- Session UUID for tracking
- Comprehensive analytics report

---

## API Reference

### Base URLs

- **Orchestrator Service:** `http://localhost:8002`
- **Workflows Registry:** `http://localhost:8002/api/v1/workflows`

### Authentication

All endpoints support Bearer token authentication:

```http
Authorization: Bearer <your-jwt-token>
```

### Common Response Format

```json
{
  "session_uuid": "uuid-v4",
  "status": "queued|processing|completed|failed",
  "progress": 0.0,
  "current_stage": "stage_name",
  "created_at": "2025-12-05T10:30:00Z",
  "completed_at": "2025-12-05T10:30:10Z",
  "results": {
    "workflow_name": {
      "data": {},
      "metrics": {}
    }
  },
  "error_message": null
}
```

### Workflow Execution

**Start Master Lifecycle:**
```http
POST /api/v1/master-lifecycle/start
Content-Type: application/json
Authorization: Bearer <token>

{
  "source_id": "string",
  "source_identifier": "string",
  "source_type": "media|camera|stream",
  "workflow_types": ["array"],
  "execution_trigger": "string",
  "config": {}
}
```

**Check Workflow Status:**
```http
GET /api/v1/master-lifecycle/status/{session_uuid}
Authorization: Bearer <token>
```

**Get Workflow Results:**
```http
GET /api/v1/master-lifecycle/results/{session_uuid}
Authorization: Bearer <token>
```

**Cancel Workflow:**
```http
POST /api/v1/master-lifecycle/cancel/{session_uuid}
Authorization: Bearer <token>
```

### Workflow Registry

**List All Workflows:**
```http
GET /api/v1/workflows/registry
GET /api/v1/workflows/registry?category=detection
GET /api/v1/workflows/registry?is_active=true
```

**Get Workflow Details:**
```http
GET /api/v1/workflows/registry/{workflow_id}
```

**Get Statistics:**
```http
GET /api/v1/workflows/count
```

---

## Integration Guide

### Frontend Integration

The PPL Meta Frontend automatically displays all registered workflows in the **Actions** tab at `http://localhost:3000/#/triggers`.

**Components:**
- `lib/models/workflow_action_model.dart` - Workflow data models
- `lib/services/workflow_action_service.dart` - API client
- `lib/widgets/actions_tab.dart` - UI component

**Example Usage:**
```dart
// Initialize workflow service
final workflowService = WorkflowActionService();

// Get auth token
final authService = AuthService();
final token = await authService.getStoredToken();
if (token != null) {
  workflowService.setAuthToken(token);
}

// Fetch workflows
final workflows = await workflowService.getWorkflows();

// Filter by category
final detectionWorkflows = await workflowService
    .getWorkflowsByCategory('detection');
```

### Trigger Integration

Workflows can be executed automatically through the **Triggers** system:

1. **Create Trigger** in Media Service
2. **Set Action** to workflow ID (e.g., "face_detection")
3. **Configure Conditions** (time-based, event-based)
4. **Link to Source** (media ID, camera ID)

**Example Trigger:**
```json
{
  "name": "Morning Face Detection",
  "description": "Run face detection every morning at 8 AM",
  "trigger_type": "time_based",
  "action": "face_detection",
  "action_params": {
    "confidence_threshold": 0.7,
    "enable_distance_calculation": true
  },
  "schedule": "0 8 * * *",
  "is_active": true
}
```

### Python Client Example

```python
import requests

# Orchestrator base URL
ORCHESTRATOR_URL = "http://localhost:8002"

# Get auth token (from your auth system)
auth_token = "your-jwt-token-here"
headers = {"Authorization": f"Bearer {auth_token}"}

# List all workflows
response = requests.get(
    f"{ORCHESTRATOR_URL}/api/v1/workflows/registry",
    headers=headers
)
workflows = response.json()

# Start face detection workflow
start_response = requests.post(
    f"{ORCHESTRATOR_URL}/api/v1/master-lifecycle/start",
    headers=headers,
    json={
        "source_id": "media-uuid-123",
        "source_identifier": "video.mp4",
        "workflow_types": ["face_detection"],
        "config": {
            "confidence_threshold": 0.7
        }
    }
)

session = start_response.json()
session_uuid = session["session_uuid"]

# Poll for status
import time
while True:
    status_response = requests.get(
        f"{ORCHESTRATOR_URL}/api/v1/master-lifecycle/status/{session_uuid}",
        headers=headers
    )
    status = status_response.json()
    
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# Get results
results_response = requests.get(
    f"{ORCHESTRATOR_URL}/api/v1/master-lifecycle/results/{session_uuid}",
    headers=headers
)
results = results_response.json()
```

---

## Best Practices

### 1. Workflow Selection

- Use **face_detection** alone for quick face identification
- Use **person_objects** when tracking individuals across frames
- Use **person_routes** for movement analysis
- Use **master_lifecycle** for comprehensive analysis
- Use **bulk_processing** for large media collections

### 2. Parameter Tuning

**Confidence Threshold:**
- `0.5` - Standard detection (default)
- `0.7` - High precision, fewer false positives
- `0.3` - High recall, more detections (may include false positives)

**Merge Threshold:**
- `0.7` - Standard merging (default)
- `0.8` - Stricter merging, more unique persons
- `0.6` - Looser merging, fewer person objects

### 3. Performance Optimization

- Use batch processing for non-real-time scenarios
- Enable real-time only for camera streams
- Adjust confidence thresholds based on media quality
- Monitor execution times and success rates
- Use progress endpoints for long-running workflows

### 4. Error Handling

- Always check workflow status before retrieving results
- Implement retry logic for failed workflows
- Monitor error messages for debugging
- Use session UUIDs for tracking across systems

---

## Monitoring & Metrics

### Workflow Statistics

Each workflow tracks:
- **Execution Count:** Total times executed
- **Success Rate:** Percentage of successful completions
- **Average Duration:** Mean execution time
- **Active Status:** Whether workflow is currently enabled

### Health Checks

```bash
# Orchestrator health
curl http://localhost:8002/health

# Workflow registry health
curl http://localhost:8002/api/v1/workflows/count
```

### Logging

Workflow execution logs are stored in:
- **Orchestrator:** `/ppl-meta-orchestrator/logs/ppl-meta-orchestrator.log`
- **Session Logs:** Database with session UUID

---

## Future Enhancements

### Planned Features

1. **User-Specific Workflows**
   - Custom workflow creation per user
   - Private workflow registry
   - Workflow sharing and permissions

2. **Workflow Templates**
   - Pre-configured workflow chains
   - Industry-specific templates
   - Quick-start configurations

3. **Advanced Scheduling**
   - Cron-based scheduling
   - Event-driven triggers
   - Conditional execution

4. **Result Caching**
   - Avoid duplicate processing
   - Faster result retrieval
   - Resource optimization

5. **Workflow Versioning**
   - Version control for workflows
   - Rollback capabilities
   - A/B testing support

---

## Support & Resources

### Documentation
- Architecture: `/docs/architecture/`
- API Docs: `/docs/api/`
- Development: `/docs/guides/developer/`

### Services
- **Orchestrator:** Port 8002
- **Vision:** Port 8003
- **Media:** Port 8000
- **Cameras:** Port 8005

### Contact
For questions or issues, refer to the main PPL Meta Platform documentation or contact the development team.

---

**Document Version:** 1.0  
**Platform Version:** 2.19.70  
**Last Updated:** December 5, 2025
