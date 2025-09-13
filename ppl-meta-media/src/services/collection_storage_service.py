"""
Collection Storage Configuration Service

Manages storage configurations for individual collections, including capacity
monitoring, archival rules, and storage analytics.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.collection_storage import (
    CollectionStorageConfig,
    CollectionStorageUsage,
    MediaArchiveStatus,
)
from src.models.media import MediaCollection
from src.schemas.storage import (
    CollectionStorageConfigResponse,
    StorageCleanupRequest,
    StorageCleanupResponse,
)


class CollectionStorageConfigService:
    """Service for managing collection storage configurations."""

    def __init__(self, db: Session):
        self.db = db

    async def get_collection_config(
        self, collection_id: int, user_id: UUID
    ) -> Optional[CollectionStorageConfig]:
        """Get storage configuration for a collection."""
        # Verify user owns the collection
        collection = (
            self.db.query(MediaCollection)
            .filter(
                MediaCollection.id == collection_id,
                MediaCollection.created_by == user_id,
            )
            .first()
        )

        if not collection:
            return None

        config = (
            self.db.query(CollectionStorageConfig)
            .filter(CollectionStorageConfig.collection_id == collection_id)
            .first()
        )

        return config

    async def initialize_collection_storage(
        self,
        collection_id: int,
        user_id: UUID,
        config_data: Optional[Dict[str, Any]] = None,
    ) -> CollectionStorageConfig:
        """Initialize storage configuration for a collection."""
        # Check if config already exists
        existing_config = await self.get_collection_config(collection_id, user_id)
        if existing_config:
            return existing_config

        # Default configuration
        default_config = {
            "collection_id": collection_id,
            "total_size_gb": 50.0,
            "live_portion_percentage": 70.0,
            "archive_portion_percentage": 30.0,
            "auto_archive_enabled": True,
            "min_age_for_archive_days": 7,
            "warning_threshold_percentage": 80.0,
            "auto_delete_enabled": False,
            "auto_delete_after_days": 365,
        }

        # Apply custom config if provided
        if config_data:
            default_config.update(config_data)

        storage_config = CollectionStorageConfig(**default_config)
        self.db.add(storage_config)

        # Create initial usage tracking
        storage_usage = CollectionStorageUsage(collection_id=collection_id)
        self.db.add(storage_usage)

        try:
            self.db.commit()
            self.db.refresh(storage_config)
            return storage_config
        except IntegrityError:
            self.db.rollback()
            # Config might have been created by another process
            return await self.get_collection_config(collection_id, user_id)

    async def update_collection_config(
        self, collection_id: int, user_id: UUID, updates: Dict[str, Any]
    ) -> Optional[CollectionStorageConfig]:
        """Update collection storage configuration."""
        config = await self.get_collection_config(collection_id, user_id)
        if not config:
            return None

        # Update provided fields
        for field, value in updates.items():
            if hasattr(config, field):
                setattr(config, field, value)

        # Ensure archive percentage is calculated correctly
        if "live_portion_percentage" in updates:
            config.archive_portion_percentage = 100 - config.live_portion_percentage

        self.db.commit()
        self.db.refresh(config)
        return config

    async def get_storage_usage(
        self, collection_id: int, user_id: UUID
    ) -> Optional[CollectionStorageUsage]:
        """Get current storage usage for a collection."""
        # Verify access
        if not await self.get_collection_config(collection_id, user_id):
            return None

        usage = (
            self.db.query(CollectionStorageUsage)
            .filter(CollectionStorageUsage.collection_id == collection_id)
            .first()
        )

        return usage

    async def update_storage_usage(
        self, collection_id: int, used_bytes: int, live_bytes: int, archive_bytes: int
    ) -> CollectionStorageUsage:
        """Update storage usage statistics for a collection."""
        usage = (
            self.db.query(CollectionStorageUsage)
            .filter(CollectionStorageUsage.collection_id == collection_id)
            .first()
        )

        if not usage:
            usage = CollectionStorageUsage(collection_id=collection_id)
            self.db.add(usage)

        usage.total_used_bytes = used_bytes
        usage.live_portion_used_bytes = live_bytes
        usage.archive_portion_used_bytes = archive_bytes

        # Update capacity flags
        config = (
            self.db.query(CollectionStorageConfig)
            .filter(CollectionStorageConfig.collection_id == collection_id)
            .first()
        )

        if config:
            total_capacity = (
                config.total_size_gb * 1024 * 1024 * 1024
            )  # Convert to bytes
            usage_percentage = (used_bytes / total_capacity) * 100

            usage.is_near_capacity = (
                usage_percentage >= config.warning_threshold_percentage
            )
            usage.is_at_capacity = usage_percentage >= 100.0

        self.db.commit()
        self.db.refresh(usage)
        return usage

    async def get_storage_analytics(
        self, collection_id: int, user_id: UUID
    ) -> Dict[str, Any]:
        """Get detailed storage analytics for a collection."""
        config = await self.get_collection_config(collection_id, user_id)
        usage = await self.get_storage_usage(collection_id, user_id)

        if not config or not usage:
            return {"error": "Collection not found or no access"}

        total_capacity_bytes = config.total_size_gb * 1024 * 1024 * 1024
        live_capacity_bytes = total_capacity_bytes * (
            config.live_portion_percentage / 100
        )
        archive_capacity_bytes = total_capacity_bytes * (
            config.archive_portion_percentage / 100
        )

        # Calculate percentages
        total_usage_pct = (usage.total_used_bytes / total_capacity_bytes) * 100
        live_usage_pct = (
            (usage.live_portion_used_bytes / live_capacity_bytes) * 100
            if live_capacity_bytes > 0
            else 0
        )
        archive_usage_pct = (
            (usage.archive_portion_used_bytes / archive_capacity_bytes) * 100
            if archive_capacity_bytes > 0
            else 0
        )

        # Get media counts
        from src.models.media import Media

        total_media = (
            self.db.query(Media)
            .join(Media.collections)
            .filter(MediaCollection.id == collection_id)
            .count()
        )

        archived_media = (
            self.db.query(MediaArchiveStatus)
            .join(Media, MediaArchiveStatus.media_id == Media.id)
            .join(Media.collections)
            .filter(
                MediaCollection.id == collection_id,
                MediaArchiveStatus.is_archived == True,
            )
            .count()
        )

        live_media = total_media - archived_media

        return {
            "collection_id": collection_id,
            "total_capacity_gb": config.total_size_gb,
            "usage_statistics": {
                "total_used_gb": round(usage.total_used_bytes / (1024**3), 2),
                "total_usage_percentage": round(total_usage_pct, 1),
                "live_used_gb": round(usage.live_portion_used_bytes / (1024**3), 2),
                "live_usage_percentage": round(live_usage_pct, 1),
                "archive_used_gb": round(
                    usage.archive_portion_used_bytes / (1024**3), 2
                ),
                "archive_usage_percentage": round(archive_usage_pct, 1),
            },
            "media_counts": {
                "total_media": total_media,
                "live_media": live_media,
                "archived_media": archived_media,
            },
            "capacity_status": {
                "is_near_capacity": usage.is_near_capacity,
                "is_at_capacity": usage.is_at_capacity,
                "warning_threshold": config.warning_threshold_percentage,
            },
            "configuration": {
                "live_portion_percentage": config.live_portion_percentage,
                "archive_portion_percentage": config.archive_portion_percentage,
                "auto_archive_enabled": config.auto_archive_enabled,
                "min_age_for_archive_days": config.min_age_for_archive_days,
            },
        }

    async def trigger_storage_cleanup(
        self, collection_id: int, user_id: UUID, cleanup_request: StorageCleanupRequest
    ) -> StorageCleanupResponse:
        """Trigger storage cleanup operations."""
        config = await self.get_collection_config(collection_id, user_id)
        if not config:
            raise ValueError("Collection not found or no access")

        cleanup_result = {
            "collection_id": collection_id,
            "cleanup_type": cleanup_request.action,
            "files_processed": 0,
            "bytes_freed": 0,
            "errors": [],
        }

        try:
            if cleanup_request.action == "delete_old":
                result = await self._delete_old_media(
                    collection_id, cleanup_request.days_threshold or 30
                )
                cleanup_result.update(result)
            elif cleanup_request.action == "archive_all":
                result = await self._archive_all_live_media(collection_id)
                cleanup_result.update(result)
            elif cleanup_request.action == "optimize_storage":
                result = await self._optimize_storage_layout(collection_id)
                cleanup_result.update(result)

            # Update usage statistics after cleanup
            await self._recalculate_usage(collection_id)

        except Exception as e:
            cleanup_result["errors"].append(str(e))

        return StorageCleanupResponse(**cleanup_result)

    async def _delete_old_media(
        self, collection_id: int, days_threshold: int
    ) -> Dict[str, Any]:
        """Delete media older than threshold."""
        from datetime import datetime, timedelta

        from src.models.media import Media

        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        old_media = (
            self.db.query(Media)
            .join(Media.collections)
            .filter(MediaCollection.id == collection_id, Media.created_at < cutoff_date)
            .all()
        )

        files_processed = 0
        bytes_freed = 0

        for media in old_media:
            if media.file_size:
                bytes_freed += media.file_size

            # Remove from collections and delete
            media.collections.clear()
            self.db.delete(media)
            files_processed += 1

        self.db.commit()

        return {
            "files_processed": files_processed,
            "bytes_freed": bytes_freed,
        }

    async def _archive_all_live_media(self, collection_id: int) -> Dict[str, Any]:
        """Archive all live media in collection."""
        from datetime import datetime

        from src.models.media import Media

        live_media = (
            self.db.query(Media)
            .join(Media.collections)
            .outerjoin(MediaArchiveStatus, MediaArchiveStatus.media_id == Media.id)
            .filter(
                MediaCollection.id == collection_id,
                MediaArchiveStatus.is_archived != True,
            )
            .all()
        )

        files_processed = 0
        bytes_freed = 0

        for media in live_media:
            # Create or update archive status
            archive_status = (
                self.db.query(MediaArchiveStatus)
                .filter(MediaArchiveStatus.media_id == media.id)
                .first()
            )

            if not archive_status:
                archive_status = MediaArchiveStatus(media_id=media.id)
                self.db.add(archive_status)

            archive_status.is_archived = True
            archive_status.archived_at = datetime.utcnow()
            archive_status.archive_reason = "manual_archive"
            archive_status.can_stream_immediately = False
            archive_status.requires_retrieval = True

            files_processed += 1
            if media.file_size:
                bytes_freed += media.file_size

        self.db.commit()

        return {
            "files_processed": files_processed,
            "bytes_freed": bytes_freed,
        }

    async def _optimize_storage_layout(self, collection_id: int) -> Dict[str, Any]:
        """Optimize storage layout and organization."""
        # This would implement storage optimization logic
        # For now, return a placeholder
        return {
            "files_processed": 0,
            "bytes_freed": 0,
            "optimization_applied": "storage_defragmentation",
        }

    async def _recalculate_usage(self, collection_id: int):
        """Recalculate storage usage statistics."""
        from src.models.media import Media

        # Calculate total usage
        total_size_result = (
            self.db.query(self.db.func.sum(Media.file_size))
            .join(Media.collections)
            .filter(MediaCollection.id == collection_id)
            .scalar()
        )

        # Calculate archived usage
        archived_size_result = (
            self.db.query(self.db.func.sum(Media.file_size))
            .join(Media.collections)
            .join(MediaArchiveStatus, MediaArchiveStatus.media_id == Media.id)
            .filter(
                MediaCollection.id == collection_id,
                MediaArchiveStatus.is_archived == True,
            )
            .scalar()
        )

        total_bytes = total_size_result or 0
        archived_bytes = archived_size_result or 0
        live_bytes = total_bytes - archived_bytes

        await self.update_storage_usage(
            collection_id, total_bytes, live_bytes, archived_bytes
        )

    async def get_storage_health_status(self, user_id: UUID) -> Dict[str, Any]:
        """Get overall storage health status for user."""
        collections = (
            self.db.query(MediaCollection)
            .filter(MediaCollection.created_by == user_id)
            .all()
        )

        total_collections = len(collections)
        healthy_collections = 0
        warning_collections = 0
        critical_collections = 0

        for collection in collections:
            usage = await self.get_storage_usage(collection.id, user_id)
            if usage:
                if usage.is_at_capacity:
                    critical_collections += 1
                elif usage.is_near_capacity:
                    warning_collections += 1
                else:
                    healthy_collections += 1

        health_score = (
            (healthy_collections / total_collections * 100)
            if total_collections > 0
            else 100
        )

        return {
            "overall_health_score": round(health_score, 1),
            "total_collections": total_collections,
            "healthy_collections": healthy_collections,
            "warning_collections": warning_collections,
            "critical_collections": critical_collections,
            "recommendations": self._generate_health_recommendations(
                warning_collections, critical_collections
            ),
        }

    def _generate_health_recommendations(
        self, warning_count: int, critical_count: int
    ) -> List[str]:
        """Generate storage health recommendations."""
        recommendations = []

        if critical_count > 0:
            recommendations.append(
                f"Immediate action needed: {critical_count} collections at capacity"
            )
            recommendations.append("Consider expanding storage or deleting old content")

        if warning_count > 0:
            recommendations.append(
                f"Monitor closely: {warning_count} collections approaching capacity"
            )
            recommendations.append("Enable auto-archival to prevent capacity issues")

        if warning_count == 0 and critical_count == 0:
            recommendations.append("Storage health is good")
            recommendations.append("Continue monitoring usage patterns")

        return recommendations
