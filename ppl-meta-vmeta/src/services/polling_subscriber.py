"""
Polling Event Subscriber
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Polling-based event subscription as fallback when WebSocket unavailable.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable, Dict, Any, Set
from uuid import UUID
import aiohttp

from ..models.events import (
    SubscriptionStatus,
    PollingConfig
)
from .event_subscriber import EventSubscriber


logger = logging.getLogger(__name__)


class PollingEventSubscriber(EventSubscriber):
    """
    Polling-based event subscriber.
    
    Polls Vision Service for completed face detection sessions as fallback
    when WebSocket connection is unavailable.
    
    Features:
    - Periodic polling with configurable interval
    - Deduplication to prevent duplicate event processing
    - Lookback window to catch recent completions
    """
    
    def __init__(
        self,
        config: PollingConfig,
        on_event: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Initialize polling subscriber.
        
        Args:
            config: Polling configuration
            on_event: Async callback for event handling
        """
        super().__init__(subscriber_type="polling", on_event=on_event)
        
        self.config = config
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Deduplication tracking
        self._processed_sessions: Set[str] = set()
        self._last_cleanup_at: datetime = datetime.utcnow()
        
        # Build Vision Service URL
        self.vision_url = (
            f"{config.vision_service_url}{config.sessions_endpoint}"
        )
        
        logger.info(
            f"[POLLING] Initialized with URL: {self.vision_url}, "
            f"interval: {config.polling_interval_seconds}s"
        )
    
    # =============================================
    # CONNECTION MANAGEMENT
    # =============================================
    
    async def connect(self) -> bool:
        """
        Initialize HTTP session for polling.
        
        Returns:
            True (polling always succeeds)
        """
        try:
            logger.info("[POLLING] Initializing HTTP session...")
            
            # Create aiohttp session
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Update state
            self.update_state(
                status=SubscriptionStatus.CONNECTED,
                connected_at=datetime.utcnow(),
                disconnected_at=None
            )
            
            logger.info("[POLLING] HTTP session initialized")
            return True
        
        except Exception as e:
            logger.error(f"[POLLING] Failed to initialize session: {e}")
            self.record_error(e)
            self.update_state(status=SubscriptionStatus.FAILED)
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP session."""
        try:
            logger.info("[POLLING] Closing HTTP session...")
            
            # Close session
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
            
            # Update state
            self.update_state(
                status=SubscriptionStatus.DISCONNECTED,
                disconnected_at=datetime.utcnow()
            )
            
            logger.info("[POLLING] HTTP session closed")
        
        except Exception as e:
            logger.error(f"[POLLING] Error during disconnect: {e}")
            self.record_error(e)
    
    # =============================================
    # POLLING LOOP
    # =============================================
    
    async def _run_subscription(self) -> None:
        """Main polling loop."""
        try:
            # Initial connection
            success = await self.connect()
            
            if not success:
                logger.error("[POLLING] Failed to initialize")
                return
            
            # Main polling loop
            while self._running and not self._stop_requested:
                try:
                    # Poll for new sessions
                    await self._poll_completed_sessions()
                    
                    # Cleanup old deduplication entries
                    await self._cleanup_deduplication_cache()
                    
                    # Wait for next poll
                    await asyncio.sleep(self.config.polling_interval_seconds)
                
                except asyncio.CancelledError:
                    logger.info("[POLLING] Polling loop cancelled")
                    break
                
                except Exception as e:
                    logger.error(
                        f"[POLLING] Error in polling loop: {e}",
                        exc_info=True
                    )
                    self.record_error(e)
                    
                    # Continue polling despite errors
                    await asyncio.sleep(self.config.polling_interval_seconds)
        
        except Exception as e:
            logger.error(
                f"[POLLING] Fatal error in polling: {e}",
                exc_info=True
            )
            self.record_error(e)
            self.update_state(status=SubscriptionStatus.FAILED)
    
    async def _poll_completed_sessions(self) -> None:
        """Poll Vision Service for completed sessions."""
        try:
            if not self._session:
                logger.warning("[POLLING] No active session")
                return
            
            # Calculate lookback time
            lookback_time = datetime.utcnow() - timedelta(
                minutes=self.config.lookback_minutes
            )
            
            # Query Vision Service for completed sessions
            params = {
                'status': 'completed',
                'completed_after': lookback_time.isoformat(),
                'limit': 100
            }
            
            logger.debug(
                f"[POLLING] Querying sessions completed after "
                f"{lookback_time.isoformat()}"
            )
            
            async with self._session.get(
                self.vision_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status != 200:
                    logger.warning(
                        f"[POLLING] Vision Service returned "
                        f"status {response.status}"
                    )
                    return
                
                data = await response.json()
                sessions = data.get('sessions', [])
                
                logger.debug(
                    f"[POLLING] Found {len(sessions)} completed sessions"
                )
                
                # Process each session
                for session in sessions:
                    await self._process_session(session)
        
        except aiohttp.ClientError as e:
            logger.error(f"[POLLING] HTTP error: {e}")
            self.record_error(e)
        
        except Exception as e:
            logger.error(
                f"[POLLING] Error polling sessions: {e}",
                exc_info=True
            )
            self.record_error(e)
    
    async def _process_session(self, session: Dict[str, Any]) -> None:
        """
        Process a completed session.
        
        Args:
            session: Session data from Vision Service
        """
        try:
            session_uuid = session.get('session_uuid')
            
            if not session_uuid:
                logger.warning("[POLLING] Session missing UUID")
                return
            
            # Check deduplication
            if self.config.deduplication_enabled:
                if session_uuid in self._processed_sessions:
                    logger.debug(
                        f"[POLLING] Skipping duplicate session "
                        f"{session_uuid[:8]}..."
                    )
                    return
                
                # Mark as processed
                self._processed_sessions.add(session_uuid)
            
            # Convert to event format
            event_data = self._session_to_event(session)
            
            # Handle event
            await self.handle_event(event_data)
            
            logger.debug(
                f"[POLLING] Processed session {session_uuid[:8]}..."
            )
        
        except Exception as e:
            logger.error(
                f"[POLLING] Error processing session: {e}",
                exc_info=True
            )
            self.record_error(e)
    
    def _session_to_event(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Vision Service session to event format.
        
        Args:
            session: Session data from Vision Service
        
        Returns:
            Event data in standard format
        """
        # Extract session data
        return {
            'event_type': 'face_detection_completed',
            'event_source': 'vision',
            'timestamp': session.get('completed_at', datetime.utcnow().isoformat()),
            'payload': {
                'session_uuid': session.get('session_uuid'),
                'video_uuid': session.get('video_uuid'),
                'collection_id': session.get('collection_id'),
                'video_start_time': session.get('video_start_time'),
                'video_end_time': session.get('video_end_time'),
                'faces_detected': session.get('faces_detected', 0),
                'individuals_created': session.get('individuals_created', 0),
                'individuals_cached': session.get('individuals_cached', 0),
                'processing_time_seconds': session.get('processing_time_seconds', 0),
                'cache_hit_rate': session.get('cache_hit_rate'),
                'completed_at': session.get('completed_at')
            }
        }
    
    # =============================================
    # DEDUPLICATION
    # =============================================
    
    async def _cleanup_deduplication_cache(self) -> None:
        """Clean up old entries from deduplication cache."""
        try:
            # Only cleanup periodically (every 10 minutes)
            now = datetime.utcnow()
            time_since_cleanup = (now - self._last_cleanup_at).total_seconds()
            
            if time_since_cleanup < 600:  # 10 minutes
                return
            
            # Get deduplication window
            window_minutes = self.config.deduplication_window_minutes
            
            # Clear entire cache (simple approach)
            # In production, you'd track timestamps and remove only old entries
            old_size = len(self._processed_sessions)
            self._processed_sessions.clear()
            
            self._last_cleanup_at = now
            
            logger.debug(
                f"[POLLING] Deduplication cache cleared "
                f"({old_size} entries removed)"
            )
        
        except Exception as e:
            logger.error(
                f"[POLLING] Error cleaning deduplication cache: {e}"
            )
            self.record_error(e)
    
    # =============================================
    # HEALTH CHECK
    # =============================================
    
    def is_healthy(self) -> bool:
        """
        Check if polling subscriber is healthy.
        
        Returns:
            True if healthy
        """
        # Polling is healthy if:
        # 1. Session is active
        # 2. No recent errors (within last 5 minutes)
        
        if not self._session or self._session.closed:
            return False
        
        if self.state.last_error_at:
            time_since_error = (
                datetime.utcnow() - self.state.last_error_at
            ).total_seconds()
            if time_since_error < 300:  # 5 minutes
                return False
        
        return True
