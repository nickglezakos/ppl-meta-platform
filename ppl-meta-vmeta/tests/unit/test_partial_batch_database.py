"""
Test Partial Batch Database Support
Tests the new partial batch fields in batch_processing_state and repository methods
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.database.batch_repository import BatchProcessingRepository
from src.models.batch_processing import (
    BatchProcessingState,
    BatchStatus,
    TriggerReason
)


@pytest_asyncio.fixture
async def repository(db_connection_pool):
    """Create repository instance."""
    return BatchProcessingRepository(db_connection_pool)


@pytest_asyncio.fixture
async def sample_batch():
    """Create sample batch for testing."""
    return BatchProcessingState(
        batch_uuid=uuid4(),
        collection_id="test-collection",
        batch_number=1,
        status=BatchStatus.ACCUMULATING,
        video_count=3,
        batch_size_threshold=5,
        is_partial_batch=False,
        trigger_reason=None,
        last_video_time=None,
        timeout_at=None
    )


class TestPartialBatchFields:
    """Test partial batch field operations."""
    
    @pytest.mark.asyncio
    async def test_create_batch_with_partial_fields(self, repository, sample_batch):
        """Test creating batch with partial batch fields."""
        # Set partial batch fields
        sample_batch.is_partial_batch = True
        sample_batch.trigger_reason = TriggerReason.RECORDING_STOPPED
        sample_batch.last_video_time = datetime.now(timezone.utc)
        sample_batch.timeout_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Create batch
        created_batch = await repository.create_batch(sample_batch)
        
        # Verify fields saved
        assert created_batch.is_partial_batch is True
        assert created_batch.trigger_reason == TriggerReason.RECORDING_STOPPED
        assert created_batch.last_video_time is not None
        assert created_batch.timeout_at is not None
    
    @pytest.mark.asyncio
    async def test_update_batch_timeout(self, repository, sample_batch):
        """Test updating batch timeout fields."""
        # Create batch
        created_batch = await repository.create_batch(sample_batch)
        
        # Update timeout
        timeout_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        last_video_time = datetime.now(timezone.utc)
        
        success = await repository.update_batch_timeout(
            batch_uuid=created_batch.batch_uuid,
            timeout_at=timeout_at,
            last_video_time=last_video_time
        )
        
        assert success is True
        
        # Verify update
        updated_batch = await repository.get_batch(created_batch.batch_uuid)
        assert updated_batch.timeout_at is not None
        assert updated_batch.last_video_time is not None
    
    @pytest.mark.asyncio
    async def test_mark_batch_as_partial(self, repository, sample_batch):
        """Test marking batch as partial."""
        # Create batch
        created_batch = await repository.create_batch(sample_batch)
        
        # Mark as partial
        success = await repository.mark_batch_as_partial(
            batch_uuid=created_batch.batch_uuid,
            trigger_reason=TriggerReason.TIMEOUT_REACHED
        )
        
        assert success is True
        
        # Verify
        updated_batch = await repository.get_batch(created_batch.batch_uuid)
        assert updated_batch.is_partial_batch is True
        assert updated_batch.trigger_reason == TriggerReason.TIMEOUT_REACHED
        assert updated_batch.triggered_at is not None


class TestPartialBatchQueries:
    """Test querying partial batches."""
    
    @pytest.mark.asyncio
    async def test_get_timeout_batches(self, repository):
        """Test getting batches that have reached timeout."""
        # Create batch with expired timeout
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.ACCUMULATING,
            video_count=3,
            batch_size_threshold=5,
            timeout_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        
        await repository.create_batch(batch)
        
        # Query timeout batches
        timeout_batches = await repository.get_timeout_batches()
        
        # Verify batch is in results
        batch_uuids = [b.batch_uuid for b in timeout_batches]
        assert batch.batch_uuid in batch_uuids
    
    @pytest.mark.asyncio
    async def test_get_partial_batches(self, repository):
        """Test getting partial batches."""
        # Create partial batch
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.COMPLETED,
            video_count=3,
            batch_size_threshold=5,
            is_partial_batch=True,
            trigger_reason=TriggerReason.RECORDING_STOPPED
        )
        
        await repository.create_batch(batch)
        
        # Query partial batches
        partial_batches = await repository.get_partial_batches(
            collection_id="test-collection"
        )
        
        # Verify batch is in results
        batch_uuids = [b.batch_uuid for b in partial_batches]
        assert batch.batch_uuid in batch_uuids
    
    @pytest.mark.asyncio
    async def test_get_incomplete_batches(self, repository):
        """Test getting incomplete batches."""
        # Create incomplete batch
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.INCOMPLETE,
            video_count=1,
            batch_size_threshold=5
        )
        
        await repository.create_batch(batch)
        
        # Query incomplete batches
        incomplete_batches = await repository.get_incomplete_batches(
            collection_id="test-collection"
        )
        
        # Verify batch is in results
        batch_uuids = [b.batch_uuid for b in incomplete_batches]
        assert batch.batch_uuid in batch_uuids


class TestPartialBatchScenarios:
    """Test real-world partial batch scenarios."""
    
    @pytest.mark.asyncio
    async def test_recording_stop_partial_batch(self, repository):
        """Test recording stop triggering partial batch."""
        # Create accumulating batch
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.ACCUMULATING,
            video_count=3,
            batch_size_threshold=5,
            last_video_time=datetime.now(timezone.utc)
        )
        
        created_batch = await repository.create_batch(batch)
        
        # Simulate recording stop
        await repository.mark_batch_as_partial(
            batch_uuid=created_batch.batch_uuid,
            trigger_reason=TriggerReason.RECORDING_STOPPED
        )
        
        # Update status to processing
        await repository.update_batch(
            batch_uuid=created_batch.batch_uuid,
            status=BatchStatus.PROCESSING
        )
        
        # Verify
        updated_batch = await repository.get_batch(created_batch.batch_uuid)
        assert updated_batch.is_partial_batch is True
        assert updated_batch.trigger_reason == TriggerReason.RECORDING_STOPPED
        assert updated_batch.status == BatchStatus.PROCESSING
    
    @pytest.mark.asyncio
    async def test_timeout_fallback_partial_batch(self, repository):
        """Test timeout triggering partial batch."""
        # Create batch with timeout
        timeout_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.ACCUMULATING,
            video_count=3,
            batch_size_threshold=5,
            timeout_at=timeout_at
        )
        
        created_batch = await repository.create_batch(batch)
        
        # Simulate timeout expiry
        await repository.mark_batch_as_partial(
            batch_uuid=created_batch.batch_uuid,
            trigger_reason=TriggerReason.TIMEOUT_REACHED
        )
        
        # Verify
        updated_batch = await repository.get_batch(created_batch.batch_uuid)
        assert updated_batch.is_partial_batch is True
        assert updated_batch.trigger_reason == TriggerReason.TIMEOUT_REACHED
    
    @pytest.mark.asyncio
    async def test_normal_batch_vs_partial_batch(self, repository):
        """Test distinction between normal and partial batches."""
        # Create normal batch (reaches threshold)
        normal_batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=1,
            status=BatchStatus.COMPLETED,
            video_count=5,
            batch_size_threshold=5,
            is_partial_batch=False,
            trigger_reason=TriggerReason.BATCH_SIZE_REACHED
        )
        
        # Create partial batch
        partial_batch = BatchProcessingState(
            batch_uuid=uuid4(),
            collection_id="test-collection",
            batch_number=2,
            status=BatchStatus.COMPLETED,
            video_count=3,
            batch_size_threshold=5,
            is_partial_batch=True,
            trigger_reason=TriggerReason.RECORDING_STOPPED
        )
        
        await repository.create_batch(normal_batch)
        await repository.create_batch(partial_batch)
        
        # Query partial batches only
        partial_batches = await repository.get_partial_batches(
            collection_id="test-collection"
        )
        
        partial_uuids = [b.batch_uuid for b in partial_batches]
        
        # Verify only partial batch is returned
        assert partial_batch.batch_uuid in partial_uuids
        assert normal_batch.batch_uuid not in partial_uuids
