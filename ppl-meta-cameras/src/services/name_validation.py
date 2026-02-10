"""Validation utilities for camera names and collection names."""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.models.camera import Camera

logger = logging.getLogger(__name__)


def validate_camera_name_unique(
    db: Session,
    name: str,
    exclude_device_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate that a camera name is unique across the platform.
    
    Args:
        db: Database session
        name: Camera name to validate
        exclude_device_id: Optional device_id to exclude from check (for updates)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        query = db.query(Camera).filter(Camera.name == name)
        
        # For updates, exclude the camera being updated
        if exclude_device_id:
            query = query.filter(Camera.device_id != exclude_device_id)
        
        existing = query.first()
        
        if existing:
            return False, f"Camera name '{name}' is already in use. Please choose a unique name."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating camera name uniqueness: {e}")
        return False, "Failed to validate camera name"


def sanitize_camera_name(name: str) -> str:
    """
    Sanitize camera name to ensure it's valid.
    
    Args:
        name: Raw camera name
        
    Returns:
        Sanitized camera name
    """
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Replace multiple spaces with single space
    import re
    name = re.sub(r'\s+', ' ', name)
    
    # Limit length
    if len(name) > 255:
        name = name[:255]
    
    return name


def generate_unique_camera_name(db: Session, base_name: str) -> str:
    """
    Generate a unique camera name by appending a number if needed.
    
    Args:
        db: Database session
        base_name: Base name to start with
        
    Returns:
        Unique camera name
    """
    name = sanitize_camera_name(base_name)
    
    # Check if base name is unique
    is_valid, _ = validate_camera_name_unique(db, name)
    if is_valid:
        return name
    
    # Append number to make it unique
    counter = 1
    while counter < 1000:  # Safety limit
        candidate = f"{name} ({counter})"
        is_valid, _ = validate_camera_name_unique(db, candidate)
        if is_valid:
            return candidate
        counter += 1
    
    # Fallback to UUID suffix
    import uuid
    return f"{name} ({uuid.uuid4().hex[:8]})"
