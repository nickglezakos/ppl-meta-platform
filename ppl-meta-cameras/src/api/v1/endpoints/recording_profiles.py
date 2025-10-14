# ppl-meta-cameras/src/api/v1/endpoints/recording_profiles.py

"""
Recording Profile API Endpoints
CRUD operations for camera recording profiles
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.database import get_db
from src.security.auth import get_current_user
from src.services.recording_profile_service import RecordingProfileService

router = APIRouter(prefix="/recording-profiles", tags=["recording-profiles"])


# Pydantic models for request/response
class RecordingProfileCreate(BaseModel):
    """Request model for creating a new recording profile."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    segment_interval_seconds: Optional[int] = Field(None, ge=5, le=3600)
    segment_duration_seconds: int = Field(30, ge=5, le=300)
    auto_segment_recording: bool = Field(False)
    recording_quality: str = Field("high", regex="^(low|medium|high)$")
    video_codec: str = Field("h264", regex="^(h264|h265|vp8|vp9)$")
    audio_enabled: bool = Field(False)
    auto_face_detection_enabled: bool = Field(True)
    face_detection_method: str = Field(
        "two_stage", regex="^(single_stage|two_stage|cascade)$"
    )
    enable_motion_detection: bool = Field(False)
    storage_location: str = Field("local", regex="^(local|s3|gcs|azure)$")
    retention_days: int = Field(30, ge=1, le=365)
    auto_cleanup_enabled: bool = Field(True)


class RecordingProfileUpdate(BaseModel):
    """Request model for updating a recording profile."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    segment_interval_seconds: Optional[int] = Field(None, ge=5, le=3600)
    segment_duration_seconds: Optional[int] = Field(None, ge=5, le=300)
    auto_segment_recording: Optional[bool] = None
    recording_quality: Optional[str] = Field(None, regex="^(low|medium|high)$")
    video_codec: Optional[str] = Field(None, regex="^(h264|h265|vp8|vp9)$")
    audio_enabled: Optional[bool] = None
    auto_face_detection_enabled: Optional[bool] = None
    face_detection_method: Optional[str] = Field(
        None, regex="^(single_stage|two_stage|cascade)$"
    )
    enable_motion_detection: Optional[bool] = None
    storage_location: Optional[str] = Field(None, regex="^(local|s3|gcs|azure)$")
    retention_days: Optional[int] = Field(None, ge=1, le=365)
    auto_cleanup_enabled: Optional[bool] = None


class RecordingProfileResponse(BaseModel):
    """Response model for recording profile data."""

    id: int
    profile_uuid: str
    name: str
    description: Optional[str]
    is_system_default: bool
    is_active: bool
    created_by_user_id: str
    configuration: Dict[str, Any]
    usage_count: int
    last_used_at: Optional[str]
    created_at: str
    updated_at: str


class CameraAssignmentRequest(BaseModel):
    """Request model for assigning profile to camera."""

    camera_id: int = Field(..., gt=0)


@router.post(
    "/", response_model=RecordingProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_recording_profile(
    profile_data: RecordingProfileCreate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingProfileResponse:
    """Create a new recording profile."""

    service = RecordingProfileService(db)

    try:
        profile = await service.create_profile(
            name=profile_data.name,
            created_by_user_id=current_user.get("sub"),
            description=profile_data.description,
            **profile_data.dict(exclude={"name", "description"})
        )

        return RecordingProfileResponse(**profile.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[RecordingProfileResponse])
async def get_recording_profiles(
    include_system_defaults: bool = Query(
        True, description="Include system default profiles"
    ),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecordingProfileResponse]:
    """Get all recording profiles accessible to the current user."""

    service = RecordingProfileService(db)

    profiles = await service.get_user_profiles(
        user_id=current_user.get("sub"), include_system_defaults=include_system_defaults
    )

    return [RecordingProfileResponse(**profile.to_dict()) for profile in profiles]


@router.get("/system-defaults", response_model=List[RecordingProfileResponse])
async def get_system_default_profiles(
    db: Session = Depends(get_db),
) -> List[RecordingProfileResponse]:
    """Get all system default recording profiles."""

    service = RecordingProfileService(db)
    profiles = await service.get_system_default_profiles()

    return [RecordingProfileResponse(**profile.to_dict()) for profile in profiles]


@router.get("/search", response_model=List[RecordingProfileResponse])
async def search_recording_profiles(
    q: str = Query(..., min_length=1, description="Search query"),
    include_system_defaults: bool = Query(
        True, description="Include system default profiles"
    ),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecordingProfileResponse]:
    """Search recording profiles by name or description."""

    service = RecordingProfileService(db)

    profiles = await service.search_profiles(
        user_id=current_user.get("sub"),
        query=q,
        include_system_defaults=include_system_defaults,
    )

    return [RecordingProfileResponse(**profile.to_dict()) for profile in profiles]


@router.get("/{profile_id}", response_model=RecordingProfileResponse)
async def get_recording_profile(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingProfileResponse:
    """Get a specific recording profile by ID."""

    service = RecordingProfileService(db)
    profile = await service.get_profile_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording profile not found"
        )

    # Check if user has access to this profile
    user_profiles = await service.get_user_profiles(current_user.get("sub"))
    if profile not in user_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this recording profile",
        )

    return RecordingProfileResponse(**profile.to_dict())


@router.put("/{profile_id}", response_model=RecordingProfileResponse)
async def update_recording_profile(
    profile_id: int,
    updates: RecordingProfileUpdate,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingProfileResponse:
    """Update a recording profile."""

    service = RecordingProfileService(db)

    try:
        # Filter out None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}

        profile = await service.update_profile(
            profile_id=profile_id, user_id=current_user.get("sub"), updates=update_data
        )

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording profile not found or access denied",
            )

        return RecordingProfileResponse(**profile.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recording_profile(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a recording profile."""

    service = RecordingProfileService(db)

    success = await service.delete_profile(
        profile_id=profile_id, user_id=current_user.get("sub")
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording profile not found, access denied, or profile is in use",
        )


@router.post(
    "/{profile_id}/clone",
    response_model=RecordingProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_recording_profile(
    profile_id: int,
    new_name: str = Query(..., min_length=1, max_length=100),
    description: Optional[str] = Query(None, max_length=500),
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingProfileResponse:
    """Clone an existing recording profile."""

    service = RecordingProfileService(db)

    cloned_profile = await service.clone_profile(
        source_profile_id=profile_id,
        new_name=new_name,
        user_id=current_user.get("sub"),
        description=description,
    )

    if not cloned_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source recording profile not found",
        )

    return RecordingProfileResponse(**cloned_profile.to_dict())


@router.post("/{profile_id}/assign", status_code=status.HTTP_200_OK)
async def assign_profile_to_camera(
    profile_id: int,
    assignment: CameraAssignmentRequest,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Assign a recording profile to a camera."""

    service = RecordingProfileService(db)

    success = await service.assign_profile_to_camera(
        camera_id=assignment.camera_id,
        profile_id=profile_id,
        user_id=current_user.get("sub"),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign profile: profile not found, camera not found, or access denied",
        )

    return {"message": "Profile assigned to camera successfully"}


@router.delete("/{profile_id}/assign/{camera_id}", status_code=status.HTTP_200_OK)
async def remove_profile_from_camera(
    profile_id: int,
    camera_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Remove profile assignment from a camera."""

    service = RecordingProfileService(db)

    success = await service.remove_profile_from_camera(camera_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    return {"message": "Profile assignment removed from camera"}


@router.get("/{profile_id}/cameras", response_model=List[Dict[str, Any]])
async def get_cameras_using_profile(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get list of cameras using a specific recording profile."""

    service = RecordingProfileService(db)

    # Verify user has access to this profile
    profile = await service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording profile not found"
        )

    user_profiles = await service.get_user_profiles(current_user.get("sub"))
    if profile not in user_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this recording profile",
        )

    cameras = await service.get_cameras_using_profile(profile_id)
    return cameras


@router.get("/{profile_id}/usage", response_model=Dict[str, Any])
async def get_profile_usage_statistics(
    profile_id: int,
    current_user: Dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get usage statistics for a recording profile."""

    service = RecordingProfileService(db)

    # Verify user has access to this profile
    profile = await service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording profile not found"
        )

    user_profiles = await service.get_user_profiles(current_user.get("sub"))
    if profile not in user_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this recording profile",
        )

    usage_stats = await service.get_profile_usage_statistics(profile_id)
    return usage_stats
