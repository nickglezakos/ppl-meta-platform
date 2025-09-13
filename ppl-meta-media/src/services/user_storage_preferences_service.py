"""
User Storage Preferences Service

Manages user-specific storage preferences, default settings, and collection configuration.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.models.collection_storage import (
    CollectionStorageConfig,
    CollectionStorageUsage,
    UserStoragePreferences,
)
from src.models.media import MediaCollection
from src.schemas.storage import (
    UserStoragePreferencesCreate,
    UserStoragePreferencesResponse,
    UserStoragePreferencesUpdate,
)


class UserStoragePreferencesService:
    """Service for managing user storage preferences."""

    def __init__(self, db: Session):
        self.db = db

    async def get_user_preferences(
        self, user_id: UUID
    ) -> Optional[UserStoragePreferences]:
        """Get user storage preferences, creating defaults if none exist."""
        preferences = (
            self.db.query(UserStoragePreferences)
            .filter(UserStoragePreferences.user_id == user_id)
            .first()
        )

        if not preferences:
            preferences = await self.create_default_preferences(user_id)

        return preferences

    async def create_default_preferences(self, user_id: UUID) -> UserStoragePreferences:
        """Create default storage preferences for a new user."""
        default_prefs = UserStoragePreferences.get_default_preferences()
        default_prefs["user_id"] = user_id

        preferences = UserStoragePreferences(**default_prefs)

        try:
            self.db.add(preferences)
            self.db.commit()
            self.db.refresh(preferences)
            return preferences
        except IntegrityError:
            self.db.rollback()
            # User preferences already exist, fetch them
            return (
                self.db.query(UserStoragePreferences)
                .filter(UserStoragePreferences.user_id == user_id)
                .first()
            )

    async def update_preferences(
        self, user_id: UUID, preferences_update: UserStoragePreferencesUpdate
    ) -> UserStoragePreferences:
        """Update user storage preferences."""
        preferences = await self.get_user_preferences(user_id)

        # Update fields that were provided
        update_data = preferences_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)

        self.db.commit()
        self.db.refresh(preferences)
        return preferences

    async def get_preferences_dict(self, user_id: UUID) -> Dict[str, Any]:
        """Get user preferences as a dictionary."""
        preferences = await self.get_user_preferences(user_id)
        return preferences.to_dict() if preferences else {}

    async def initialize_collection_storage(
        self,
        collection_id: int,
        user_id: UUID,
        override_settings: Optional[Dict[str, Any]] = None,
    ) -> CollectionStorageConfig:
        """Initialize storage configuration for a new collection using user preferences."""

        # Get user preferences
        user_prefs = await self.get_user_preferences(user_id)

        # Create storage configuration
        config_data = {
            "collection_id": collection_id,
            "total_size_gb": user_prefs.default_collection_size_gb,
            "live_portion_percentage": user_prefs.default_live_portion_percentage,
            "archive_portion_percentage": 100
            - user_prefs.default_live_portion_percentage,
            "auto_archive_enabled": user_prefs.default_auto_archive_enabled,
            "min_age_for_archive_days": user_prefs.default_min_age_for_archive_days,
            "warning_threshold_percentage": user_prefs.notification_threshold_percentage,
            "auto_delete_enabled": user_prefs.auto_delete_old_archives_enabled,
            "auto_delete_after_days": user_prefs.auto_delete_after_days,
        }

        # Apply any override settings
        if override_settings:
            config_data.update(override_settings)

        storage_config = CollectionStorageConfig(**config_data)
        self.db.add(storage_config)

        # Create usage tracking
        storage_usage = CollectionStorageUsage(collection_id=collection_id)
        self.db.add(storage_usage)

        self.db.commit()
        self.db.refresh(storage_config)

        return storage_config

    async def apply_preferences_to_existing_collections(self, user_id: UUID) -> int:
        """Apply current user preferences to existing collections they own."""
        user_prefs = await self.get_user_preferences(user_id)

        # Get user's collections that don't have storage config
        collections = (
            self.db.query(MediaCollection)
            .filter(MediaCollection.created_by == user_id)
            .all()
        )

        collections_updated = 0

        for collection in collections:
            # Check if storage config already exists
            existing_config = (
                self.db.query(CollectionStorageConfig)
                .filter(CollectionStorageConfig.collection_id == collection.id)
                .first()
            )

            if not existing_config:
                await self.initialize_collection_storage(collection.id, user_id)
                collections_updated += 1
            else:
                # Update existing config with current user preferences
                existing_config.warning_threshold_percentage = (
                    user_prefs.notification_threshold_percentage
                )
                existing_config.auto_delete_enabled = (
                    user_prefs.auto_delete_old_archives_enabled
                )
                existing_config.auto_delete_after_days = (
                    user_prefs.auto_delete_after_days
                )
                collections_updated += 1

        if collections_updated > 0:
            self.db.commit()

        return collections_updated

    async def get_collection_size_recommendation(
        self, user_id: UUID, camera_type: str = "mobile"
    ) -> Dict[str, float]:
        """Get recommended collection size based on user preferences and camera type."""
        user_prefs = await self.get_user_preferences(user_id)

        base_size = user_prefs.default_collection_size_gb

        # Adjust recommendations based on camera type
        size_multipliers = {
            "mobile": 0.8,  # Mobile cameras typically have lower quality
            "usb": 1.0,  # Standard definition
            "rtsp": 1.5,  # Often higher quality IP cameras
            "professional": 2.0,  # High-end cameras
        }

        multiplier = size_multipliers.get(camera_type.lower(), 1.0)
        recommended_size = base_size * multiplier

        return {
            "recommended_total_gb": recommended_size,
            "recommended_live_gb": recommended_size
            * (user_prefs.default_live_portion_percentage / 100),
            "recommended_archive_gb": recommended_size
            * ((100 - user_prefs.default_live_portion_percentage) / 100),
            "camera_type": camera_type,
            "base_user_preference": base_size,
            "adjustment_multiplier": multiplier,
        }

    async def validate_storage_settings(
        self, preferences: UserStoragePreferencesUpdate
    ) -> Dict[str, Any]:
        """Validate storage preference settings and return any warnings or errors."""
        warnings = []
        errors = []

        # Validate size settings
        if (
            hasattr(preferences, "default_collection_size_gb")
            and preferences.default_collection_size_gb
        ):
            if preferences.default_collection_size_gb < 1.0:
                errors.append("Collection size must be at least 1GB")
            elif preferences.default_collection_size_gb > 1000.0:
                warnings.append("Collection size over 1TB may impact performance")

        # Validate live portion percentage
        if (
            hasattr(preferences, "default_live_portion_percentage")
            and preferences.default_live_portion_percentage
        ):
            if preferences.default_live_portion_percentage < 10.0:
                errors.append("Live portion must be at least 10%")
            elif preferences.default_live_portion_percentage > 95.0:
                errors.append("Live portion cannot exceed 95%")
            elif preferences.default_live_portion_percentage < 50.0:
                warnings.append(
                    "Low live portion may limit immediate access to recordings"
                )

        # Validate notification threshold
        if (
            hasattr(preferences, "notification_threshold_percentage")
            and preferences.notification_threshold_percentage
        ):
            if preferences.notification_threshold_percentage < 50.0:
                warnings.append(
                    "Low notification threshold may result in frequent alerts"
                )
            elif preferences.notification_threshold_percentage > 98.0:
                warnings.append(
                    "High notification threshold may not provide enough time for cleanup"
                )

        # Validate auto-delete settings
        if (
            hasattr(preferences, "auto_delete_after_days")
            and preferences.auto_delete_after_days
        ):
            if preferences.auto_delete_after_days < 30:
                warnings.append(
                    "Auto-delete period less than 30 days is not recommended"
                )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    async def get_storage_usage_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get summary of storage usage across all user collections."""
        collections = (
            self.db.query(MediaCollection)
            .filter(MediaCollection.created_by == user_id)
            .all()
        )

        total_collections = len(collections)
        total_allocated_gb = 0.0
        total_used_gb = 0.0
        collections_near_capacity = 0
        collections_at_capacity = 0

        for collection in collections:
            if collection.storage_config:
                total_allocated_gb += collection.storage_config.total_size_gb

            if collection.storage_usage:
                total_used_gb += collection.storage_usage.total_used_gb
                if collection.storage_usage.is_near_capacity:
                    collections_near_capacity += 1
                if collection.storage_usage.is_at_capacity:
                    collections_at_capacity += 1

        usage_percentage = (
            (total_used_gb / total_allocated_gb * 100) if total_allocated_gb > 0 else 0
        )

        return {
            "total_collections": total_collections,
            "total_allocated_gb": round(total_allocated_gb, 2),
            "total_used_gb": round(total_used_gb, 2),
            "usage_percentage": round(usage_percentage, 1),
            "collections_near_capacity": collections_near_capacity,
            "collections_at_capacity": collections_at_capacity,
            "efficiency_score": self._calculate_efficiency_score(collections),
        }

    def _calculate_efficiency_score(self, collections) -> float:
        """Calculate storage efficiency score (0-100) based on usage patterns."""
        if not collections:
            return 100.0

        scores = []
        for collection in collections:
            if collection.storage_config and collection.storage_usage:
                config = collection.storage_config
                usage = collection.storage_usage

                # Calculate utilization score
                utilization = usage.calculate_usage_percentage(
                    config.total_capacity_bytes
                )

                # Optimal utilization is around 70-85%
                if 70 <= utilization <= 85:
                    util_score = 100
                elif utilization < 70:
                    util_score = utilization / 70 * 100
                else:  # utilization > 85
                    util_score = max(0, 100 - (utilization - 85) * 2)

                # Factor in live vs archive balance
                live_percentage = usage.calculate_live_usage_percentage(
                    config.live_capacity_bytes
                )
                archive_percentage = (
                    usage.archive_portion_used_bytes
                    / config.archive_capacity_bytes
                    * 100
                    if config.archive_capacity_bytes > 0
                    else 0
                )

                balance_score = 100 - abs(live_percentage - archive_percentage)

                # Combined score
                collection_score = (util_score * 0.7) + (balance_score * 0.3)
                scores.append(collection_score)

        return round(sum(scores) / len(scores), 1) if scores else 100.0

    async def reset_to_defaults(self, user_id: UUID) -> UserStoragePreferences:
        """Reset user storage preferences to default values."""
        preferences = await self.get_user_preferences(user_id)

        # Get default preferences
        defaults = UserStoragePreferences.get_default_preferences()

        # Update current preferences with defaults (excluding user_id)
        for field, value in defaults.items():
            if field != "user_id" and hasattr(preferences, field):
                setattr(preferences, field, value)

        self.db.commit()
        self.db.refresh(preferences)
        return preferences

    async def get_storage_recommendations(self, user_id: UUID) -> list:
        """Get storage optimization recommendations for user."""
        summary = await self.get_storage_usage_summary(user_id)
        recommendations = []

        if summary["usage_percentage"] > 90:
            recommendations.append(
                {
                    "type": "critical_storage",
                    "message": "Storage usage is critically high",
                    "action": "Consider increasing storage quotas or cleaning up old files",
                }
            )
        elif summary["usage_percentage"] > 80:
            recommendations.append(
                {
                    "type": "warning_storage",
                    "message": "Storage usage is approaching limits",
                    "action": "Review and archive old recordings",
                }
            )

        if summary["collections_at_capacity"] > 0:
            recommendations.append(
                {
                    "type": "collection_full",
                    "message": f"{summary['collections_at_capacity']} collections are at capacity",
                    "action": "Expand storage or enable auto-archival",
                }
            )

        if summary["efficiency_score"] < 70:
            recommendations.append(
                {
                    "type": "efficiency_low",
                    "message": "Storage efficiency could be improved",
                    "action": "Optimize live/archive balance in collection settings",
                }
            )

        return recommendations
