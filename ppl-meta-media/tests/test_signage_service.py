"""
Unit tests for Signage Simple Player Service

Tests for video list management, synchronization, and playback control.
"""

import os
import sys
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Base
from src.models.media import Media, MediaCollection, MediaCollectionItem, MediaDetails, MediaType
from src.models.signage import (
    LoopMode,
    SignageDevice,
    SyncStatus,
    VideoList,
    VideoListItem,
    VideoListSyncHistory,
)
from src.schemas.signage import (
    PlaybackCommand,
    PlaybackControlRequest,
    SyncMode,
    VideoListCreate,
    VideoListUpdate,
)
from src.services.signage_service import (
    SignagePlaybackService,
    SignageService,
    SignageSyncService,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid.uuid4()


@pytest.fixture
def test_collection(db_session, user_id):
    """Create a test media collection."""
    collection = MediaCollection(
        name="Test Collection",
        description="Test collection for signage",
        created_by=user_id,
        is_public=False,
    )
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)
    return collection


@pytest.fixture
def test_videos(db_session, test_collection, user_id):
    """Create test video media items and add them to the collection."""
    videos = []
    for i in range(5):
        media = Media(
            filename=f"video_{i}.mp4",
            original_filename=f"video_{i}.mp4",
            media_type=MediaType.VIDEO,
            mime_type="video/mp4",
            file_extension="mp4",
            file_size=1024000,
            file_path=f"/path/to/video_{i}.mp4",
            checksum=f"checksum_{i}",
            uploaded_by=user_id,
            title=f"Test Video {i}",
        )
        db_session.add(media)
        db_session.flush()

        # Add media details
        details = MediaDetails(
            media_id=media.id,
            duration=60.0 + i * 10,  # 60, 70, 80, 90, 100 seconds
            width=1920,
            height=1080,
            frame_rate=30.0,
            codec="h264",
        )
        db_session.add(details)

        # Add video to collection
        collection_item = MediaCollectionItem(
            collection_id=test_collection.id,
            media_id=media.id,
            sort_order=i,
            added_by=user_id,
        )
        db_session.add(collection_item)

        videos.append(media)

    db_session.commit()
    return videos


@pytest.fixture
def test_device(db_session):
    """Create a test signage device."""
    device_id = uuid.uuid4()
    device = SignageDevice(
        device_id=device_id,
        device_name="Test Signage Device",
        ip_address="192.168.1.100",
        port=8009,
        is_active=True,
        is_online=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


# ============================================================================
# SignageService Tests
# ============================================================================


class TestSignageService:
    """Tests for SignageService."""

    def test_create_video_list(self, db_session, user_id, test_collection, test_videos):
        """Test creating a video list from collections."""
        service = SignageService(db_session)

        data = VideoListCreate(
            name="Test Playlist",
            description="Test playlist description",
            collection_ids=[test_collection.id],
            loop_mode=LoopMode.CONTINUOUS,
            transition_duration=1000,
        )

        video_list = service.create_video_list(user_id, data)

        assert video_list is not None
        assert video_list.name == "Test Playlist"
        assert video_list.user_id == user_id
        assert video_list.loop_mode == LoopMode.CONTINUOUS.value
        assert video_list.video_count > 0

    def test_create_video_list_with_manual_order(
        self, db_session, user_id, test_collection, test_videos
    ):
        """Test creating a video list with manual video ordering."""
        service = SignageService(db_session)

        video_order = [
            {
                "collection_id": test_collection.id,
                "video_id": test_videos[2].id,
                "sequence": 1,
            },
            {
                "collection_id": test_collection.id,
                "video_id": test_videos[0].id,
                "sequence": 2,
            },
        ]

        data = VideoListCreate(
            name="Ordered Playlist",
            collection_ids=[test_collection.id],
            video_order=video_order,
        )

        video_list = service.create_video_list(user_id, data)

        assert video_list.video_count == 2
        assert video_list.video_items[0].video_id == test_videos[2].id
        assert video_list.video_items[1].video_id == test_videos[0].id

    def test_create_video_list_invalid_collection(self, db_session, user_id):
        """Test creating a video list with invalid collection ID."""
        service = SignageService(db_session)

        data = VideoListCreate(
            name="Invalid Playlist",
            collection_ids=[999999],  # Non-existent collection
        )

        with pytest.raises(ValueError, match="not found or unauthorized"):
            service.create_video_list(user_id, data)

    def test_get_video_list(self, db_session, user_id, test_collection, test_videos):
        """Test retrieving a video list."""
        service = SignageService(db_session)

        # Create a video list
        data = VideoListCreate(
            name="Test Playlist", collection_ids=[test_collection.id]
        )
        created_list = service.create_video_list(user_id, data)

        # Retrieve it
        retrieved_list = service.get_video_list(created_list.id, user_id)

        assert retrieved_list is not None
        assert retrieved_list.id == created_list.id
        assert retrieved_list.name == "Test Playlist"

    def test_get_video_list_with_items(
        self, db_session, user_id, test_collection, test_videos
    ):
        """Test retrieving a video list with items loaded."""
        service = SignageService(db_session)

        data = VideoListCreate(
            name="Test Playlist", collection_ids=[test_collection.id]
        )
        created_list = service.create_video_list(user_id, data)

        # Retrieve with items
        retrieved_list = service.get_video_list(
            created_list.id, user_id, include_items=True
        )

        assert len(retrieved_list.video_items) > 0
        assert all(isinstance(item, VideoListItem) for item in retrieved_list.video_items)

    def test_list_video_lists(self, db_session, user_id, test_collection, test_videos):
        """Test listing video lists with pagination."""
        service = SignageService(db_session)

        # Create multiple video lists
        for i in range(5):
            data = VideoListCreate(
                name=f"Playlist {i}", collection_ids=[test_collection.id]
            )
            service.create_video_list(user_id, data)

        # List with pagination
        lists, total = service.list_video_lists(user_id, page=1, page_size=3)

        assert len(lists) == 3
        assert total == 5

    def test_list_video_lists_with_search(
        self, db_session, user_id, test_collection, test_videos
    ):
        """Test listing video lists with search filter."""
        service = SignageService(db_session)

        # Create video lists with different names
        data1 = VideoListCreate(name="Morning Show", collection_ids=[test_collection.id])
        data2 = VideoListCreate(name="Evening News", collection_ids=[test_collection.id])
        service.create_video_list(user_id, data1)
        service.create_video_list(user_id, data2)

        # Search for "Morning"
        lists, total = service.list_video_lists(user_id, search="Morning")

        assert total == 1
        assert lists[0].name == "Morning Show"

    def test_update_video_list(self, db_session, user_id, test_collection, test_videos):
        """Test updating a video list."""
        service = SignageService(db_session)

        # Create
        data = VideoListCreate(
            name="Original Name", collection_ids=[test_collection.id]
        )
        video_list = service.create_video_list(user_id, data)

        # Update
        update_data = VideoListUpdate(
            name="Updated Name",
            description="Updated description",
            is_published=True,
        )
        updated_list = service.update_video_list(video_list.id, user_id, update_data)

        assert updated_list.name == "Updated Name"
        assert updated_list.description == "Updated description"
        assert updated_list.is_published is True

    def test_delete_video_list(self, db_session, user_id, test_collection, test_videos):
        """Test deleting a video list."""
        service = SignageService(db_session)

        # Create
        data = VideoListCreate(name="To Delete", collection_ids=[test_collection.id])
        video_list = service.create_video_list(user_id, data)

        # Delete
        result = service.delete_video_list(video_list.id, user_id)

        assert result is True

        # Verify it's gone
        deleted_list = service.get_video_list(video_list.id, user_id)
        assert deleted_list is None

    def test_register_device(self, db_session, user_id):
        """Test registering a signage device."""
        service = SignageService(db_session)

        device_id = uuid.uuid4()
        device_data = {
            "device_name": "New Device",
            "ip_address": "192.168.1.200",
            "port": 8009,
        }

        device = service.register_device(device_id, device_data, user_id)

        assert device is not None
        assert device.device_id == device_id
        assert device.device_name == "New Device"
        assert device.is_online is True

    def test_register_device_update_existing(self, db_session, test_device, user_id):
        """Test updating an existing device registration."""
        service = SignageService(db_session)

        device_data = {
            "device_name": "Updated Device Name",
            "ip_address": "192.168.1.250",
        }

        updated_device = service.register_device(
            test_device.device_id, device_data, user_id
        )

        assert updated_device.id == test_device.id
        assert updated_device.device_name == "Updated Device Name"
        assert updated_device.ip_address == "192.168.1.250"

    def test_update_device_heartbeat(self, db_session, test_device):
        """Test updating device heartbeat."""
        service = SignageService(db_session)

        # Update heartbeat
        success = service.update_device_heartbeat(test_device.device_id)

        assert success is True

        # Verify heartbeat was updated
        db_session.refresh(test_device)
        assert test_device.last_heartbeat is not None

    def test_list_devices(self, db_session, test_device):
        """Test listing devices with pagination."""
        service = SignageService(db_session)

        devices, total = service.list_devices(page=1, page_size=10)

        assert len(devices) >= 1
        assert total >= 1
        assert any(d.device_id == test_device.device_id for d in devices)

    def test_list_devices_filter_online(self, db_session, test_device):
        """Test listing devices filtered by online status."""
        service = SignageService(db_session)

        # Create an offline device
        offline_device = SignageDevice(
            device_id=uuid.uuid4(),
            device_name="Offline Device",
            is_online=False,
        )
        db_session.add(offline_device)
        db_session.commit()

        # List only online devices
        devices, total = service.list_devices(is_online=True)

        assert all(d.is_online for d in devices)

    def test_create_sync_history(
        self, db_session, user_id, test_collection, test_videos, test_device
    ):
        """Test creating sync history record."""
        service = SignageService(db_session)

        # Create a video list
        data = VideoListCreate(name="Test Playlist", collection_ids=[test_collection.id])
        video_list = service.create_video_list(user_id, data)

        # Create sync history
        history = service.create_sync_history(
            video_list.id, test_device.device_id, "full", user_id
        )

        assert history is not None
        assert history.video_list_id == video_list.id
        assert history.signage_device_id == test_device.device_id
        assert history.sync_mode == "full"
        assert history.sync_status == SyncStatus.IN_PROGRESS.value

    def test_get_sync_history(
        self, db_session, user_id, test_collection, test_videos, test_device
    ):
        """Test retrieving sync history."""
        service = SignageService(db_session)

        # Create video list and sync history
        data = VideoListCreate(name="Test Playlist", collection_ids=[test_collection.id])
        video_list = service.create_video_list(user_id, data)
        service.create_sync_history(video_list.id, test_device.device_id, "full", user_id)

        # Get history
        history, total = service.get_sync_history(video_list_id=video_list.id)

        assert len(history) == 1
        assert total == 1
        assert history[0].video_list_id == video_list.id


# ============================================================================
# SignageSyncService Tests
# ============================================================================


class TestSignageSyncService:
    """Tests for SignageSyncService."""

    @pytest.mark.asyncio
    async def test_sync_video_list_to_device(
        self, db_session, user_id, test_collection, test_videos, test_device
    ):
        """Test syncing a video list to a device."""
        service = SignageSyncService(db_session)

        # Create a video list
        signage_service = SignageService(db_session)
        data = VideoListCreate(name="Test Playlist", collection_ids=[test_collection.id])
        video_list = signage_service.create_video_list(user_id, data)

        # Mock the HTTP request to device
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            # Sync
            history = await service.sync_video_list_to_device(
                video_list.uuid,
                test_device.device_id,
                SyncMode.FULL,
                user_id,
            )

            assert history is not None
            assert history.sync_status == SyncStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_sync_video_list_device_offline(
        self, db_session, user_id, test_collection, test_videos
    ):
        """Test syncing to an offline device."""
        service = SignageSyncService(db_session)

        # Create offline device
        offline_device = SignageDevice(
            device_id=uuid.uuid4(),
            device_name="Offline Device",
            is_online=False,
        )
        db_session.add(offline_device)
        db_session.commit()

        # Create video list
        signage_service = SignageService(db_session)
        data = VideoListCreate(name="Test Playlist", collection_ids=[test_collection.id])
        video_list = signage_service.create_video_list(user_id, data)

        # Attempt to sync
        with pytest.raises(ValueError, match="offline"):
            await service.sync_video_list_to_device(
                video_list.uuid,
                offline_device.device_id,
                SyncMode.FULL,
                user_id,
            )


# ============================================================================
# SignagePlaybackService Tests
# ============================================================================


class TestSignagePlaybackService:
    """Tests for SignagePlaybackService."""

    @pytest.mark.asyncio
    async def test_control_playback_start(self, db_session, test_device):
        """Test sending start playback command."""
        service = SignagePlaybackService(db_session)

        request = PlaybackControlRequest(
            device_ids=[test_device.device_id],
            command=PlaybackCommand.START,
            video_list_id=uuid.uuid4(),
        )

        # Mock HTTP request
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            result = await service.control_playback(request)

            assert result["affected_devices"] == 1
            assert result["total_devices"] == 1

            # Verify device state updated
            db_session.refresh(test_device)
            assert test_device.playback_state == "playing"

    @pytest.mark.asyncio
    async def test_control_playback_pause(self, db_session, test_device):
        """Test sending pause playback command."""
        service = SignagePlaybackService(db_session)

        request = PlaybackControlRequest(
            device_ids=[test_device.device_id],
            command=PlaybackCommand.PAUSE,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            result = await service.control_playback(request)

            assert result["affected_devices"] == 1

            db_session.refresh(test_device)
            assert test_device.playback_state == "paused"

    @pytest.mark.asyncio
    async def test_control_playback_multiple_devices(self, db_session):
        """Test controlling multiple devices at once."""
        service = SignagePlaybackService(db_session)

        # Create multiple devices
        devices = []
        for i in range(3):
            device = SignageDevice(
                device_id=uuid.uuid4(),
                device_name=f"Device {i}",
                ip_address=f"192.168.1.{100+i}",
                is_online=True,
            )
            db_session.add(device)
            devices.append(device)
        db_session.commit()

        request = PlaybackControlRequest(
            device_ids=[d.device_id for d in devices],
            command=PlaybackCommand.STOP,
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value = mock_response

            result = await service.control_playback(request)

            assert result["affected_devices"] == 3
            assert result["total_devices"] == 3


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
