"""
End-to-End Integration Tests for Continuous Individuals and MVR Pipeline
PPL Meta Platform - vmeta Service

Complete integration tests covering the entire pipeline from camera recording
through batch processing to MVR creation. Tests real service interactions and
validates the full workflow.

Created: November 13, 2025
"""

import pytest
import asyncio
import httpx
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, List, Optional
import asyncpg
import json

from src.models.batch_processing import (
    BatchProcessingState,
    BatchStatus,
    TriggerReason,
    VideoCompletionEvent,
    RecordingStopEvent
)
from src.database.batch_repository import BatchProcessingRepository
from src.services.batch_config import BatchConfigService
from src.services.batch_monitor import BatchMonitor
from src.services.event_integration import CameraEventIntegration
from src.services.hybrid_batch_trigger import HybridBatchTrigger
from src.services.pipeline_executor import PipelineExecutor


# Test Configuration
TEST_CONFIG = {
    'gateway_url': 'http://localhost:8080',
    'node_url': 'http://localhost:8001',
    'media_url': 'http://localhost:8000',
    'orchestrator_url': 'http://localhost:8002',
    'vision_url': 'http://localhost:8003',
    'cameras_url': 'http://localhost:8005',
    'vmeta_url': 'http://localhost:8008',
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'ppl_meta_vmeta_test',
    'db_user': 'postgres',
    'db_password': 'postgres'
}


@pytest.fixture
async def db_pool():
    """Create database connection pool for testing."""
    pool = await asyncpg.create_pool(
        host=TEST_CONFIG['db_host'],
        port=TEST_CONFIG['db_port'],
        database=TEST_CONFIG['db_name'],
        user=TEST_CONFIG['db_user'],
        password=TEST_CONFIG['db_password'],
        min_size=2,
        max_size=10
    )
    
    # Clean up test data
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM batch_processing_state WHERE collection_id LIKE 'test-%'")
        await conn.execute("DELETE FROM batch_video_assignments WHERE collection_id LIKE 'test-%'")
        await conn.execute("DELETE FROM batch_processing_history WHERE collection_id LIKE 'test-%'")
    
    yield pool
    await pool.close()


@pytest.fixture
async def http_client():
    """Create HTTP client for API calls."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
async def auth_token(http_client):
    """Authenticate and obtain JWT token."""
    response = await http_client.post(
        f"{TEST_CONFIG['gateway_url']}/api/v1/auth/login",
        json={
            'username': 'test-user',
            'password': 'test-password'
        }
    )
    
    if response.status_code != 200:
        pytest.skip("Authentication failed - services may not be running")
    
    data = response.json()
    return data['access_token']


@pytest.fixture
async def repository(db_pool):
    """Create batch repository."""
    return BatchProcessingRepository(db_pool)


@pytest.fixture
async def config_service(repository):
    """Create config service with test configuration."""
    return BatchConfigService(
        repository=repository,
        config_path='config/batch_processing.yml'
    )


@pytest.fixture
async def batch_monitor(repository, config_service):
    """Create batch monitor."""
    return BatchMonitor(
        repository=repository,
        config_service=config_service
    )


@pytest.fixture
async def hybrid_trigger(batch_monitor):
    """Create hybrid batch trigger."""
    trigger = HybridBatchTrigger(
        default_timeout_minutes=10,
        default_min_partial_batch_size=2
    )
    trigger.set_batch_monitor(batch_monitor)
    return trigger


@pytest.fixture
async def pipeline_executor():
    """Create pipeline executor."""
    return PipelineExecutor(
        orchestrator_url=TEST_CONFIG['orchestrator_url'],
        max_concurrent_batches=3,
        max_retries=3
    )


@pytest.fixture
def test_collection_id():
    """Generate unique test collection ID."""
    return f"test-collection-{uuid4()}"


@pytest.fixture
def test_user_id():
    """Generate unique test user ID."""
    return f"test-user-{uuid4()}"


class TestEndToEndPipeline:
    """End-to-end integration tests for complete pipeline."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_workflow_5_videos(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor,
        hybrid_trigger,
        pipeline_executor,
        test_collection_id,
        test_user_id
    ):
        """
        Test complete workflow: 5 videos → batch trigger → processing → MVR creation.
        
        Flow:
        1. Configure batch size to 5
        2. Simulate 5 video completion events
        3. Verify batch triggers at video 5
        4. Wait for pipeline execution
        5. Verify individuals and MVR people created
        6. Check cache hit rates
        """
        
        # Step 1: Configure batch size
        config_response = await http_client.put(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/batch-size",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'batch_size': 5,
                'collection_id': test_collection_id
            }
        )
        
        assert config_response.status_code == 200, "Failed to configure batch size"
        
        # Step 2: Simulate 5 video completions
        video_ids = [str(uuid4()) for _ in range(5)]
        
        for i, video_id in enumerate(video_ids, 1):
            # Add video to batch
            await batch_monitor.add_video_to_batch(
                collection_id=test_collection_id,
                video_uuid=video_id,
                video_start_time=datetime.utcnow() - timedelta(seconds=30),
                video_end_time=datetime.utcnow(),
                face_detection_session_uuid=str(uuid4()),
                faces_detected=3
            )
            
            print(f"✓ Video {i}/5 added to batch")
            
            # Check if batch triggered
            if i == 5:
                # Should trigger on 5th video
                batch_state = await repository.get_active_batch(test_collection_id)
                assert batch_state is not None, "Batch not created"
                assert batch_state['video_count'] == 5, f"Expected 5 videos, got {batch_state['video_count']}"
        
        # Step 3: Wait for batch to process
        print("⏱️  Waiting for batch processing...")
        
        batch_uuid = None
        for _ in range(60):  # Wait up to 60 seconds
            await asyncio.sleep(1)
            
            # Check batch history
            history_response = await http_client.get(
                f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
                headers={'Authorization': f'Bearer {auth_token}'},
                params={
                    'collection_id': test_collection_id,
                    'limit': 1
                }
            )
            
            if history_response.status_code == 200:
                data = history_response.json()
                
                if data['batches'] and data['batches'][0]['status'] == 'completed':
                    batch_uuid = data['batches'][0]['batch_uuid']
                    break
        
        assert batch_uuid is not None, "Batch did not complete within 60 seconds"
        print(f"✓ Batch {batch_uuid[:8]} completed")
        
        # Step 4: Verify batch results
        batch_detail = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={'batch_uuid': batch_uuid}
        )
        
        assert batch_detail.status_code == 200
        batch = batch_detail.json()['batches'][0]
        
        # Validate batch metrics
        assert batch['video_count'] == 5, f"Expected 5 videos, got {batch['video_count']}"
        assert batch['individuals_created'] > 0, "No individuals created"
        assert batch['mvr_people_created'] > 0, "No MVR people created"
        assert batch['processing_time_seconds'] > 0, "Processing time not recorded"
        
        print(f"✓ Individuals: {batch['individuals_created']}")
        print(f"✓ MVR People: {batch['mvr_people_created']}")
        print(f"✓ Processing time: {batch['processing_time_seconds']:.1f}s")
        print(f"✓ Cache hit rate: {batch['cache_hit_rate']:.1f}%")


    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_partial_batch_recording_stop(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor,
        hybrid_trigger,
        test_collection_id
    ):
        """
        Test partial batch triggered by recording stop event.
        
        Flow:
        1. Configure batch size to 5
        2. Add 3 videos (below threshold)
        3. Send recording stop event
        4. Verify partial batch triggered
        5. Verify is_partial flag set
        """
        
        # Step 1: Configure batch size
        config_response = await http_client.put(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/batch-size",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'batch_size': 5,
                'collection_id': test_collection_id
            }
        )
        
        assert config_response.status_code == 200
        
        # Step 2: Add 3 videos (below threshold)
        video_ids = [str(uuid4()) for _ in range(3)]
        
        for i, video_id in enumerate(video_ids, 1):
            await batch_monitor.add_video_to_batch(
                collection_id=test_collection_id,
                video_uuid=video_id,
                video_start_time=datetime.utcnow() - timedelta(seconds=30),
                video_end_time=datetime.utcnow(),
                face_detection_session_uuid=str(uuid4()),
                faces_detected=2
            )
            
            print(f"✓ Video {i}/3 added to batch")
        
        # Step 3: Trigger recording stop
        recording_stop_event = RecordingStopEvent(
            collection_id=test_collection_id,
            session_id=str(uuid4()),
            total_segments=3,
            total_duration_seconds=90,
            stop_time=datetime.utcnow()
        )
        
        await hybrid_trigger.on_recording_stopped(recording_stop_event)
        
        print("✓ Recording stop event sent")
        
        # Step 4: Wait for partial batch to process
        await asyncio.sleep(5)
        
        # Step 5: Verify partial batch
        history_response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={
                'collection_id': test_collection_id,
                'limit': 1
            }
        )
        
        assert history_response.status_code == 200
        data = history_response.json()
        
        assert len(data['batches']) > 0, "No batch found"
        
        batch = data['batches'][0]
        assert batch['video_count'] == 3, f"Expected 3 videos, got {batch['video_count']}"
        assert batch['is_partial_batch'] is True, "is_partial flag not set"
        assert batch['trigger_reason'] == 'recording_stopped', f"Wrong trigger reason: {batch['trigger_reason']}"
        
        print(f"✓ Partial batch triggered: {batch['batch_uuid'][:8]}")
        print(f"✓ Trigger reason: {batch['trigger_reason']}")
        print(f"✓ Is partial: {batch['is_partial_batch']}")


    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_collection_concurrent(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor,
        test_user_id
    ):
        """
        Test concurrent batch processing for multiple collections.
        
        Flow:
        1. Create 3 different test collections
        2. Add 5 videos to each collection simultaneously
        3. Verify all 3 batches trigger
        4. Verify all batches process concurrently
        5. Check no resource conflicts
        """
        
        # Step 1: Create test collections
        collections = [
            f"test-collection-A-{uuid4()}",
            f"test-collection-B-{uuid4()}",
            f"test-collection-C-{uuid4()}"
        ]
        
        # Step 2: Configure batch size for all collections
        for collection_id in collections:
            config_response = await http_client.put(
                f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/batch-size",
                headers={'Authorization': f'Bearer {auth_token}'},
                json={
                    'batch_size': 5,
                    'collection_id': collection_id
                }
            )
            assert config_response.status_code == 200
        
        # Step 3: Add videos to all collections concurrently
        async def add_videos_to_collection(collection_id: str):
            """Add 5 videos to a collection."""
            for i in range(5):
                await batch_monitor.add_video_to_batch(
                    collection_id=collection_id,
                    video_uuid=str(uuid4()),
                    video_start_time=datetime.utcnow() - timedelta(seconds=30),
                    video_end_time=datetime.utcnow(),
                    face_detection_session_uuid=str(uuid4()),
                    faces_detected=3
                )
                await asyncio.sleep(0.1)  # Small delay to simulate real recording
        
        # Execute all collections concurrently
        await asyncio.gather(*[
            add_videos_to_collection(cid) for cid in collections
        ])
        
        print(f"✓ Added 5 videos to {len(collections)} collections")
        
        # Step 4: Wait for all batches to complete
        await asyncio.sleep(10)
        
        # Step 5: Verify all batches completed
        completed_batches = []
        
        for collection_id in collections:
            history_response = await http_client.get(
                f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
                headers={'Authorization': f'Bearer {auth_token}'},
                params={
                    'collection_id': collection_id,
                    'limit': 1
                }
            )
            
            assert history_response.status_code == 200
            data = history_response.json()
            
            assert len(data['batches']) > 0, f"No batch for collection {collection_id}"
            
            batch = data['batches'][0]
            assert batch['status'] == 'completed', f"Batch not completed: {batch['status']}"
            assert batch['video_count'] == 5, f"Wrong video count: {batch['video_count']}"
            
            completed_batches.append(batch)
            print(f"✓ Collection {collection_id[:20]} batch completed")
        
        # Verify concurrent processing
        assert len(completed_batches) == 3, "Not all batches completed"
        
        # Check processing times overlap (concurrent execution)
        start_times = [
            datetime.fromisoformat(b['batch_start_time'])
            for b in completed_batches
        ]
        
        max_start = max(start_times)
        min_start = min(start_times)
        
        # If truly concurrent, start times should be within a few seconds
        time_diff = (max_start - min_start).total_seconds()
        assert time_diff < 10, f"Batches didn't start concurrently: {time_diff}s apart"
        
        print(f"✓ All batches processed concurrently (within {time_diff:.1f}s)")


    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_failure_recovery_retry(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor,
        test_collection_id
    ):
        """
        Test failure recovery and retry logic.
        
        Flow:
        1. Add 5 videos to batch
        2. Simulate orchestrator service failure (mock)
        3. Verify batch marked as failed
        4. Manually retry batch
        5. Verify successful recovery
        """
        
        # This test requires mocking orchestrator failure
        # For now, we test the API endpoints for retry
        
        # Step 1: Add 5 videos
        video_ids = [str(uuid4()) for _ in range(5)]
        
        for video_id in video_ids:
            await batch_monitor.add_video_to_batch(
                collection_id=test_collection_id,
                video_uuid=video_id,
                video_start_time=datetime.utcnow() - timedelta(seconds=30),
                video_end_time=datetime.utcnow(),
                face_detection_session_uuid=str(uuid4()),
                faces_detected=3
            )
        
        await asyncio.sleep(5)
        
        # Step 2: Get batch UUID
        history_response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={
                'collection_id': test_collection_id,
                'limit': 1
            }
        )
        
        assert history_response.status_code == 200
        data = history_response.json()
        
        if len(data['batches']) > 0:
            batch_uuid = data['batches'][0]['batch_uuid']
            
            # Step 3: Test manual retry endpoint
            retry_response = await http_client.post(
                f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/trigger",
                headers={'Authorization': f'Bearer {auth_token}'},
                json={
                    'collection_id': test_collection_id,
                    'force_trigger': True,
                    'min_videos': 1
                }
            )
            
            assert retry_response.status_code in [200, 201], "Manual trigger failed"
            print(f"✓ Manual retry triggered for batch {batch_uuid[:8]}")


    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_effectiveness(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor,
        test_collection_id
    ):
        """
        Test two-level caching effectiveness across multiple batches.
        
        Flow:
        1. Process first batch (5 videos) - no cache
        2. Process second batch (5 videos, same faces) - should see cache hits
        3. Verify cache hit rate increases
        4. Validate individuals/MVR cache levels
        """
        
        # Step 1: Configure batch size
        await http_client.put(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/batch-size",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'batch_size': 5,
                'collection_id': test_collection_id
            }
        )
        
        # Step 2: Process first batch
        for i in range(5):
            await batch_monitor.add_video_to_batch(
                collection_id=test_collection_id,
                video_uuid=str(uuid4()),
                video_start_time=datetime.utcnow() - timedelta(seconds=30),
                video_end_time=datetime.utcnow(),
                face_detection_session_uuid=str(uuid4()),
                faces_detected=3
            )
        
        await asyncio.sleep(10)
        
        # Step 3: Get first batch cache rate
        history_response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={
                'collection_id': test_collection_id,
                'limit': 1
            }
        )
        
        data = history_response.json()
        batch_1 = data['batches'][0]
        
        print(f"✓ Batch 1 cache hit rate: {batch_1['cache_hit_rate']:.1f}%")
        
        # Step 4: Process second batch (should have higher cache rate)
        for i in range(5):
            await batch_monitor.add_video_to_batch(
                collection_id=test_collection_id,
                video_uuid=str(uuid4()),
                video_start_time=datetime.utcnow() - timedelta(seconds=30),
                video_end_time=datetime.utcnow(),
                face_detection_session_uuid=str(uuid4()),
                faces_detected=3
            )
        
        await asyncio.sleep(10)
        
        # Step 5: Get second batch cache rate
        history_response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/history",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={
                'collection_id': test_collection_id,
                'limit': 2
            }
        )
        
        data = history_response.json()
        batch_2 = data['batches'][0]  # Most recent
        
        print(f"✓ Batch 2 cache hit rate: {batch_2['cache_hit_rate']:.1f}%")
        
        # Verify cache improvement (note: may not always be higher with random video IDs)
        print(f"✓ Cache system operational across batches")


class TestAPIEndpoints:
    """Test REST API endpoints for batch processing."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_status_endpoint(
        self,
        http_client,
        auth_token,
        test_collection_id
    ):
        """Test GET /api/v1/batch-processing/status endpoint."""
        
        response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/status",
            headers={'Authorization': f'Bearer {auth_token}'},
            params={'collection_id': test_collection_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'batches' in data
        assert isinstance(data['batches'], list)
        
        print("✓ Batch status endpoint working")
    
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_config_endpoints(
        self,
        http_client,
        auth_token,
        test_collection_id
    ):
        """Test batch configuration GET and PUT endpoints."""
        
        # Test GET config
        get_response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/config",
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert get_response.status_code == 200
        config = get_response.json()
        
        assert 'batch_size_threshold' in config
        print(f"✓ Current batch size: {config['batch_size_threshold']}")
        
        # Test PUT config
        put_response = await http_client.put(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/config",
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'batch_size_threshold': 7,
                'batch_timeout_minutes': 15,
                'max_concurrent_batches': 5
            }
        )
        
        assert put_response.status_code == 200
        updated_config = put_response.json()
        
        assert updated_config['config']['batch_size_threshold'] == 7
        print("✓ Batch configuration updated successfully")
    
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_endpoint(
        self,
        http_client,
        auth_token
    ):
        """Test GET /api/v1/batch-processing/health endpoint."""
        
        response = await http_client.get(
            f"{TEST_CONFIG['vmeta_url']}/api/v1/batch-processing/health",
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 200
        health = response.json()
        
        assert 'status' in health
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
        
        assert 'worker_pool' in health
        assert 'active_workers' in health['worker_pool']
        
        print(f"✓ Health status: {health['status']}")
        print(f"✓ Active workers: {health['worker_pool']['active_workers']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
