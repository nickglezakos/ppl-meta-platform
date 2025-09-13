# Default Collection Size Assignment Service
# Automatically applies user storage preferences when creating new collections

import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..models.collection_storage import CollectionStorageConfig, UserStoragePreferences
from ..models.media import MediaCollection
from ..services.user_storage_preferences_service import UserStoragePreferencesService

logger = logging.getLogger(__name__)


class DefaultCollectionAssignmentService:
    """Service for automatically assigning storage configurations to new collections."""

    def __init__(self, db: Session):
        self.db = db
        self.preferences_service = UserStoragePreferencesService(db)

    async def assign_default_storage_to_collection(
        self,
        collection_id: str,
        user_uuid: str,
        override_size_gb: Optional[float] = None,
    ) -> CollectionStorageConfig:
        """
        Automatically assign storage configuration to a new collection
        based on user preferences.

        Args:
            collection_id: UUID of the collection to configure
            user_uuid: UUID of the user who owns the collection
            override_size_gb: Optional override for the default size

        Returns:
            CollectionStorageConfig: The created storage configuration

        Raises:
            ValueError: If collection doesn't exist or already has storage config
        """

        # Verify collection exists
        collection = (
            self.db.query(MediaCollection)
            .filter(MediaCollection.collection_id == collection_id)
            .first()
        )

        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        # Check if storage config already exists
        existing_config = (
            self.db.query(CollectionStorageConfig)
            .filter(CollectionStorageConfig.collection_id == collection_id)
            .first()
        )

        if existing_config:
            logger.warning(
                f"Collection {collection_id} already has storage configuration"
            )
            return existing_config

        # Get user preferences
        try:
            preferences = await self.preferences_service.get_user_preferences(user_uuid)
        except Exception as e:
            logger.warning(
                f"Failed to load user preferences for {user_uuid}, using defaults: {e}"
            )
            # Create default preferences if none exist
            preferences = await self.preferences_service._create_default_preferences(
                user_uuid
            )

        # Determine collection size
        collection_size_gb = override_size_gb or preferences.default_collection_size_gb

        # Calculate storage distribution
        live_storage_gb = collection_size_gb * (
            preferences.default_live_portion_percentage / 100
        )
        archive_storage_gb = collection_size_gb - live_storage_gb

        # Create storage configuration
        storage_config = CollectionStorageConfig(
            collection_id=collection_id,
            total_size_gb=collection_size_gb,
            live_storage_gb=live_storage_gb,
            archive_storage_gb=archive_storage_gb,
            auto_archive_enabled=preferences.default_auto_archive_enabled,
            min_age_for_archive_days=preferences.default_min_age_for_archive_days,
            video_quality=preferences.preferred_video_quality,
            compression_enabled=preferences.preferred_compression_enabled,
        )

        self.db.add(storage_config)
        self.db.commit()
        self.db.refresh(storage_config)

        logger.info(
            f"Assigned default storage configuration to collection {collection_id}: "
            f"{collection_size_gb}GB total ({live_storage_gb:.1f}GB live, "
            f"{archive_storage_gb:.1f}GB archive)"
        )

        return storage_config

    async def bulk_assign_storage_to_collections(
        self,
        user_uuid: str,
        collection_ids: list[str],
        override_size_gb: Optional[float] = None,
    ) -> list[CollectionStorageConfig]:
        """
        Assign storage configurations to multiple collections in bulk.

        Args:
            user_uuid: UUID of the user who owns the collections
            collection_ids: List of collection UUIDs to configure
            override_size_gb: Optional override for the default size

        Returns:
            list[CollectionStorageConfig]: List of created storage configurations
        """

        results = []

        for collection_id in collection_ids:
            try:
                config = await self.assign_default_storage_to_collection(
                    collection_id, user_uuid, override_size_gb
                )
                results.append(config)
            except Exception as e:
                logger.error(
                    f"Failed to assign storage to collection {collection_id}: {e}"
                )
                continue

        logger.info(
            f"Bulk assigned storage to {len(results)}/{len(collection_ids)} collections "
            f"for user {user_uuid}"
        )

        return results

    async def update_collection_storage_from_preferences(
        self, collection_id: str, user_uuid: str
    ) -> CollectionStorageConfig:
        """
        Update an existing collection's storage configuration based on
        current user preferences.

        Args:
            collection_id: UUID of the collection to update
            user_uuid: UUID of the user who owns the collection

        Returns:
            CollectionStorageConfig: The updated storage configuration

        Raises:
            ValueError: If collection or storage config doesn't exist
        """

        # Get existing storage config
        storage_config = (
            self.db.query(CollectionStorageConfig)
            .filter(CollectionStorageConfig.collection_id == collection_id)
            .first()
        )

        if not storage_config:
            raise ValueError(
                f"Storage configuration not found for collection {collection_id}"
            )

        # Get current preferences
        preferences = await self.preferences_service.get_user_preferences(user_uuid)

        # Calculate new storage distribution based on current total size
        current_total = storage_config.total_size_gb
        new_live_storage_gb = current_total * (
            preferences.default_live_portion_percentage / 100
        )
        new_archive_storage_gb = current_total - new_live_storage_gb

        # Update configuration
        storage_config.live_storage_gb = new_live_storage_gb
        storage_config.archive_storage_gb = new_archive_storage_gb
        storage_config.auto_archive_enabled = preferences.default_auto_archive_enabled
        storage_config.min_age_for_archive_days = (
            preferences.default_min_age_for_archive_days
        )
        storage_config.video_quality = preferences.preferred_video_quality
        storage_config.compression_enabled = preferences.preferred_compression_enabled

        self.db.commit()
        self.db.refresh(storage_config)

        logger.info(
            f"Updated storage configuration for collection {collection_id} "
            f"based on user preferences"
        )

        return storage_config

    async def auto_assign_storage_to_unconfigured_collections(
        self, user_uuid: str
    ) -> list[CollectionStorageConfig]:
        """
        Find all collections owned by a user that don't have storage
        configurations and assign them based on user preferences.

        Args:
            user_uuid: UUID of the user

        Returns:
            list[CollectionStorageConfig]: List of newly created storage configurations
        """

        # Find collections without storage configurations
        unconfigured_collections = (
            self.db.query(MediaCollection)
            .outerjoin(
                CollectionStorageConfig,
                MediaCollection.collection_id == CollectionStorageConfig.collection_id,
            )
            .filter(
                MediaCollection.user_uuid == user_uuid,
                CollectionStorageConfig.id.is_(None),
            )
            .all()
        )

        if not unconfigured_collections:
            logger.info(f"No unconfigured collections found for user {user_uuid}")
            return []

        collection_ids = [
            collection.collection_id for collection in unconfigured_collections
        ]

        logger.info(
            f"Found {len(collection_ids)} unconfigured collections for user {user_uuid}"
        )

        return await self.bulk_assign_storage_to_collections(user_uuid, collection_ids)

    async def apply_new_preferences_to_existing_collections(
        self, user_uuid: str, apply_to_all: bool = False
    ) -> dict:
        """
        Apply updated user preferences to existing collections.

        Args:
            user_uuid: UUID of the user
            apply_to_all: If True, apply to all collections. If False, only apply to
                         collections that are not at capacity

        Returns:
            dict: Summary of operations performed
        """

        # Get all user collections with storage configurations
        collections_with_storage = (
            self.db.query(CollectionStorageConfig)
            .join(
                MediaCollection,
                CollectionStorageConfig.collection_id == MediaCollection.collection_id,
            )
            .filter(MediaCollection.user_uuid == user_uuid)
            .all()
        )

        if not collections_with_storage:
            return {
                "collections_processed": 0,
                "collections_updated": 0,
                "collections_skipped": 0,
                "message": "No collections with storage configurations found",
            }

        updated_count = 0
        skipped_count = 0

        for storage_config in collections_with_storage:
            try:
                # Skip collections at high capacity unless apply_to_all is True
                if not apply_to_all:
                    usage_percentage = storage_config.usage_percentage
                    if usage_percentage > 85.0:
                        skipped_count += 1
                        logger.info(
                            f"Skipping collection {storage_config.collection_id} "
                            f"(usage: {usage_percentage:.1f}%)"
                        )
                        continue

                await self.update_collection_storage_from_preferences(
                    storage_config.collection_id, user_uuid
                )
                updated_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to update collection {storage_config.collection_id}: {e}"
                )
                skipped_count += 1

        return {
            "collections_processed": len(collections_with_storage),
            "collections_updated": updated_count,
            "collections_skipped": skipped_count,
            "message": f"Updated {updated_count} collections with new preferences",
        }

    async def migrate_legacy_collections_to_storage_system(
        self, user_uuid: str
    ) -> dict:
        """
        Migrate existing collections that were created before the storage
        management system to use the new storage configuration system.

        Args:
            user_uuid: UUID of the user

        Returns:
            dict: Summary of migration operations
        """

        # Auto-assign storage to unconfigured collections
        new_configs = await self.auto_assign_storage_to_unconfigured_collections(
            user_uuid
        )

        result = {
            "migrated_collections": len(new_configs),
            "collection_ids": [config.collection_id for config in new_configs],
            "message": f"Successfully migrated {len(new_configs)} collections to storage system",
        }

        logger.info(f"Migration complete for user {user_uuid}: {result}")

        return result
