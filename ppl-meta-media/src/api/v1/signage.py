"""
Signage Simple Player API Routes

REST API endpoints for video list management, device control, and synchronization.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...auth import AuthUser, get_current_user
from ...database import get_db
from ...schemas.signage import (
    ErrorResponse,
    PlaybackControlRequest,
    PlaybackControlResponse,
    SignageDeviceListResponse,
    SignageDeviceRegister,
    SignageDeviceResponse,
    SignageDeviceUpdate,
    SuccessResponse,
    SyncHistoryListResponse,
    SyncMode,
    SyncRequest,
    SyncResponse,
    VideoListCreate,
    VideoListDetailResponse,
    VideoListListResponse,
    VideoListResponse,
    VideoListSummary,
    VideoListUpdate,
)
from ...services.signage_service import (
    SignagePlaybackService,
    SignageService,
    SignageSyncService,
)
from ...services.signage_etl_worker import (
    get_batch_sync_manager,
    get_etl_worker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signage", tags=["signage"])


# ============================================================================
# Video List Endpoints
# ============================================================================


@router.post(
    "/video-lists",
    response_model=VideoListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new video list",
    description="Create a video list from one or more user collections",
)
async def create_video_list(
    data: VideoListCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoListResponse:
    """
    Create a new video list from user collections.

    - **name**: User-defined name for the video list
    - **collection_ids**: List of collection IDs to aggregate videos from
    - **video_order**: Optional manual ordering of videos
    - **loop_mode**: Playback loop mode (continuous, once, shuffle, repeat_one)
    """
    try:
        from uuid import UUID
        user_id = UUID(current_user.user_id)
        service = SignageService(db)

        video_list = service.create_video_list(user_id, data)

        return VideoListResponse.model_validate(video_list)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating video list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create video list",
        )


@router.get(
    "/video-lists",
    response_model=VideoListListResponse,
    summary="List video lists",
    description="Get paginated list of user's video lists with filtering",
)
async def list_video_lists(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    search: Optional[str] = Query(None, description="Search by name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoListListResponse:
    """
    List user's video lists with pagination and filtering.

    - **page**: Page number (1-indexed)
    - **page_size**: Number of results per page (max 100)
    - **search**: Search term for video list name
    - **is_active**: Filter by active status
    """
    try:
        user_id = UUID(current_user.user_id)
        service = SignageService(db)

        video_lists, total_count = service.list_video_lists(
            user_id, page, page_size, search, is_active
        )

        # Convert to summary format
        summaries = [
            VideoListSummary(
                id=vl.id,
                uuid=vl.uuid,
                name=vl.name,
                video_count=vl.video_count,
                total_duration_ms=vl.total_duration_ms,
                is_active=vl.is_active,
                is_published=vl.is_published,
                last_synced_at=None,  # TODO: Get from sync history
                created_at=vl.created_at,
            )
            for vl in video_lists
        ]

        return VideoListListResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            results=summaries,
        )

    except Exception as e:
        logger.error(f"Error listing video lists: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list video lists",
        )


@router.get(
    "/video-lists/{list_uuid}",
    response_model=VideoListDetailResponse,
    summary="Get video list details",
    description="Get detailed information about a video list including all videos",
)
async def get_video_list(
    list_uuid: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoListDetailResponse:
    """
    Get detailed information about a specific video list.

    - **list_uuid**: UUID of the video list
    """
    try:
        user_id = current_user.user_id
        service = SignageService(db)

        video_list = service.get_video_list_by_uuid(
            list_uuid, user_id, include_items=True
        )

        if not video_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video list not found or unauthorized",
            )

        return VideoListDetailResponse.model_validate(video_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get video list",
        )


@router.put(
    "/video-lists/{list_uuid}",
    response_model=VideoListResponse,
    summary="Update video list",
    description="Update video list properties",
)
async def update_video_list(
    list_uuid: UUID,
    data: VideoListUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VideoListResponse:
    """
    Update a video list's properties.

    - **list_uuid**: UUID of the video list
    - **data**: Fields to update
    """
    try:
        from uuid import UUID as UUIDType
        user_id = UUIDType(current_user.user_id)
        service = SignageService(db)

        # Get video list to find ID
        video_list = service.get_video_list_by_uuid(list_uuid, user_id)
        if not video_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video list not found or unauthorized",
            )

        # Update
        updated_list = service.update_video_list(video_list.id, user_id, data)

        return VideoListResponse.model_validate(updated_list)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating video list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update video list",
        )


@router.delete(
    "/video-lists/{list_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete video list",
    description="Delete a video list",
)
async def delete_video_list(
    list_uuid: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a video list.

    - **list_uuid**: UUID of the video list to delete
    """
    try:
        from uuid import UUID as UUIDType
        user_id = UUIDType(current_user.user_id)
        service = SignageService(db)

        # Get video list to find ID
        video_list = service.get_video_list_by_uuid(list_uuid, user_id)
        if not video_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video list not found or unauthorized",
            )

        # Delete
        service.delete_video_list(video_list.id, user_id)

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete video list",
        )


# ============================================================================
# ETL Synchronization Endpoints
# ============================================================================


@router.post(
    "/etl/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync video list to device(s)",
    description="Synchronize a video list to one or more signage devices",
)
async def sync_video_list(
    data: SyncRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResponse:
    """
    Synchronize a video list to signage device(s).

    This endpoint initiates an ETL process to push the video list metadata
    to the specified devices. The sync can be full (all videos) or incremental
    (only changes since last sync).

    - **video_list_id**: UUID of the video list to sync
    - **target_devices**: List of device UUIDs to sync to
    - **sync_mode**: "full" or "incremental"
    - **force_update**: Force re-sync even if up-to-date
    """
    try:
        user_id = current_user.user_id
        service = SignageSyncService(db)

        # For now, sync to first device (can be extended to batch sync)
        device_id = data.target_devices[0]

        history = await service.sync_video_list_to_device(
            data.video_list_id,
            device_id,
            data.sync_mode,
            user_id,
            data.force_update,
        )

        return SyncResponse(
            sync_job_id=history.uuid,
            status=history.sync_status,
            target_device_count=len(data.target_devices),
            estimated_completion_at=None,  # Could be calculated based on video count
            message=f"Sync initiated for {len(data.target_devices)} device(s)",
        )

    except ValueError as e:
        logger.warning(f"Validation error during sync: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during sync: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Device communication error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error during sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot reach device: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"\n{'='*80}\n❌ SYNC ERROR:\n{error_details}\n{'='*80}\n", flush=True)
        logger.error(f"Error syncing video list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync video list: {str(e)}",
        )


@router.get(
    "/etl/sync-history",
    response_model=SyncHistoryListResponse,
    summary="Get sync history",
    description="Get synchronization history with filtering",
)
async def get_sync_history(
    video_list_id: Optional[int] = Query(None, description="Filter by video list ID"),
    device_id: Optional[UUID] = Query(None, description="Filter by device UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
) -> SyncHistoryListResponse:
    """
    Get synchronization history with optional filtering.

    - **video_list_id**: Filter by video list database ID
    - **device_id**: Filter by signage device UUID
    - **page**: Page number (1-indexed)
    - **page_size**: Number of results per page
    """
    try:
        service = SignageService(db)

        history, total_count = service.get_sync_history(
            video_list_id, device_id, page, page_size
        )

        return SyncHistoryListResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            results=history,
        )

    except Exception as e:
        logger.error(f"Error getting sync history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync history",
        )


# ============================================================================
# Remote Playback Control Endpoints
# ============================================================================


@router.post(
    "/playback/control",
    response_model=PlaybackControlResponse,
    summary="Control playback on device(s)",
    description="Send playback control commands to signage devices",
)
async def control_playback(
    data: PlaybackControlRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaybackControlResponse:
    """
    Send playback control command to one or more signage devices.

    Supported commands:
    - **start**: Start playing a video list
    - **pause**: Pause playback
    - **resume**: Resume paused playback
    - **stop**: Stop playback and reset
    - **next**: Skip to next video
    - **previous**: Go to previous video

    - **device_ids**: List of device UUIDs to control
    - **command**: Playback command to execute
    - **video_list_id**: Video list UUID (required for 'start' command)
    - **parameters**: Optional parameters (volume, speed, start_index)
    """
    try:
        logger.info(f"🎮 Playback control request received:")
        logger.info(f"   device_ids: {data.device_ids}")
        logger.info(f"   command: {data.command}")
        logger.info(f"   video_list_id: {data.video_list_id}")
        logger.info(f"   parameters: {data.parameters}")
        
        service = SignagePlaybackService(db)

        result = await service.control_playback(data)

        return PlaybackControlResponse(
            command_id=UUID("00000000-0000-0000-0000-000000000001"),  # TODO: Generate proper ID
            status="executed" if result["affected_devices"] > 0 else "failed",
            affected_devices=result["affected_devices"],
            executed_at=__import__("datetime").datetime.utcnow(),
            message=f"Command sent to {result['affected_devices']}/{result['total_devices']} devices",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error controlling playback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to control playback",
        )


# ============================================================================
# Signage Device Management Endpoints
# ============================================================================


@router.post(
    "/devices",
    response_model=SignageDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a signage device",
    description="Register a new signage device or update existing one",
)
async def register_device(
    data: SignageDeviceRegister,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SignageDeviceResponse:
    """
    Register a signage device with the media service.

    This endpoint is typically called by the signage device itself during
    initialization, or by an administrator to manually register a device.

    - **device_id**: Unique device identifier from discovery service
    - **device_name**: Human-readable device name
    - **ip_address**: Device IP address
    - **port**: HTTP server port on device
    """
    try:
        user_id = current_user.user_id
        service = SignageService(db)

        device_data = data.dict(exclude={"device_id"})
        device = service.register_device(data.device_id, device_data, user_id)

        return SignageDeviceResponse.model_validate(device)

    except Exception as e:
        logger.error(f"Error registering device: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device",
        )


@router.get(
    "/devices",
    response_model=SignageDeviceListResponse,
    summary="List signage devices",
    description="Get paginated list of signage devices",
)
async def list_devices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    is_online: Optional[bool] = Query(None, description="Filter by online status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
) -> SignageDeviceListResponse:
    """
    List registered signage devices with filtering.

    - **page**: Page number (1-indexed)
    - **page_size**: Number of results per page
    - **is_online**: Filter by online status
    - **is_active**: Filter by active status
    """
    try:
        service = SignageService(db)

        devices, total_count = service.list_devices(page, page_size, is_online, is_active)

        return SignageDeviceListResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            results=devices,
        )

    except Exception as e:
        logger.error(f"Error listing devices: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list devices",
        )


@router.get(
    "/devices/{device_id}",
    response_model=SignageDeviceResponse,
    summary="Get device details",
    description="Get detailed information about a signage device",
)
async def get_device(
    device_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SignageDeviceResponse:
    """
    Get detailed information about a signage device.

    - **device_id**: Device UUID
    """
    try:
        service = SignageService(db)

        device = service.get_device_by_id(device_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        return SignageDeviceResponse.model_validate(device)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get device",
        )


@router.patch(
    "/devices/{device_id}",
    response_model=SignageDeviceResponse,
    summary="Update device",
    description="Update device information",
)
async def update_device(
    device_id: UUID,
    data: SignageDeviceUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SignageDeviceResponse:
    """
    Update device information.

    - **device_id**: Device UUID
    - **data**: Fields to update
    """
    try:
        service = SignageService(db)

        device = service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        # Update fields
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(device, field):
                setattr(device, field, value)

        db.commit()
        db.refresh(device)

        return SignageDeviceResponse.model_validate(device)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device",
        )


@router.post(
    "/devices/{device_id}/heartbeat",
    response_model=SuccessResponse,
    summary="Send device heartbeat",
    description="Update device heartbeat timestamp",
)
async def device_heartbeat(
    device_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """
    Send heartbeat to keep device marked as online.

    Signage devices should call this endpoint every 30-60 seconds.

    - **device_id**: Device UUID
    """
    try:
        service = SignageService(db)

        success = service.update_device_heartbeat(device_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )

        return SuccessResponse(
            success=True,
            message="Heartbeat recorded",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording heartbeat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record heartbeat",
        )


# ============================================================================
# Batch Sync Endpoints
# ============================================================================


@router.post(
    "/etl/batch-sync",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch sync video lists to devices",
    description="Sync one or more video lists to one or more devices",
)
async def batch_sync(
    video_list_ids: List[int],
    device_ids: List[UUID],
    sync_mode: SyncMode = SyncMode.FULL,
    force_update: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Batch synchronization of video lists to devices.

    This endpoint queues multiple sync jobs to efficiently sync
    multiple video lists to multiple devices.

    - **video_list_ids**: List of video list database IDs to sync
    - **device_ids**: List of device UUIDs to sync to
    - **sync_mode**: "full" or "incremental"
    - **force_update**: Force re-sync even if up-to-date
    """
    try:
        user_id = current_user.user_id
        batch_manager = get_batch_sync_manager()

        job_ids = await batch_manager.sync_lists_to_devices(
            video_list_ids, device_ids, sync_mode.value, user_id, force_update
        )

        return {
            "status": "accepted",
            "job_count": len(job_ids),
            "job_ids": [str(jid) for jid in job_ids],
            "video_list_count": len(video_list_ids),
            "device_count": len(device_ids),
            "message": f"Queued {len(job_ids)} sync job(s)",
        }

    except Exception as e:
        logger.error(f"Error creating batch sync: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch sync",
        )


@router.post(
    "/etl/sync-to-all",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync video list to all online devices",
    description="Sync a video list to all currently online devices",
)
async def sync_to_all_devices(
    video_list_id: int,
    sync_mode: SyncMode = SyncMode.FULL,
    force_update: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Sync a video list to all online devices.

    Convenient endpoint for broadcasting a video list to all connected devices.

    - **video_list_id**: Video list database ID to sync
    - **sync_mode**: "full" or "incremental"
    - **force_update**: Force re-sync even if up-to-date
    """
    try:
        user_id = current_user.user_id
        batch_manager = get_batch_sync_manager()

        job_id = await batch_manager.sync_to_all_online_devices(
            video_list_id, sync_mode.value, user_id, force_update
        )

        if job_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No online devices found",
            )

        return {
            "status": "accepted",
            "job_id": str(job_id),
            "message": "Sync job queued for all online devices",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating sync-to-all job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sync job",
        )


@router.get(
    "/etl/job-status/{job_id}",
    response_model=dict,
    summary="Get sync job status",
    description="Get the status of a queued sync job",
)
async def get_sync_job_status(job_id: UUID) -> dict:
    """
    Get the status of a sync job.

    - **job_id**: Sync job UUID
    """
    try:
        worker = get_etl_worker()
        status_data = await worker.get_job_status(job_id)

        if status_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sync job not found",
            )

        return status_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.get(
    "/health",
    response_model=dict,
    summary="Signage service health check",
    description="Check if the signage endpoints are operational",
)
async def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Health check endpoint for signage service.
    """
    try:
        # Simple database check
        db.execute("SELECT 1")

        return {
            "status": "healthy",
            "service": "signage",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "signage",
            "error": str(e),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }


@router.get(
    "/stream/{media_id}",
    summary="Stream media for signage devices",
    description="Unauthenticated video streaming endpoint for signage devices",
)
async def stream_signage_media(
    media_id: str,
    request: __import__("fastapi").Request,
    db: Session = Depends(get_db),
):
    """
    Stream media file for signage devices without authentication.
    Supports range requests for video playback.
    
    This is a special endpoint for signage devices that doesn't require
    user authentication since devices operate autonomously.
    """
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    from ...models.media import Media
    
    # Get media record
    try:
        media = db.query(Media).filter(Media.id == int(media_id)).first()
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
        
        file_path = Path(media.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found on disk")
        
        file_size = file_path.stat().st_size
        range_header = request.headers.get("Range")
        
        def generate_chunks(start: int, end: int):
            """Generate file chunks for streaming"""
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        # Handle range requests
        if range_header:
            range_str = range_header.replace("bytes=", "")
            range_parts = range_str.split("-")
            start = int(range_parts[0]) if range_parts[0] else 0
            end = int(range_parts[1]) if len(range_parts) > 1 and range_parts[1] else file_size - 1
            
            content_length = end - start + 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": media.mime_type or "video/mp4",
            }
            
            return StreamingResponse(
                generate_chunks(start, end),
                status_code=206,
                headers=headers,
            )
        
        # Full file streaming
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": media.mime_type or "video/mp4",
        }
        
        return StreamingResponse(
            generate_chunks(0, file_size - 1),
            headers=headers,
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid media ID")
    except Exception as e:
        logger.error(f"Error streaming signage media {media_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")
