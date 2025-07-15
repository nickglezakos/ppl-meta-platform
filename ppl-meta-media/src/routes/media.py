"""
Media API routes for PPL Meta Platform Media Service.
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.media import Media, MediaType
from ..schemas.media import (
    BulkMediaRequest,
    BulkMediaUpdateRequest,
    BulkPrivacyUpdateRequest,
    MediaArchiveRequest,
    MediaCollectionResponse,
    MediaLocationUpdateRequest,
    MediaMetadataUpdateRequest,
    MediaPrivacyUpdateRequest,
    MediaResponse,
    MediaSearchRequest,
    MediaShareResponse,
    MediaUpdateRequest,
    MediaUploadRequest,
    VariantCreateRequest,
    VariantGenerateRequest,
    VariantResponse,
    VariantResponseDetailed,
    VariantStatisticsResponse,
    VariantTypeEnum,
    VariantUpdateRequest,
)
from ..services.media_service import MediaService

router = APIRouter(prefix="/api/v1/media", tags=["media"])


@router.post("/upload", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    categories: Optional[str] = Form(None),  # JSON string
    is_public: bool = Form(False),
    # Device information
    device_name: Optional[str] = Form(None),
    device_model: Optional[str] = Form(None),
    device_manufacturer: Optional[str] = Form(None),
    device_os: Optional[str] = Form(None),
    app_name: Optional[str] = Form(None),
    app_version: Optional[str] = Form(None),
    location_data: Optional[str] = Form(None),  # JSON string
    capture_timestamp: Optional[str] = Form(None),  # ISO string
    db: Session = Depends(get_db),
):
    """Upload a new media file with metadata and device information."""
    try:
        media_service = MediaService(db)

        # Create upload request from form data
        upload_request = MediaUploadRequest(
            user_id=UUID(user_id),
            title=title,
            description=description,
            tags=tags.split(",") if tags else [],
            categories=categories.split(",") if categories else [],
            is_public=is_public,
            device_name=device_name,
            device_model=device_model,
            device_manufacturer=device_manufacturer,
            device_os=device_os,
            app_name=app_name,
            app_version=app_version,
            location_data=location_data,
            capture_timestamp=capture_timestamp,
        )

        media = await media_service.upload_media(file, upload_request)
        return MediaResponse.model_validate(media)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=List[MediaResponse])
async def search_media(
    user_id: Optional[str] = None,
    media_type: Optional[MediaType] = None,
    tags: Optional[str] = None,  # Comma-separated
    categories: Optional[str] = None,  # Comma-separated
    device_name: Optional[str] = None,
    device_manufacturer: Optional[str] = None,
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Search media with various filters including device information."""
    try:
        media_service = MediaService(db)

        search_request = MediaSearchRequest(
            user_id=UUID(user_id) if user_id else None,
            media_type=media_type,
            tags=tags.split(",") if tags else None,
            categories=categories.split(",") if categories else None,
            device_name=device_name,
            device_manufacturer=device_manufacturer,
            is_public=is_public,
            limit=limit,
            offset=offset,
        )

        media_list = await media_service.search_media(search_request)
        return [MediaResponse.model_validate(media) for media in media_list]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get media by ID with access control."""
    try:
        media_service = MediaService(db)
        media = await media_service.get_media(
            media_id, user_id=UUID(user_id) if user_id else None
        )

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{media_id}")
async def delete_media(
    media_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Delete media (soft delete)."""
    try:
        media_service = MediaService(db)
        success = await media_service.delete_media(media_id, UUID(user_id))

        if not success:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return {"message": "Media deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}/grouped", response_model=dict)
async def get_user_media_grouped(
    user_id: str,
    group_by: str = "device_name",  # device_name, media_type, month, etc.
    db: Session = Depends(get_db),
):
    """Get user's media grouped by specified criteria (device, type, etc.)."""
    try:
        media_service = MediaService(db)
        grouped_media = await media_service.get_media_grouped(
            UUID(user_id), group_by=group_by
        )

        return grouped_media

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}/stats", response_model=dict)
async def get_user_media_stats(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get statistics about user's media including device breakdown."""
    try:
        media_service = MediaService(db)
        stats = await media_service.get_user_media_stats(UUID(user_id))

        return stats

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Collection routes
@router.post("/collections", response_model=MediaCollectionResponse)
async def create_collection(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Form(...),
    is_public: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Create a new media collection."""
    try:
        media_service = MediaService(db)
        collection = await media_service.create_collection(
            name=name,
            description=description,
            user_id=UUID(user_id),
            is_public=is_public,
        )

        return MediaCollectionResponse.model_validate(collection)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/collections/{collection_id}/add/{media_id}")
async def add_media_to_collection(
    collection_id: str,
    media_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Add media to a collection."""
    try:
        media_service = MediaService(db)
        success = await media_service.add_media_to_collection(
            collection_id=collection_id,
            media_id=media_id,
            user_id=UUID(user_id),
        )

        if not success:
            raise HTTPException(status_code=404, detail="Collection or media not found")

        return {"message": "Media added to collection successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Sharing routes
@router.post("/share/{media_id}", response_model=MediaShareResponse)
async def create_share_link(
    media_id: str,
    user_id: str,
    can_download: bool = False,
    expires_hours: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Create a share link for media."""
    try:
        media_service = MediaService(db)
        share = await media_service.create_share_link(
            media_id=media_id,
            user_id=UUID(user_id),
            can_download=can_download,
            expires_hours=expires_hours,
        )

        return MediaShareResponse.model_validate(share)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Issue #013: Complete Media CRUD Operations - API Routes


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    categories: Optional[str] = Form(None),  # JSON string
    is_public: Optional[bool] = Form(None),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Update media metadata (PUT operation - complete replacement)."""
    try:
        media_service = MediaService(db)

        # Create update request using proper schema
        update_request = MediaUpdateRequest(
            title=title,
            description=description,
            tags=tags.split(",") if tags else [],
            categories=categories.split(",") if categories else [],
            is_public=is_public,
        )

        media = await media_service.update_media(
            media_id, update_request, UUID(user_id)
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{media_id}", response_model=MediaResponse)
async def patch_media(
    media_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    categories: Optional[str] = Form(None),  # JSON string
    is_public: Optional[bool] = Form(None),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Partially update media metadata (PATCH operation)."""
    try:
        media_service = MediaService(db)

        # Create update request using proper schema
        update_request = MediaUpdateRequest(
            title=title,
            description=description,
            tags=tags.split(",") if tags else None,
            categories=categories.split(",") if categories else None,
            is_public=is_public,
        )

        media = await media_service.update_media(
            media_id, update_request, UUID(user_id)
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{media_id}/metadata", response_model=MediaResponse)
async def update_media_metadata(
    media_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    categories: Optional[str] = Form(None),  # JSON string
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Update only metadata fields (tags, description, title)."""
    try:
        media_service = MediaService(db)

        # Create metadata request using proper schema
        metadata_request = MediaMetadataUpdateRequest(
            title=title,
            description=description,
            tags=tags.split(",") if tags else None,
            categories=categories.split(",") if categories else None,
        )

        media = await media_service.update_media(
            media_id, metadata_request, UUID(user_id)
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{media_id}/privacy", response_model=MediaResponse)
async def update_media_privacy(
    media_id: str,
    is_public: bool = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Update privacy settings (public/private)."""
    try:
        media_service = MediaService(db)

        media = await media_service.update_media_privacy(
            media_id, is_public, UUID(user_id)
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{media_id}/location", response_model=MediaResponse)
async def update_media_location(
    media_id: str,
    location_data: Optional[str] = Form(None),  # JSON string
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Update GPS/location data."""
    try:
        media_service = MediaService(db)

        # Parse location data if provided
        parsed_location = None
        if location_data:
            try:
                parsed_location = json.loads(location_data)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=400, detail="Invalid location data format"
                ) from exc

        media = await media_service.update_media_location(
            media_id, parsed_location, UUID(user_id)
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Bulk Operations


@router.get("/bulk", response_model=List[MediaResponse])
async def get_media_bulk(
    media_ids: str,  # Comma-separated media IDs
    user_id: str,
    db: Session = Depends(get_db),
):
    """Bulk media retrieval with ID list."""
    try:
        media_service = MediaService(db)

        # Parse media IDs
        media_id_list = media_ids.split(",")
        if len(media_id_list) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 media IDs allowed per request"
            )

        media_list = await media_service.get_media_bulk(media_id_list, UUID(user_id))

        return [MediaResponse.model_validate(media) for media in media_list]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-update")
async def bulk_update_media(
    media_ids: str = Form(...),  # Comma-separated media IDs
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    categories: Optional[str] = Form(None),  # JSON string
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Bulk metadata updates."""
    try:
        media_service = MediaService(db)

        # Parse media IDs
        media_id_list = media_ids.split(",")
        if len(media_id_list) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 media IDs allowed per request"
            )

        # Prepare updates
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tags.split(",")
        if categories is not None:
            updates["categories"] = categories.split(",")

        result = await media_service.bulk_update_media(
            media_id_list, updates, UUID(user_id)
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/bulk-delete")
async def bulk_delete_media(
    media_ids: str = Form(...),  # Comma-separated media IDs
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Bulk media deletion."""
    try:
        media_service = MediaService(db)

        # Parse media IDs
        media_id_list = media_ids.split(",")
        if len(media_id_list) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 media IDs allowed per request"
            )

        result = await media_service.bulk_delete_media(media_id_list, UUID(user_id))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/bulk-privacy")
async def bulk_update_privacy(
    media_ids: str = Form(...),  # Comma-separated media IDs
    is_public: bool = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Bulk privacy settings changes."""
    try:
        media_service = MediaService(db)

        # Parse media IDs
        media_id_list = media_ids.split(",")
        if len(media_id_list) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 media IDs allowed per request"
            )

        result = await media_service.bulk_update_privacy(
            media_id_list, is_public, UUID(user_id)
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Media Organization Operations


@router.post("/{media_id}/archive", response_model=MediaResponse)
async def archive_media(
    media_id: str,
    archive_reason: Optional[str] = Form(None),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Archive media (soft delete)."""
    try:
        media_service = MediaService(db)

        media = await media_service.archive_media(
            media_id, UUID(user_id), archive_reason
        )

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{media_id}/restore", response_model=MediaResponse)
async def restore_archived_media(
    media_id: str,
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Restore archived media."""
    try:
        media_service = MediaService(db)

        media = await media_service.restore_archived_media(media_id, UUID(user_id))

        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# MEDIA VARIANTS ENDPOINTS
# ============================================================================


@router.get("/{media_id}/variants", response_model=List[VariantResponse])
async def get_media_variants(
    media_id: str,
    user_id: str,
    variant_type: Optional[VariantTypeEnum] = None,
    db: Session = Depends(get_db),
):
    """Get all variants for a media file."""
    try:
        media_service = MediaService(db)

        # Convert string IDs to integers
        media_id_int = int(media_id)

        variants = await media_service.get_media_variants(
            media_id_int, UUID(user_id), variant_type
        )

        return [VariantResponse.model_validate(variant) for variant in variants]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{media_id}/variants", response_model=VariantResponseDetailed)
async def create_media_variant(
    media_id: str,
    variant_data: VariantCreateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Create a new variant for a media file."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        media_id_int = int(media_id)

        variant = await media_service.create_media_variant(
            media_id_int,
            UUID(user_id),
            variant_data.file_path,
            variant_data.filename,
            variant_data.file_size,
            variant_data.mime_type,
            variant_data.variant_type,
            variant_data.quality_level,
            variant_data.metadata,
        )

        if not variant:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return VariantResponseDetailed.model_validate(variant)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/{media_id}/variants/generate", response_model=List[VariantResponseDetailed]
)
async def generate_media_variants(
    media_id: str,
    generate_request: VariantGenerateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Generate standard variants for a media file."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        media_id_int = int(media_id)

        variants = await media_service.generate_standard_variants(
            media_id_int,
            UUID(user_id),
            generate_request.variant_types,
            generate_request.quality_levels,
        )

        if not variants:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return [VariantResponseDetailed.model_validate(variant) for variant in variants]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{media_id}/variants/{variant_id}", response_model=VariantResponseDetailed)
async def get_variant_details(
    media_id: str,  # Keep for REST API consistency
    variant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific variant."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        variant_id_int = int(variant_id)

        # Get variant by ID - we'll need to implement this method
        variant = await media_service.get_variant_by_id(variant_id_int, UUID(user_id))

        if not variant:
            raise HTTPException(
                status_code=404, detail="Variant not found or access denied"
            )

        return VariantResponseDetailed.model_validate(variant)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{media_id}/variants/{variant_id}", response_model=VariantResponseDetailed)
async def update_media_variant(
    media_id: str,  # Keep for REST API consistency
    variant_id: str,
    variant_data: VariantUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update a media variant."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        variant_id_int = int(variant_id)

        # Convert Pydantic model to dict
        update_dict = variant_data.model_dump(exclude_unset=True)

        variant = await media_service.update_variant(
            variant_id_int, UUID(user_id), update_dict
        )

        if not variant:
            raise HTTPException(
                status_code=404, detail="Variant not found or access denied"
            )

        return VariantResponseDetailed.model_validate(variant)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{media_id}/variants/{variant_id}")
async def delete_media_variant(
    media_id: str,  # Keep for REST API consistency
    variant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Delete a media variant."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        variant_id_int = int(variant_id)

        success = await media_service.delete_variant(variant_id_int, UUID(user_id))

        if not success:
            raise HTTPException(
                status_code=404, detail="Variant not found or access denied"
            )

        return {"message": "Variant deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{media_id}/variants/statistics", response_model=VariantStatisticsResponse)
async def get_variant_statistics(
    media_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get statistics about media variants."""
    try:
        media_service = MediaService(db)

        # Convert string ID to integer
        media_id_int = int(media_id)

        stats = await media_service.get_variant_statistics(media_id_int, UUID(user_id))

        if not stats:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return VariantStatisticsResponse.model_validate(stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/variants/types", response_model=List[str])
async def get_variant_types(db: Session = Depends(get_db)):
    """Get available variant types."""
    try:
        media_service = MediaService(db)
        return media_service.get_variant_types()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
