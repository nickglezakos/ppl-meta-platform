"""
Signage Simple Player Service

Business logic for video list management, synchronization, and playback control.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from ..models.media import Media, MediaCollection, MediaCollectionItem, MediaType
from ..models.signage import (
    SignageDevice,
    SyncStatus,
    VideoList,
    VideoListItem,
    VideoListSyncHistory,
)
from ..schemas.signage import (
    PlaybackCommand,
    PlaybackControlRequest,
    SyncMode,
    VideoListCreate,
    VideoListUpdate,
)

# Use simple logging like other working services
logger = logging.getLogger(__name__)


def _discovery_auth_headers() -> dict:
    """Service-token headers required by discovery once AUTH_ENFORCE is on."""
    return {
        "Authorization": f"Bearer {os.getenv('INTERNAL_SERVICE_TOKEN', 'ppl-meta-internal-service-secret-key-change-in-production')}",
        "X-Service-Name": "ppl-meta-media",
    }


class SignageService:
    """Service for managing video lists and signage operations."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Video List CRUD Operations
    # ========================================================================

    def create_video_list(
        self, user_id: UUID, data: VideoListCreate
    ) -> VideoList:
        """
        Create a new video list from user collections.

        Args:
            user_id: UUID of the user creating the list
            data: Video list creation data

        Returns:
            Created VideoList object

        Raises:
            ValueError: If collections don't exist or user doesn't have access
        """
        # Validate collections exist and belong to user (using UUIDs)
        # Convert string UUIDs to UUID objects for query
        from uuid import UUID as UUIDType
        collection_uuids = [UUIDType(uuid_str) for uuid_str in data.collection_ids]
        
        logger.info(f"Creating video list for user {user_id}")
        logger.info(f"Looking for collections with UUIDs: {collection_uuids}")
        
        collections = (
            self.db.query(MediaCollection)
            .filter(
                and_(
                    MediaCollection.uuid.in_(collection_uuids),
                    MediaCollection.created_by == user_id,
                )
            )
            .all()
        )
        
        logger.info(f"Found {len(collections)} collections (expected {len(data.collection_ids)})")
        if collections:
            for c in collections:
                logger.info(f"  - Collection: {c.name} (UUID: {c.uuid}, Owner: {c.created_by})")

        if len(collections) != len(data.collection_ids):
            # Debug: Check if collections exist but belong to different user
            all_collections = (
                self.db.query(MediaCollection)
                .filter(MediaCollection.uuid.in_(collection_uuids))
                .all()
            )
            if all_collections:
                logger.warning(f"Collections found but ownership mismatch:")
                for c in all_collections:
                    logger.warning(f"  - {c.name} (UUID: {c.uuid}, Owner: {c.created_by} vs requested: {user_id})")
            raise ValueError("One or more collections not found or unauthorized")
        
        # Convert UUIDs to IDs for internal use
        collection_id_map = {str(c.uuid): c.id for c in collections}

        # Create video list
        video_list = VideoList(
            name=data.name,
            description=data.description,
            user_id=user_id,
            loop_mode=data.loop_mode.value,
            transition_duration=data.transition_duration,
            last_modified_by=user_id,
        )

        self.db.add(video_list)
        self.db.flush()  # Get the ID

        # Convert UUID collection_ids to integer IDs for internal processing
        internal_collection_ids = [collection_id_map[uuid_str] for uuid_str in data.collection_ids]
        
        # Convert video_order UUIDs to IDs if provided
        internal_video_order = None
        if data.video_order:
            # Get all video UUIDs from video_order
            video_uuids = [UUIDType(item["video_id"]) for item in data.video_order]
            
            # Query videos and create UUID to ID mapping
            videos = (
                self.db.query(Media)
                .filter(Media.uuid.in_(video_uuids))
                .all()
            )
            video_id_map = {str(v.uuid): v.id for v in videos}
            
            logger.info(f"Video UUID to ID mapping: {video_id_map}")
            
            internal_video_order = [
                {
                    "collection_id": collection_id_map[item["collection_id"]],
                    "video_id": video_id_map.get(item["video_id"]),
                    "sequence": item["sequence"]
                }
                for item in data.video_order
                if item["video_id"] in video_id_map  # Skip videos not found
            ]

        # Add videos from collections
        self._add_videos_from_collections(
            video_list, internal_collection_ids, internal_video_order
        )

        # Update cached statistics
        video_list.update_cached_stats()

        self.db.commit()
        self.db.refresh(video_list)

        logger.info(
            f"Created video list '{video_list.name}' (UUID: {video_list.uuid}) "
            f"with {video_list.video_count} videos"
        )

        return video_list

    def get_video_list(
        self, list_id: int, user_id: UUID, include_items: bool = False
    ) -> Optional[VideoList]:
        """
        Get a video list by ID.

        Args:
            list_id: Video list database ID
            user_id: User UUID for authorization
            include_items: Whether to load video items

        Returns:
            VideoList object or None if not found
        """
        query = self.db.query(VideoList).filter(
            and_(VideoList.id == list_id, VideoList.user_id == user_id)
        )

        if include_items:
            query = query.options(
                joinedload(VideoList.video_items).joinedload(VideoListItem.media),
                joinedload(VideoList.video_items).joinedload(VideoListItem.collection)
            )

        return query.first()

    def get_video_list_by_uuid(
        self, uuid: UUID, user_id: UUID, include_items: bool = False
    ) -> Optional[VideoList]:
        """
        Get a video list by UUID.

        Args:
            uuid: Video list UUID
            user_id: User UUID for authorization
            include_items: Whether to load video items

        Returns:
            VideoList object or None if not found
        """
        query = self.db.query(VideoList).filter(
            and_(VideoList.uuid == uuid, VideoList.user_id == user_id)
        )

        if include_items:
            query = query.options(
                joinedload(VideoList.video_items).joinedload(VideoListItem.media),
                joinedload(VideoList.video_items).joinedload(VideoListItem.collection)
            )

        return query.first()

    def list_video_lists(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[VideoList], int]:
        """
        List video lists with pagination and filtering.

        Args:
            user_id: User UUID for filtering
            page: Page number (1-indexed)
            page_size: Results per page
            search: Search term for name
            is_active: Filter by active status

        Returns:
            Tuple of (video_lists, total_count)
        """
        query = self.db.query(VideoList).filter(VideoList.user_id == user_id)

        # Apply filters
        if search:
            query = query.filter(VideoList.name.ilike(f"%{search}%"))
        if is_active is not None:
            query = query.filter(VideoList.is_active == is_active)

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        video_lists = query.order_by(VideoList.created_at.desc()).offset(offset).limit(page_size).all()

        return video_lists, total_count

    def update_video_list(
        self, list_id: int, user_id: UUID, data: VideoListUpdate
    ) -> VideoList:
        """
        Update a video list.

        Args:
            list_id: Video list database ID
            user_id: User UUID for authorization
            data: Update data

        Returns:
            Updated VideoList object

        Raises:
            ValueError: If video list not found or unauthorized
        """
        video_list = self.get_video_list(list_id, user_id, include_items=True)
        if not video_list:
            raise ValueError("Video list not found or unauthorized")

        # Pop video_order from the update data before the field loop so it
        # isn't blindly setattr'd onto the ORM model (which lacks that column).
        update_data = data.dict(exclude_unset=True)
        video_order = update_data.pop("video_order", None)

        # Update scalar fields
        for field, value in update_data.items():
            if hasattr(video_list, field):
                if field == "loop_mode" and value:
                    setattr(video_list, field, value.value)
                else:
                    setattr(video_list, field, value)

        video_list.last_modified_by = user_id

        # If a new video order was submitted, replace the entire item list
        # with the new order so drag-reorder survives the edit.
        if video_order is not None:
            # The frontend sends integer DB IDs (as strings) for both
            # collection_id and video_id — these come from the detail
            # endpoint's VideoListItemResponse.  Try int conversion first;
            # fall back to UUID→int lookup for the create pathway.
            internal_order = []
            for item in video_order:
                try:
                    cid = int(item["collection_id"])
                    vid = int(item["video_id"])
                except (ValueError, TypeError):
                    # UUID lookup — client used the create-via-UUID pathway
                    try:
                        from uuid import UUID as UUIDType
                        cid_q = self.db.query(MediaCollection.id).filter(
                            MediaCollection.uuid == UUIDType(item["collection_id"])
                        ).scalar()
                        vid_q = self.db.query(Media.id).filter(
                            Media.uuid == UUIDType(item["video_id"])
                        ).scalar()
                    except Exception:
                        cid_q = vid_q = None
                    if cid_q is None or vid_q is None:
                        logger.warning(
                            "Skipping video_order item – "
                            "collection %s or video %s not found",
                            item.get("collection_id"),
                            item.get("video_id"),
                        )
                        continue
                    cid = cid_q
                    vid = vid_q
                internal_order.append({
                    "collection_id": cid,
                    "video_id": vid,
                    "sequence": item["sequence"],
                })

            # Clear existing items — cascade will remove them from the DB.
            for old_item in list(video_list.video_items):
                self.db.delete(old_item)
            self.db.flush()
            video_list.video_items = []

            # Re-add videos in the new order.
            self._add_videos_from_collections(
                video_list,
                list(set(item["collection_id"] for item in internal_order)),
                internal_order,
            )

        video_list.update_cached_stats()
        self.db.commit()
        self.db.refresh(video_list)

        logger.info(f"Updated video list '{video_list.name}' (UUID: {video_list.uuid})")

        return video_list

    def delete_video_list(self, list_id: int, user_id: UUID) -> bool:
        """
        Delete a video list.

        Args:
            list_id: Video list database ID
            user_id: User UUID for authorization

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If unauthorized
        """
        video_list = self.get_video_list(list_id, user_id)
        if not video_list:
            return False

        name = video_list.name
        uuid = video_list.uuid

        self.db.delete(video_list)
        self.db.commit()

        logger.info(f"Deleted video list '{name}' (UUID: {uuid})")

        return True

    # ========================================================================
    # Video List Item Management
    # ========================================================================

    def _add_videos_from_collections(
        self,
        video_list: VideoList,
        collection_ids: List[int],
        video_order: Optional[List[dict]] = None,
    ):
        """
        Add videos from collections to a video list.

        Args:
            video_list: VideoList object to add items to
            collection_ids: List of collection IDs to pull videos from
            video_order: Optional manual ordering specification
        """
        if video_order:
            # Manual ordering specified
            for order_item in video_order:
                self._add_video_item(
                    video_list,
                    order_item["collection_id"],
                    order_item["video_id"],
                    order_item["sequence"],
                )
        else:
            # Automatic ordering: add all videos from collections
            sequence = 1
            for collection_id in collection_ids:
                # Query videos through MediaCollectionItem
                videos = (
                    self.db.query(Media)
                    .join(MediaCollectionItem, MediaCollectionItem.media_id == Media.id)
                    .filter(MediaCollectionItem.collection_id == collection_id)
                    .filter(Media.media_type == MediaType.VIDEO)
                    .order_by(MediaCollectionItem.sort_order, Media.created_at)
                    .all()
                )

                for video in videos:
                    self._add_video_item(video_list, collection_id, video.id, sequence)
                    sequence += 1

    def _add_video_item(
        self, video_list: VideoList, collection_id: int, video_id: int, sequence: int
    ):
        """Add a single video item to a video list."""
        # Get video metadata
        media = self.db.query(Media).filter(Media.id == video_id).first()
        if not media:
            logger.warning(f"Video {video_id} not found, skipping")
            return

        # Get duration from media_details if available
        duration_ms = None
        if media.media_details and media.media_details.duration:
            duration_ms = int(media.media_details.duration * 1000)

        item = VideoListItem(
            video_list=video_list,
            collection_id=collection_id,
            video_id=video_id,
            sequence_order=sequence,
            video_filename=media.filename,
            video_file_path=media.file_path,
            duration_ms=duration_ms,
            is_available=True,
        )

        # Attaching via the relationship (not just the FK) keeps the parent's
        # `video_list.video_items` collection populated, so the cached stats
        # (video_count / total_duration_ms) computed by update_cached_stats()
        # right after the add loop reflect these new items.
        self.db.add(item)

    def reorder_video_items(
        self, list_id: int, user_id: UUID, new_order: List[dict]
    ) -> VideoList:
        """
        Reorder videos in a video list.

        Args:
            list_id: Video list database ID
            user_id: User UUID for authorization
            new_order: List of {item_id: int, new_sequence: int}

        Returns:
            Updated VideoList object

        Raises:
            ValueError: If video list not found or unauthorized
        """
        video_list = self.get_video_list(list_id, user_id, include_items=True)
        if not video_list:
            raise ValueError("Video list not found or unauthorized")

        # Update sequence orders
        for order_spec in new_order:
            item = next(
                (i for i in video_list.video_items if i.id == order_spec["item_id"]),
                None,
            )
            if item:
                item.sequence_order = order_spec["new_sequence"]

        video_list.last_modified_by = user_id
        video_list.update_cached_stats()

        self.db.commit()
        self.db.refresh(video_list)

        logger.info(f"Reordered videos in list '{video_list.name}'")

        return video_list

    # ========================================================================
    # Signage Device Management
    # ========================================================================

    def register_device(
        self, device_id: UUID, device_data: dict, registered_by: UUID
    ) -> SignageDevice:
        """
        Register or update a signage device.

        Args:
            device_id: Unique device identifier
            device_data: Device information
            registered_by: User UUID registering the device

        Returns:
            SignageDevice object
        """
        # Check if device already exists by device_name (stable identifier)
        device_name = device_data.get('device_name')
        
        if device_name:
            # First, try to find by device_name (the stable identifier)
            device = (
                self.db.query(SignageDevice)
                .filter(SignageDevice.device_name == device_name)
                .first()
            )
            
            if device:
                # Update existing device
                for key, value in device_data.items():
                    if hasattr(device, key):
                        setattr(device, key, value)
                # Only update device_id if it has changed
                if device.device_id != device_id:
                    device.device_id = device_id
                device.update_heartbeat()
                logger.info(f"Updated signage device '{device.device_name}' (ID: {device_id})")
            else:
                # Device name not found, check if device_id exists (might be a rename)
                existing_device_by_id = (
                    self.db.query(SignageDevice)
                    .filter(SignageDevice.device_id == device_id)
                    .first()
                )
                
                if existing_device_by_id:
                    # Update the existing device found by device_id
                    for key, value in device_data.items():
                        if hasattr(existing_device_by_id, key):
                            setattr(existing_device_by_id, key, value)
                    existing_device_by_id.update_heartbeat()
                    device = existing_device_by_id
                    logger.info(f"Updated signage device '{device.device_name}' (ID: {device_id})")
                else:
                    # Create new device
                    device = SignageDevice(
                        device_id=device_id, registered_by=registered_by, **device_data
                    )
                    device.update_heartbeat()
                    self.db.add(device)
                    logger.info(f"Registered new signage device '{device.device_name}' (ID: {device_id})")
        else:
            # Fallback to device_id lookup if no device_name
            device = (
                self.db.query(SignageDevice)
                .filter(SignageDevice.device_id == device_id)
                .first()
            )
            
            if device:
                # Update existing device
                for key, value in device_data.items():
                    if hasattr(device, key):
                        setattr(device, key, value)
                device.update_heartbeat()
                logger.info(f"Updated signage device (ID: {device_id})")
            else:
                # Create new device
                device = SignageDevice(
                    device_id=device_id, registered_by=registered_by, **device_data
                )
                device.update_heartbeat()
                self.db.add(device)
                logger.info(f"Registered new signage device (ID: {device_id})")

        self.db.commit()
        self.db.refresh(device)

        return device

    def get_device_by_id(self, device_id: UUID) -> Optional[SignageDevice]:
        """
        Get a signage device by its `device_id`.

        As a fallback, also matches the device's API `uuid`. This makes callers
        that pass either identifier work — e.g. the frontend sends the API
        `uuid`, while device heartbeat / direct backend calls send `device_id`.
        """
        device = (
            self.db.query(SignageDevice)
            .filter(SignageDevice.device_id == device_id)
            .first()
        )
        if device:
            return device
        return (
            self.db.query(SignageDevice)
            .filter(SignageDevice.uuid == device_id)
            .first()
        )

    def list_devices(
        self,
        page: int = 1,
        page_size: int = 50,
        is_online: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[SignageDevice], int]:
        """
        List signage devices with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Results per page
            is_online: Filter by online status
            is_active: Filter by active status

        Returns:
            Tuple of (devices, total_count)
        """
        query = self.db.query(SignageDevice)

        # Apply filters
        if is_online is not None:
            query = query.filter(SignageDevice.is_online == is_online)
        if is_active is not None:
            query = query.filter(SignageDevice.is_active == is_active)

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        devices = query.order_by(SignageDevice.last_seen.desc()).offset(offset).limit(page_size).all()

        return devices, total_count

    def update_device_heartbeat(self, device_id: UUID) -> bool:
        """
        Update device heartbeat timestamp.

        Args:
            device_id: Device UUID

        Returns:
            True if updated, False if device not found
        """
        device = self.get_device_by_id(device_id)
        if not device:
            return False

        device.update_heartbeat()
        self.db.commit()

        return True

    # ========================================================================
    # Sync History Management
    # ========================================================================

    def create_sync_history(
        self,
        video_list_id: int,
        device_id: UUID,
        sync_mode: str,
        initiated_by: UUID,
    ) -> VideoListSyncHistory:
        """
        Create a sync history record.

        Args:
            video_list_id: Video list database ID
            device_id: Signage device UUID
            sync_mode: "full" or "incremental"
            initiated_by: User UUID who initiated sync

        Returns:
            VideoListSyncHistory object
        """
        device = self.get_device_by_id(device_id)

        history = VideoListSyncHistory(
            video_list_id=video_list_id,
            signage_device_id=device_id,
            sync_mode=sync_mode,
            initiated_by=initiated_by,
            device_ip_address=device.ip_address if device else None,
            device_hostname=device.device_hostname if device else None,
        )

        history.mark_started()

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return history

    def update_sync_history(
        self,
        history_id: int,
        status: str,
        videos_synced: int = 0,
        videos_failed: int = 0,
        videos_skipped: int = 0,
        error_message: str = None,
    ):
        """
        Update sync history with results.

        Args:
            history_id: Sync history database ID
            status: Sync status
            videos_synced: Number of videos successfully synced
            videos_failed: Number of videos that failed
            videos_skipped: Number of videos already present and unchanged
            error_message: Error message if failed
        """
        history = (
            self.db.query(VideoListSyncHistory)
            .filter(VideoListSyncHistory.id == history_id)
            .first()
        )

        if not history:
            logger.warning(f"Sync history {history_id} not found")
            return

        if status == SyncStatus.FAILED.value:
            history.mark_failed(error_message or "Unknown error")
        else:
            history.mark_completed(videos_synced, videos_failed, videos_skipped)

        self.db.commit()

    def get_sync_history(
        self,
        video_list_id: Optional[int] = None,
        device_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[VideoListSyncHistory], int]:
        """
        Get sync history with filtering and pagination.

        Args:
            video_list_id: Filter by video list ID
            device_id: Filter by device UUID
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Tuple of (sync_history, total_count)
        """
        query = self.db.query(VideoListSyncHistory)

        # Apply filters
        if video_list_id:
            query = query.filter(VideoListSyncHistory.video_list_id == video_list_id)
        if device_id:
            query = query.filter(VideoListSyncHistory.signage_device_id == device_id)

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        history = (
            query.order_by(VideoListSyncHistory.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return history, total_count


class SignageSyncService:
    """Service for ETL synchronization of video lists to devices."""

    def __init__(self, db: Session):
        self.db = db
        self.signage_service = SignageService(db)

    async def sync_video_list_to_device(
        self,
        video_list_uuid: UUID,
        device_id: UUID,
        sync_mode: SyncMode,
        user_id: UUID,
        force_update: bool = False,
    ) -> VideoListSyncHistory:
        """
        Synchronize a video list to a signage device.

        Args:
            video_list_uuid: Video list UUID to sync
            device_id: Target device UUID
            sync_mode: Sync mode (full or incremental)
            user_id: User initiating the sync
            force_update: Force re-sync even if up-to-date

        Returns:
            VideoListSyncHistory object

        Raises:
            ValueError: If video list or device not found
        """
        # Get video list
        video_list = self.signage_service.get_video_list_by_uuid(
            video_list_uuid, user_id, include_items=True
        )
        if not video_list:
            raise ValueError("Video list not found or unauthorized")

        # Get device
        device = self.signage_service.get_device_by_id(device_id)
        
        # If device not found in database, try to auto-register from discovery service
        if not device:
            logger.info(f"Device {device_id} not found in database, attempting auto-registration from discovery")
            try:
                # Query discovery service for device info
                discovery_url = "http://localhost:8006"  # Discovery service
                logger.info(f"Querying discovery service at {discovery_url}/api/v1/services/{device_id}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{discovery_url}/api/v1/services/{device_id}", timeout=5.0, headers=_discovery_auth_headers())
                    response.raise_for_status()
                    discovery_device = response.json()
                logger.info(f"Found device in discovery: {discovery_device.get('name')}")
                
                # Extract device info
                device_data = {
                    "device_name": discovery_device.get("name", f"Device-{str(device_id)[:8]}"),
                    "device_hostname": discovery_device.get("host"),
                    "ip_address": discovery_device.get("host"),
                    "port": discovery_device.get("port"),
                    "is_online": discovery_device.get("status") == "healthy",
                }
                
                logger.info(f"Registering device with data: {device_data}")
                # Auto-register with system user (UUID all zeros)
                system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
                device = self.signage_service.register_device(
                    device_id=device_id,
                    device_data=device_data,
                    registered_by=system_user_id
                )
                logger.info(f"✅ Auto-registered device {device_id} from discovery service")
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error querying discovery service for device {device_id}: {e}")
                logger.exception("Full traceback:")
                raise ValueError(f"Device not found in database or discovery service")
            except Exception as e:
                logger.error(f"Failed to auto-register device {device_id}: {e}")
                logger.exception("Full traceback:")
                raise ValueError("Device not found or offline")
        
        if not device.is_online:
            raise ValueError("Device offline")

        # Create sync history record
        history = self.signage_service.create_sync_history(
            video_list.id, device_id, sync_mode.value, user_id
        )

        try:
            # Query the device's current content manifest so we can compute a
            # delta (idempotent sync). Fall back to a full push if the device
            # doesn't expose /api/v1/assets (older player) or the fetch fails.
            existing_ids: Optional[Set[str]] = None
            existing_ordered: Optional[List[str]] = None
            if not force_update:
                existing_ids, existing_ordered = await self._get_device_assets(
                    device, str(video_list.uuid)
                )

            playlist_ordered_ids = [
                str(item.video_id)
                for item in sorted(
                    video_list.video_items, key=lambda x: x.sequence_order
                )
            ]
            playlist_ordered_set = set(playlist_ordered_ids)

            # Reorder-aware classification of every playlist video:
            #  - added     : new to the device (not in its manifest)
            #  - reordered : already on device but in a different position
            #  - skipped   : already on device and in the same position
            #  - removed   : on device but no longer in the playlist
            added_ids: Set[str] = set()
            reordered_ids: Set[str] = set()
            skipped_count = 0
            if existing_ids is not None and existing_ordered is not None:
                existing_set = set(existing_ids)
                existing_pos = {
                    str(vid): i for i, vid in enumerate(existing_ordered)
                }
                added_ids = playlist_ordered_set - existing_set
                for i, vid in enumerate(playlist_ordered_ids):
                    if vid in added_ids:
                        continue
                    if existing_pos.get(vid) == i:
                        skipped_count += 1
                    else:
                        reordered_ids.add(vid)
                # Only count removed if we want to log it (delivery below uses
                # the playlist's own list, so removed videos simply drop out).
                removed_count = len(existing_set - playlist_ordered_set)

            same_content = existing_ids is not None and not added_ids
            same_order = existing_ids is not None and existing_ordered == playlist_ordered_ids

            if same_content and same_order:
                # Device already has every video in the same order: nothing new
                # to deliver. Send an empty videos[] as a no-op confirmation.
                video_list_data = self._prepare_video_list_data(
                    video_list, include_videos=False
                )
                videos_synced = 0
                videos_skipped = skipped_count
            else:
                # Deliver the full (ordered) list. This satisfies both:
                #  - new content (added) must reach the device, and
                #  - reordered videos must be delivered so the order-sensitive
                #    player re-applies the new sequence.
                video_list_data = self._prepare_video_list_data(video_list)
                if existing_ids is not None:
                    videos_synced = len(added_ids)
                    videos_skipped = skipped_count
                else:
                    # No manifest available -> full push counts everything.
                    videos_synced = len(video_list.video_items)
                    videos_skipped = 0

            logger.info(
                f"Delta for '{video_list.name}' -> device '{device.device_name}': "
                f"added={len(added_ids)}, reordered={len(reordered_ids)}, "
                f"skipped={skipped_count}, removed={removed_count if existing_ids is not None else 'n/a'}, "
                f"forced={force_update}"
            )

            # Send to device
            success = await self._send_to_device(
                device, video_list_data, sync_mode, force_update
            )

            if success:
                # Update sync history with accurate counts
                self.signage_service.update_sync_history(
                    history.id,
                    SyncStatus.COMPLETED.value,
                    videos_synced=videos_synced,
                    videos_failed=0,
                    videos_skipped=videos_skipped,
                )

                # Update device's current video list
                device.current_video_list_id = video_list.id
                self.db.commit()

                logger.info(
                    f"Successfully synced video list '{video_list.name}' to device '{device.device_name}' "
                    f"(synced={videos_synced}, skipped={videos_skipped})"
                )
            else:
                self.signage_service.update_sync_history(
                    history.id,
                    SyncStatus.FAILED.value,
                    error_message="Failed to send data to device",
                )

        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            self.signage_service.update_sync_history(
                history.id, SyncStatus.FAILED.value, error_message=str(e)
            )
            raise

        return history

    def _prepare_video_list_data(
        self, video_list: VideoList, include_videos: bool = True
    ) -> dict:
        """
        Prepare video list data for transmission to device.

        Args:
            video_list: VideoList object with loaded items
            include_videos: When False, emit an empty videos[] (used when the
                device already has all videos in the correct order and only the
                playlist metadata needs to be (re)confirmed).

        Returns:
            Dictionary with video list data
        """
        # Get media service endpoint from discovery
        media_service_url = "http://localhost:8000"  # Default fallback
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.get("http://localhost:8006/api/v1/services", headers=_discovery_auth_headers())
                if response.status_code == 200:
                    services = response.json().get("services", [])
                    for service in services:
                        if service.get("service_type") == "backend" and "media" in service.get("name", "").lower():
                            media_service_url = f"http://{service['host']}:{service['port']}"
                            logger.info(f"🔍 Using media service URL from discovery: {media_service_url}")
                            break
        except Exception as e:
            logger.warning(f"Could not query discovery for media service, using default: {e}")
        
        return {
            "id": str(video_list.uuid),
            "name": video_list.name,
            "description": video_list.description,
            "loop_mode": video_list.loop_mode,
            "transition_duration": video_list.transition_duration,
            "videos": [
                {
                    "id": str(item.uuid),
                    "video_id": item.video_id,
                    "sequence_order": item.sequence_order,
                    "filename": item.video_filename,
                    "file_path": f"{media_service_url}/api/v1/media/stream/{item.video_id}",  # Full HTTP URL
                    "duration_ms": item.effective_duration_ms,
                    "title": item.effective_title,
                    "thumbnail_url": f"{media_service_url}/api/v1/media/thumbnail/{item.video_id}?size=medium" if item.thumbnail_url else None,
                }
                for item in sorted(video_list.video_items, key=lambda x: x.sequence_order)
            ] if include_videos else [],
        }

    async def _send_to_device(
        self,
        device: SignageDevice,
        video_list_data: dict,
        sync_mode: SyncMode,
        force_update: bool,
    ) -> bool:
        """
        Send video list data to signage device via HTTP.

        Args:
            device: SignageDevice object
            video_list_data: Prepared video list data
            sync_mode: Sync mode (full/incremental)
            force_update: Force update even if device has current list

        Returns:
            Success status
        """
        try:
            # Query discovery service for current device endpoint (handles network changes)
            logger.info(f"Querying discovery service for device {device.device_id} ({device.device_name}) current endpoint")
            discovery_device = await self._get_device_from_discovery(device.device_id)
            
            if not discovery_device:
                logger.error(f"Device {device.device_id} not found in discovery service or unhealthy")
                # Fall back to database IP (may be stale)
                logger.warning(f"Falling back to database IP: {device.ip_address}:{device.port or 8009}")
                url = f"http://{device.ip_address}:{device.port or 8009}/api/v1/sync"
            else:
                # Use fresh endpoint from discovery service
                host = discovery_device['host']
                port = discovery_device['port']
                
                # Apply IP translation for Tailscale scenarios
                host = self._translate_ip_for_tailscale(host)
                
                logger.info(f"Using discovery endpoint for {device.device_name}: http://{host}:{port}")
                url = f"http://{host}:{port}/api/v1/sync"

            payload = {
                "video_list": video_list_data,
                "sync_mode": sync_mode.value,
                "force_update": force_update,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Sending sync request to device: {url}")
                logger.info(f"Sync payload: video_list_id={video_list_data['id']}, "
                           f"videos={len(video_list_data['videos'])}, "
                           f"sync_mode={sync_mode.value}, force_update={force_update}")
                
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                success = result.get("status") == "success"
                
                if success:
                    logger.info(f"✅ Successfully synced video list to {device.device_name} "
                               f"({len(video_list_data['videos'])} videos)")
                else:
                    logger.warning(f"⚠️ Sync returned non-success status: {result}")
                
                return success

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error syncing to {device.device_name}: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"❌ Request error syncing to {device.device_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send to device {device.device_name}: {str(e)}")
            logger.exception("Full traceback:")
            return False

    async def _get_device_assets(
        self, device: SignageDevice, playlist_id: str
    ) -> tuple[Optional[Set[str]], Optional[List[str]]]:
        """
        Query the device's current content manifest (GET /api/v1/assets) and
        return the set and ordered list of video IDs it holds for the given
        playlist.

        Args:
            device: SignageDevice object
            playlist_id: The playlist UUID (source list id) to look up

        Returns:
            Tuple of (set_of_video_ids, ordered_list_of_video_ids) for the
            matching playlist, or (None, None) if the manifest is unreachable,
            the player is old, or the playlist is not present on the device.
        """
        try:
            # Resolve the device endpoint (mirror _send_to_device logic).
            discovery_device = await self._get_device_from_discovery(device.device_id)
            if discovery_device:
                host = self._translate_ip_for_tailscale(discovery_device["host"])
                port = discovery_device["port"]
            else:
                host = device.ip_address
                port = device.port or 8009
            url = f"http://{host}:{port}/api/v1/assets"

            logger.info(f"Querying device assets manifest for {device.device_name}: {url}")

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=_discovery_auth_headers())
                response.raise_for_status()
                data = response.json()

            playlists = data.get("playlists", []) or []
            for pl in playlists:
                if pl.get("playlist_id") != playlist_id:
                    continue
                videos = pl.get("videos", []) or []
                ordered_ids = [v["video_id"] for v in videos]
                return set(ordered_ids), ordered_ids

            # Playlist not present on the device yet -> all videos are "added".
            logger.info(f"Playlist {playlist_id} not found in device assets manifest")
            return set(), []

        except Exception as e:
            logger.warning(
                f"Could not fetch device assets manifest for {device.device_name}: {e}. "
                f"Falling back to full push."
            )
            return None, None

    def _translate_ip_for_tailscale(self, host: str) -> str:
        """
        Translate local network IPs to Tailscale IP if running in Tailscale environment.
        
        If the device registered with a local IP but we need to reach it via Tailscale,
        use the server's Tailscale IP to connect.
        
        Args:
            host: Original host IP from discovery
            
        Returns:
            Translated host IP if needed, otherwise original host
        """
        # If IP is already in Tailscale range (10.x or 100.x), don't translate
        # These are already endpoint IPs from the mesh network
        if host.startswith('10.') or host.startswith('100.'):
            logger.debug(f"IP {host} is already in Tailscale range, using as-is")
            return host
        
        # Check if host is a local network IP (but not Tailscale)
        if not self._is_local_ip(host):
            # Already a public IP, no translation needed
            return host
            
        # Check if we have a Tailscale IP configured
        try:
            import subprocess
            result = subprocess.run(
                ["ip", "addr", "show", "tailscale0"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "inet " in line and "100." in line:
                        tailscale_ip = line.split()[1].split("/")[0]
                        logger.info(f"🔄 Translating local IP {host} → Tailscale IP {tailscale_ip}")
                        return tailscale_ip
        except Exception as e:
            logger.debug(f"No Tailscale interface detected: {e}")
            
        # No translation needed, return original
        return host
    
    def _is_local_ip(self, ip: str) -> bool:
        """Check if an IP is a local network address."""
        return (
            ip.startswith('192.168.') or
            ip.startswith('10.') or
            ip.startswith('172.16.') or ip.startswith('172.17.') or ip.startswith('172.18.') or
            ip.startswith('172.19.') or ip.startswith('172.20.') or ip.startswith('172.21.') or
            ip.startswith('172.22.') or ip.startswith('172.23.') or ip.startswith('172.24.') or
            ip.startswith('172.25.') or ip.startswith('172.26.') or ip.startswith('172.27.') or
            ip.startswith('172.28.') or ip.startswith('172.29.') or ip.startswith('172.30.') or
            ip.startswith('172.31.') or
            ip.startswith('127.') or
            ip == 'localhost'
        )

    async def _get_device_from_discovery(self, service_id: UUID) -> dict | None:
        """
        Query discovery service to get device information.

        Args:
            service_id: Service ID from discovery service

        Returns:
            Device info dict with host, port, name, status, or None if not found
        """
        try:
            discovery_url = "http://localhost:8006"
            logger.info(f"Querying discovery service at {discovery_url}/api/v1/services/{service_id}")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{discovery_url}/api/v1/services/{service_id}", headers=_discovery_auth_headers())
                
                if response.status_code == 200:
                    service_data = response.json()
                    logger.info(f"Found device in discovery: {service_data['name']} - {service_data['host']}:{service_data['port']}")
                    
                    # Check if device is healthy
                    if service_data.get('status') != 'healthy':
                        logger.warning(f"Device {service_id} is not healthy: {service_data.get('status')}")
                        return None
                    
                    return {
                        'name': service_data['name'],
                        'host': service_data['host'],
                        'port': service_data['port'],
                        'status': service_data['status'],
                        'service_id': service_data['service_id']
                    }
                elif response.status_code == 404:
                    logger.warning(f"Device {service_id} not found in discovery service")
                    return None
                else:
                    logger.error(f"Discovery service returned status {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to query discovery service for device {service_id}: {e}")
            return None


class SignagePlaybackService:
    """Service for remote playback control."""

    def __init__(self, db: Session):
        self.db = db
        self.signage_service = SignageService(db)

    async def control_playback(
        self, request: PlaybackControlRequest, user_id: Optional[str] = None
    ) -> dict:
        """
        Send playback control command to device(s) via discovery service.

        Args:
            request: Playback control request

        Returns:
            Dictionary with command execution results
        """
        results = []
        success_count = 0

        request_user_uuid: Optional[UUID] = None
        if user_id:
            try:
                request_user_uuid = UUID(str(user_id))
            except (ValueError, TypeError):
                logger.warning(f"Invalid user_id for playback fallback sync: {user_id}")

        for device_id in request.device_ids:
            logger.info(f"Processing control command '{request.command.value}' for device: {device_id}")
            
            # Query discovery service to get device endpoint
            device_info = await self._get_device_from_discovery(device_id)
            
            if not device_info:
                logger.warning(f"Device {device_id} not found in discovery service")
                results.append(
                    {
                        "device_id": str(device_id),
                        "status": "failed",
                        "error": "Device not found or offline",
                    }
                )
                continue

            try:
                # Apply IP translation for Tailscale scenarios
                translated_host = self._translate_ip_for_tailscale(device_info['host'])
                
                logger.info(f"Sending {request.command.value} command to device {device_info['name']} ({translated_host}:{device_info['port']})")
                control_result = await self._send_control_command_to_endpoint(
                    host=translated_host,
                    port=device_info['port'],
                    device_name=device_info['name'],
                    request=request
                )
                success = control_result.get("success", False)

                if (
                    not success
                    and request.command == PlaybackCommand.START
                    and request.video_list_id
                    and request_user_uuid
                ):
                    failure_message = (control_result.get("message") or "").lower()
                    should_retry_after_sync = (
                        "not be synced" in failure_message
                        or "failed to load playlist" in failure_message
                        or "playlist not found" in failure_message
                    )

                    if should_retry_after_sync:
                        logger.info(
                            f"Playlist may not be synced on {device_info['name']}; attempting sync and retry"
                        )
                        sync_success = await self._sync_playlist_for_start_retry(
                            video_list_uuid=request.video_list_id,
                            device_id=device_id,
                            user_id=request_user_uuid,
                        )

                        if sync_success:
                            retry_result = await self._send_control_command_to_endpoint(
                                host=translated_host,
                                port=device_info['port'],
                                device_name=device_info['name'],
                                request=request,
                            )
                            success = retry_result.get("success", False)
                            if success:
                                logger.info(
                                    f"✅ Playback start succeeded on retry after sync for {device_info['name']}"
                                )

                if success:
                    success_count += 1
                    logger.info(f"✅ Command {request.command.value} executed successfully on {device_info['name']}")

                results.append(
                    {
                        "device_id": str(device_id),
                        "status": "success" if success else "failed",
                    }
                )

            except Exception as e:
                logger.error(
                    f"Failed to control playback on device {device_info.get('name', device_id)}: {str(e)}"
                )
                results.append(
                    {"device_id": str(device_id), "status": "failed", "error": str(e)}
                )

        return {
            "affected_devices": success_count,
            "total_devices": len(request.device_ids),
            "results": results,
        }

    async def _get_device_from_discovery(self, service_id: UUID) -> dict | None:
        """
        Query discovery service to get device information.

        Args:
            service_id: Service ID from discovery service

        Returns:
            Device info dict with host, port, name, status, or None if not found
        """
        try:
            discovery_url = "http://localhost:8006"
            logger.info(f"Querying discovery service at {discovery_url}/api/v1/services/{service_id}")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{discovery_url}/api/v1/services/{service_id}", headers=_discovery_auth_headers())
                
                if response.status_code == 200:
                    service_data = response.json()
                    logger.info(f"Found device in discovery: {service_data['name']} - {service_data['host']}:{service_data['port']}")
                    
                    # Check if device is healthy
                    if service_data.get('status') != 'healthy':
                        logger.warning(f"Device {service_id} is not healthy: {service_data.get('status')}")
                        return None
                    
                    return {
                        'name': service_data['name'],
                        'host': service_data['host'],
                        'port': service_data['port'],
                        'status': service_data['status'],
                        'service_id': service_data['service_id']
                    }
                elif response.status_code == 404:
                    logger.warning(f"Device {service_id} not found in discovery service")
                    return None
                else:
                    logger.error(f"Discovery service returned status {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to query discovery service for device {service_id}: {e}")
            return None
    
    def _translate_ip_for_tailscale(self, host: str) -> str:
        """
        Translate local network IPs to Tailscale IP if running in Tailscale environment.
        
        If the device registered with a local IP but we need to reach it via Tailscale,
        use the server's Tailscale IP to connect.
        
        Args:
            host: Original host IP from discovery
            
        Returns:
            Translated host IP if needed, otherwise original host
        """
        # If IP is already in Tailscale range (10.x or 100.x), don't translate
        # These are already endpoint IPs from the mesh network
        if host.startswith('10.') or host.startswith('100.'):
            logger.debug(f"IP {host} is already in Tailscale range, using as-is")
            return host
        
        # Check if host is a local network IP (but not Tailscale)
        if not self._is_local_ip(host):
            # Already a public IP, no translation needed
            return host
            
        # Check if we have a Tailscale IP configured
        try:
            import subprocess
            result = subprocess.run(
                ["ip", "addr", "show", "tailscale0"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "inet " in line and "100." in line:
                        tailscale_ip = line.split()[1].split("/")[0]
                        logger.info(f"🔄 Translating local IP {host} → Tailscale IP {tailscale_ip}")
                        return tailscale_ip
        except Exception as e:
            logger.debug(f"No Tailscale interface detected: {e}")
            
        # No translation needed, return original
        return host
    
    def _is_local_ip(self, ip: str) -> bool:
        """Check if an IP is a local network address."""
        return (
            ip.startswith('192.168.') or
            ip.startswith('10.') or
            ip.startswith('172.16.') or ip.startswith('172.17.') or ip.startswith('172.18.') or
            ip.startswith('172.19.') or ip.startswith('172.20.') or ip.startswith('172.21.') or
            ip.startswith('172.22.') or ip.startswith('172.23.') or ip.startswith('172.24.') or
            ip.startswith('172.25.') or ip.startswith('172.26.') or ip.startswith('172.27.') or
            ip.startswith('172.28.') or ip.startswith('172.29.') or ip.startswith('172.30.') or
            ip.startswith('172.31.') or
            ip.startswith('127.') or
            ip == 'localhost'
        )

    async def _sync_playlist_for_start_retry(
        self,
        video_list_uuid: UUID,
        device_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Sync requested playlist to device before retrying START command."""
        try:
            sync_service = SignageSyncService(self.db)
            await sync_service.sync_video_list_to_device(
                video_list_uuid=video_list_uuid,
                device_id=device_id,
                sync_mode=SyncMode.INCREMENTAL,
                user_id=user_id,
                force_update=False,
            )
            return True
        except Exception as e:
            logger.warning(
                f"Fallback sync before START retry failed for device {device_id}: {e}"
            )
            return False

    async def _send_control_command_to_endpoint(
        self, host: str, port: int, device_name: str, request: PlaybackControlRequest
    ) -> Dict[str, Any]:
        """
        Send control command to device via HTTP endpoint.

        Args:
            host: Device IP address
            port: Device port
            device_name: Device name for logging
            request: Playback control request

        Returns:
            Parsed result containing success flag and device response fields
        """
        try:
            url = f"http://{host}:{port}/api/v1/control"

            payload = {
                "command": request.command.value,
                "video_list_id": (
                    str(request.video_list_id) if request.video_list_id else None
                ),
                "parameters": (
                    request.parameters.dict() if request.parameters else {}
                ),
            }

            logger.info(f"Sending control request to {url}")
            logger.info(f"Payload: {payload}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Device response: {result}")

                success = bool(result.get("success")) or result.get("status") == "success"
                return {
                    "success": success,
                    "message": result.get("message"),
                    "raw": result,
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from device {device_name}: {e.response.status_code} - {e.response.text}")
            return {"success": False, "message": str(e), "raw": None}
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to device {device_name} at {host}:{port}: {e}")
            return {"success": False, "message": str(e), "raw": None}
        except Exception as e:
            logger.error(f"Failed to send control command to {device_name}: {str(e)}")
            return {"success": False, "message": str(e), "raw": None}
