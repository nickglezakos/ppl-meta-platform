"""
Camera Event Integration Service
PPL Meta vmeta - Phase 5: Partial Batch Handling

Integrates Camera Service recording stop events with the batch processing
pipeline by wiring CameraEventSubscriber to BatchMonitor and HybridBatchTrigger.

This service acts as the glue between:
1. Camera Service events (recording stopped/completed)
2. BatchMonitor (batch accumulation)
3. HybridBatchTrigger (partial batch triggering)

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import logging
from typing import Optional
import asyncio

from .camera_event_subscriber import CameraEventSubscriber
from .batch_monitor import BatchMonitor
from .hybrid_batch_trigger import HybridBatchTrigger

logger = logging.getLogger(__name__)


class CameraEventIntegration:
    """
    Integrates Camera Service events with batch processing pipeline.
    
    Event Flow:
    1. Camera Service stops recording → Event published
    2. CameraEventSubscriber receives event
    3. BatchMonitor.handle_recording_stop() called
    4. HybridBatchTrigger processes partial batch
    5. Timeout tasks cancelled (no longer needed)
    """
    
    def __init__(
        self,
        batch_monitor: BatchMonitor,
        hybrid_trigger: Optional[HybridBatchTrigger] = None,
        orchestrator_url: str = "http://localhost:8002",
        camera_service_url: str = "http://localhost:8005",
        enable_websocket: bool = True,
        enable_polling: bool = True,
        polling_interval_seconds: int = 10
    ):
        """
        Initialize camera event integration.
        
        Args:
            batch_monitor: BatchMonitor instance
            hybrid_trigger: HybridBatchTrigger instance (optional)
            orchestrator_url: Orchestrator service URL
            camera_service_url: Camera service URL
            enable_websocket: Enable WebSocket subscription
            enable_polling: Enable polling fallback
            polling_interval_seconds: Polling interval
        """
        self.batch_monitor = batch_monitor
        self.hybrid_trigger = hybrid_trigger
        
        # Create camera event subscriber
        self.subscriber = CameraEventSubscriber(
            orchestrator_url=orchestrator_url,
            camera_service_url=camera_service_url,
            polling_interval_seconds=polling_interval_seconds,
            enable_websocket=enable_websocket,
            enable_polling=enable_polling
        )
        
        # Wire up event handlers
        self.subscriber.set_recording_stopped_handler(
            self._handle_recording_stopped
        )
        self.subscriber.set_recording_completed_handler(
            self._handle_recording_completed
        )
        
        self.is_running = False
        
        logger.info("CameraEventIntegration initialized")
    
    async def start(self):
        """Start camera event subscription."""
        if self.is_running:
            logger.warning("CameraEventIntegration already running")
            return
        
        logger.info("Starting CameraEventIntegration...")
        
        # Start subscriber
        await self.subscriber.start()
        
        self.is_running = True
        logger.info("✅ CameraEventIntegration started successfully")
    
    async def stop(self):
        """Stop camera event subscription."""
        if not self.is_running:
            return
        
        logger.info("Stopping CameraEventIntegration...")
        
        # Stop subscriber
        await self.subscriber.stop()
        
        self.is_running = False
        logger.info("✅ CameraEventIntegration stopped")
    
    async def _handle_recording_stopped(
        self,
        collection_id: str,
        session_id: str,
        reason: Optional[str]
    ):
        """
        Handle recording_stopped event from Camera Service.
        
        This is the PRIMARY TRIGGER for partial batch processing.
        
        Args:
            collection_id: Camera collection ID
            session_id: Recording session UUID
            reason: Stop reason (user_stopped, error, timeout, etc.)
        """
        try:
            logger.info(
                f"🎬 [INTEGRATION] Recording stopped event received: "
                f"Collection={collection_id}, Session={session_id[:8]}..., "
                f"Reason={reason}"
            )
            
            # Call batch monitor to handle recording stop
            await self.batch_monitor.handle_recording_stop(
                collection_id=collection_id,
                recording_session_id=session_id,
                reason=reason
            )
            
            logger.info(
                f"✅ Recording stop event processed successfully for {collection_id}"
            )
        
        except Exception as e:
            logger.error(
                f"❌ Error handling recording stop event: {e}",
                exc_info=True
            )
    
    async def _handle_recording_completed(
        self,
        collection_id: str,
        event_data: dict
    ):
        """
        Handle recording_completed event from Camera Service.
        
        This event provides additional metadata about the completed recording.
        It's informational and doesn't trigger batch processing directly
        (recording_stopped is the trigger).
        
        Args:
            collection_id: Camera collection ID
            event_data: Full event data
        """
        try:
            logger.info(
                f"🎬 [INTEGRATION] Recording completed event received: "
                f"Collection={collection_id}"
            )
            
            # Log metadata for observability
            session_id = event_data.get("recording_session_id")
            duration = event_data.get("recording_duration_seconds", 0)
            file_size = event_data.get("file_size_bytes", 0)
            
            logger.info(
                f"Recording metadata: Session={session_id[:8] if session_id else 'unknown'}..., "
                f"Duration={duration:.1f}s, Size={file_size / 1024 / 1024:.2f}MB"
            )
        
        except Exception as e:
            logger.error(
                f"❌ Error handling recording completed event: {e}",
                exc_info=True
            )
    
    def get_statistics(self) -> dict:
        """Get integration statistics."""
        return {
            "is_running": self.is_running,
            "subscriber_stats": self.subscriber.get_statistics(),
            "batch_monitor_stats": self.batch_monitor.get_statistics(),
            "hybrid_trigger_enabled": self.hybrid_trigger is not None,
            "hybrid_trigger_stats": (
                self.hybrid_trigger.get_statistics()
                if self.hybrid_trigger
                else None
            )
        }
