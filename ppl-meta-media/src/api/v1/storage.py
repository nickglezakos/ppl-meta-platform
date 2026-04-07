# Storage Management API Routes
# Provides REST endpoints for user storage preferences and configuration

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth import AuthUser, get_current_user
from ...database import get_db
from ...models.storage_location import LocationType, StorageTier
from ...schemas.storage import (
    CollectionStorageConfigResponse,
    StorageCleanupRequest,
    StorageCleanupResponse,
    StorageDashboardResponse,
    StorageLocationCreate,
    StorageLocationResponse,
    StorageLocationUpdate,
    StorageLocationVerifyResponse,
    StorageRecommendationResponse,
    StorageUsageSummaryResponse,
    UserStoragePreferencesResponse,
    UserStoragePreferencesUpdate,
)
from ...services.collection_storage_service import CollectionStorageConfigService
from ...services.storage_location_service import StorageLocationService
from ...services.user_storage_preferences_service import UserStoragePreferencesService

router = APIRouter(prefix="/users", tags=["storage"])


@router.get("/storage-preferences", response_model=UserStoragePreferencesResponse)
async def get_storage_preferences(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user storage preferences."""
    service = UserStoragePreferencesService(db)

    try:
        user_uuid = UUID(current_user.user_id)
        preferences = await service.get_user_preferences(user_uuid)
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage preferences: {str(e)}",
        )


@router.put("/storage-preferences", response_model=UserStoragePreferencesResponse)
async def update_storage_preferences(
    preferences_update: UserStoragePreferencesUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user storage preferences."""
    service = UserStoragePreferencesService(db)

    try:
        updated_preferences = await service.update_preferences(
            UUID(current_user.user_id), preferences_update
        )
        return updated_preferences
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update storage preferences: {str(e)}",
        )


@router.post(
    "/storage-preferences/reset", response_model=UserStoragePreferencesResponse
)
async def reset_storage_preferences(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Reset user storage preferences to defaults."""
    service = UserStoragePreferencesService(db)

    try:
        reset_preferences = await service.reset_to_defaults(UUID(current_user.user_id))
        return reset_preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset storage preferences: {str(e)}",
        )


@router.get("/storage-summary", response_model=StorageUsageSummaryResponse)
async def get_storage_summary(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user storage usage summary."""
    service = UserStoragePreferencesService(db)

    try:
        summary = await service.get_storage_usage_summary(UUID(current_user.user_id))
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage summary: {str(e)}",
        )


@router.get("/storage-recommendations")
async def get_storage_recommendations(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get intelligent storage size recommendations."""
    service = UserStoragePreferencesService(db)

    try:
        recommendations = await service.get_storage_recommendations(
            UUID(current_user.user_id)
        )
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage recommendations: {str(e)}",
        )


@router.get(
    "/collections/{collection_id}/storage-config",
    response_model=CollectionStorageConfigResponse,
)
async def get_collection_storage_config(
    collection_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get storage configuration for a specific collection."""
    service = CollectionStorageConfigService(db)

    try:
        config = await service.get_collection_config(
            collection_id, UUID(current_user.user_id)
        )
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection storage configuration not found",
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collection storage config: {str(e)}",
        )


@router.post("/collections/{collection_id}/initialize-storage")
async def initialize_collection_storage(
    collection_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initialize storage configuration for a collection using user preferences."""
    service = CollectionStorageConfigService(db)

    try:
        config = await service.initialize_collection_storage(
            collection_id, UUID(current_user.user_id)
        )
        return {
            "message": "Collection storage initialized successfully",
            "collection_id": collection_id,
            "storage_config": config,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize collection storage: {str(e)}",
        )


@router.post("/storage-cleanup", response_model=StorageCleanupResponse)
async def trigger_storage_cleanup(
    cleanup_request: StorageCleanupRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger storage cleanup operations."""
    service = UserStoragePreferencesService(db)

    try:
        result = await service.trigger_storage_cleanup(
            UUID(current_user.user_id), cleanup_request
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger storage cleanup: {str(e)}",
        )


@router.get("/storage-analytics")
async def get_storage_analytics(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed storage analytics for the user."""
    service = UserStoragePreferencesService(db)

    try:
        analytics = await service.get_storage_analytics(UUID(current_user.user_id))
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage analytics: {str(e)}",
        )


@router.get("/storage-health")
async def get_storage_health(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get storage health status and recommendations."""
    service = UserStoragePreferencesService(db)

    try:
        health_data = await service.get_storage_health_status(
            UUID(current_user.user_id)
        )
        return health_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage health: {str(e)}",
        )


@router.post("/collections/{collection_id}/optimize-storage")
async def optimize_collection_storage(
    collection_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply storage optimizations to a specific collection."""
    service = UserStoragePreferencesService(db)

    try:
        result = await service.optimize_collection_storage(
            collection_id, UUID(current_user.user_id)
        )
        return {
            "message": "Collection storage optimized successfully",
            "collection_id": collection_id,
            "optimizations_applied": result["optimizations"],
            "space_saved_gb": result["space_saved_gb"],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize collection storage: {str(e)}",
        )


@router.get("/storage-notifications")
async def get_storage_notifications(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current storage-related notifications for the user."""
    service = UserStoragePreferencesService(db)

    try:
        notifications = await service.get_storage_notifications(
            UUID(current_user.user_id)
        )
        return {"notifications": notifications}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage notifications: {str(e)}",
        )


@router.post("/storage-notifications/{notification_id}/dismiss")
async def dismiss_storage_notification(
    notification_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss a storage notification."""
    service = UserStoragePreferencesService(db)

    try:
        await service.dismiss_storage_notification(
            notification_id, UUID(current_user.user_id)
        )
        return {"message": "Notification dismissed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss notification: {str(e)}",
        )


# ── Storage Location Endpoints ───────────────────────────────────────


@router.get("/storage/locations", response_model=List[StorageLocationResponse])
async def list_storage_locations(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all storage locations for the current user."""
    service = StorageLocationService(db)
    locations = await service.list_locations(UUID(current_user.user_id))

    return [
        StorageLocationResponse(
            uuid=loc.uuid,
            user_id=loc.user_id,
            name=loc.name,
            location_type=loc.location_type.value,
            base_path=loc.base_path,
            tier=loc.tier.value,
            is_active=loc.is_active,
            is_default=loc.is_default,
            total_capacity_bytes=loc.total_capacity_bytes,
            used_bytes=loc.used_bytes,
            file_count=loc.file_count,
            usage_percentage=loc.usage_percentage,
            used_gb=loc.used_gb,
            total_capacity_gb=loc.total_capacity_gb,
            free_gb=loc.free_gb,
            mount_verified=loc.mount_verified,
            last_verified_at=loc.last_verified_at,
            created_at=loc.created_at,
            updated_at=loc.updated_at,
        )
        for loc in locations
    ]


@router.post("/storage/locations", response_model=StorageLocationResponse, status_code=201)
async def create_storage_location(
    body: StorageLocationCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new storage location."""
    service = StorageLocationService(db)

    try:
        location = await service.create_location(
            user_id=UUID(current_user.user_id),
            name=body.name,
            location_type=LocationType(body.location_type),
            base_path=body.base_path,
            tier=StorageTier(body.tier),
            is_default=body.is_default,
            cloud_config=body.cloud_config,
        )
        return StorageLocationResponse(
            uuid=location.uuid,
            user_id=location.user_id,
            name=location.name,
            location_type=location.location_type.value,
            base_path=location.base_path,
            tier=location.tier.value,
            is_active=location.is_active,
            is_default=location.is_default,
            total_capacity_bytes=location.total_capacity_bytes,
            used_bytes=location.used_bytes,
            file_count=location.file_count,
            usage_percentage=location.usage_percentage,
            used_gb=location.used_gb,
            total_capacity_gb=location.total_capacity_gb,
            free_gb=location.free_gb,
            mount_verified=location.mount_verified,
            last_verified_at=location.last_verified_at,
            created_at=location.created_at,
            updated_at=location.updated_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create storage location: {str(e)}",
        )


@router.get("/storage/locations/summary", response_model=StorageDashboardResponse)
async def get_storage_dashboard(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get full storage dashboard with all locations, usage, and alerts."""
    service = StorageLocationService(db)
    user_id = UUID(current_user.user_id)

    summary = await service.get_summary(user_id)
    alerts = await service.get_alerts(user_id)
    summary["alerts"] = alerts

    return StorageDashboardResponse(**summary)


@router.get("/storage/locations/{location_id}", response_model=StorageLocationResponse)
async def get_storage_location(
    location_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details for a single storage location."""
    service = StorageLocationService(db)
    location = await service.get_location(UUID(current_user.user_id), location_id)

    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")

    return StorageLocationResponse(
        uuid=location.uuid,
        user_id=location.user_id,
        name=location.name,
        location_type=location.location_type.value,
        base_path=location.base_path,
        tier=location.tier.value,
        is_active=location.is_active,
        is_default=location.is_default,
        total_capacity_bytes=location.total_capacity_bytes,
        used_bytes=location.used_bytes,
        file_count=location.file_count,
        usage_percentage=location.usage_percentage,
        used_gb=location.used_gb,
        total_capacity_gb=location.total_capacity_gb,
        free_gb=location.free_gb,
        mount_verified=location.mount_verified,
        last_verified_at=location.last_verified_at,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


@router.put("/storage/locations/{location_id}", response_model=StorageLocationResponse)
async def update_storage_location(
    location_id: UUID,
    body: StorageLocationUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a storage location."""
    service = StorageLocationService(db)
    updates = body.dict(exclude_unset=True)

    location = await service.update_location(
        UUID(current_user.user_id), location_id, updates
    )
    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")

    return StorageLocationResponse(
        uuid=location.uuid,
        user_id=location.user_id,
        name=location.name,
        location_type=location.location_type.value,
        base_path=location.base_path,
        tier=location.tier.value,
        is_active=location.is_active,
        is_default=location.is_default,
        total_capacity_bytes=location.total_capacity_bytes,
        used_bytes=location.used_bytes,
        file_count=location.file_count,
        usage_percentage=location.usage_percentage,
        used_gb=location.used_gb,
        total_capacity_gb=location.total_capacity_gb,
        free_gb=location.free_gb,
        mount_verified=location.mount_verified,
        last_verified_at=location.last_verified_at,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


@router.delete("/storage/locations/{location_id}")
async def delete_storage_location(
    location_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a storage location. Fails if files still reference it."""
    service = StorageLocationService(db)

    try:
        deleted = await service.delete_location(UUID(current_user.user_id), location_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Storage location not found")
        return {"message": "Storage location deleted"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/storage/locations/{location_id}/verify",
    response_model=StorageLocationVerifyResponse,
)
async def verify_storage_location(
    location_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a storage location is accessible and update capacity."""
    service = StorageLocationService(db)
    result = await service.verify_location(UUID(current_user.user_id), location_id)

    if "error" in result and result.get("error") == "Location not found":
        raise HTTPException(status_code=404, detail="Storage location not found")

    return StorageLocationVerifyResponse(**result)


@router.post("/storage/locations/{location_id}/set-default")
async def set_default_storage_location(
    location_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a storage location as the default for its tier."""
    service = StorageLocationService(db)
    location = await service.set_default(UUID(current_user.user_id), location_id)

    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")

    return {"message": f"'{location.name}' set as default {location.tier.value} location"}


@router.get("/storage/alerts")
async def get_storage_alerts(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get active storage alerts/warnings."""
    service = StorageLocationService(db)
    alerts = await service.get_alerts(UUID(current_user.user_id))
    return {"alerts": alerts}
