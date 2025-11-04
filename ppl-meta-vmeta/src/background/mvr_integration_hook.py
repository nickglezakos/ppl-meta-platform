"""
MVR-People Integration Hooks

Provides integration points for automatic MVR-People processing
during Individual creation and lifecycle events.
"""

import logging
from typing import Optional
from uuid import UUID

from background.mvr_background_processor import MVRBackgroundProcessor

logger = logging.getLogger(__name__)


class MVRIntegrationHook:
    """
    Integration hook for MVR-People automatic processing.
    
    This class provides a clean integration point that can be called
    from the Individual creation workflow to trigger automatic
    MVR-People creation and matching.
    """
    
    def __init__(self, background_processor: MVRBackgroundProcessor):
        """
        Initialize integration hook.
        
        Args:
            background_processor: MVRBackgroundProcessor instance
        """
        self.background_processor = background_processor
        self._enabled = True
        logger.info("✅ MVR Integration Hook initialized")
    
    async def on_individual_created(
        self,
        individual_uuid: UUID,
        session_uuid: Optional[UUID] = None,
        auto_match: bool = True
    ) -> None:
        """
        Hook called when a new Individual is created.
        
        This triggers automatic MVR-People creation and matching
        in the background (non-blocking).
        
        Args:
            individual_uuid: UUID of newly created Individual
            session_uuid: Optional session UUID for context
            auto_match: Whether to automatically match and merge
        """
        if not self._enabled:
            logger.debug(
                f"ℹ️ MVR processing disabled, skipping Individual "
                f"{individual_uuid}"
            )
            return
        
        try:
            # Trigger background processing (non-blocking)
            await self.background_processor.process_new_individual(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid,
                auto_match=auto_match
            )
            
            logger.info(
                f"✅ Triggered MVR processing for Individual "
                f"{individual_uuid}"
            )
            
        except Exception as e:
            # Log error but don't fail Individual creation
            logger.error(
                f"❌ Failed to trigger MVR processing for Individual "
                f"{individual_uuid}: {e}"
            )
    
    def enable(self) -> None:
        """Enable automatic MVR processing."""
        self._enabled = True
        logger.info("✅ MVR automatic processing enabled")
    
    def disable(self) -> None:
        """Disable automatic MVR processing."""
        self._enabled = False
        logger.info("⚠️ MVR automatic processing disabled")
    
    def is_enabled(self) -> bool:
        """Check if automatic MVR processing is enabled."""
        return self._enabled
