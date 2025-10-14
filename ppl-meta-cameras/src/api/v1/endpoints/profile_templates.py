# ppl-meta-cameras/src/api/v1/endpoints/profile_templates.py

"""
Profile Template API Endpoints
REST API for managing user profile templates with CRUD operations,
search functionality, and template sharing capabilities
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from services.profile_storage_service import (
    ProfileStorageService,
    TemplateSearchFilters,
)
from services.template_import_export_service import TemplateImportExportService
from sqlalchemy.orm import Session

from utils.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile-templates", tags=["profile-templates"])


# Pydantic Models for Request/Response


class TemplateConfigurationRequest(BaseModel):
    """Template configuration request model."""

    # Recording Quality Settings
    quality: str = Field(default="high", description="Recording quality")
    format: str = Field(default="mp4", description="Video format")
    resolution: str = Field(default="1920x1080", description="Video resolution")
    frame_rate: int = Field(default=30, description="Frame rate")
    bitrate_kbps: int = Field(default=5000, description="Video bitrate in kbps")

    # Duration and Timing
    default_duration_seconds: int = Field(
        default=30, description="Default recording duration"
    )
    max_duration_seconds: int = Field(
        default=3600, description="Maximum recording duration"
    )
    segment_interval_seconds: Optional[int] = Field(
        None, description="Segment interval"
    )

    # Automatic Recording Settings
    enable_auto_recording: bool = Field(
        default=False, description="Enable automatic recording"
    )
    auto_recording_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Auto recording schedule"
    )
    motion_detection_enabled: bool = Field(
        default=False, description="Enable motion detection"
    )
    motion_sensitivity: str = Field(
        default="medium", description="Motion detection sensitivity"
    )

    # Audio Settings
    enable_audio: bool = Field(default=True, description="Enable audio recording")
    audio_quality: str = Field(default="medium", description="Audio quality")
    audio_bitrate_kbps: int = Field(default=128, description="Audio bitrate in kbps")

    # Storage and Retention
    storage_location: str = Field(default="default", description="Storage location")
    retention_days: int = Field(default=30, description="Retention period in days")
    auto_delete_enabled: bool = Field(
        default=True, description="Enable automatic deletion"
    )
    compression_enabled: bool = Field(default=True, description="Enable compression")

    # Processing Settings
    enable_face_detection: bool = Field(
        default=False, description="Enable face detection"
    )
    enable_object_detection: bool = Field(
        default=False, description="Enable object detection"
    )
    processing_priority: str = Field(
        default="normal", description="Processing priority"
    )

    # Advanced Configuration
    custom_ffmpeg_params: Optional[Dict[str, Any]] = Field(
        None, description="Custom FFmpeg parameters"
    )
    metadata_config: Optional[Dict[str, Any]] = Field(
        None, description="Metadata configuration"
    )
    notification_config: Optional[Dict[str, Any]] = Field(
        None, description="Notification configuration"
    )

    @validator("quality")
    def validate_quality(cls, v):
        if v not in ["low", "medium", "high", "ultra"]:
            raise ValueError("Quality must be one of: low, medium, high, ultra")
        return v

    @validator("format")
    def validate_format(cls, v):
        if v not in ["mp4", "avi", "mkv", "webm"]:
            raise ValueError("Format must be one of: mp4, avi, mkv, webm")
        return v

    @validator("motion_sensitivity")
    def validate_motion_sensitivity(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError("Motion sensitivity must be one of: low, medium, high")
        return v

    @validator("audio_quality")
    def validate_audio_quality(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError("Audio quality must be one of: low, medium, high")
        return v

    @validator("processing_priority")
    def validate_processing_priority(cls, v):
        if v not in ["low", "normal", "high"]:
            raise ValueError("Processing priority must be one of: low, normal, high")
        return v


class CreateTemplateRequest(BaseModel):
    """Request model for creating a new template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Template description"
    )
    category: Optional[str] = Field(
        None, max_length=50, description="Template category"
    )
    tags: Optional[List[str]] = Field(default_factory=list, description="Template tags")
    is_public: bool = Field(
        default=False, description="Make template publicly shareable"
    )
    configuration: TemplateConfigurationRequest = Field(
        ..., description="Template configuration"
    )


class UpdateTemplateRequest(BaseModel):
    """Request model for updating a template."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Template name"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Template description"
    )
    category: Optional[str] = Field(
        None, max_length=50, description="Template category"
    )
    tags: Optional[List[str]] = Field(None, description="Template tags")
    is_public: Optional[bool] = Field(
        None, description="Make template publicly shareable"
    )
    configuration: Optional[TemplateConfigurationRequest] = Field(
        None, description="Template configuration"
    )


class CloneTemplateRequest(BaseModel):
    """Request model for cloning a template."""

    new_name: str = Field(
        ..., min_length=1, max_length=100, description="Name for cloned template"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Description for cloned template"
    )


class ApplyTemplateRequest(BaseModel):
    """Request model for applying a template to create a profile."""

    profile_name: str = Field(
        ..., min_length=1, max_length=100, description="Name for new profile"
    )
    camera_id: Optional[str] = Field(None, description="Camera ID context")


class TemplateResponse(BaseModel):
    """Template response model."""

    id: int
    template_uuid: str
    name: str
    description: Optional[str]
    category: Optional[str]
    tags: List[str]
    configuration: Dict[str, Any]
    metadata: Dict[str, Any]
    usage_stats: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


class TemplateListResponse(BaseModel):
    """Template list response model."""

    templates: List[TemplateResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool


class TemplateAnalyticsResponse(BaseModel):
    """Template analytics response model."""

    template_id: int
    total_usage_count: int
    favorite_count: int
    last_used_at: Optional[str]
    recent_30_days: Dict[str, Any]


# API Endpoints


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Create a new user profile template.

    Creates a new template with the specified configuration that can be
    reused to create recording profiles or shared with other users.
    """
    try:
        service = ProfileStorageService(db)

        template = service.create_template(
            name=request.name,
            user_id=current_user_id,
            configuration=request.configuration.dict(),
            description=request.description,
            category=request.category,
            tags=request.tags,
            is_public=request.is_public,
        )

        return TemplateResponse(**template.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error creating template: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template",
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get a specific template by ID."""
    service = ProfileStorageService(db)
    template = service.get_template(template_id, current_user_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or access denied",
        )

    return TemplateResponse(**template.to_dict())


@router.get("/uuid/{template_uuid}", response_model=TemplateResponse)
async def get_template_by_uuid(
    template_uuid: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get a specific template by UUID."""
    service = ProfileStorageService(db)
    template = service.get_template_by_uuid(template_uuid, current_user_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or access denied",
        )

    return TemplateResponse(**template.to_dict())


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Update an existing template."""
    try:
        service = ProfileStorageService(db)

        # Prepare updates dictionary
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.category is not None:
            updates["category"] = request.category
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.is_public is not None:
            updates["is_public"] = request.is_public
        if request.configuration is not None:
            updates.update(request.configuration.dict())

        template = service.update_template(template_id, current_user_id, updates)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found or access denied",
            )

        return TemplateResponse(**template.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error updating template %d: %s", template_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template",
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Delete a template."""
    service = ProfileStorageService(db)
    success = service.delete_template(template_id, current_user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or access denied",
        )


@router.get("/", response_model=TemplateListResponse)
async def search_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    search_text: Optional[str] = Query(
        None, description="Search in name and description"
    ),
    created_by_user_id: Optional[str] = Query(None, description="Filter by creator"),
    min_usage_count: Optional[int] = Query(None, description="Minimum usage count"),
    min_favorite_count: Optional[int] = Query(
        None, description="Minimum favorite count"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Search templates with filters and pagination.

    Returns templates accessible to the current user with optional filtering
    by category, tags, public status, search text, and other criteria.
    """
    try:
        service = ProfileStorageService(db)

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Build search filters
        filters = TemplateSearchFilters(
            category=category,
            tags=tag_list,
            created_by_user_id=created_by_user_id,
            is_public=is_public,
            is_featured=is_featured,
            min_usage_count=min_usage_count,
            min_favorite_count=min_favorite_count,
            search_text=search_text,
        )

        templates, total_count = service.search_templates(
            filters=filters,
            user_id=current_user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Convert to response models
        template_responses = [
            TemplateResponse(**template.to_dict()) for template in templates
        ]

        # Calculate pagination info
        has_next = (page * page_size) < total_count
        has_previous = page > 1

        return TemplateListResponse(
            templates=template_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous,
        )

    except Exception as e:
        logger.error("Error searching templates: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search templates",
        )


@router.post(
    "/{template_id}/clone",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_template(
    template_id: int,
    request: CloneTemplateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Clone an existing template."""
    try:
        service = ProfileStorageService(db)

        cloned_template = service.clone_template(
            template_id=template_id,
            user_id=current_user_id,
            new_name=request.new_name,
            description=request.description,
        )

        if not cloned_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found or access denied",
            )

        return TemplateResponse(**cloned_template.to_dict())

    except Exception as e:
        logger.error("Error cloning template %d: %s", template_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clone template",
        )


@router.post("/{template_id}/apply", response_model=Dict[str, Any])
async def apply_template(
    template_id: int,
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Apply a template to create a new recording profile."""
    try:
        service = ProfileStorageService(db)

        profile = service.apply_template_to_profile(
            template_id=template_id,
            user_id=current_user_id,
            profile_name=request.profile_name,
            camera_id=request.camera_id,
        )

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found or access denied",
            )

        return {
            "message": "Template applied successfully",
            "profile_id": profile.id,
            "profile_uuid": profile.profile_uuid,
            "profile_name": profile.name,
        }

    except Exception as e:
        logger.error("Error applying template %d: %s", template_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply template",
        )


@router.post("/{template_id}/favorite", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    template_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Add a template to user favorites."""
    service = ProfileStorageService(db)
    success = service.add_favorite(template_id, current_user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or access denied",
        )

    return {"message": "Template added to favorites"}


@router.delete("/{template_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    template_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Remove a template from user favorites."""
    service = ProfileStorageService(db)
    service.remove_favorite(template_id, current_user_id)


@router.get("/favorites/mine", response_model=List[TemplateResponse])
async def get_my_favorites(
    db: Session = Depends(get_db), current_user_id: str = Depends(get_current_user_id)
):
    """Get user's favorite templates."""
    service = ProfileStorageService(db)
    favorites = service.get_user_favorites(current_user_id)

    return [TemplateResponse(**template.to_dict()) for template in favorites]


@router.get("/{template_id}/analytics", response_model=TemplateAnalyticsResponse)
async def get_template_analytics(
    template_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get analytics for a template."""
    service = ProfileStorageService(db)
    analytics = service.get_template_analytics(template_id, current_user_id)

    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or access denied",
        )

    return TemplateAnalyticsResponse(**analytics)


@router.get("/popular/top", response_model=List[TemplateResponse])
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50, description="Number of templates to return"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Get most popular templates based on usage and favorites."""
    service = ProfileStorageService(db)
    templates = service.get_popular_templates(current_user_id, limit)

    return [TemplateResponse(**template.to_dict()) for template in templates]


# Import/Export Endpoints


class ExportTemplatesRequest(BaseModel):
    """Request model for exporting templates."""

    template_ids: List[int] = Field(..., description="Template IDs to export")
    include_metadata: bool = Field(
        default=True, description="Include metadata in export"
    )
    include_analytics: bool = Field(
        default=False, description="Include analytics in export"
    )
    format: str = Field(default="json", regex="^(json)$", description="Export format")


class ImportTemplatesRequest(BaseModel):
    """Request model for importing templates."""

    import_data: Dict[str, Any] = Field(..., description="Import data")
    conflict_resolution: str = Field(
        default="skip",
        regex="^(skip|rename|overwrite)$",
        description="Conflict resolution strategy",
    )
    category_override: Optional[str] = Field(
        None, description="Override category for imported templates"
    )
    make_private: bool = Field(
        default=True, description="Make imported templates private"
    )


class ImportResultResponse(BaseModel):
    """Response model for import operations."""

    total_processed: int
    success_count: int
    failure_count: int
    skipped_count: int
    successful_imports: List[Dict[str, Any]]
    failed_imports: List[Dict[str, Any]]
    skipped_imports: List[Dict[str, Any]]


@router.post("/export", response_model=Dict[str, Any])
async def export_templates(
    request: ExportTemplatesRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Export selected templates to JSON format.

    Exports templates with their configurations and optionally metadata
    and analytics for sharing or backup purposes.
    """
    try:
        service = TemplateImportExportService(db)

        export_data = service.export_templates(
            template_ids=request.template_ids,
            user_id=current_user_id,
            include_metadata=request.include_metadata,
            include_analytics=request.include_analytics,
        )

        return export_data

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error exporting templates: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export templates",
        ) from e


@router.post("/export/user", response_model=Dict[str, Any])
async def export_user_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_metadata: bool = Query(True, description="Include metadata in export"),
    include_analytics: bool = Query(False, description="Include analytics in export"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Export all user's templates to JSON format.

    Exports all templates created by the current user with optional
    category filtering and metadata/analytics inclusion.
    """
    try:
        service = TemplateImportExportService(db)

        export_data = service.export_user_templates(
            user_id=current_user_id,
            category=category,
            include_metadata=include_metadata,
            include_analytics=include_analytics,
        )

        return export_data

    except Exception as e:
        logger.error("Error exporting user templates: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user templates",
        ) from e


@router.post("/import", response_model=ImportResultResponse)
async def import_templates(
    request: ImportTemplatesRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Import templates from JSON data.

    Imports templates with configurable conflict resolution and
    category/privacy overrides.
    """
    try:
        service = TemplateImportExportService(db)

        result = service.import_templates(
            import_data=request.import_data,
            user_id=current_user_id,
            conflict_resolution=request.conflict_resolution,
            category_override=request.category_override,
            make_private=request.make_private,
        )

        return ImportResultResponse(**result.to_dict())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error importing templates: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import templates",
        ) from e


@router.post("/import/preview", response_model=Dict[str, Any])
async def preview_import(
    import_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Preview import operation without actually importing.

    Analyzes import data and returns information about conflicts,
    validation issues, and import statistics.
    """
    try:
        service = TemplateImportExportService(db)

        preview = service.get_import_preview(
            import_data=import_data, user_id=current_user_id
        )

        return preview

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Error previewing import: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview import",
        ) from e
