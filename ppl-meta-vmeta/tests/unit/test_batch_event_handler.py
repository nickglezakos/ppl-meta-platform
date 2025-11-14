"""
Unit Tests for Batch Event Handler
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Tests for event parsing, routing, and error handling.

Created: November 13, 2025
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from uuid import uuid4
import json

from src.models.batch_processing import VideoCompletionEvent, RecordingStopEvent
from src.services.batch_event_handler import BatchEventHandler


@pytest.fixture
def mock_batch_monitor():
    """Mock batch monitor."""
    monitor = Mock()
    monitor.handle_video_completion = AsyncMock()
    monitor.handle_recording_stop = AsyncMock()
    return monitor


@pytest.fixture
def event_handler(mock_batch_monitor):
    """Create event handler with mocked monitor."""
    return BatchEventHandler(batch_monitor=mock_batch_monitor)


class TestBatchEventHandler:
    """Test suite for BatchEventHandler."""
    
    def test_initialization(self, mock_batch_monitor):
        """Test event handler initialization."""
        handler = BatchEventHandler(mock_batch_monitor)
        
        assert handler.batch_monitor == mock_batch_monitor
        assert handler.statistics['events_received'] == 0
        assert handler.statistics['events_processed'] == 0
        assert handler.statistics['parsing_errors'] == 0
    
    @pytest.mark.asyncio
    async def test_handle_video_completion_direct_format(
        self, event_handler, mock_batch_monitor
    ):
        """Test video completion event - direct format."""
        event_data = {
            'video_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4()),
            'recording_id': str(uuid4()),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        await event_handler.handle_video_completion_event(event_data)
        
        mock_batch_monitor.handle_video_completion.assert_called_once()
        call_args = mock_batch_monitor.handle_video_completion.call_args[0][0]
        assert isinstance(call_args, VideoCompletionEvent)
        assert call_args.video_id == event_data['video_id']
        assert event_handler.statistics['events_processed'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_video_completion_nested_payload(
        self, event_handler, mock_batch_monitor
    ):
        """Test video completion event - nested payload format."""
        video_id = str(uuid4())
        collection_id = 'test-collection'
        
        event_data = {
            'type': 'video.completed',
            'timestamp': datetime.utcnow().isoformat(),
            'payload': {
                'video_id': video_id,
                'collection_id': collection_id,
                'session_id': str(uuid4()),
                'recording_id': str(uuid4())
            }
        }
        
        await event_handler.handle_video_completion_event(event_data)
        
        mock_batch_monitor.handle_video_completion.assert_called_once()
        call_args = mock_batch_monitor.handle_video_completion.call_args[0][0]
        assert call_args.video_id == video_id
        assert call_args.collection_id == collection_id
    
    @pytest.mark.asyncio
    async def test_handle_video_completion_data_field(
        self, event_handler, mock_batch_monitor
    ):
        """Test video completion event - data field format."""
        video_id = str(uuid4())
        
        event_data = {
            'event_type': 'VideoCompleted',
            'data': {
                'video_id': video_id,
                'collection_id': 'test-collection',
                'session_id': str(uuid4())
            }
        }
        
        await event_handler.handle_video_completion_event(event_data)
        
        mock_batch_monitor.handle_video_completion.assert_called_once()
        call_args = mock_batch_monitor.handle_video_completion.call_args[0][0]
        assert call_args.video_id == video_id
    
    @pytest.mark.asyncio
    async def test_handle_video_completion_missing_video_id(
        self, event_handler, mock_batch_monitor
    ):
        """Test video completion event with missing video_id."""
        event_data = {
            'collection_id': 'test-collection',
            'session_id': str(uuid4())
        }
        
        await event_handler.handle_video_completion_event(event_data)
        
        mock_batch_monitor.handle_video_completion.assert_not_called()
        assert event_handler.statistics['parsing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_video_completion_missing_collection_id(
        self, event_handler, mock_batch_monitor
    ):
        """Test video completion event with missing collection_id."""
        event_data = {
            'video_id': str(uuid4()),
            'session_id': str(uuid4())
        }
        
        await event_handler.handle_video_completion_event(event_data)
        
        mock_batch_monitor.handle_video_completion.assert_not_called()
        assert event_handler.statistics['parsing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_recording_stop_direct_format(
        self, event_handler, mock_batch_monitor
    ):
        """Test recording stop event - direct format."""
        event_data = {
            'recording_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4()),
            'stopped_at': datetime.utcnow().isoformat(),
            'reason': 'user_stopped'
        }
        
        await event_handler.handle_recording_stop_event(event_data)
        
        mock_batch_monitor.handle_recording_stop.assert_called_once()
        call_args = mock_batch_monitor.handle_recording_stop.call_args[0][0]
        assert isinstance(call_args, RecordingStopEvent)
        assert call_args.recording_id == event_data['recording_id']
        assert event_handler.statistics['events_processed'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_recording_stop_nested_payload(
        self, event_handler, mock_batch_monitor
    ):
        """Test recording stop event - nested payload format."""
        recording_id = str(uuid4())
        collection_id = 'test-collection'
        
        event_data = {
            'type': 'recording.stopped',
            'timestamp': datetime.utcnow().isoformat(),
            'payload': {
                'recording_id': recording_id,
                'collection_id': collection_id,
                'session_id': str(uuid4()),
                'reason': 'timeout'
            }
        }
        
        await event_handler.handle_recording_stop_event(event_data)
        
        mock_batch_monitor.handle_recording_stop.assert_called_once()
        call_args = mock_batch_monitor.handle_recording_stop.call_args[0][0]
        assert call_args.recording_id == recording_id
        assert call_args.collection_id == collection_id
    
    @pytest.mark.asyncio
    async def test_handle_recording_stop_missing_recording_id(
        self, event_handler, mock_batch_monitor
    ):
        """Test recording stop event with missing recording_id."""
        event_data = {
            'collection_id': 'test-collection',
            'session_id': str(uuid4())
        }
        
        await event_handler.handle_recording_stop_event(event_data)
        
        mock_batch_monitor.handle_recording_stop.assert_not_called()
        assert event_handler.statistics['parsing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_event_handler_statistics_tracking(
        self, event_handler, mock_batch_monitor
    ):
        """Test statistics tracking across multiple events."""
        # Process several events
        valid_event = {
            'video_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4())
        }
        
        invalid_event = {
            'collection_id': 'test-collection'  # Missing video_id
        }
        
        await event_handler.handle_video_completion_event(valid_event)
        await event_handler.handle_video_completion_event(valid_event)
        await event_handler.handle_video_completion_event(invalid_event)
        
        assert event_handler.statistics['events_received'] == 3
        assert event_handler.statistics['events_processed'] == 2
        assert event_handler.statistics['parsing_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_monitor_error_handling(
        self, event_handler, mock_batch_monitor
    ):
        """Test error handling when batch monitor fails."""
        mock_batch_monitor.handle_video_completion.side_effect = Exception(
            "Database error"
        )
        
        event_data = {
            'video_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4())
        }
        
        # Should not raise exception
        await event_handler.handle_video_completion_event(event_data)
        
        # Event was parsed but processing failed
        assert event_handler.statistics['events_received'] == 1
        assert event_handler.statistics['processing_errors'] == 1
    
    def test_parse_video_completion_event(self, event_handler):
        """Test parsing video completion event."""
        event_data = {
            'video_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4()),
            'recording_id': str(uuid4())
        }
        
        event = event_handler._parse_video_completion(event_data)
        
        assert event is not None
        assert event.video_id == event_data['video_id']
        assert event.collection_id == event_data['collection_id']
    
    def test_parse_recording_stop_event(self, event_handler):
        """Test parsing recording stop event."""
        event_data = {
            'recording_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4()),
            'reason': 'user_stopped'
        }
        
        event = event_handler._parse_recording_stop(event_data)
        
        assert event is not None
        assert event.recording_id == event_data['recording_id']
        assert event.reason == event_data['reason']
    
    def test_parse_with_string_event(self, event_handler):
        """Test parsing when event is JSON string."""
        event_dict = {
            'video_id': str(uuid4()),
            'collection_id': 'test-collection',
            'session_id': str(uuid4())
        }
        event_string = json.dumps(event_dict)
        
        event = event_handler._parse_video_completion(event_string)
        
        assert event is not None
        assert event.video_id == event_dict['video_id']
    
    def test_get_statistics(self, event_handler):
        """Test getting statistics."""
        stats = event_handler.get_statistics()
        
        assert 'events_received' in stats
        assert 'events_processed' in stats
        assert 'parsing_errors' in stats
        assert 'processing_errors' in stats
        assert stats['events_received'] == 0
    
    def test_reset_statistics(self, event_handler):
        """Test resetting statistics."""
        # Increment counters
        event_handler.statistics['events_received'] = 10
        event_handler.statistics['parsing_errors'] = 2
        
        event_handler.reset_statistics()
        
        assert event_handler.statistics['events_received'] == 0
        assert event_handler.statistics['parsing_errors'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
