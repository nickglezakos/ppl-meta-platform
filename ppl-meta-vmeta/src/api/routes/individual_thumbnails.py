"""
Individual Thumbnails API Routes
Endpoints for generating and retrieving individual thumbnails.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, status

from api.dependencies import get_groups_manager
from services.individual_thumbnail_service import IndividualThumbnailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/individuals", tags=["individual-thumbnails"])


# Dependency to get thumbnail service
async def get_thumbnail_service() -> IndividualThumbnailService:
    """Get IndividualThumbnailService instance"""
    from main import db_client
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    service = IndividualThumbnailService(db_client)
    return service


@router.get("/{individual_id}/thumbnail")
async def get_thumbnail(
    individual_id: str,
    size: str = Query("medium", regex="^(small|medium|large)$"),
    service: IndividualThumbnailService = Depends(get_thumbnail_service),
):
    """
    Get thumbnail image for an individual.
    
    Args:
        individual_id: Individual identifier
        size: Thumbnail size (small=128, medium=256, large=512)
        service: ThumbnailService dependency
        
    Returns:
        JPEG image response or 404 if not found
    """
    try:
        thumbnail_data = await service.get_thumbnail_data(individual_id, size=size)
        
        if not thumbnail_data:
            # Generate fallback placeholder
            placeholder = service.generate_fallback_placeholder(size=size)
            
            # Extract base64 data and decode
            if placeholder.startswith("data:image"):
                import base64
                base64_data = placeholder.split(",")[1]
                thumbnail_data = base64.b64decode(base64_data)
            else:
                thumbnail_data = placeholder.encode()
        
        return Response(
            content=thumbnail_data,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting thumbnail for {individual_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thumbnail: {str(e)}"
        )
    finally:
        await service.close()


@router.post("/{individual_id}/thumbnail/generate")
async def generate_thumbnail(
    individual_id: str,
    size: str = Query("medium", regex="^(small|medium|large)$"),
    service: IndividualThumbnailService = Depends(get_thumbnail_service),
):
    """
    Generate or regenerate thumbnail for an individual.
    
    Args:
        individual_id: Individual identifier
        size: Thumbnail size preset
        service: ThumbnailService dependency
        
    Returns:
        Thumbnail URL and generation timestamp
    """
    try:
        from datetime import datetime
        
        thumbnail_url = await service.generate_thumbnail(individual_id, size=size)
        
        if not thumbnail_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not generate thumbnail for individual {individual_id}"
            )
        
        return {
            "thumbnail_url": thumbnail_url,
            "generated_at": datetime.utcnow().isoformat(),
            "size": size,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating thumbnail for {individual_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )
    finally:
        await service.close()


@router.post("/{individual_id}/thumbnail/upload")
async def upload_thumbnail(
    individual_id: str,
    file: UploadFile = File(...),
    service: IndividualThumbnailService = Depends(get_thumbnail_service),
):
    """
    Upload a custom thumbnail for an individual.
    
    Args:
        individual_id: Individual identifier
        file: Image file upload
        service: ThumbnailService dependency
        
    Returns:
        Thumbnail URL
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Read file content
        image_data = await file.read()
        
        # Update thumbnail
        thumbnail_url = await service.update_thumbnail(individual_id, image_data)
        
        if not thumbnail_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process uploaded image"
            )
        
        return {
            "thumbnail_url": thumbnail_url,
            "filename": file.filename,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading thumbnail for {individual_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload thumbnail: {str(e)}"
        )
    finally:
        await service.close()


@router.get("/{individual_id}/thumbnail/url")
async def get_thumbnail_url(
    individual_id: str,
    service: IndividualThumbnailService = Depends(get_thumbnail_service),
):
    """
    Get the thumbnail URL for an individual without downloading the image.
    
    Args:
        individual_id: Individual identifier
        service: ThumbnailService dependency
        
    Returns:
        Thumbnail URL or None
    """
    try:
        thumbnail_url = await service.get_thumbnail_url(individual_id)
        
        return {
            "individual_id": individual_id,
            "thumbnail_url": thumbnail_url,
            "has_thumbnail": thumbnail_url is not None,
        }
        
    except Exception as e:
        logger.error(f"Error getting thumbnail URL for {individual_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thumbnail URL: {str(e)}"
        )
    finally:
        await service.close()
