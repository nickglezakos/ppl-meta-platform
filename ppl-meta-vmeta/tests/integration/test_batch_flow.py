"""
Integration Tests for Batch Processing Flow
PPL Meta Platform - Continuous Individuals and MVR Pipeline

End-to-end tests for complete batch accumulation workflow.

Created: November 13, 2025
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
import asyncpg

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
from src.services.batch_event_handler import BatchEventHandler


@pytest.fixture
async def db_pool():
    """Create database connection pool."""
    pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        database='ppl_meta_vmeta_test',
        user='postgres',
        password='postgres'
    )
    yield pool
    await pool.close()


@pytest.fixture
async def repository(db_pool):
    """Create batch repository."""
    return BatchProcessingRepository(db_pool)


@pytest.fixture
async def config_service(repository):
    """Create config service."""
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
async def event_handler(batch_monitor):
    """Create event handler."""
    return BatchEventHandler(batch_monitor=batch_monitor)


@pytest.fixture
def collection_id():
    """Generate unique collection ID for test."""
    return f"test-collection-{uuid4()}"


@pytest.fixture
def session_id():
    """Generate unique session ID for test."""
    return str(uuid4())


class TestBatchProcessingFlow:
    """Integration tests for batch processing workflow."""
    
    @pytest.mark.asyncio
    async def test_full_batch_accumulation(
        self, event_handler, batch_monitor, repository, collection_id, session_id
    ):
        """Test full batch accumulation (5 videos → trigger)."""
        video_ids = [str(uuid4()) for _ in range(5)]
        
        # Send 5 video completion events
        for i, video_id in enumerate(video_ids):
            event = VideoCompletionEvent(
                video_id=video_id,
                collection_id=collection_id,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            
            await event_handler.handle_video_completion_event(event.model_dump())
            
            # Check batch status after each video
            active_batch = await repository.get_active_batch(collection_id)
            
            if i < 4:
                # Should still be accumulating
                assert active_batch is not None
                assert active_batch.status == BatchStatus.ACCUMULATING
                assert active_batch.video_count == i + 1
            else:
                # Should have triggered after 5th video
                # Active batch should be cleared
                assert active_batch is None
                
                # Check completed batch in history
                history = await repository.get_batch_history(
                    collection_id=collection_id,
                    limit=1
                )
                assert len(history) == 1
                assert history[0].video_count == 5
                assert history[0].trigger_reason == TriggerReason.THRESHOLD_REACHED
    
    @pytest.mark.asyncio
    async def test_partial_batch_recording_stop(
        self, event_handler, batch_monitor, repository, collection_id, session_id
    ):
        """Test partial batch trigger via recording stop event."""
        recording_id = str(uuid4())
        video_ids = [str(uuid4()) for _ in range(3)]
        
        # Send 3 video completion events
        for video_id in video_ids:
            event = VideoCompletionEvent(
                video_id=video_id,
                collection_id=collection_id,
                session_id=session_id,
                recording_id=recording_id,
                completed_at=datetime.utcnow()
            )
            await event_handler.handle_video_completion_event(event.model_dump())
        
        # Verify batch is accumulating
        active_batch = await repository.get_active_batch(collection_id)
        assert active_batch is not None
        assert active_batch.video_count == 3
        
        # Send recording stop event
        stop_event = RecordingStopEvent(
            recording_id=recording_id,
            collection_id=collection_id,
            session_id=session_id,
            stopped_at=datetime.utcnow(),
            reason='user_stopped'
        )
        await event_handler.handle_recording_stop_event(stop_event.model_dump())
        
        # Wait for event processing
        await asyncio.sleep(2.5)  # Slightly more than trigger delay
        
        # Batch should be triggered
        active_batch = await repository.get_active_batch(collection_id)
        assert active_batch is None
        
        # Check history
        history = await repository.get_batch_history(
            collection_id=collection_id,
            limit=1
        )
        assert len(history) == 1
        assert history[0].video_count == 3
        assert history[0].trigger_reason == TriggerReason.RECORDING_STOPPED
    
    @pytest.mark.asyncio
    async def test_partial_batch_timeout(
        self, batch_monitor, repository, collection_id, session_id, config_service
    ):
        """Test partial batch trigger via timeout."""
        video_ids = [str(uuid4()) for _ in range(2)]
        
        # Send 2 video completion events
        for video_id in video_ids:
            event = VideoCompletionEvent(
                video_id=video_id,
                collection_id=collection_id,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            await batch_monitor.handle_video_completion(event)
        
        # Verify batch is accumulating
        active_batch = await repository.get_active_batch(collection_id)
        assert active_batch is not None
        assert active_batch.video_count == 2
        
        # Manually trigger timeout
        await batch_monitor.handle_batch_timeout(active_batch.id)
        
        # Batch should be triggered
        active_batch = await repository.get_active_batch(collection_id)
        assert active_batch is None
        
        # Check history
        history = await repository.get_batch_history(
            collection_id=collection_id,
            limit=1
        )
        assert len(history) == 1
        assert history[0].video_count == 2
        assert history[0].trigger_reason == TriggerReason.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_concurrent_video_completions(
        self, batch_monitor, repository, collection_id, session_id
    ):
        """Test handling concurrent video completion events."""
        video_ids = [str(uuid4()) for _ in range(10)]
        
        # Create events
        events = [
            VideoCompletionEvent(
                video_id=vid,
                collection_id=collection_id,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            for vid in video_ids
        ]
        
        # Process all events concurrently
        tasks = [
            batch_monitor.handle_video_completion(event)
            for event in events
        ]
        await asyncio.gather(*tasks)
        
        # Should have triggered 2 batches (5 + 5)
        history = await repository.get_batch_history(
            collection_id=collection_id,
            limit=10
        )
        assert len(history) == 2
        assert all(h.video_count == 5 for h in history)
    
    @pytest.mark.asyncio
    async def test_multiple_collections(
        self, batch_monitor, repository, session_id
    ):
        """Test handling multiple collections independently."""
        collection1 = f"test-collection-{uuid4()}"
        collection2 = f"test-collection-{uuid4()}"
        
        # Send 3 videos to collection1
        for _ in range(3):
            event = VideoCompletionEvent(
                video_id=str(uuid4()),
                collection_id=collection1,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            await batch_monitor.handle_video_completion(event)
        
        # Send 4 videos to collection2
        for _ in range(4):
            event = VideoCompletionEvent(
                video_id=str(uuid4()),
                collection_id=collection2,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            await batch_monitor.handle_video_completion(event)
        
        # Check both batches are accumulating independently
        batch1 = await repository.get_active_batch(collection1)
        batch2 = await repository.get_active_batch(collection2)
        
        assert batch1 is not None
        assert batch1.video_count == 3
        assert batch2 is not None
        assert batch2.video_count == 4
    
    @pytest.mark.asyncio
    async def test_batch_statistics(
        self, event_handler, repository, collection_id, session_id
    ):
        """Test batch statistics tracking."""
        # Complete one full batch
        for _ in range(5):
            event = VideoCompletionEvent(
                video_id=str(uuid4()),
                collection_id=collection_id,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            await event_handler.handle_video_completion_event(event.model_dump())
        
        # Get statistics
        stats = await repository.get_collection_stats(collection_id)
        
        assert stats is not None
        assert stats['total_batches'] >= 1
        assert stats['total_videos'] >= 5
        assert stats['avg_videos_per_batch'] > 0
    
    @pytest.mark.asyncio
    async def test_duplicate_video_handling(
        self, batch_monitor, repository, collection_id, session_id
    ):
        """Test handling duplicate video completion events."""
        video_id = str(uuid4())
        
        event = VideoCompletionEvent(
            video_id=video_id,
            collection_id=collection_id,
            session_id=session_id,
            recording_id=str(uuid4()),
            completed_at=datetime.utcnow()
        )
        
        # Send same event twice
        await batch_monitor.handle_video_completion(event)
        await batch_monitor.handle_video_completion(event)
        
        # Should only be counted once
        active_batch = await repository.get_active_batch(collection_id)
        assert active_batch is not None
        assert active_batch.video_count == 1
    
    @pytest.mark.asyncio
    async def test_batch_state_transitions(
        self, batch_monitor, repository, collection_id, session_id
    ):
        """Test batch state transitions."""
        # Start with no active batch
        batch = await repository.get_active_batch(collection_id)
        assert batch is None
        
        # Add first video -> creates batch in ACCUMULATING
        event = VideoCompletionEvent(
            video_id=str(uuid4()),
            collection_id=collection_id,
            session_id=session_id,
            recording_id=str(uuid4()),
            completed_at=datetime.utcnow()
        )
        await batch_monitor.handle_video_completion(event)
        
        batch = await repository.get_active_batch(collection_id)
        assert batch is not None
        assert batch.status == BatchStatus.ACCUMULATING
        
        # Add 4 more videos -> triggers batch
        for _ in range(4):
            event = VideoCompletionEvent(
                video_id=str(uuid4()),
                collection_id=collection_id,
                session_id=session_id,
                recording_id=str(uuid4()),
                completed_at=datetime.utcnow()
            )
            await batch_monitor.handle_video_completion(event)
        
        # Batch should be cleared (moved to history)
        batch = await repository.get_active_batch(collection_id)
        assert batch is None


@pytest.mark.asyncio
async def test_cleanup(db_pool):
    """Cleanup test data after all tests."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM batch_video_assignments WHERE batch_id IN "
            "(SELECT id FROM batch_processing_state WHERE collection_id LIKE 'test-collection-%')"
        )
        await conn.execute(
            "DELETE FROM batch_processing_history WHERE collection_id LIKE 'test-collection-%'"
        )
        await conn.execute(
            "DELETE FROM batch_processing_state WHERE collection_id LIKE 'test-collection-%'"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
