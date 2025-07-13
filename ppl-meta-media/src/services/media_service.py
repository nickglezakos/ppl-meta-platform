"""
Media service layer for PPL Meta Platform Media Service.
"""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from ..models.media import (
    Media,
    MediaCollection,
    MediaCollectionItem,
    MediaDetails,
    MediaShare,
    MediaType,
    MediaVariant,
    ProcessingStatus,
)
from ..schemas.media import MediaSearchRequest, MediaUploadRequest


class MediaService:
    """Service for media operations."""

    def __init__(self, db: Session):
        self.db = db

    async def upload_media(
        self, file: UploadFile, upload_request: MediaUploadRequest
    ) -> Media:
        """Upload and process a media file."""

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Generate file hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()

        # Check if file already exists
        existing_media = (
            self.db.query(Media)
            .filter(Media.checksum == file_hash)
            .filter(Media.uploaded_by == upload_request.user_id)
            .first()
        )

        if existing_media:
            return existing_media

        # Determine media type from MIME type
        mime_type = file.content_type or "application/octet-stream"
        media_type = self._determine_media_type(mime_type)

        # Generate unique filename
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{secrets.token_hex(16)}{file_extension}"

        # Create storage path
        storage_path = self._create_storage_path(
            upload_request.user_id, media_type, unique_filename
        )

        # Parse optional JSON fields
        tags = upload_request.tags or []
        categories = upload_request.categories or []
        location_data = None
        capture_timestamp = None

        if upload_request.location_data:
            try:
                location_data = json.loads(upload_request.location_data)
            except json.JSONDecodeError:
                pass

        if upload_request.capture_timestamp:
            try:
                capture_timestamp = datetime.fromisoformat(
                    upload_request.capture_timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Create media record
        media = Media(
            filename=unique_filename,
            original_filename=file.filename,
            media_type=media_type,
            mime_type=mime_type,
            file_extension=file_extension,
            file_size=file_size,
            file_path=storage_path,
            checksum=file_hash,
            uploaded_by=upload_request.user_id,
            title=upload_request.title,
            description=upload_request.description,
            tags=tags,
            categories=categories,
            is_public=upload_request.is_public,
            # Device information
            device_name=upload_request.device_name,
            device_model=upload_request.device_model,
            device_manufacturer=upload_request.device_manufacturer,
            device_os=upload_request.device_os,
            app_name=upload_request.app_name,
            app_version=upload_request.app_version,
            location_data=location_data,
            capture_timestamp=capture_timestamp,
        )

        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)

        # Save file to storage
        await self._save_file_to_storage(content, storage_path)

        # Process media asynchronously (thumbnails, metadata extraction, etc.)
        await self._process_media_async(media)

        return media

    async def search_media(self, search_request: MediaSearchRequest) -> List[Media]:
        """Search media with various filters."""

        query = self.db.query(Media)

        # Apply filters
        if search_request.uploaded_by:
            query = query.filter(Media.uploaded_by == search_request.uploaded_by)

        if search_request.media_types:
            query = query.filter(Media.media_type.in_(search_request.media_types))

        if search_request.tags:
            # Search for any of the provided tags
            tag_conditions = [Media.tags.contains([tag]) for tag in search_request.tags]
            query = query.filter(or_(*tag_conditions))

        if search_request.categories:
            # Search for any of the provided categories
            category_conditions = [
                Media.categories.contains([cat]) for cat in search_request.categories
            ]
            query = query.filter(or_(*category_conditions))

        if search_request.is_public is not None:
            query = query.filter(Media.is_public == search_request.is_public)

        if search_request.date_from:
            query = query.filter(Media.created_at >= search_request.date_from)

        if search_request.date_to:
            query = query.filter(Media.created_at <= search_request.date_to)

        # Apply sorting
        query = query.order_by(desc(Media.created_at))

        # Apply pagination
        offset = (search_request.page - 1) * search_request.page_size
        query = query.offset(offset).limit(search_request.page_size)

        return query.all()

    async def get_media(
        self, media_id: str, user_id: Optional[UUID] = None
    ) -> Optional[Media]:
        """Get media by ID with access control."""

        query = self.db.query(Media)

        # Try to find by UUID first, then by ID
        try:
            uuid_val = UUID(media_id)
            query = query.filter(Media.uuid == uuid_val)
        except ValueError:
            query = query.filter(Media.id == int(media_id))

        media = query.first()

        if not media:
            return None

        # Check access permissions
        if not media.is_public and user_id != media.uploaded_by:
            return None

        return media

    async def delete_media(self, media_id: str, user_id: UUID) -> bool:
        """Delete media (soft delete)."""

        media = await self.get_media(media_id, user_id)

        if not media or media.uploaded_by != user_id:
            return False

        # Soft delete
        media.is_archived = True
        media.processing_status = ProcessingStatus.ARCHIVED

        self.db.commit()
        return True

    async def get_media_grouped(
        self, user_id: UUID, group_by: str = "device_name"
    ) -> Dict:
        """Get user's media grouped by specified criteria."""

        query = self.db.query(Media).filter(Media.uploaded_by == user_id)

        if group_by == "device_name":
            grouped = {}
            for media in query.all():
                device = media.device_name or "Unknown Device"
                if device not in grouped:
                    grouped[device] = []
                grouped[device].append(media)
            return grouped

        elif group_by == "media_type":
            grouped = {}
            for media in query.all():
                media_type = media.media_type.value
                if media_type not in grouped:
                    grouped[media_type] = []
                grouped[media_type].append(media)
            return grouped

        elif group_by == "month":
            grouped = {}
            for media in query.all():
                month_key = media.created_at.strftime("%Y-%m")
                if month_key not in grouped:
                    grouped[month_key] = []
                grouped[month_key].append(media)
            return grouped

        else:
            return {"error": f"Unsupported group_by: {group_by}"}

    async def get_user_media_stats(self, user_id: UUID) -> Dict:
        """Get statistics about user's media."""

        query = self.db.query(Media).filter(Media.uploaded_by == user_id)

        # Basic counts
        total_count = query.count()
        total_size = query.with_entities(func.sum(Media.file_size)).scalar() or 0

        # By media type
        type_stats = (
            query.with_entities(Media.media_type, func.count(Media.id))
            .group_by(Media.media_type)
            .all()
        )

        # By device
        device_stats = (
            query.filter(Media.device_name.isnot(None))
            .with_entities(Media.device_name, func.count(Media.id))
            .group_by(Media.device_name)
            .all()
        )

        # Recent uploads (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = query.filter(Media.created_at >= thirty_days_ago).count()

        return {
            "total_count": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "recent_uploads_30d": recent_count,
            "by_type": {media_type.value: count for media_type, count in type_stats},
            "by_device": {device: count for device, count in device_stats},
        }

    # Collection methods
    async def create_collection(
        self, name: str, description: str, user_id: UUID, is_public: bool = False
    ) -> MediaCollection:
        """Create a new media collection."""

        collection = MediaCollection(
            name=name,
            description=description,
            created_by=user_id,
            is_public=is_public,
        )

        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)

        return collection

    async def add_media_to_collection(
        self, collection_id: str, media_id: str, user_id: UUID
    ) -> bool:
        """Add media to a collection."""

        # Get collection
        collection = (
            self.db.query(MediaCollection)
            .filter(MediaCollection.uuid == UUID(collection_id))
            .first()
        )

        if not collection or collection.created_by != user_id:
            return False

        # Get media
        media = await self.get_media(media_id, user_id)
        if not media:
            return False

        # Check if already in collection
        existing = (
            self.db.query(MediaCollectionItem)
            .filter(
                and_(
                    MediaCollectionItem.collection_id == collection.id,
                    MediaCollectionItem.media_id == media.id,
                )
            )
            .first()
        )

        if existing:
            return True  # Already in collection

        # Add to collection
        collection_item = MediaCollectionItem(
            collection_id=collection.id,
            media_id=media.id,
            added_by=user_id,
        )

        self.db.add(collection_item)
        self.db.commit()

        return True

    # Sharing methods
    async def create_share_link(
        self,
        media_id: str,
        user_id: UUID,
        can_download: bool = False,
        expires_hours: Optional[int] = None,
    ) -> MediaShare:
        """Create a share link for media."""

        media = await self.get_media(media_id, user_id)
        if not media or media.uploaded_by != user_id:
            raise ValueError("Media not found or access denied")

        # Calculate expiration
        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

        # Create share
        share = MediaShare(
            media_id=media.id,
            shared_by=user_id,
            share_token=secrets.token_urlsafe(32),
            can_download=can_download,
            expires_at=expires_at,
        )

        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)

        return share

    # Private helper methods
    def _determine_media_type(self, mime_type: str) -> MediaType:
        """Determine media type from MIME type."""

        if mime_type.startswith("video/"):
            return MediaType.VIDEO
        elif mime_type.startswith("image/"):
            return MediaType.PICTURE
        elif mime_type.startswith("audio/"):
            return MediaType.SOUND
        elif mime_type in ["application/pdf", "text/plain", "application/msword"]:
            return MediaType.DOCUMENT
        else:
            return MediaType.DOCUMENT  # Default

    def _create_storage_path(
        self, user_id: UUID, media_type: MediaType, filename: str
    ) -> str:
        """Create storage path for media file."""

        year_month = datetime.utcnow().strftime("%Y/%m")
        return f"media/{user_id}/{media_type.value}/{year_month}/{filename}"

    async def _save_file_to_storage(self, content: bytes, storage_path: str):
        """Save file content to storage."""

        # For now, save to local storage
        # TODO: Implement cloud storage providers
        full_path = Path("storage") / storage_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

    async def _process_media_async(self, media: Media):
        """Process media asynchronously (thumbnails, metadata extraction, etc.)."""

        # TODO: Implement async processing
        # - Generate thumbnails for images/videos
        # - Extract metadata (EXIF, video info, etc.)
        # - Create different quality variants
        # - Update processing status

        # For now, just mark as completed
        media.processing_status = ProcessingStatus.COMPLETED
        self.db.commit()
