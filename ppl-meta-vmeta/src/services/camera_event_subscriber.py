"""
Camera Service Event Subscriber
PPL Meta vmeta - Phase 5: Partial Batch Handling

Subscribes to Camera Service recording stop events to trigger immediate
partial batch processing when recordings end.

Event Flow:
1. Camera Service stops recording → Publishes event to Orchestrator
2. vmeta subscribes to Orchestrator camera events
3. On recording_stopped event → Trigger partial batch via HybridBatchTrigger
4. Timeout fallback handles missed events

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import aiohttp
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class CameraEventSubscriber:
    """
    Subscribes to Camera Service recording stop events via Orchestrator.
    
    Implements both WebSocket (preferred) and polling (fallback) mechanisms
    for reliable event delivery.
    """
    
    def __init__(
        self,
        orchestrator_url: str = "http://localhost:8002",
        camera_service_url: str = "http://localhost:8005",
        polling_interval_seconds: int = 5,
        enable_websocket: bool = True,
        enable_polling: bool = True
    ):
        """
        Initialize camera event subscriber.
        
        Args:
            orchestrator_url: Orchestrator service base URL
            camera_service_url: Camera service base URL (for polling fallback)
            polling_interval_seconds: Polling interval for fallback
            enable_websocket: Enable WebSocket subscription
            enable_polling: Enable polling fallback
        """
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.camera_service_url = camera_service_url.rstrip("/")
        self.polling_interval_seconds = polling_interval_seconds
        self.enable_websocket = enable_websocket
        self.enable_polling = enable_polling
        
        # Event handlers
        self.on_recording_stopped: Optional[Callable] = None
        self.on_recording_completed: Optional[Callable] = None
        
        # State tracking
        self.is_running = False
        self.websocket_task: Optional[asyncio.Task] = None
        self.polling_task: Optional[asyncio.Task] = None
        self.last_processed_events: Dict[str, datetime] = {}
        
        # Statistics
        self.events_received = 0
        self.events_processed = 0
        self.events_failed = 0
        self.reconnection_count = 0
        
        logger.info(
            f"CameraEventSubscriber initialized "
            f"(WebSocket: {enable_websocket}, Polling: {enable_polling})"
        )
    
    def set_recording_stopped_handler(
        self,
        handler: Callable[[str, str, Optional[str]], None]
    ):
        """
        Set handler for recording_stopped events.
        
        Args:
            handler: Async function(collection_id, session_id, reason)
        """
        self.on_recording_stopped = handler
        logger.info("Recording stopped handler registered")
    
    def set_recording_completed_handler(
        self,
        handler: Callable[[str, Dict[str, Any]], None]
    ):
        """
        Set handler for recording_completed events.
        
        Args:
            handler: Async function(collection_id, event_data)
        """
        self.on_recording_completed = handler
        logger.info("Recording completed handler registered")
    
    async def start(self):
        """Start event subscription."""
        if self.is_running:
            logger.warning("CameraEventSubscriber already running")
            return
        
        self.is_running = True
        logger.info("Starting CameraEventSubscriber...")
        
        # Start WebSocket subscription
        if self.enable_websocket:
            self.websocket_task = asyncio.create_task(
                self._websocket_subscription_loop()
            )
            logger.info("WebSocket subscription task started")
        
        # Start polling fallback
        if self.enable_polling:
            self.polling_task = asyncio.create_task(
                self._polling_loop()
            )
            logger.info("Polling fallback task started")
        
        logger.info("✅ CameraEventSubscriber started successfully")
    
    async def stop(self):
        """Stop event subscription."""
        if not self.is_running:
            return
        
        logger.info("Stopping CameraEventSubscriber...")
        self.is_running = False
        
        # Cancel tasks
        if self.websocket_task and not self.websocket_task.done():
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass
        
        if self.polling_task and not self.polling_task.done():
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ CameraEventSubscriber stopped")
    
    async def _websocket_subscription_loop(self):
        """WebSocket subscription loop with auto-reconnection."""
        while self.is_running:
            try:
                logger.info("Connecting to Orchestrator WebSocket...")
                
                # WebSocket endpoint for camera events
                ws_url = self.orchestrator_url.replace("http://", "ws://")
                ws_url = ws_url.replace("https://", "wss://")
                ws_url = urljoin(ws_url, "/ws/camera-events")
                
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        logger.info(f"✅ Connected to {ws_url}")
                        self.reconnection_count += 1
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self._handle_websocket_message(msg.data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket error: {ws.exception()}")
                                break
            
            except asyncio.CancelledError:
                logger.info("WebSocket subscription cancelled")
                break
            
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                
                # Reconnect after delay
                if self.is_running:
                    await asyncio.sleep(5)
                    logger.info("Attempting WebSocket reconnection...")
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message."""
        try:
            import json
            event = json.loads(message)
            self.events_received += 1
            
            await self._process_event(event)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
            self.events_failed += 1
        
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            self.events_failed += 1
    
    async def _polling_loop(self):
        """Polling fallback loop."""
        logger.info(
            f"Polling loop started (interval: {self.polling_interval_seconds}s)"
        )
        
        while self.is_running:
            try:
                await self._poll_camera_service()
                await asyncio.sleep(self.polling_interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(self.polling_interval_seconds)
    
    async def _poll_camera_service(self):
        """Poll Camera Service for recently stopped recording sessions."""
        try:
            # Query Camera Service for recently completed sessions
            url = urljoin(
                self.camera_service_url,
                "/api/v1/recordings/recent?status=completed&limit=10"
            )
            
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        sessions = data.get("sessions", [])
                        
                        for session_data in sessions:
                            # Check if already processed
                            session_id = session_data.get("session_uuid")
                            stopped_at = session_data.get("stopped_at")
                            
                            if session_id and stopped_at:
                                # Create event from session data
                                event = {
                                    "event_type": "recording_stopped",
                                    "recording_session_id": session_id,
                                    "camera_device_id": session_data.get(
                                        "camera_device_id"
                                    ),
                                    "collection_id": session_data.get(
                                        "collection_id"
                                    ),
                                    "stopped_at": stopped_at,
                                    "reason": "user_stopped",
                                    "metadata": session_data.get("metadata", {})
                                }
                                
                                await self._process_event(event)
        
        except asyncio.TimeoutError:
            logger.debug("Polling timeout (Camera Service not responding)")
        
        except Exception as e:
            logger.error(f"Polling failed: {e}")
    
    async def _process_event(self, event: Dict[str, Any]):
        """
        Process camera event and call appropriate handler.
        
        Args:
            event: Event data dictionary
        """
        try:
            event_type = event.get("event_type")
            
            if not event_type:
                logger.warning("Event missing event_type, skipping")
                return
            
            # Check if already processed (deduplication)
            session_id = event.get("recording_session_id")
            if session_id:
                event_key = f"{event_type}:{session_id}"
                if event_key in self.last_processed_events:
                    logger.debug(
                        f"Event {event_key} already processed, skipping"
                    )
                    return
                
                # Mark as processed
                self.last_processed_events[event_key] = datetime.now()
                
                # Cleanup old entries (keep last 1000)
                if len(self.last_processed_events) > 1000:
                    oldest_keys = sorted(
                        self.last_processed_events.keys(),
                        key=lambda k: self.last_processed_events[k]
                    )[:500]
                    for key in oldest_keys:
                        del self.last_processed_events[key]
            
            # Route to appropriate handler
            if event_type == "recording_stopped":
                await self._handle_recording_stopped(event)
            elif event_type == "recording_completed":
                await self._handle_recording_completed(event)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
            
            self.events_processed += 1
        
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            self.events_failed += 1
    
    async def _handle_recording_stopped(self, event: Dict[str, Any]):
        """Handle recording_stopped event."""
        collection_id = event.get("collection_id")
        session_id = event.get("recording_session_id")
        reason = event.get("reason", "unknown")
        
        if not collection_id or not session_id:
            logger.warning(
                f"recording_stopped event missing required fields: {event}"
            )
            return
        
        logger.info(
            f"🎬 [RECORDING STOPPED] Collection: {collection_id}, "
            f"Session: {session_id[:8]}..., Reason: {reason}"
        )
        
        # Call handler if registered
        if self.on_recording_stopped:
            try:
                await self.on_recording_stopped(
                    collection_id,
                    session_id,
                    reason
                )
            except Exception as e:
                logger.error(
                    f"Error in recording_stopped handler: {e}",
                    exc_info=True
                )
        else:
            logger.warning("No recording_stopped handler registered")
    
    async def _handle_recording_completed(self, event: Dict[str, Any]):
        """Handle recording_completed event."""
        collection_id = event.get("collection_id")
        
        if not collection_id:
            logger.warning(
                f"recording_completed event missing collection_id: {event}"
            )
            return
        
        logger.info(
            f"🎬 [RECORDING COMPLETED] Collection: {collection_id}"
        )
        
        # Call handler if registered
        if self.on_recording_completed:
            try:
                await self.on_recording_completed(collection_id, event)
            except Exception as e:
                logger.error(
                    f"Error in recording_completed handler: {e}",
                    exc_info=True
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get subscriber statistics."""
        return {
            "is_running": self.is_running,
            "websocket_enabled": self.enable_websocket,
            "polling_enabled": self.enable_polling,
            "events_received": self.events_received,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "reconnection_count": self.reconnection_count,
            "processed_events_cached": len(self.last_processed_events),
            "handlers_registered": {
                "recording_stopped": self.on_recording_stopped is not None,
                "recording_completed": self.on_recording_completed is not None
            }
        }
