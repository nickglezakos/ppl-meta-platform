"""Validation utilities for collection names."""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from src.models.media import MediaCollection

logger = logging.getLogger(__name__)


def validate_collection_name_unique(
    db: Session,
    name: str,
    exclude_uuid: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate that a collection name is unique across the platform.
    
    Args:
        db: Database session
        name: Collection name to validate
        exclude_uuid: Optional collection UUID to exclude from check (for updates)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        query = db.query(MediaCollection).filter(MediaCollection.name == name)
        
        # For updates, exclude the collection being updated
        if exclude_uuid:
            from uuid import UUID
            query = query.filter(MediaCollection.uuid != UUID(exclude_uuid))
        
        existing = query.first()
        
        if existing:
            return False, f"Collection name '{name}' is already in use. Please choose a unique name."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating collection name uniqueness: {e}")
        return False, "Failed to validate collection name"


def sanitize_collection_name(name: str) -> str:
    """
    Sanitize collection name to ensure it's valid.
    
    Args:
        name: Raw collection name
        
    Returns:
        Sanitized collection name
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
