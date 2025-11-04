"""
MVR-People Integration Helper

Provides global access to MVR integration hook for triggering
automatic MVR-People creation on Individual lifecycle events.
"""

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Global MVR integration hook (initialized on startup)
_mvr_hook = None


def set_mvr_integration_hook(hook):
    """
    Set global MVR integration hook.
    
    Called during application startup to make hook available globally.
    
    Args:
        hook: MVRIntegrationHook instance
    """
    global _mvr_hook
    _mvr_hook = hook
    logger.info("✅ MVR integration hook registered globally")


def get_mvr_integration_hook():
    """
    Get global MVR integration hook.
    
    Returns:
        MVRIntegrationHook instance or None if not initialized
    """
    return _mvr_hook


async def trigger_mvr_creation(
    individual_uuid: UUID,
    session_uuid: Optional[UUID] = None,
    auto_match: bool = True
) -> bool:
    """
    Convenience function to trigger MVR-People creation.
    
    This is the main function to call from Individual creation code.
    
    Args:
        individual_uuid: UUID of newly created Individual
        session_uuid: Optional session UUID for context
        auto_match: Whether to automatically match and merge
    
    Returns:
        True if triggered successfully, False if hook not available
    """
    if _mvr_hook is None:
        logger.debug(
            "MVR integration hook not available, "
            f"skipping Individual {individual_uuid}"
        )
        return False
    
    try:
        await _mvr_hook.on_individual_created(
            individual_uuid=individual_uuid,
            session_uuid=session_uuid,
            auto_match=auto_match
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to trigger MVR creation for Individual "
            f"{individual_uuid}: {e}"
        )
        return False


def is_mvr_enabled() -> bool:
    """
    Check if MVR-People automatic processing is enabled.
    
    Returns:
        True if enabled and available, False otherwise
    """
    return _mvr_hook is not None and _mvr_hook.is_enabled()
