"""
Camera settings endpoints for PPL Meta Cameras API.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.camera_settings import CameraSettings
from src.schemas.camera_settings import (
    CameraSettingsCreate,
    CameraSettingsResponse,
    CameraSettingsUpdate,
)
from src.security.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{device_id}/settings", response_model=CameraSettingsResponse)
async def get_camera_settings(
    device_id: str,
    user_id: str = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get camera settings for a specific user and camera."""
    try:
        # Use current user if user_id not provided
        target_user_id = user_id if user_id else current_user.get("user_id")

        # Query settings
        settings = (
            db.query(CameraSettings)
            .filter(
                CameraSettings.camera_device_id == device_id,
                CameraSettings.user_id == target_user_id,
            )
            .first()
        )

        if not settings:
            # Return default settings if none exist
            default_settings = CameraSettings(
                camera_device_id=device_id,
                user_id=target_user_id,
                auto_face_detection=False,
                detection_methods=["two_stage"],
                processing_options={},
                auto_recording=False,
                recording_duration=30,
                notifications_enabled=True,
                notification_methods=["email"],
                store_faces_in_memory=True,
                persist_after_recording=True,
            )
            db.add(default_settings)
            db.commit()
            db.refresh(default_settings)
            settings = default_settings

        return CameraSettingsResponse(**settings.to_dict())

    except Exception as e:
        logger.error(f"Error getting camera settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera settings: {str(e)}",
        )


@router.put("/{device_id}/settings", response_model=CameraSettingsResponse)
async def update_camera_settings(
    device_id: str,
    settings_update: CameraSettingsUpdate,
    user_id: str = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update camera settings for a specific user and camera."""
    try:
        # Use current user if user_id not provided
        target_user_id = user_id if user_id else current_user.get("user_id")

        # Get existing settings or create new ones
        settings = (
            db.query(CameraSettings)
            .filter(
                CameraSettings.camera_device_id == device_id,
                CameraSettings.user_id == target_user_id,
            )
            .first()
        )

        if not settings:
            # Create new settings if none exist
            settings = CameraSettings(
                camera_device_id=device_id,
                user_id=target_user_id,
            )
            db.add(settings)

        # Update fields that are provided
        update_data = settings_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        db.commit()
        db.refresh(settings)

        logger.info(
            f"Updated camera settings for device {device_id}, user {target_user_id}"
        )

        return CameraSettingsResponse(**settings.to_dict())

    except Exception as e:
        logger.error(f"Error updating camera settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update camera settings: {str(e)}",
        )


@router.post("/{device_id}/settings", response_model=CameraSettingsResponse)
async def create_camera_settings(
    device_id: str,
    settings_create: CameraSettingsCreate,
    user_id: str = None,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create camera settings for a specific user and camera."""
    try:
        # Use current user if user_id not provided
        target_user_id = user_id if user_id else current_user.get("user_id")

        # Check if settings already exist
        existing_settings = (
            db.query(CameraSettings)
            .filter(
                CameraSettings.camera_device_id == device_id,
                CameraSettings.user_id == target_user_id,
            )
            .first()
        )

        if existing_settings:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Camera settings already exist for this user and camera",
            )

        # Create new settings
        settings = CameraSettings(
            camera_device_id=device_id,
            user_id=target_user_id,
            **settings_create.dict(),
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

        logger.info(
            f"Created camera settings for device {device_id}, user {target_user_id}"
        )

        return CameraSettingsResponse(**settings.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating camera settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create camera settings: {str(e)}",
        )
