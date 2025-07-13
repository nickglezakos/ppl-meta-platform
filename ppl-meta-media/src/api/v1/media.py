"""
Media API routes for PPL Meta Platform Media Service - API v1.
"""

import os
import sys
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from src.database import get_db
from src.schemas.media import (
    MediaCollectionResponse,
    MediaResponse,
    MediaSearchRequest,
    MediaShareResponse,
    MediaType,
    MediaUploadRequest,
)
from src.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])


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
                import json

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
        return MediaResponse.model_validate(media)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/search", response_model=List[MediaResponse])
async def search_media(
    user_id: Optional[str] = None,
    media_types: Optional[str] = None,  # Comma-separated MediaType values
    tags: Optional[str] = None,  # Comma-separated
    categories: Optional[str] = None,  # Comma-separated
    device_name: Optional[str] = None,
    device_manufacturer: Optional[str] = None,
    is_public: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """Search media with various filters including device information."""
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

        search_request = MediaSearchRequest(
            uploaded_by=UUID(user_id) if user_id else None,
            media_types=parsed_media_types,
            tags=tags.split(",") if tags else None,
            categories=categories.split(",") if categories else None,
            is_public=is_public,
            page=page,
            page_size=page_size,
        )

        media_list = await media_service.search_media(search_request)
        return [MediaResponse.model_validate(media) for media in media_list]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
