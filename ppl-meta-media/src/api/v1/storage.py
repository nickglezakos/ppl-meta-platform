# Storage Management API Routes
# Provides REST endpoints for user storage preferences and configuration

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth import AuthUser, get_current_user
from ...database import get_db
from ...schemas.storage import (
    CollectionStorageConfigResponse,
    StorageCleanupRequest,
    StorageCleanupResponse,
    StorageRecommendationResponse,
    StorageUsageSummaryResponse,
    UserStoragePreferencesResponse,
    UserStoragePreferencesUpdate,
)
from ...services.collection_storage_service import CollectionStorageConfigService
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
