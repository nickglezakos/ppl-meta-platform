# Automatic PPL Thread Trigger - Queue-Based Solution

## Problem Analysis
The direct service-to-service automatic triggering approach has proven unreliable due to:
- Service coupling issues
- API parameter validation complexities  
- Session management coordination
- Race conditions between face detection completion and PPL Thread triggering

## Solution 1: Redis/Celery Queue System (Recommended)

### Architecture Overview
```
Face Detection Workflow Completion → Redis Queue → Celery Worker → PPL Thread Trigger
```

### Implementation Steps

#### 1. Install Dependencies
```bash
# Add to requirements.txt for relevant services
redis==4.5.4
celery==5.3.1
```

#### 2. Queue Configuration
```python
# shared/queue_config.py
from celery import Celery
import redis

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Celery app configuration  
celery_app = Celery(
    'ppl_workflows',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'trigger_ppl_thread': {'queue': 'ppl_thread_queue'},
    }
)
```

#### 3. Celery Worker Task
```python
# workers/ppl_thread_worker.py
from celery import Celery
import httpx
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name='trigger_ppl_thread')
def trigger_ppl_thread_task(media_id: str, total_faces: int, workflow_id: str):
    """
    Celery task to trigger PPL Thread workflow after face detection completion.
    Runs asynchronously in a separate worker process.
    """
    try:
        logger.info(f"🚀 QUEUE TRIGGER: Processing PPL Thread for media {media_id}")
        
        # Make API call to trigger PPL Thread
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "http://localhost:8003/api/v1/person-objects/workflow/trigger",
                json={
                    "media_id": media_id,
                    "total_faces": str(total_faces),
                    "trigger_reason": f"automatic_queue_trigger_from_workflow_{workflow_id}",
                    "session_uuid": f"queue-session-{workflow_id}"
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"✅ QUEUE TRIGGER: Successfully triggered PPL Thread for {media_id}")
                return {"success": True, "media_id": media_id, "response": response.json()}
            else:
                logger.error(f"❌ QUEUE TRIGGER: Failed with status {response.status_code}: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}", "media_id": media_id}
                
    except Exception as e:
        logger.error(f"❌ QUEUE TRIGGER: Exception for {media_id}: {e}")
        return {"success": False, "error": str(e), "media_id": media_id}
```

#### 4. Queue Producer (Media Service Integration)
```python
# In ppl-meta-media/src/api/v1/face_detection_workflows.py
from shared.queue_config import redis_client
from workers.ppl_thread_worker import trigger_ppl_thread_task

async def queue_ppl_thread_trigger(media_id: str, total_faces: int, workflow_id: str):
    """
    Queue PPL Thread trigger instead of direct API call.
    Much more reliable than direct service-to-service calls.
    """
    try:
        # Add to Redis queue for async processing
        task = trigger_ppl_thread_task.delay(
            media_id=media_id,
            total_faces=total_faces, 
            workflow_id=workflow_id
        )
        
        logger.info(f"🎯 QUEUED PPL TRIGGER: Task {task.id} queued for media {media_id}")
        return {"queued": True, "task_id": task.id}
        
    except Exception as e:
        logger.error(f"❌ QUEUE ERROR: Failed to queue PPL trigger for {media_id}: {e}")
        return {"queued": False, "error": str(e)}

# Replace the existing trigger_automatic_ppl_thread_workflow function
async def trigger_automatic_ppl_thread_workflow(media_ids: List[str], total_faces: int, workflow_id: str):
    """
    UPDATED: Use queue-based triggering instead of direct API calls
    """
    if not media_ids:
        logger.warning("No media IDs provided for automatic PPL Thread trigger")
        return

    logger.info(f"🎯 AUTOMATIC PPL TRIGGER: Queueing PPL Thread for {len(media_ids)} media items")
    
    for media_id in media_ids:
        result = await queue_ppl_thread_trigger(media_id, total_faces, workflow_id)
        if result.get("queued"):
            logger.info(f"✅ QUEUED: PPL Thread trigger for {media_id} (task: {result.get('task_id')})")
        else:
            logger.error(f"❌ QUEUE FAILED: Could not queue PPL trigger for {media_id}")
```

### 5. Deployment Setup
```bash
# Start Redis server
redis-server

# Start Celery worker (separate process)
celery -A workers.ppl_thread_worker worker --loglevel=info --queue=ppl_thread_queue

# Start Celery monitoring (optional)  
celery -A workers.ppl_thread_worker flower
```

### Benefits of Queue Approach
1. **Decoupling**: Services don't need to know about each other's APIs
2. **Reliability**: Tasks can be retried, persistent across restarts
3. **Scalability**: Multiple workers can process triggers
4. **Monitoring**: Easy to see queued/failed tasks
5. **No Race Conditions**: Async processing eliminates timing issues

---

## Solution 2: Orchestrator Workflow Management (Alternative)

### Architecture Overview
```
Orchestrator Workflow Engine → Monitor Face Detection Status → Auto-trigger PPL Thread
```

### Implementation in Orchestrator Service

#### 1. Workflow Definition
```python
# ppl-meta-orchestrator/src/workflows/auto_ppl_workflow.py
from typing import Dict, Any
import asyncio
import httpx
import logging

class AutoPPLWorkflow:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def monitor_and_trigger_workflow(self, media_id: str, check_interval: int = 5):
        """
        Orchestrator workflow that monitors face detection completion
        and automatically triggers PPL Thread processing.
        """
        try:
            self.logger.info(f"🔍 ORCHESTRATOR: Starting auto-PPL workflow for {media_id}")
            
            # Step 1: Wait for face detection to complete
            face_data = await self._wait_for_face_detection(media_id, check_interval)
            
            if not face_data or face_data.get("total_faces", 0) == 0:
                self.logger.info(f"⏭️ ORCHESTRATOR: No faces detected for {media_id}, skipping PPL Thread")
                return {"success": True, "skipped": True, "reason": "no_faces"}
                
            # Step 2: Trigger PPL Thread workflow
            ppl_result = await self._trigger_ppl_thread(media_id, face_data["total_faces"])
            
            # Step 3: Monitor PPL Thread completion
            person_data = await self._wait_for_ppl_completion(media_id)
            
            self.logger.info(f"✅ ORCHESTRATOR: Auto-PPL workflow completed for {media_id}")
            return {
                "success": True,
                "media_id": media_id,
                "faces_detected": face_data["total_faces"],
                "persons_created": person_data.get("total_persons", 0),
                "workflow_completed": True
            }
            
        except Exception as e:
            self.logger.error(f"❌ ORCHESTRATOR: Auto-PPL workflow failed for {media_id}: {e}")
            return {"success": False, "error": str(e), "media_id": media_id}
    
    async def _wait_for_face_detection(self, media_id: str, check_interval: int = 5, max_wait: int = 120):
        """Wait for face detection to complete with timeout"""
        waited = 0
        while waited < max_wait:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:8003/faces/media/{media_id}")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("total_faces", 0) > 0:
                            return data
                
                await asyncio.sleep(check_interval)
                waited += check_interval
                
            except Exception as e:
                self.logger.warning(f"Face detection check failed: {e}")
                await asyncio.sleep(check_interval)
                waited += check_interval
                
        return None
    
    async def _trigger_ppl_thread(self, media_id: str, total_faces: int):
        """Trigger PPL Thread workflow"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8003/api/v1/person-objects/workflow/trigger",
                json={
                    "media_id": media_id,
                    "total_faces": str(total_faces),
                    "trigger_reason": "orchestrator_auto_workflow",
                    "session_uuid": f"orchestrator-{media_id}"
                }
            )
            return response.json()
    
    async def _wait_for_ppl_completion(self, media_id: str, check_interval: int = 3, max_wait: int = 60):
        """Wait for PPL Thread to complete"""
        waited = 0
        while waited < max_wait:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:8002/person-objects/{media_id}")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") not in ["pending", "processing"]:
                            return data
                
                await asyncio.sleep(check_interval)
                waited += check_interval
                
            except Exception as e:
                self.logger.warning(f"PPL Thread check failed: {e}")
                await asyncio.sleep(check_interval)
                waited += check_interval
                
        return {"status": "timeout"}
```

#### 2. Orchestrator API Endpoint
```python
# ppl-meta-orchestrator/src/main.py
from workflows.auto_ppl_workflow import AutoPPLWorkflow

@app.post("/workflows/auto-ppl/{media_id}")
async def start_auto_ppl_workflow(media_id: str, background_tasks: BackgroundTasks):
    """
    Start an orchestrated workflow that handles face detection → PPL Thread automatically
    """
    workflow = AutoPPLWorkflow()
    
    # Run workflow in background
    background_tasks.add_task(workflow.monitor_and_trigger_workflow, media_id)
    
    return {
        "workflow_started": True,
        "media_id": media_id,
        "message": "Auto-PPL workflow started in background"
    }
```

#### 3. Integration with Face Detection
```python
# In Media Service, replace direct trigger with orchestrator call
async def trigger_orchestrator_auto_workflow(media_id: str):
    """
    Trigger orchestrator auto-workflow instead of direct PPL Thread trigger
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8002/workflows/auto-ppl/{media_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Failed to trigger orchestrator auto-workflow: {e}")
        return {"success": False, "error": str(e)}
```

### Benefits of Orchestrator Approach
1. **Centralized Logic**: All workflow coordination in one service
2. **Monitoring**: Built-in workflow status tracking
3. **Retry Logic**: Can implement sophisticated retry strategies
4. **No New Dependencies**: Uses existing orchestrator infrastructure

---

## Recommendation

**Use Solution 1 (Queue-Based)** for production because:
- **Proven Architecture**: Redis/Celery is battle-tested for async workflows
- **Better Scaling**: Can handle high volume of face detection → PPL Thread triggers
- **Fault Tolerance**: Tasks survive service restarts
- **Easy Monitoring**: Flower UI for queue inspection

**Use Solution 2 (Orchestrator)** if you prefer:
- **No New Dependencies**: Stays within existing service architecture
- **Simpler Deployment**: No Redis/Celery setup required
- **Centralized Control**: All workflow logic in orchestrator service

Both solutions eliminate the unreliable direct service-to-service triggering that has been causing issues.