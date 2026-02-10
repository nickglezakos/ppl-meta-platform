"""
Media API routes for PPL Meta Platform Media Service - API v1.
"""

import asyncio
import io
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiohttp
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from src.auth import AuthUser, get_current_user, get_user_from_token
from src.database import get_db
from src.models.media import Media
from src.schemas.media import (  # Variant schemas; Issue #016 - Advanced Metadata Management
    BulkCollectionItemRequest,
    BulkMetadataOperationResponse,
    BulkMetadataUpdateRequest,
    CollectionReorderRequest,
    CollectionSearchRequest,
    CollectionStatsResponse,
    CustomMetadataFieldRequest,
    MediaCollectionResponse,
    MediaCollectionUpdateRequest,
    MediaDetailsCompleteUpdateRequest,
    MediaDetailsDetailedResponse,
    MediaMetadataUpdateRequest,
    MediaResponse,
    MediaSearchRequest,
    MediaShareResponse,
    MediaType,
    MediaUpdateRequest,
    MediaUploadRequest,
    MetadataAnalyticsRequest,
    MetadataAnalyticsResponse,
    MetadataExportRequest,
    MetadataExportResponse,
    MetadataImportRequest,
    MetadataImportResponse,
    MetadataSchemaResponse,
    MetadataSearchRequest,
    MetadataSearchResponse,
    MetadataValidationRequest,
    MetadataValidationResponse,
    TechnicalMetadataUpdateRequest,
    UserMetadataUpdateRequest,
    VariantCreateRequest,
    VariantGenerateRequest,
    VariantResponse,
    VariantResponseDetailed,
    VariantTypeEnum,
    VariantUpdateRequest,
    VideoFrameResponse,
)
from src.services.media_service import MediaService
from src.services.thumbnail_service import ThumbnailService

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])


async def _trigger_enhanced_logic_v2_for_media(
    media_uuid: str, current_user: Optional[AuthUser] = None
):
    """
    Trigger Enhanced Logic V2 face detection for uploaded media.

    This function calls the Orchestrator's Enhanced Logic V2 endpoint
    to process face detection for newly uploaded videos.
    """
    try:
        # Import service auth utilities
        import sys
        from pathlib import Path
        # Add shared module to path
        shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
        if str(shared_path) not in sys.path:
            sys.path.insert(0, str(shared_path))
        
        from auth.service_auth import get_service_auth_headers
        
        # Service URLs
        ORCHESTRATOR_SERVICE_URL = "http://localhost:8002"

        # Build the Enhanced Logic V2 endpoint URL
        orchestrator_url = (
            f"{ORCHESTRATOR_SERVICE_URL}/api/v1/media/"
            f"{media_uuid}/faces/enhanced-v2"
        )

        # Prepare headers with service-to-service authentication
        headers = get_service_auth_headers("ppl-meta-media")

        # For now, we'll make a simple GET request
        # In the future, this could include user context if needed
        async with aiohttp.ClientSession() as session:
            async with session.get(orchestrator_url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    session_uuid = result.get("session_uuid")
                    total_faces = result.get("total_faces", 0)
                    source = result.get("source", "unknown")
                    processing_time = result.get("processing_time", 0)

                    logger.info(
                        f"🎯 ✅ Enhanced Logic V2 face detection completed "
                        f"for uploaded media {media_uuid}: {total_faces} faces "
                        f"found ({source}, {processing_time:.3f}s, "
                        f"session: {session_uuid})"
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"🎯 ❌ Failed to trigger Enhanced Logic V2 "
                        f"for uploaded media {media_uuid}: "
                        f"{response.status} - {error_text}"
                    )
    except Exception as e:
        logger.error(
            f"🎯 Error triggering Enhanced Logic V2 "
            f"for uploaded media {media_uuid}: {e}"
        )


@router.post("/register", response_model=MediaResponse)
async def register_media(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Register an existing camera video file with the media service."""
    try:
        # Import required modules at the top
        import hashlib
        import secrets
        from pathlib import Path
        from uuid import UUID

        from src.models.media import Media, MediaType

        # Extract required fields
        file_path = request.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        # Determine user ID (use a default for camera recordings)
        user_id_input = request.get("user_id", "1")  # Default camera user

        # Handle user_id: convert string to UUID if needed
        try:
            if isinstance(user_id_input, str) and len(user_id_input) < 36:
                # For simple user IDs, create a deterministic UUID v5
                import uuid

                namespace = uuid.UUID("12345678-1234-5678-1234-567812345678")
                user_id_uuid = uuid.uuid5(namespace, f"user_{user_id_input}")
            else:
                # Try to parse as UUID directly
                user_id_uuid = UUID(user_id_input)
        except (ValueError, TypeError):
            # Fallback to a random UUID v4 for camera recordings
            import uuid

            user_id_uuid = uuid.uuid4()

        file_path_obj = Path(file_path)

        # Create media entry directly
        media = Media(
            filename=file_path_obj.name,
            original_filename=file_path_obj.name,
            media_type=MediaType.VIDEO,
            mime_type="video/mp4",  # Default for camera recordings
            file_extension=file_path_obj.suffix.lower(),
            file_size=0,  # Will be updated when file is processed
            file_path=file_path,
            checksum=secrets.token_hex(16),  # Placeholder
            uploaded_by=user_id_uuid,
            title=f"Camera Recording - {file_path_obj.name}",
            description="Camera recording from automated workflow",
            is_public=False,
            # Camera-specific metadata
            device_name=request.get("camera_device_id", "Camera"),
        )

        # Add camera-specific fields if present in metadata
        metadata = request.get("metadata", {})
        if "camera_device_id" in request:
            # Store camera device ID in metadata for now
            metadata["camera_device_id"] = request["camera_device_id"]
        if "recording_session_id" in request:
            metadata["recording_session_id"] = request["recording_session_id"]

        # Store the metadata
        media.categories = ["camera_recording"]
        media.tags = [f"camera_{request.get('camera_device_id', 'unknown')}"]

        # Save to database
        db.add(media)
        db.commit()
        db.refresh(media)

        logging.getLogger(__name__).info(
            f"Registered camera video: {file_path} for user {user_id_input}"
        )

        return MediaResponse.model_validate(media)

    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to register media: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to register media: {str(e)}"
        )


@router.post("/upload", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    media_type: MediaType = Form(...),  # Now required
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

        # Parse optional fields
        parsed_location_data = None
        if location_data:
            try:
                parsed_location_data = json.loads(location_data)
            except json.JSONDecodeError:
                pass

        parsed_capture_timestamp = None
        if capture_timestamp:
            try:
                from datetime import datetime

                parsed_capture_timestamp = datetime.fromisoformat(
                    capture_timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Create upload request from form data
        upload_request = MediaUploadRequest(
            media_type=media_type,
            user_id=UUID(user_id),  # Include user_id
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
            location_data=parsed_location_data,
            capture_timestamp=parsed_capture_timestamp,
        )

        media = await media_service.upload_media(file, upload_request)

        # Generate URLs for the uploaded media
        media_response = MediaResponse.model_validate(media)
        urls = media_service.generate_media_urls(media)
        media_response.thumbnail_url = urls["thumbnail_url"]
        media_response.url = urls["url"]

        # 🎯 AUTO-TRIGGER: Enhanced Logic V2 for video uploads
        # ⚠️ DISABLED - November 20, 2025
        # Note: This trigger is for bulk upload endpoint, NOT needed for continuous pipeline.
        # The continuous pipeline uses Camera service auto-trigger instead.
        # Only re-enable if bulk upload workflow needs automatic face detection.
        # if media.media_type == MediaType.VIDEO:
        #     try:
        #         await _trigger_enhanced_logic_v2_for_media(
        #             str(media.uuid), current_user=None
        #         )
        #     except Exception as e:
        #         logger.warning(
        #             f"Failed to trigger Enhanced Logic V2 for uploaded media "
        #             f"{media.uuid}: {e}"
        #         )

        return media_response

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/search", response_model=List[MediaResponse])
async def search_media(
    media_types: Optional[str] = None,  # Comma-separated MediaType values
    tags: Optional[str] = None,  # Comma-separated
    categories: Optional[str] = None,  # Comma-separated
    device_name: Optional[str] = None,
    device_manufacturer: Optional[str] = None,
    is_public: Optional[bool] = None,
    start_date: Optional[str] = None,  # ISO 8601 date string
    end_date: Optional[str] = None,  # ISO 8601 date string
    start_time: Optional[str] = None,  # Alias for start_date (vmeta compatibility)
    end_time: Optional[str] = None,  # Alias for end_date (vmeta compatibility)
    collection: Optional[str] = None,  # Alias for collection_id (vmeta compatibility)
    collection_id: Optional[str] = None,  # Filter by specific collection
    collection_ids: Optional[
        str
    ] = None,  # Filter by multiple collections (comma-separated)
    page: int = 1,
    page_size: int = 20,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search authenticated user's media with various filters.
    
    Time filtering uses start_timestamp (recording time) for camera videos,
    falls back to created_at for other media types.
    """
    try:
        media_service = MediaService(db)

        # Parse media types if provided
        parsed_media_types = None
        if media_types:
            try:
                parsed_media_types = [
                    MediaType(mt.strip()) for mt in media_types.split(",")
                ]
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid media type: {e}"
                ) from e

        # Parse date parameters if provided (support both start_date and start_time)
        parsed_start_date = None
        parsed_end_date = None

        start_param = start_time or start_date
        end_param = end_time or end_date

        if start_param:
            try:
                # Handle ISO format with Z timezone
                date_str = start_param.replace("Z", "+00:00")
                parsed_start_date = datetime.fromisoformat(date_str)
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid start time/date format: {e}"
                ) from e

        if end_param:
            try:
                # Handle ISO format with Z timezone
                date_str = end_param.replace("Z", "+00:00")
                parsed_end_date = datetime.fromisoformat(date_str)
            except ValueError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid end time/date format: {e}"
                ) from e

        # Support both collection and collection_id parameters
        effective_collection_id = collection or collection_id

        # Debug collection filtering
        logger.info(
            f"DEBUG API: collection={collection}, collection_id={collection_id}, effective={effective_collection_id}, collection_ids={collection_ids}"
        )
        if collection_ids:
            parsed_collection_ids = collection_ids.split(",")
            logger.info(f"DEBUG API: parsed_collection_ids={parsed_collection_ids}")
        else:
            parsed_collection_ids = None

        search_request = MediaSearchRequest(
            uploaded_by=UUID(current_user.user_id),  # Filter by user
            media_types=parsed_media_types,
            tags=tags.split(",") if tags else None,
            categories=categories.split(",") if categories else None,
            is_public=is_public,
            date_from=parsed_start_date,
            date_to=parsed_end_date,
            collection_id=effective_collection_id,
            collection_ids=parsed_collection_ids,
            page=page,
            page_size=page_size,
        )

        media_list = await media_service.search_media(search_request)

        # Generate URLs for each media item and load collections
        result = []
        print(f"🔍 DEBUG SEARCH ENDPOINT: Processing {len(media_list)} media items")
        for media in media_list:
            print(f"🔍 DEBUG SEARCH ENDPOINT: Processing media ID {media.id}")
            media_response = MediaResponse.model_validate(media)
            urls = media_service.generate_media_urls(media)
            media_response.thumbnail_url = urls["thumbnail_url"]
            media_response.url = urls["url"]

            # Load collections for this media item
            print(
                f"🔍 DEBUG SEARCH ENDPOINT: About to call get_media_collections for media ID {media.id}"
            )
            collections = await media_service.get_media_collections(media.id)
            print(
                f"🔍 DEBUG SEARCH ENDPOINT: Got {len(collections)} collections for media ID {media.id}"
            )
            media_response.collections = [
                {
                    "id": col.id,
                    "uuid": str(col.uuid),
                    "name": col.name,
                    "description": col.description,
                }
                for col in collections
            ]

            result.append(media_response)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# COLLECTION CRUD ENDPOINTS - Issue #014 Implementation
# ============================================================================


@router.get("/collections", response_model=List[MediaCollectionResponse])
async def list_collections(
    skip: int = 0,
    limit: int = 100,
    include_public: bool = False,
    exclude_camera_collections: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authenticated user's collections with pagination.
    
    Args:
        skip: Number of collections to skip for pagination
        limit: Maximum number of collections to return
        include_public: Include public collections from other users
        exclude_camera_collections: Exclude auto-created camera collections (only return user-created collections)
    """
    try:
        media_service = MediaService(db)
        collections = await media_service.get_collections(
            user_id=UUID(current_user.user_id),
            skip=skip,
            limit=limit,
            include_public=include_public,
            exclude_camera_collections=exclude_camera_collections,
        )

        return [MediaCollectionResponse.model_validate(col) for col in collections]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/collections/lookup")
async def lookup_collection(
    name: Optional[str] = None,
    uuid: Optional[str] = None,
    id: Optional[int] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lookup collection by name, UUID, or ID and return its identifiers.
    
    This endpoint helps resolve collection names to IDs/UUIDs for filtering.
    Supports partial name matching (e.g., 'usb_camera_0' matches 'usb_camera_0 Collection').
    """
    try:
        from ...models.media import MediaCollection
        from sqlalchemy import or_
        
        query = db.query(MediaCollection).filter(
            MediaCollection.created_by == UUID(current_user.user_id)
        )
        
        if name:
            # Support both exact match and partial match with LIKE
            query = query.filter(
                or_(
                    MediaCollection.name == name,
                    MediaCollection.name.ilike(f"{name}%"),
                    MediaCollection.name.ilike(f"%{name}%")
                )
            )
        elif uuid:
            query = query.filter(MediaCollection.uuid == UUID(uuid))
        elif id:
            query = query.filter(MediaCollection.id == id)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Must provide name, uuid, or id parameter"
            )
        
        collection = query.first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        return {
            "id": collection.id,
            "uuid": str(collection.uuid),
            "name": collection.name,
            "description": collection.description,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/collections/search", response_model=List[MediaCollectionResponse])
async def search_collections(
    query: str,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Search collections by name, description, or tags."""
    try:
        media_service = MediaService(db)
        collections = await media_service.search_collections(
            UUID(user_id), query, skip, limit
        )

        return [MediaCollectionResponse.model_validate(col) for col in collections]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch(
    "/collections/{collection_uuid}/name",
    summary="Update collection name",
)
async def update_collection_name(
    collection_uuid: str,
    name: str,
    db: Session = Depends(get_db),
):
    """
    Update collection name.
    
    Collection names must be unique across the platform.
    This endpoint is typically called when a camera name is updated.
    """
    try:
        from src.models.media import MediaCollection
        from src.services.collection_name_validation import (
            validate_collection_name_unique,
            sanitize_collection_name
        )
        from uuid import UUID

        # Find the collection
        collection = (
            db.query(MediaCollection)
            .filter(MediaCollection.uuid == UUID(collection_uuid))
            .first()
        )

        if not collection:
            raise HTTPException(
                status_code=404,
                detail=f"Collection {collection_uuid} not found"
            )

        # Sanitize and validate the new name
        new_name = sanitize_collection_name(name)
        
        # Check if name is actually changing
        if new_name == collection.name:
            return {
                "message": "Collection name unchanged",
                "collection": {
                    "uuid": str(collection.uuid),
                    "name": collection.name,
                }
            }

        is_valid, error_msg = validate_collection_name_unique(
            db, new_name, exclude_uuid=collection_uuid
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        old_name = collection.name
        collection.name = new_name
        db.commit()
        db.refresh(collection)

        logger.info(
            f"Collection name updated: {old_name} -> {new_name} "
            f"(UUID: {collection_uuid}, camera: {collection.camera_device_id})"
        )

        return {
            "message": "Collection name updated successfully",
            "collection": {
                "uuid": str(collection.uuid),
                "name": collection.name,
                "old_name": old_name,
                "camera_device_id": collection.camera_device_id,
            }
        }

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection UUID")
    except Exception as e:
        logger.error(f"Error updating collection name: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update collection name: {str(e)}"
        )


@router.get(
    "/collections/by-camera/{camera_device_id}",
    response_model=Optional[MediaCollectionResponse],
)
async def get_collection_by_camera(
    camera_device_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get collection associated with a specific camera device ID."""
    try:
        media_service = MediaService(db)
        collection = await media_service.get_collection_by_camera_device_id(
            camera_device_id=camera_device_id,
            user_id=UUID(current_user.user_id),
        )

        if not collection:
            return None

        return MediaCollectionResponse.model_validate(collection)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/collections/{collection_id}", response_model=MediaCollectionResponse)
async def get_collection(
    collection_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific collection by ID."""
    try:
        media_service = MediaService(db)
        collection = await media_service.get_collection(collection_id, UUID(user_id))

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return MediaCollectionResponse.model_validate(collection)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/collections/{collection_id}/items", response_model=List[MediaResponse])
async def get_collection_items(
    collection_id: str,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get media items in a collection with pagination."""
    try:
        media_service = MediaService(db)
        items = await media_service.get_collection_items(
            collection_id, UUID(user_id), skip, limit
        )

        # Generate URLs for each media item
        result = []
        for item in items:
            media_response = MediaResponse.model_validate(item)
            urls = media_service.generate_media_urls(item)
            media_response.thumbnail_url = urls["thumbnail_url"]
            media_response.url = urls["url"]
            result.append(media_response)

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/collections/{collection_id}/stats", response_model=CollectionStatsResponse
)
async def get_collection_stats(
    collection_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get statistics for a collection."""
    try:
        media_service = MediaService(db)
        stats = await media_service.get_collection_stats(collection_id, UUID(user_id))

        if not stats:
            raise HTTPException(status_code=404, detail="Collection not found")

        return CollectionStatsResponse.model_validate(stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/collections/{collection_id}", response_model=MediaCollectionResponse)
async def update_collection(
    collection_id: str,
    update_data: MediaCollectionUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update a collection completely."""
    try:
        media_service = MediaService(db)
        collection = await media_service.update_collection(
            collection_id, UUID(user_id), update_data.model_dump()
        )

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return MediaCollectionResponse.model_validate(collection)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/collections/{collection_id}", response_model=MediaCollectionResponse)
async def partial_update_collection(
    collection_id: str,
    update_data: MediaCollectionUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Partially update a collection with only provided fields."""
    try:
        media_service = MediaService(db)
        # Only include non-None values for partial update
        update_dict = {
            k: v for k, v in update_data.model_dump().items() if v is not None
        }

        collection = await media_service.update_collection(
            collection_id, UUID(user_id), update_dict
        )

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return MediaCollectionResponse.model_validate(collection)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a collection."""
    try:
        media_service = MediaService(db)
        success = await media_service.delete_collection(
            collection_id, UUID(current_user.user_id)
        )

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"message": "Collection deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/collections/{collection_id}/remove/{media_id}")
async def remove_media_from_collection(
    collection_id: str,
    media_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Remove media from a collection."""
    try:
        media_service = MediaService(db)
        success = await media_service.remove_media_from_collection(
            collection_id, media_id, UUID(user_id)
        )

        if not success:
            raise HTTPException(status_code=404, detail="Collection or media not found")

        return {"message": "Media removed from collection successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/collections/{collection_id}/bulk-add")
async def bulk_add_to_collection(
    collection_id: str,
    request: BulkCollectionItemRequest,
    db: Session = Depends(get_db),
):
    """Bulk add media items to a collection."""
    try:
        media_service = MediaService(db)
        result = await media_service.bulk_add_to_collection(
            collection_id, request.media_ids, request.user_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/collections/{collection_id}/bulk-remove")
async def bulk_remove_from_collection(
    collection_id: str,
    request: BulkCollectionItemRequest,
    db: Session = Depends(get_db),
):
    """Bulk remove media items from a collection."""
    try:
        media_service = MediaService(db)
        result = await media_service.bulk_remove_from_collection(
            collection_id, request.media_ids, request.user_id
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/collections/{collection_id}/reorder")
async def reorder_collection_items(
    collection_id: str,
    request: CollectionReorderRequest,
    db: Session = Depends(get_db),
):
    """Reorder items in a collection."""
    try:
        media_service = MediaService(db)
        success = await media_service.reorder_collection_items(
            collection_id, request.user_id, request.item_orders
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Collection not found or access denied"
            )

        return {"message": "Collection items reordered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: str,
    user_id: Optional[str] = None,
    current_user: Optional[AuthUser] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get media by ID with access control."""
    try:
        media_service = MediaService(db)
        # Use authenticated user if no user_id provided
        effective_user_id = user_id or (current_user.user_id if current_user else None)
        media = await media_service.get_media(
            media_id, user_id=UUID(effective_user_id) if effective_user_id else None
        )

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Generate URLs for the media item
        media_response = MediaResponse.model_validate(media)
        urls = media_service.generate_media_urls(media)
        media_response.thumbnail_url = urls["thumbnail_url"]
        media_response.url = urls["url"]

        return media_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: str,
    update_data: MediaUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update media with full replacement."""
    try:
        media_service = MediaService(db)
        media = await media_service.update_media(media_id, update_data.model_dump())

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Generate URLs for the updated media item
        media_response = MediaResponse.model_validate(media)
        urls = media_service.generate_media_urls(media)
        media_response.thumbnail_url = urls["thumbnail_url"]
        media_response.url = urls["url"]

        return media_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{media_id}", response_model=MediaResponse)
async def partial_update_media(
    media_id: str,
    update_data: MediaUpdateRequest,
    db: Session = Depends(get_db),
):
    """Partially update media with only provided fields."""
    try:
        media_service = MediaService(db)
        # Only include non-None values for partial update
        update_dict = {
            k: v for k, v in update_data.model_dump().items() if v is not None
        }

        media = await media_service.update_media(media_id, update_dict)

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Generate URLs for the updated media item
        media_response = MediaResponse.model_validate(media)
        urls = media_service.generate_media_urls(media)
        media_response.thumbnail_url = urls["thumbnail_url"]
        media_response.url = urls["url"]

        return media_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/{media_id}/metadata", response_model=MediaResponse)
async def update_media_metadata(
    media_id: str,
    metadata_update: MediaMetadataUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update only the metadata fields of a media item."""
    try:
        media_service = MediaService(db)
        media = await media_service.update_media_metadata(
            media_id, metadata_update.model_dump()
        )

        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Generate URLs for the updated media item
        media_response = MediaResponse.model_validate(media)
        urls = media_service.generate_media_urls(media)
        media_response.thumbnail_url = urls["thumbnail_url"]
        media_response.url = urls["url"]

        return media_response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e


# Collection routes
@router.post("/collections", response_model=MediaCollectionResponse)
async def create_collection(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Form(...),
    is_public: bool = Form(False),
    camera_device_id: Optional[str] = Form(None),
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
            camera_device_id=camera_device_id,
        )

        return MediaCollectionResponse.model_validate(collection)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# FILE SERVING ENDPOINTS - Issue #006 Implementation
# ============================================================================


# Initialize thumbnail service with storage path
def get_thumbnail_service() -> ThumbnailService:
    """Get thumbnail service instance."""
    from src.config import get_config

    settings = get_config()
    redis_url = getattr(settings, "REDIS_URL", None)
    return ThumbnailService(settings.STORAGE_PATH, redis_url=redis_url)


def get_storage_root() -> str:
    """Get the storage root path."""
    from src.config import get_config

    settings = get_config()
    return settings.STORAGE_PATH


def get_media_access_check(
    media_id: str,
    user_id: Optional[str] = None,
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Check if user has access to media file.
    Returns media info if access is granted, raises HTTPException otherwise.
    """
    try:
        media_service = MediaService(db)

        # Get media information
        media = media_service.get_media_by_id(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Check access permissions
        has_access = False

        # Option 0: Internal service (system user) - bypass all checks
        if user_id == "00000000-0000-0000-0000-000000000000":
            has_access = True

        # Option 1: User owns the media
        elif user_id and str(media.uploaded_by) == user_id:
            has_access = True

        # Option 2: Media is public
        elif media.is_public:
            has_access = True

        # Option 3: Valid share token provided
        elif share_token:
            share = media_service.get_share_by_token(share_token)
            if share and str(share.media_id) == media_id:
                has_access = True

        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this media")

        return {
            "media": media,
            "file_path": str(media.file_path),  # Use exact database path
            "mime_type": str(media.mime_type),
            "filename": str(media.original_filename or media.filename),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/download/{media_id}")
async def download_media(
    media_id: str,
    current_user: AuthUser = Depends(get_current_user),
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Download media file directly with proper access control.

    Args:
        media_id: UUID of the media to download
        current_user: Authenticated user
        share_token: Optional share token for public access

    Returns:
        FileResponse with the media file
    """
    # Check access permissions using authenticated user's UUID
    access_info = get_media_access_check(
        media_id, current_user.user_id, share_token, db
    )

    file_path = Path(access_info["file_path"])

    # Verify file exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    # Return file with proper headers
    return FileResponse(
        path=str(file_path),
        media_type=access_info["mime_type"],
        filename=access_info["filename"],
        headers={
            "Content-Disposition": (
                f'attachment; filename="{access_info["filename"]}"'
            ),
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/stream/{media_id}")
async def stream_media(
    media_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Stream media file with range request support for video/audio content.

    Args:
        media_id: UUID of the media to stream
        request: FastAPI request object for range headers
        current_user: Authenticated user
        share_token: Optional share token for public access

    Returns:
        StreamingResponse with range request support
    """
    # Check access permissions using the authenticated user's UUID
    access_info = get_media_access_check(
        media_id, current_user.user_id, share_token, db
    )

    # 🎯 AUTO-TRIGGER: Enhanced Logic V2 for video loads
    media = access_info["media"]
    if media.media_type == MediaType.VIDEO:
        try:
            # Trigger Enhanced Logic V2 asynchronously (don't block streaming)
            asyncio.create_task(
                _trigger_enhanced_logic_v2_for_media(
                    media_id, current_user=current_user
                )
            )
        except Exception as e:
            logger.warning(
                f"Failed to trigger Enhanced Logic V2 for loaded media "
                f"{media_id}: {e}"
            )

    file_path = Path(access_info["file_path"])

    # Verify file exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")

    def generate_chunks(start: int, end: int):
        """Generate file chunks for streaming."""
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk_size = min(8192, remaining)  # 8KB chunks
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    # Handle range requests
    if range_header:
        try:
            # Parse range header (e.g., "bytes=0-1023")
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1

            # Validate range
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(status_code=416, detail="Range not satisfiable")

            content_length = end - start + 1

            return StreamingResponse(
                generate_chunks(start, end),
                status_code=206,  # Partial Content
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Content-Type": access_info["mime_type"],
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "private, max-age=3600",
                },
            )
        except (ValueError, IndexError):
            # Invalid range header, fall back to full file
            pass

    # Return full file if no range request or invalid range
    return StreamingResponse(
        generate_chunks(0, file_size - 1),
        media_type=access_info["mime_type"],
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/stream-token/{media_id}")
async def stream_media_with_token(
    media_id: str,
    token: str,  # JWT token as query parameter
    request: Request,
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Stream media file with JWT token as query parameter.
    This endpoint is designed for Flutter video player web compatibility.

    Args:
        media_id: UUID of the media to stream
        token: JWT authentication token as query parameter
        request: FastAPI request object for range headers
        share_token: Optional share token for public access

    Returns:
        StreamingResponse with range request support
    """
    # Authenticate user from token query parameter
    current_user = await get_user_from_token(token)

    # Check access permissions using the authenticated user's UUID
    access_info = get_media_access_check(
        media_id, current_user.user_id, share_token, db
    )

    # 🎯 AUTO-TRIGGER: Enhanced Logic V2 for video loads (token endpoint)
    media = access_info["media"]
    if media.media_type == MediaType.VIDEO:
        try:
            # Trigger Enhanced Logic V2 asynchronously (don't block streaming)
            asyncio.create_task(
                _trigger_enhanced_logic_v2_for_media(
                    media_id, current_user=current_user
                )
            )
        except Exception as e:
            logger.warning(
                f"Failed to trigger Enhanced Logic V2 for loaded media "
                f"{media_id}: {e}"
            )

    file_path = Path(access_info["file_path"])

    # Verify file exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range")

    def generate_chunks(start: int, end: int):
        """Generate file chunks for streaming."""
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk_size = min(8192, remaining)  # 8KB chunks
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    # Handle range requests
    if range_header:
        try:
            # Parse range header (e.g., "bytes=0-1023")
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1

            # Validate range
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(status_code=416, detail="Range not satisfiable")

            content_length = end - start + 1

            return StreamingResponse(
                generate_chunks(start, end),
                status_code=206,  # Partial Content
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Length": str(content_length),
                    "Content-Type": access_info["mime_type"],
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "private, max-age=3600",
                },
            )
        except (ValueError, IndexError):
            # Invalid range header, fall back to full file
            pass

    # Return full file if no range request or invalid range
    return StreamingResponse(
        generate_chunks(0, file_size - 1),
        media_type=access_info["mime_type"],
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/thumbnail/{media_id}")
async def get_thumbnail(
    media_id: str,
    size: str = "medium",
    video_position: str = "start",
    video_timestamp: Optional[str] = None,
    share_token: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    thumbnail_service: ThumbnailService = Depends(get_thumbnail_service),
):
    """
    Generate and serve thumbnail for media file.

    Args:
        media_id: UUID of the media to generate thumbnail for
        size: Thumbnail size (small, medium, large)
        video_position: Video position for thumbnail ("start", "middle", "end")
        video_timestamp: Custom timestamp for video thumbnails (e.g.,
                        "00:02:30")
        share_token: Optional share token for public access

    Returns:
        Response with thumbnail image bytes
    """
    # Check access permissions using authenticated user
    access_info = get_media_access_check(media_id, user.user_id, share_token, db)

    file_path = Path(access_info["file_path"])

    # Verify file exists on disk
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    # Generate thumbnail with enhanced options
    thumbnail_bytes = thumbnail_service.generate_thumbnail(
        str(file_path),
        size=size,
        video_timestamp=video_timestamp,
        video_position=video_position,
    )

    if not thumbnail_bytes:
        # Return a default video thumbnail instead of 422 error
        # This prevents UI failures when thumbnail generation fails
        default_thumbnail = thumbnail_service.get_default_video_thumbnail(size)
        if default_thumbnail:
            return Response(
                content=default_thumbnail,
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": (
                        f"inline; filename=default_thumbnail_{size}.jpg"
                    ),
                    "Cache-Control": "public, max-age=86400",
                },
            )
        else:
            raise HTTPException(
                status_code=422,
                detail="Unable to generate thumbnail for this media type",
            )

    # Return thumbnail with proper headers
    return Response(
        content=thumbnail_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "Content-Length": str(len(thumbnail_bytes)),
        },
    )


@router.get("/{media_id}/frame/{frame_number}")
async def extract_video_frame(
    media_id: str,
    frame_number: int,
    format: str = "jpeg",
    quality: int = 85,
    size: Optional[str] = None,
    share_token: Optional[str] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract a specific frame from a video file and return as image.

    Args:
        media_id: UUID of the video file
        frame_number: Frame number to extract (0-based indexing)
        format: Output format (jpeg, png, webp) - default: jpeg
        quality: JPEG quality (1-100) - default: 85
        size: Optional resize parameter (small, medium, large, or WxH format)
        share_token: Optional share token for public access
        current_user: Authenticated user

    Returns:
        Response with frame image bytes and metadata headers
    """
    try:
        # Validate format
        if format.lower() not in ["jpeg", "png", "webp"]:
            raise HTTPException(
                status_code=400, detail="Invalid format. Supported: jpeg, png, webp"
            )

        # Validate quality
        if not 1 <= quality <= 100:
            raise HTTPException(
                status_code=400, detail="Quality must be between 1 and 100"
            )

        # Validate frame number
        if frame_number < 0:
            raise HTTPException(
                status_code=400, detail="Frame number must be non-negative"
            )

        # Parse size parameter if provided
        width, height = None, None
        if size:
            if size.lower() == "small":
                width, height = 320, 240
            elif size.lower() == "medium":
                width, height = 640, 480
            elif size.lower() == "large":
                width, height = 1280, 720
            elif "x" in size.lower():
                try:
                    w_str, h_str = size.lower().split("x")
                    width, height = int(w_str), int(h_str)
                    if width <= 0 or height <= 0 or width > 7680 or height > 4320:
                        raise ValueError("Invalid dimensions")
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid size format. Use: small, medium, large, "
                            "or WxH (e.g., 1920x1080)"
                        ),
                    )

        # Check access permissions using the authenticated user's UUID
        get_media_access_check(media_id, current_user.user_id, share_token, db)

        media_service = MediaService(db)

        # Extract frame
        frame_data = await media_service.extract_video_frame(
            media_id=media_id,
            frame_number=frame_number,
            user_id=UUID(current_user.user_id),
            output_format=format,
            quality=quality,
            width=width,
            height=height,
        )

        # Create frame info header
        frame_info = {
            "frame_number": frame_data["frame_number"],
            "frame_timestamp": frame_data["frame_timestamp"],
            "total_frames": frame_data["total_frames"],
            "video_duration": frame_data["video_duration"],
            "format": frame_data["format"],
            "width": frame_data["width"],
            "height": frame_data["height"],
        }

        return Response(
            content=frame_data["frame_data"],
            media_type=frame_data["mime_type"],
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Length": str(frame_data["file_size"]),
                "X-Frame-Info": json.dumps(frame_info),
            },
        )

    except ValueError as e:
        if "out of range" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "not a video" in str(e):
            raise HTTPException(status_code=415, detail=str(e))
        elif "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Frame extraction failed: {str(e)}"
        )


@router.get("/exif/{media_id}")
async def get_exif_metadata(
    media_id: str,
    user_id: Optional[str] = None,
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get EXIF metadata for a specific media file.

    Args:
        media_id: UUID of the media to get EXIF data for
        user_id: Optional user ID for access control
        share_token: Optional share token for public access

    Returns:
        EXIF metadata dictionary
    """
    # Check access permissions
    access_info = get_media_access_check(media_id, user_id, share_token, db)

    media_record = db.query(Media).filter(Media.id == media_id).first()
    if not media_record:
        raise HTTPException(status_code=404, detail="Media not found")

    # Get EXIF data from technical_metadata
    technical_metadata = media_record.technical_metadata or {}
    exif_data = technical_metadata.get("exif")

    if exif_data is None:
        # Try to extract EXIF data if not already done
        from src.services.exif_extractor import ExifExtractor

        extractor = ExifExtractor(privacy_mode=False)
        file_path = Path(access_info["file_path"])

        if file_path.exists():
            exif_data = extractor.extract_exif_data(str(file_path))
            if exif_data:
                return {
                    "media_id": media_id,
                    "exif_data": exif_data,
                    "extracted_on_demand": True,
                }

        raise HTTPException(
            status_code=404, detail="No EXIF data available for this media file"
        )

    return {"media_id": media_id, "exif_data": exif_data, "extracted_on_demand": False}


@router.post("/exif/extract/{media_id}")
async def extract_exif_metadata(
    media_id: str,
    privacy_mode: bool = False,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Extract or re-extract EXIF metadata for a specific media file.

    Args:
        media_id: UUID of the media to extract EXIF data for
        privacy_mode: If True, removes GPS and sensitive metadata
        user_id: User ID for access control

    Returns:
        Extracted EXIF metadata
    """
    # Verify media exists and user has access
    media_record = db.query(Media).filter(Media.id == media_id).first()
    if not media_record:
        raise HTTPException(status_code=404, detail="Media not found")

    # Check user permission (only owner can extract EXIF)
    if user_id and str(media_record.uploaded_by) != user_id:
        raise HTTPException(
            status_code=403, detail="Only the media owner can extract EXIF data"
        )

    # Only extract from image files
    if media_record.media_type != MediaType.PICTURE:
        raise HTTPException(
            status_code=422, detail="EXIF extraction is only supported for image files"
        )

    try:
        from src.services.exif_extractor import ExifExtractor

        extractor = ExifExtractor(privacy_mode=privacy_mode)
        exif_data = extractor.extract_exif_data(str(media_record.file_path))

        if not exif_data:
            raise HTTPException(
                status_code=404, detail="No EXIF data found in this image file"
            )

        # Update media record with extracted EXIF data
        if not media_record.technical_metadata:
            media_record.technical_metadata = {}

        media_record.technical_metadata["exif"] = exif_data
        media_record.technical_metadata["exif_summary"] = extractor.get_summary_stats(
            exif_data
        )
        media_record.technical_metadata["exif_extraction_date"] = (
            datetime.utcnow().isoformat()
        )
        media_record.technical_metadata["privacy_mode"] = privacy_mode

        db.commit()

        return {
            "media_id": media_id,
            "exif_data": exif_data,
            "privacy_mode": privacy_mode,
            "extraction_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error extracting EXIF data: {str(e)}"
        )


@router.post("/exif/bulk-extract")
async def bulk_extract_exif(
    user_id: str,
    privacy_mode: bool = False,
    media_type_filter: Optional[str] = "picture",
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Bulk extract EXIF metadata for user's media files.

    Args:
        user_id: User ID to extract EXIF data for
        privacy_mode: If True, removes GPS and sensitive metadata
        media_type_filter: Filter by media type (default: "picture")
        limit: Maximum number of files to process

    Returns:
        Summary of bulk extraction results
    """
    try:
        from src.services.exif_extractor import ExifExtractor

        # Query user's image files without EXIF data
        query = db.query(Media).filter(Media.uploaded_by == user_id)

        if media_type_filter == "picture":
            query = query.filter(Media.media_type == MediaType.PICTURE)

        # Get files that don't have EXIF data yet
        media_files = query.limit(limit).all()

        extractor = ExifExtractor(privacy_mode=privacy_mode)

        results = {
            "processed": 0,
            "extracted": 0,
            "skipped": 0,
            "errors": 0,
            "details": [],
        }

        for media_record in media_files:
            try:
                results["processed"] += 1

                # Check if EXIF already exists
                technical_metadata = media_record.technical_metadata or {}
                if technical_metadata.get("exif"):
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "media_id": str(media_record.id),
                            "status": "skipped",
                            "reason": "EXIF data already exists",
                        }
                    )
                    continue

                # Extract EXIF data
                exif_data = extractor.extract_exif_data(str(media_record.file_path))

                if exif_data:
                    # Update media record
                    if not media_record.technical_metadata:
                        media_record.technical_metadata = {}

                    media_record.technical_metadata["exif"] = exif_data
                    media_record.technical_metadata["exif_summary"] = (
                        extractor.get_summary_stats(exif_data)
                    )
                    media_record.technical_metadata["exif_extraction_date"] = (
                        datetime.utcnow().isoformat()
                    )
                    media_record.technical_metadata["privacy_mode"] = privacy_mode

                    results["extracted"] += 1
                    results["details"].append(
                        {
                            "media_id": str(media_record.id),
                            "status": "extracted",
                            "exif_summary": extractor.get_summary_stats(exif_data),
                        }
                    )
                else:
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "media_id": str(media_record.id),
                            "status": "no_exif",
                            "reason": "No EXIF data found in file",
                        }
                    )

            except Exception as e:
                results["errors"] += 1
                results["details"].append(
                    {
                        "media_id": str(media_record.id),
                        "status": "error",
                        "error": str(e),
                    }
                )

        # Commit all changes
        db.commit()

        return {
            "user_id": user_id,
            "privacy_mode": privacy_mode,
            "bulk_extraction_summary": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error during bulk EXIF extraction: {str(e)}"
        )


# ============================================================================
# MEDIA VARIANTS ENDPOINTS - Issue #015 Implementation
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
            variant_data.variant_type,
            variant_data.file_path,
            variant_data.filename,
            variant_data.file_size,
            variant_data.mime_type,
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


@router.post("/{media_id}/variants/generate", response_model=Dict[str, Any])
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

        result = await media_service.generate_standard_variants(
            media_id_int,
            UUID(user_id),
            generate_request.variant_types,
            generate_request.quality_levels,
        )

        if not result:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{media_id}/variants/statistics", response_model=Dict[str, Any])
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

        return stats

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

        # Refresh to get updated values and use from_attributes
        db.refresh(variant)
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


@router.get("/variants/types", response_model=List[str])
async def get_variant_types(db: Session = Depends(get_db)):
    """Get available variant types."""
    try:
        media_service = MediaService(db)
        return media_service.get_variant_types()

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# ISSUE #016: Advanced Media Details and Metadata Management API Endpoints
# ============================================================================


@router.get("/{media_id}/details", response_model=MediaDetailsDetailedResponse)
async def get_media_details(
    media_id: str,
    user_id: Optional[str] = None,
    share_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get complete media details including technical and user metadata."""
    try:
        if not user_id and not share_token:
            raise HTTPException(
                status_code=400, detail="Either user_id or share_token required"
            )

        media_service = MediaService(db)

        # Convert user_id string to UUID if provided
        user_uuid = UUID(user_id) if user_id else None

        details = await media_service.get_media_details(media_id, user_uuid)

        if not details:
            raise HTTPException(status_code=404, detail="Media details not found")

        return details

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{media_id}/details", response_model=MediaDetailsDetailedResponse)
async def update_media_details_complete(
    media_id: str,
    details_update: MediaDetailsCompleteUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update complete media details."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_details = await media_service.update_media_details_complete(
            media_id, details_update.model_dump(exclude_unset=True), user_uuid
        )

        if not updated_details:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_details

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{media_id}/details/technical", response_model=MediaResponse)
async def update_technical_metadata_only(
    media_id: str,
    technical_update: TechnicalMetadataUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update technical metadata only."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_media = await media_service.update_technical_metadata_only(
            media_id,
            technical_update.technical_metadata,
            technical_update.merge_strategy,
            user_uuid,
        )

        if not updated_media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_media

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{media_id}/details/user", response_model=MediaResponse)
async def update_user_metadata_only(
    media_id: str,
    user_metadata_update: UserMetadataUpdateRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update user metadata only."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_media = await media_service.update_user_metadata_only(
            media_id,
            user_metadata_update.user_metadata,
            user_metadata_update.merge_strategy,
            user_uuid,
        )

        if not updated_media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_media

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{media_id}/metadata/custom", response_model=Dict[str, Any])
async def get_custom_metadata_fields(
    media_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get custom user-defined metadata fields."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        custom_metadata = await media_service.get_custom_metadata_fields(
            media_id, user_uuid
        )

        if custom_metadata is None:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return custom_metadata

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{media_id}/metadata/custom", response_model=MediaResponse)
async def add_custom_metadata_field(
    media_id: str,
    field_request: CustomMetadataFieldRequest,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Add custom metadata field."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_media = await media_service.add_custom_metadata_field(
            media_id,
            field_request.field_name,
            field_request.field_value,
            field_request.field_type.value if field_request.field_type else "string",
            user_uuid,
        )

        if not updated_media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_media

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{media_id}/metadata/custom/{field_name}", response_model=MediaResponse)
async def update_custom_metadata_field(
    media_id: str,
    field_name: str,
    field_value: Any,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Update custom metadata field."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_media = await media_service.update_custom_metadata_field(
            media_id, field_name, field_value, user_uuid
        )

        if not updated_media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_media

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{media_id}/metadata/custom/{field_name}", response_model=MediaResponse)
async def delete_custom_metadata_field(
    media_id: str,
    field_name: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    """Delete custom metadata field."""
    try:
        media_service = MediaService(db)
        user_uuid = UUID(user_id)

        updated_media = await media_service.delete_custom_metadata_field(
            media_id, field_name, user_uuid
        )

        if not updated_media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        return updated_media

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metadata/bulk-update", response_model=BulkMetadataOperationResponse)
async def bulk_update_metadata(
    bulk_request: BulkMetadataUpdateRequest,
    db: Session = Depends(get_db),
):
    """Bulk update metadata for multiple media files."""
    try:
        media_service = MediaService(db)

        results = await media_service.bulk_update_metadata(
            bulk_request.media_ids,
            bulk_request.metadata_updates,
            bulk_request.update_type,
            bulk_request.merge_strategy,
            bulk_request.user_id,
        )

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metadata/bulk-export", response_model=MetadataExportResponse)
async def bulk_export_metadata(
    export_request: MetadataExportRequest,
    db: Session = Depends(get_db),
):
    """Export metadata for multiple files."""
    try:
        media_service = MediaService(db)

        export_data = await media_service.export_metadata(
            export_request.media_ids,
            export_request.export_format,
            export_request.include_technical,
            export_request.include_user,
            export_request.include_system,
            export_request.user_id,
        )

        return export_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metadata/bulk-import", response_model=MetadataImportResponse)
async def bulk_import_metadata(
    import_request: MetadataImportRequest,
    db: Session = Depends(get_db),
):
    """Import metadata from file."""
    try:
        # This would need more complex implementation for actual file import
        # For now, return a placeholder response
        return {
            "total_records": 0,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "import_errors": [],
            "import_summary": {"message": "Import functionality not yet implemented"},
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metadata/search", response_model=MetadataSearchResponse)
async def search_by_metadata(
    search_request: MetadataSearchRequest,
    db: Session = Depends(get_db),
):
    """Search media by metadata values."""
    try:
        media_service = MediaService(db)

        results = await media_service.search_by_metadata(
            search_request.search_criteria,
            search_request.search_type,
            (
                [mt.value for mt in search_request.media_types]
                if search_request.media_types
                else None
            ),
            search_request.user_id,
            search_request.skip,
            search_request.limit,
        )

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metadata/analytics", response_model=MetadataAnalyticsResponse)
async def get_metadata_analytics(
    analytics_request: MetadataAnalyticsRequest,
    db: Session = Depends(get_db),
):
    """Get metadata usage analytics."""
    try:
        media_service = MediaService(db)

        analytics = await media_service.get_metadata_analytics(
            analytics_request.analysis_type,
            (
                [mt.value for mt in analytics_request.media_types]
                if analytics_request.media_types
                else None
            ),
            analytics_request.user_id,
        )

        # Add the analysis_type to the response
        analytics["analysis_type"] = analytics_request.analysis_type

        return analytics

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metadata/validation", response_model=MetadataValidationResponse)
async def validate_metadata(
    validation_request: MetadataValidationRequest,
    db: Session = Depends(get_db),
):
    """Validate metadata against schemas and rules."""
    try:
        media_service = MediaService(db)

        validation_results = await media_service.validate_metadata(
            validation_request.metadata,
            (
                validation_request.media_type.value
                if validation_request.media_type
                else None
            ),
            validation_request.validation_level,
        )

        return validation_results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metadata/schemas/{media_type}", response_model=MetadataSchemaResponse)
async def get_metadata_schema_for_media_type(
    media_type: str,
    db: Session = Depends(get_db),
):
    """Get metadata schema for a specific media type."""
    try:
        media_service = MediaService(db)

        schema_data = await media_service.get_metadata_schema_for_media_type(media_type)

        return schema_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# METADATA TEMPLATES SYSTEM
# ============================================================================


@router.get("/metadata/templates", response_model=List[Dict[str, Any]])
async def list_metadata_templates(
    user_id: str,
    db: Session = Depends(get_db),
):
    """List metadata templates."""
    try:
        # Return mock template system for now -
        # would be implemented with database
        templates = [
            {
                "id": "photography_standard",
                "name": "Standard Photography Metadata",
                "description": ("Standard metadata fields for " "photography projects"),
                "category": "photography",
                "fields": [
                    {"name": "photographer", "type": "string", "required": True},
                    {"name": "location", "type": "string", "required": False},
                    {"name": "shoot_date", "type": "date", "required": True},
                    {"name": "equipment", "type": "string", "required": False},
                ],
                "created_by": user_id,
                "created_at": "2025-07-15T00:00:00Z",
            },
            {
                "id": "video_production",
                "name": "Video Production Metadata",
                "description": "Metadata template for video production " "workflows",
                "category": "video",
                "fields": [
                    {"name": "director", "type": "string", "required": True},
                    {"name": "project_name", "type": "string", "required": True},
                    {"name": "scene_number", "type": "integer", "required": False},
                    {"name": "take_number", "type": "integer", "required": False},
                ],
                "created_by": user_id,
                "created_at": "2025-07-15T00:00:00Z",
            },
        ]

        return templates

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metadata/templates", response_model=Dict[str, Any])
async def create_metadata_template(
    template_request: Dict[str, Any],
    user_id: str,
    db: Session = Depends(get_db),
):
    """Create metadata template."""
    try:
        # Mock template creation - would be implemented with database
        template_id = f"template_{int(time.time())}"

        created_template = {
            "id": template_id,
            "name": template_request.get("name", "Untitled Template"),
            "description": template_request.get("description", ""),
            "category": template_request.get("category", "general"),
            "fields": template_request.get("fields", []),
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "created",
        }

        return created_template

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{media_id}/metadata/apply-template", response_model=MediaResponse)
async def apply_metadata_template(
    media_id: str,
    template_request: Dict[str, Any],
    user_id: str,
    db: Session = Depends(get_db),
):
    """Apply metadata template to media."""
    try:
        media_service = MediaService(db)

        # Get media
        media = await media_service.get_media(media_id, UUID(user_id))
        if not media:
            raise HTTPException(
                status_code=404, detail="Media not found or access denied"
            )

        # Mock template application - would apply template fields to media
        template_id = template_request.get("template_id")
        field_values = template_request.get("field_values", {})

        # For now, just add the template application info
        # to technical_metadata - mock implementation
        applied_info = {
            "template_id": template_id,
            "applied_at": datetime.utcnow().isoformat(),
            "applied_by": user_id,
            "field_values": field_values,
            "status": "applied",
        }

        # Mock template application - would update database
        # For now just return success status
        db.commit()

        return MediaResponse.model_validate(media)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# END ISSUE #016: Advanced Media Details and Metadata Management


@router.get("/{media_id}/video-properties")
async def get_video_properties(
    media_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get video properties including exact frame count from stored metadata.

    This endpoint provides video metadata that was extracted during upload,
    eliminating the need for preprocessing during face detection.
    """
    try:
        media_service = MediaService(db)

        # Get video properties from stored metadata
        properties = media_service.get_video_properties(media_id, current_user.user_id)

        if not properties:
            raise HTTPException(
                status_code=404, detail="Video not found or metadata not available"
            )

        return {
            "media_id": media_id,
            "video_properties": properties,
            "metadata_available": True,
            "preprocessing_required": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/refresh-metadata")
async def refresh_metadata_for_videos_with_errors(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh video metadata for videos that have video_error in technical_metadata.

    This endpoint fixes cached metadata issues after storage path configuration changes.
    """
    try:
        media_service = MediaService(db)

        # Find videos with video_error in metadata
        videos_with_errors = []
        all_media = (
            db.query(Media)
            .filter(
                Media.media_type == "video",
                Media.processing_status == "completed",
            )
            .all()
        )

        for media in all_media:
            if (
                media.technical_metadata
                and isinstance(media.technical_metadata, dict)
                and media.technical_metadata.get("video_error")
            ):
                videos_with_errors.append(media)

        if not videos_with_errors:
            return {
                "message": "No videos with metadata errors found",
                "videos_processed": 0,
                "videos_fixed": 0,
                "videos_failed": 0,
            }

        # Process each video
        videos_fixed = 0
        videos_failed = 0

        for media in videos_with_errors:
            try:
                # Clear the error from technical_metadata
                if "video_error" in media.technical_metadata:
                    del media.technical_metadata["video_error"]

                # Re-extract video metadata
                await media_service._extract_video_metadata(media)

                # Check if error was resolved
                if not media.technical_metadata.get("video_error"):
                    videos_fixed += 1
                else:
                    videos_failed += 1

                # Commit changes for this video
                db.commit()

            except Exception as e:
                print(f"Failed to refresh metadata for {media.uuid}: {e}")
                videos_failed += 1
                db.rollback()

        return {
            "message": f"Metadata refresh complete",
            "videos_processed": len(videos_with_errors),
            "videos_fixed": videos_fixed,
            "videos_failed": videos_failed,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
