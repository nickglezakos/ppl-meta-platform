"""Edge camera management endpoints - Platform proxy to edge camera management API."""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session

from src.security.auth import get_current_user
from src.database import get_db
from src.models.camera import Camera, CameraType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge-cameras", tags=["edge-cameras"])


class EdgeConfigUpdate(BaseModel):
    """Edge camera configuration update."""
    updates: Dict[str, Any]


class EdgePlatformConfig(BaseModel):
    """Edge camera platform configuration."""
    discovery_ip: str
    discovery_port: int = 8006
    cameras_port: int = 8005
    use_nginx: bool = False
    api_key: Optional[str] = None


class EdgeControlRequest(BaseModel):
    """Edge camera control request."""
    scope: Optional[str] = "application"
    service: Optional[str] = None


class RegisterEdgeCameraRequest(BaseModel):
    """Request model for registering an edge camera."""
    name: str
    device_id: str
    ip_address: str
    management_port: int = 9001
    stream_port: int = 8554


@router.post("/register-edge")
async def register_edge_camera(
    request: RegisterEdgeCameraRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a new edge camera in the database."""
    try:
        # Validate and ensure proper UUID format
        from src.services.name_validation import validate_camera_name_unique, sanitize_camera_name
        from src.services.auto_naming_service import generate_auto_camera_name
        from src.services.device_id_service import ensure_valid_uuid
        
        # Convert device_id to proper UUID (handles legacy edge-camera-XXX format)
        device_id = ensure_valid_uuid(request.device_id, legacy_metadata={'ip': request.ip_address})
        
        # Handle camera name
        if request.name:
            camera_name = sanitize_camera_name(request.name)
            is_valid, error_msg = validate_camera_name_unique(db, camera_name)
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=error_msg
                )
        else:
            # Auto-generate unique name
            camera_name = generate_auto_camera_name(db, CameraType.EDGE)
        
        # Check if camera already exists
        existing = db.query(Camera).filter(
            Camera.device_id == device_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Edge camera with device_id '{request.device_id}' already exists"
            )
        
        # Create connection string
        connection_string = f"edge://{request.ip_address}:{request.stream_port}"
        
        # Create new camera record
        new_camera = Camera(
            name=camera_name,  # Use sanitized and validated name
            device_id=device_id,  # Use validated UUID
            camera_type=CameraType.EDGE,
            connection_string=connection_string,
            status="active",
            is_active=True
        )
        
        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)
        
        logger.info(f"✅ Registered edge camera: {request.name} ({request.device_id}) at {request.ip_address}")
        
        return {
            "success": True,
            "message": "Edge camera registered successfully",
            "camera": {
                "id": new_camera.id,
                "name": new_camera.name,
                "device_id": new_camera.device_id,
                "camera_type": new_camera.camera_type.value,
                "connection_string": new_camera.connection_string,
                "status": new_camera.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register edge camera: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register edge camera: {str(e)}"
        )


async def get_edge_camera_url(device_id: str, db: Session = Depends(get_db)) -> str:
    """
    Get edge camera management API URL from device ID.
    
    Looks up the edge camera in the database and returns its management API URL.
    Edge cameras expose their management API on port 9001.
    """
    # Query database for edge camera
    camera = db.query(Camera).filter(
        Camera.device_id == device_id,
        Camera.camera_type == CameraType.EDGE
    ).first()
    
    if not camera:
        logger.error(f"Edge camera {device_id} not found in database")
        raise HTTPException(status_code=404, detail=f"Edge camera {device_id} not found")
    
    logger.info(f"Found camera record: device_id={camera.device_id}, connection_string={camera.connection_string}")
    
    # Extract IP from connection string (format: edge://IP:PORT or just IP)
    ip_address = None
    if camera.connection_string:
        if camera.connection_string.startswith("edge://"):
            # Format: edge://192.168.1.100:8554
            ip_port = camera.connection_string.replace("edge://", "")
            ip_address = ip_port.split(":")[0]
        else:
            # Format: 192.168.1.100 or 192.168.1.100:8554
            ip_address = camera.connection_string.split(":")[0]
    
    if not ip_address or ip_address == device_id:
        logger.error(f"Edge camera {device_id} has invalid connection_string: {camera.connection_string}")
        raise HTTPException(
            status_code=503, 
            detail=f"Edge camera {device_id} has no valid IP address configured (connection_string: {camera.connection_string})"
        )
    
    management_url = f"http://{ip_address}:9001"
    logger.info(f"Edge camera {device_id} management URL: {management_url}")
    
    return management_url


async def proxy_to_edge_camera(
    device_id: str,
    method: str,
    endpoint: str,
    db: Session,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Proxy request to edge camera management API.
    
    Args:
        device_id: Edge camera device ID
        method: HTTP method (GET, POST, PUT)
        endpoint: API endpoint path
        db: Database session
        json_data: JSON body data
        params: Query parameters
        token: Bearer token for authentication
        
    Returns:
        Response from edge camera
    """
    edge_url = await get_edge_camera_url(device_id, db)
    full_url = f"{edge_url}{endpoint}"
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                response = await client.get(full_url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(full_url, json=json_data, headers=headers)
            elif method == "PUT":
                response = await client.put(full_url, json=json_data, headers=headers)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Edge camera {device_id} returned error {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Edge camera error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to edge camera {device_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach edge camera {device_id}: {str(e)}"
        )


@router.get("/{device_id}/config")
async def get_edge_camera_config(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get edge camera configuration."""
    logger.info(f"Getting configuration for edge camera {device_id}")
    
    # Use platform JWT for edge camera authentication
    token = current_user.get("token")  # Assuming token is available in user context
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="GET",
        endpoint="/api/config",
        token=token
    )
    
    return result


@router.put("/{device_id}/config")
async def update_edge_camera_config(
    device_id: str,
    config_update: EdgeConfigUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update edge camera configuration."""
    logger.info(f"Updating configuration for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="PUT",
        endpoint="/api/config",
        json_data=config_update.dict(),
        token=token
    )
    
    return result


@router.post("/{device_id}/config/platform")
async def configure_edge_camera_platform(
    device_id: str,
    platform_config: EdgePlatformConfig,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Configure edge camera platform connection."""
    logger.info(f"Configuring platform connection for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="POST",
        endpoint="/api/config/platform",
        json_data=platform_config.dict(),
        token=token
    )
    
    return result


@router.post("/{device_id}/control/start")
async def start_edge_camera(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start edge camera streaming."""
    logger.info(f"Starting streaming for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="POST",
        endpoint="/api/control/start",
        token=token
    )
    
    return result


@router.post("/{device_id}/control/stop")
async def stop_edge_camera(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop edge camera streaming."""
    logger.info(f"Stopping streaming for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="POST",
        endpoint="/api/control/stop",
        token=token
    )
    
    return result


@router.post("/{device_id}/control/restart")
async def restart_edge_camera(
    device_id: str,
    control_req: EdgeControlRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restart edge camera application or system."""
    logger.info(f"Restarting edge camera {device_id} (scope: {control_req.scope})")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="POST",
        endpoint="/api/control/restart",
        json_data=control_req.dict(),
        token=token
    )
    
    return result


@router.post("/{device_id}/control/reconnect")
async def reconnect_edge_camera(
    device_id: str,
    control_req: EdgeControlRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reconnect edge camera to platform services."""
    logger.info(f"Reconnecting edge camera {device_id} (service: {control_req.service})")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="POST",
        endpoint="/api/control/reconnect",
        json_data=control_req.dict(),
        token=token
    )
    
    return result


@router.get("/{device_id}/logs")
async def get_edge_camera_logs(
    device_id: str,
    lines: int = Query(100, ge=1, le=1000),
    follow: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get edge camera logs."""
    logger.info(f"Getting logs for edge camera {device_id} (lines: {lines})")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="GET",
        endpoint="/api/logs",
        params={"lines": lines, "follow": follow},
        token=token
    )
    
    return result


@router.get("/{device_id}/status")
async def get_edge_camera_status(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get edge camera detailed status."""
    logger.info(f"Getting status for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="GET",
        endpoint="/api/status",
        token=token
    )
    
    return result


@router.get("/{device_id}/diagnostics/network")
async def get_edge_camera_network_diagnostics(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run network diagnostics on edge camera."""
    logger.info(f"Running network diagnostics for edge camera {device_id}")
    
    token = current_user.get("token")
    
    result = await proxy_to_edge_camera(
        db=db,
        device_id=device_id,
        method="GET",
        endpoint="/api/diagnostics/network",
        token=token
    )
    
    return result
