"""
Auto-Naming Service - Generate unique camera names automatically.

Provides auto-numbering for camera names based on camera type,
ensuring uniqueness across the platform.
"""

from typing import Optional
from sqlalchemy.orm import Session
import logging

from src.models.camera import CameraType
from src.services.name_validation import validate_camera_name_unique

logger = logging.getLogger(__name__)


def generate_auto_camera_name(
    db: Session,
    camera_type: CameraType,
    index: Optional[int] = None,
    exclude_device_id: Optional[str] = None
) -> str:
    """
    Generate auto-numbered camera name with uniqueness guarantee.
    
    Args:
        db: Database session
        camera_type: Type of camera (USB, RTSP, EDGE, MOBILE)
        index: Optional starting index (used for USB cameras)
        exclude_device_id: Optional device_id to exclude from uniqueness check
    
    Returns:
        Unique camera name like "USB Camera 1", "RTSP Camera 2", etc.
    
    Examples:
        - USB Camera with index=0 → checks "USB Camera 1", "USB Camera 2", etc.
        - RTSP Camera → checks "RTSP Camera 1", "RTSP Camera 2", etc.
        - Edge Camera → checks "Edge Camera 1", "Edge Camera 2", etc.
    """
    # Base name by camera type
    type_prefix = {
        CameraType.USB: "USB Camera",
        CameraType.RTSP: "RTSP Camera",
        CameraType.EDGE: "Edge Camera",
        CameraType.MOBILE: "Mobile Camera",
        CameraType.IP: "IP Camera",
        CameraType.WEBCAM: "Webcam",
        CameraType.VIRTUAL: "Virtual Camera"
    }
    
    base = type_prefix.get(camera_type, "Camera")
    
    # For USB cameras, use detection index as starting point
    # For others, start from 1
    counter = (index + 1) if index is not None else 1
    
    # Find next available number
    max_attempts = 1000  # Safety limit
    attempts = 0
    
    while attempts < max_attempts:
        name = f"{base} {counter}"
        is_valid, _ = validate_camera_name_unique(
            db, 
            name, 
            exclude_device_id=exclude_device_id
        )
        
        if is_valid:
            logger.info(f"✅ Generated unique camera name: '{name}'")
            return name
        
        counter += 1
        attempts += 1
    
    # Fallback with UUID suffix (should never happen)
    import uuid
    fallback_name = f"{base} {uuid.uuid4().hex[:8]}"
    logger.error(
        f"⚠️ Could not find unique name after {max_attempts} attempts. "
        f"Using fallback: {fallback_name}"
    )
    return fallback_name


def suggest_camera_name(camera_type: CameraType, device_info: Optional[dict] = None) -> str:
    """
    Suggest a camera name based on type and device info (not guaranteed unique).
    
    This is useful for providing a default name in forms before validation.
    
    Args:
        camera_type: Type of camera
        device_info: Optional device information (model, manufacturer, etc.)
    
    Returns:
        Suggested camera name (may not be unique)
    """
    type_prefix = {
        CameraType.USB: "USB Camera",
        CameraType.RTSP: "RTSP Camera",
        CameraType.EDGE: "Edge Camera",
        CameraType.MOBILE: "Mobile Camera",
        CameraType.IP: "IP Camera",
        CameraType.WEBCAM: "Webcam",
        CameraType.VIRTUAL: "Virtual Camera"
    }
    
    base = type_prefix.get(camera_type, "Camera")
    
    # If device info available, try to make it more descriptive
    if device_info:
        if 'model' in device_info and device_info['model']:
            model = str(device_info['model'])[:20]  # Limit length
            return f"{base} - {model}"
        elif 'manufacturer' in device_info and device_info['manufacturer']:
            manufacturer = str(device_info['manufacturer'])[:20]
            return f"{base} - {manufacturer}"
    
    return f"{base} 1"
