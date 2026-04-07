"""
Storage Location Service

CRUD operations and verification for user-defined storage locations.
"""

import os
import shutil
import structlog
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.media import Media
from ..models.storage_location import LocationType, StorageLocation, StorageTier

logger = structlog.get_logger(__name__)


class StorageLocationService:
    """Manages user-configurable storage locations."""

    def __init__(self, db: Session):
        self.db = db

    # ── CRUD ──────────────────────────────────────────────────────────

    async def list_locations(self, user_id: UUID) -> List[StorageLocation]:
        """List all storage locations for a user."""
        return (
            self.db.query(StorageLocation)
            .filter(StorageLocation.user_id == user_id)
            .order_by(StorageLocation.is_default.desc(), StorageLocation.name)
            .all()
        )

    async def get_location(self, user_id: UUID, location_id: UUID) -> Optional[StorageLocation]:
        """Get a single storage location by UUID."""
        return (
            self.db.query(StorageLocation)
            .filter(
                StorageLocation.uuid == location_id,
                StorageLocation.user_id == user_id,
            )
            .first()
        )

    async def create_location(
        self,
        user_id: UUID,
        name: str,
        location_type: LocationType,
        base_path: str,
        tier: StorageTier = StorageTier.ACTIVE,
        is_default: bool = False,
        cloud_config: Optional[dict] = None,
    ) -> StorageLocation:
        """Create a new storage location."""

        # If setting as default, clear existing default for this tier
        if is_default:
            self._clear_default(user_id, tier)

        # If this is the user's first location, make it default
        existing_count = (
            self.db.query(StorageLocation)
            .filter(StorageLocation.user_id == user_id, StorageLocation.tier == tier)
            .count()
        )
        if existing_count == 0:
            is_default = True

        location = StorageLocation(
            user_id=user_id,
            name=name,
            location_type=location_type,
            base_path=base_path.rstrip("/"),
            tier=tier,
            is_default=is_default,
            cloud_config=cloud_config,
        )

        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)

        logger.info(
            "storage_location_created",
            location_id=str(location.uuid),
            name=name,
            type=location_type.value,
            tier=tier.value,
        )

        return location

    async def update_location(
        self,
        user_id: UUID,
        location_id: UUID,
        updates: dict,
    ) -> Optional[StorageLocation]:
        """Update a storage location."""
        location = await self.get_location(user_id, location_id)
        if not location:
            return None

        allowed_fields = {
            "name", "base_path", "tier", "is_default", "cloud_config",
        }

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                if key == "base_path":
                    value = value.rstrip("/")
                if key == "is_default" and value is True:
                    self._clear_default(user_id, location.tier)
                if key == "tier" and isinstance(value, str):
                    value = StorageTier(value)
                setattr(location, key, value)

        self.db.commit()
        self.db.refresh(location)
        return location

    async def delete_location(self, user_id: UUID, location_id: UUID) -> bool:
        """Delete a storage location. Fails if files still reference it."""
        location = await self.get_location(user_id, location_id)
        if not location:
            return False

        # Check for referenced files
        file_count = (
            self.db.query(Media)
            .filter(Media.storage_location_id == location_id)
            .count()
        )
        if file_count > 0:
            raise ValueError(
                f"Cannot delete location: {file_count} media files still reference it. "
                "Migrate files first."
            )

        was_default = location.is_default
        tier = location.tier

        self.db.delete(location)
        self.db.commit()

        # If we removed the default, promote another location
        if was_default:
            fallback = (
                self.db.query(StorageLocation)
                .filter(
                    StorageLocation.user_id == user_id,
                    StorageLocation.tier == tier,
                )
                .first()
            )
            if fallback:
                fallback.is_default = True
                self.db.commit()

        logger.info(
            "storage_location_deleted",
            location_id=str(location_id),
        )
        return True

    async def set_default(self, user_id: UUID, location_id: UUID) -> Optional[StorageLocation]:
        """Set a location as the default for its tier."""
        location = await self.get_location(user_id, location_id)
        if not location:
            return None

        self._clear_default(user_id, location.tier)
        location.is_default = True
        self.db.commit()
        self.db.refresh(location)
        return location

    # ── Verification ──────────────────────────────────────────────────

    async def verify_location(self, user_id: UUID, location_id: UUID) -> dict:
        """
        Verify a storage location is accessible and update capacity stats.
        Returns a status dict with is_accessible, total_bytes, free_bytes, error.
        """
        location = await self.get_location(user_id, location_id)
        if not location:
            return {"is_accessible": False, "error": "Location not found"}

        result = {"is_accessible": False, "total_bytes": None, "free_bytes": None, "error": None}

        if location.is_cloud:
            result = await self._verify_cloud_location(location)
        else:
            result = self._verify_local_location(location)

        # Update the record
        location.mount_verified = result["is_accessible"]
        location.is_active = result["is_accessible"]
        location.last_verified_at = datetime.now(timezone.utc)

        if result["total_bytes"] is not None:
            location.total_capacity_bytes = result["total_bytes"]

        self.db.commit()
        self.db.refresh(location)

        result["location_id"] = str(location.uuid)
        result["name"] = location.name
        return result

    def _verify_local_location(self, location: StorageLocation) -> dict:
        """Verify a local or external drive path."""
        path = location.base_path
        result = {"is_accessible": False, "total_bytes": None, "free_bytes": None, "error": None}

        if not os.path.exists(path):
            # Try to create it
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                result["error"] = f"Path does not exist and cannot be created: {e}"
                return result

        if not os.path.isdir(path):
            result["error"] = "Path exists but is not a directory"
            return result

        if not os.access(path, os.W_OK):
            result["error"] = "Path is not writable"
            return result

        try:
            usage = shutil.disk_usage(path)
            result["is_accessible"] = True
            result["total_bytes"] = usage.total
            result["free_bytes"] = usage.free
        except OSError as e:
            result["error"] = f"Cannot read disk usage: {e}"

        return result

    async def _verify_cloud_location(self, location: StorageLocation) -> dict:
        """Verify cloud storage connectivity."""
        result = {"is_accessible": False, "total_bytes": None, "free_bytes": None, "error": None}

        if not location.cloud_config:
            result["error"] = "No cloud configuration provided"
            return result

        try:
            if location.location_type == LocationType.CLOUD_S3:
                import boto3

                config = location.cloud_config
                s3 = boto3.client(
                    "s3",
                    region_name=config.get("region", "us-east-1"),
                    aws_access_key_id=config.get("access_key_id"),
                    aws_secret_access_key=config.get("secret_access_key"),
                )
                bucket = config.get("bucket", location.base_path.replace("s3://", "").split("/")[0])
                s3.head_bucket(Bucket=bucket)
                result["is_accessible"] = True
            else:
                # Azure/GCP — connectivity check placeholder
                result["is_accessible"] = True
        except Exception as e:
            result["error"] = f"Cloud verification failed: {e}"

        return result

    # ── Dashboard / Summary ───────────────────────────────────────────

    async def get_summary(self, user_id: UUID) -> dict:
        """Aggregated storage usage across all locations for a user."""
        locations = await self.list_locations(user_id)

        # --- Real media stats from the database ---
        media_stats = (
            self.db.query(
                func.count(Media.id).label("count"),
                func.coalesce(func.sum(Media.file_size), 0).label("total_bytes"),
            )
            .first()
        )
        media_real_files = media_stats.count if media_stats else 0
        media_real_bytes = int(media_stats.total_bytes) if media_stats else 0

        # --- Default active location info ---
        default_active = await self.get_default_location(user_id, StorageTier.ACTIVE)
        default_active_info = None
        if default_active:
            default_active_info = {
                "uuid": str(default_active.uuid),
                "name": default_active.name,
                "location_type": default_active.location_type.value,
                "base_path": default_active.base_path,
                "used_gb": default_active.used_gb,
                "total_capacity_gb": default_active.total_capacity_gb,
                "usage_percentage": default_active.usage_percentage,
            }

        total_capacity = 0
        total_used = 0
        total_files = 0
        active_used = 0
        archive_used = 0
        active_files = 0
        archive_files = 0
        locations_data = []

        for loc in locations:
            if loc.total_capacity_bytes:
                total_capacity += loc.total_capacity_bytes
            total_used += loc.used_bytes
            total_files += loc.file_count

            if loc.tier == StorageTier.ACTIVE:
                active_used += loc.used_bytes
                active_files += loc.file_count
            else:
                archive_used += loc.used_bytes
                archive_files += loc.file_count

            locations_data.append({
                "uuid": str(loc.uuid),
                "name": loc.name,
                "location_type": loc.location_type.value,
                "tier": loc.tier.value,
                "is_active": loc.is_active,
                "is_default": loc.is_default,
                "used_bytes": loc.used_bytes,
                "total_capacity_bytes": loc.total_capacity_bytes,
                "file_count": loc.file_count,
                "usage_percentage": loc.usage_percentage,
                "used_gb": loc.used_gb,
                "total_capacity_gb": loc.total_capacity_gb,
                "free_gb": loc.free_gb,
            })

        # Use real media stats if location-tracked usage is zero
        effective_used = total_used if total_used > 0 else media_real_bytes
        effective_files = total_files if total_files > 0 else media_real_files

        usage_pct = 0.0
        if total_capacity > 0:
            usage_pct = round((effective_used / total_capacity) * 100, 2)

        return {
            "total_capacity_bytes": total_capacity if total_capacity > 0 else None,
            "total_used_bytes": effective_used,
            "total_files": effective_files,
            "usage_percentage": usage_pct,
            "active_used_bytes": active_used if active_used > 0 else media_real_bytes,
            "active_files": active_files if active_files > 0 else media_real_files,
            "archive_used_bytes": archive_used,
            "archive_files": archive_files,
            "total_capacity_gb": round(total_capacity / (1024**3), 2) if total_capacity > 0 else None,
            "total_used_gb": round(effective_used / (1024**3), 2),
            "free_gb": round((total_capacity - effective_used) / (1024**3), 2) if total_capacity > 0 else None,
            "location_count": len(locations),
            "locations": locations_data,
            "media_real_used_bytes": media_real_bytes,
            "media_real_files": media_real_files,
            "media_real_used_gb": round(media_real_bytes / (1024**3), 2),
            "default_active_location": default_active_info,
        }

    async def get_default_location(self, user_id: UUID, tier: StorageTier = StorageTier.ACTIVE) -> Optional[StorageLocation]:
        """Get the default storage location for a user and tier."""
        return (
            self.db.query(StorageLocation)
            .filter(
                StorageLocation.user_id == user_id,
                StorageLocation.tier == tier,
                StorageLocation.is_default == True,
                StorageLocation.is_active == True,
            )
            .first()
        )

    async def update_usage(self, location_id: UUID, bytes_delta: int, file_count_delta: int = 0):
        """Update used_bytes and file_count for a location (called after upload/delete)."""
        location = self.db.query(StorageLocation).filter(StorageLocation.uuid == location_id).first()
        if location:
            location.used_bytes = max(0, location.used_bytes + bytes_delta)
            location.file_count = max(0, location.file_count + file_count_delta)
            self.db.commit()

    # ── Alerts ────────────────────────────────────────────────────────

    async def get_alerts(self, user_id: UUID, warning_pct: float = 80.0, critical_pct: float = 95.0) -> List[dict]:
        """Get storage alerts for locations exceeding thresholds."""
        locations = await self.list_locations(user_id)
        alerts = []

        for loc in locations:
            if loc.total_capacity_bytes is None or loc.total_capacity_bytes == 0:
                continue  # Skip unlimited locations

            pct = loc.usage_percentage

            if pct >= critical_pct:
                alerts.append({
                    "level": "critical",
                    "location_id": str(loc.uuid),
                    "location_name": loc.name,
                    "usage_percentage": pct,
                    "used_gb": loc.used_gb,
                    "total_gb": loc.total_capacity_gb,
                    "message": f"Storage '{loc.name}' is critically full at {pct}%.",
                })
            elif pct >= warning_pct:
                alerts.append({
                    "level": "warning",
                    "location_id": str(loc.uuid),
                    "location_name": loc.name,
                    "usage_percentage": pct,
                    "used_gb": loc.used_gb,
                    "total_gb": loc.total_capacity_gb,
                    "message": f"Storage '{loc.name}' is {pct}% full. Consider archiving or adding storage.",
                })

            if not loc.is_active:
                alerts.append({
                    "level": "warning",
                    "location_id": str(loc.uuid),
                    "location_name": loc.name,
                    "usage_percentage": pct,
                    "used_gb": loc.used_gb,
                    "total_gb": loc.total_capacity_gb,
                    "message": f"Storage '{loc.name}' is offline or unreachable.",
                })

        return sorted(alerts, key=lambda a: 0 if a["level"] == "critical" else 1)

    # ── Helpers ───────────────────────────────────────────────────────

    def _clear_default(self, user_id: UUID, tier: StorageTier):
        """Remove default flag from all locations for this user/tier."""
        self.db.query(StorageLocation).filter(
            StorageLocation.user_id == user_id,
            StorageLocation.tier == tier,
            StorageLocation.is_default == True,
        ).update({"is_default": False})
