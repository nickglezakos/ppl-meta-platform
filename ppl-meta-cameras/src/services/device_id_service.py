"""
Device ID Service - UUID validation and conversion utilities.

Handles migration from legacy device IDs to proper UUIDs while maintaining
backward compatibility for existing cameras.
"""

import re
import uuid as uuid_module
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


def ensure_valid_uuid(client_device_id: Optional[str], legacy_metadata: Optional[Dict] = None) -> str:
    """
    Validate client-provided ID OR convert to proper UUID.
    
    Args:
        client_device_id: Device ID from client (may be legacy format)
        legacy_metadata: Optional metadata to store with legacy ID mapping
    
    Returns:
        Valid UUID string
    
    Examples:
        - "550e8400-e29b-41d4-a716-446655440000" → accepted as-is
        - "edge-camera-12ab34cd" → converted to new UUID
        - "usb_camera_0" → converted to new UUID
        - None → generates new UUID
    """
    if not client_device_id:
        new_uuid = str(uuid_module.uuid4())
        logger.info(f"✅ Generated new UUID (no device_id provided): {new_uuid}")
        return new_uuid
    
    # Check if already valid UUID format (with or without hyphens)
    uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
    if re.match(uuid_pattern, client_device_id.lower()):
        # Normalize: ensure hyphens are present
        normalized = _normalize_uuid(client_device_id)
        logger.info(f"✅ Validated UUID format: {normalized}")
        return normalized
    
    # Legacy format detected - generate new UUID
    new_uuid = str(uuid_module.uuid4())
    logger.warning(
        f"⚠️ Converting legacy device_id '{client_device_id}' to UUID: {new_uuid}",
        extra={"legacy_id": client_device_id, "new_uuid": new_uuid, "metadata": legacy_metadata}
    )
    
    return new_uuid


def _normalize_uuid(uuid_str: str) -> str:
    """Normalize UUID string to standard format with hyphens."""
    # Remove any existing hyphens
    clean = uuid_str.replace('-', '').lower()
    
    # Add hyphens in standard positions
    return f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if string is a valid UUID format."""
    uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, uuid_str.lower()))


def generate_uuid() -> str:
    """Generate a new UUID v4."""
    return str(uuid_module.uuid4())
