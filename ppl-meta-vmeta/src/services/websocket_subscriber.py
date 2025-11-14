"""
WebSocket Event Subscriber
PPL Meta Platform - Continuous Individuals and MVR Pipeline

WebSocket-based event subscription for real-time events from Orchestrator.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable, Dict, Any
import aiohttp

from ..models.events import (
    SubscriptionStatus,
    SubscriptionConfig,
    WebSocketEvent,
    EventType
)
from .event_subscriber import EventSubscriber


logger = logging.getLogger(__name__)


class WebSocketEventSubscriber(EventSubscriber):
    """
    WebSocket-based event subscriber.
    
    Subscribes to real-time events from Orchestrator service via WebSocket.
    Features:
    - Auto-reconnection with exponential backoff
    - Heartbeat monitoring
    - Event filtering
    - Connection state tracking
    """
    
    def __init__(
        self,
        config: SubscriptionConfig,
        on_event: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Initialize WebSocket subscriber.
        
        Args:
            config: Subscription configuration
            on_event: Async callback for event handling
        """
        super().__init__(subscriber_type="websocket", on_event=on_event)
        
        self.config = config
        
        # WebSocket connection
        self._session: Optional[aiohttp.ClientSession] = None
        self._websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        
        # Build WebSocket URL
        ws_protocol = "ws" if "http://" in config.orchestrator_url else "wss"
        base_url = config.orchestrator_url.replace("http://", "").replace("https://", "")
        self.ws_url = f"{ws_protocol}://{base_url}{config.event_endpoint}"
        
        logger.info(
            f"[WEBSOCKET] Initialized with URL: {self.ws_url}"
        )
    
    # =============================================
    # CONNECTION MANAGEMENT
    # =============================================
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"[WEBSOCKET] Connecting to {self.ws_url}...")
            
            self.update_state(status=SubscriptionStatus.CONNECTING)
            
            # Create aiohttp session if needed
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # Build subscription request
            subscription_request = {
                'event_types': [et.value for et in self.config.event_types],
                'collections': self.config.collections
            }
            
            # Connect to WebSocket
            self._websocket = await self._session.ws_connect(
                self.ws_url,
                timeout=aiohttp.ClientTimeout(total=30),
                heartbeat=self.config.heartbeat_interval_seconds if self.config.heartbeat_enabled else None
            )
            
            # Send subscription request
            await self._websocket.send_json(subscription_request)
            
            # Wait for subscription confirmation
            msg = await asyncio.wait_for(
                self._websocket.receive(),
                timeout=10.0
            )
            
            if msg.type == aiohttp.WSMsgType.TEXT:
                response = json.loads(msg.data)
                if response.get('status') == 'subscribed':
                    logger.info(
                        f"[WEBSOCKET] Connected and subscribed successfully"
                    )
                    
                    # Update state
                    self.update_state(
                        status=SubscriptionStatus.CONNECTED,
                        connected_at=datetime.utcnow(),
                        disconnected_at=None
                    )
                    
                    # Start heartbeat if enabled
                    if self.config.heartbeat_enabled:
                        await self._start_heartbeat()
                    
                    return True
                else:
                    logger.error(
                        f"[WEBSOCKET] Subscription rejected: {response}"
                    )
                    return False
            else:
                logger.error(
                    f"[WEBSOCKET] Unexpected message type: {msg.type}"
                )
                return False
        
        except asyncio.TimeoutError:
            logger.error("[WEBSOCKET] Connection timeout")
            self.update_state(status=SubscriptionStatus.FAILED)
            return False
        
        except aiohttp.ClientError as e:
            logger.error(f"[WEBSOCKET] Connection error: {e}")
            self.record_error(e)
            self.update_state(status=SubscriptionStatus.FAILED)
            return False
        
        except Exception as e:
            logger.error(
                f"[WEBSOCKET] Unexpected error during connection: {e}",
                exc_info=True
            )
            self.record_error(e)
            self.update_state(status=SubscriptionStatus.FAILED)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        try:
            logger.info("[WEBSOCKET] Disconnecting...")
            
            # Close WebSocket
            if self._websocket and not self._websocket.closed:
                await self._websocket.close()
                self._websocket = None
            
            # Close session
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
            
            # Update state
            self.update_state(
                status=SubscriptionStatus.DISCONNECTED,
                disconnected_at=datetime.utcnow()
            )
            
            logger.info("[WEBSOCKET] Disconnected")
        
        except Exception as e:
            logger.error(f"[WEBSOCKET] Error during disconnect: {e}")
            self.record_error(e)
    
    # =============================================
    # SUBSCRIPTION LOOP
    # =============================================
    
    async def _run_subscription(self) -> None:
        """Main subscription loop."""
        try:
            # Initial connection
            success = await self.connect()
            
            if not success and self.config.reconnect_enabled:
                # Schedule reconnection
                await self.schedule_reconnect(
                    initial_delay=self.config.reconnect_interval_seconds,
                    max_delay=self.config.max_reconnect_interval_seconds,
                    backoff_multiplier=self.config.reconnect_backoff_multiplier
                )
                return
            
            # Main event loop
            while self._running and not self._stop_requested:
                try:
                    if not self._websocket or self._websocket.closed:
                        logger.warning("[WEBSOCKET] Connection lost")
                        
                        self.update_state(status=SubscriptionStatus.RECONNECTING)
                        
                        if self.config.reconnect_enabled:
                            await self.schedule_reconnect(
                                initial_delay=self.config.reconnect_interval_seconds,
                                max_delay=self.config.max_reconnect_interval_seconds,
                                backoff_multiplier=self.config.reconnect_backoff_multiplier
                            )
                        break
                    
                    # Receive message
                    msg = await self._websocket.receive()
                    
                    # Handle message
                    await self._handle_message(msg)
                
                except asyncio.CancelledError:
                    logger.info("[WEBSOCKET] Subscription loop cancelled")
                    break
                
                except Exception as e:
                    logger.error(
                        f"[WEBSOCKET] Error in subscription loop: {e}",
                        exc_info=True
                    )
                    self.record_error(e)
                    
                    # Attempt reconnection
                    if self.config.reconnect_enabled and not self._stop_requested:
                        self.update_state(status=SubscriptionStatus.RECONNECTING)
                        await self.schedule_reconnect(
                            initial_delay=self.config.reconnect_interval_seconds,
                            max_delay=self.config.max_reconnect_interval_seconds,
                            backoff_multiplier=self.config.reconnect_backoff_multiplier
                        )
                    break
        
        except Exception as e:
            logger.error(
                f"[WEBSOCKET] Fatal error in subscription: {e}",
                exc_info=True
            )
            self.record_error(e)
            self.update_state(status=SubscriptionStatus.FAILED)
    
    async def _handle_message(self, msg: aiohttp.WSMessage) -> None:
        """
        Handle WebSocket message.
        
        Args:
            msg: WebSocket message
        """
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                # Parse JSON
                event_data = json.loads(msg.data)
                
                # Handle event
                await self.handle_event(event_data)
            
            except json.JSONDecodeError as e:
                logger.error(f"[WEBSOCKET] Failed to parse JSON: {e}")
                self.increment_event_counter('events_failed')
            
            except Exception as e:
                logger.error(
                    f"[WEBSOCKET] Error handling message: {e}",
                    exc_info=True
                )
                self.record_error(e)
        
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            logger.warning("[WEBSOCKET] Connection closed by server")
            self.update_state(status=SubscriptionStatus.DISCONNECTED)
        
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.error(
                f"[WEBSOCKET] WebSocket error: {self._websocket.exception()}"
            )
            self.update_state(status=SubscriptionStatus.FAILED)
        
        elif msg.type == aiohttp.WSMsgType.PING:
            logger.debug("[WEBSOCKET] Received ping")
        
        elif msg.type == aiohttp.WSMsgType.PONG:
            logger.debug("[WEBSOCKET] Received pong")
            self.state.last_heartbeat_response_at = datetime.utcnow()
    
    # =============================================
    # HEARTBEAT
    # =============================================
    
    async def _start_heartbeat(self) -> None:
        """Start heartbeat monitoring."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            logger.debug("[WEBSOCKET] Heartbeat already running")
            return
        
        logger.info("[WEBSOCKET] Starting heartbeat monitoring...")
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        try:
            while self._running and not self._stop_requested:
                try:
                    # Wait for interval
                    await asyncio.sleep(self.config.heartbeat_interval_seconds)
                    
                    # Check connection
                    if not self._websocket or self._websocket.closed:
                        logger.warning("[WEBSOCKET] Connection lost during heartbeat")
                        break
                    
                    # Send ping
                    await self._websocket.ping()
                    self.state.last_heartbeat_at = datetime.utcnow()
                    
                    logger.debug("[WEBSOCKET] Heartbeat ping sent")
                    
                    # Wait for pong with timeout
                    try:
                        await asyncio.wait_for(
                            self._wait_for_pong(),
                            timeout=self.config.heartbeat_timeout_seconds
                        )
                        logger.debug("[WEBSOCKET] Heartbeat pong received")
                    
                    except asyncio.TimeoutError:
                        logger.warning("[WEBSOCKET] Heartbeat timeout")
                        # Connection is likely dead, trigger reconnection
                        if self.config.reconnect_enabled:
                            await self.disconnect()
                            self.update_state(status=SubscriptionStatus.RECONNECTING)
                        break
                
                except asyncio.CancelledError:
                    logger.info("[WEBSOCKET] Heartbeat loop cancelled")
                    break
                
                except Exception as e:
                    logger.error(
                        f"[WEBSOCKET] Error in heartbeat loop: {e}",
                        exc_info=True
                    )
                    self.record_error(e)
                    break
        
        except Exception as e:
            logger.error(
                f"[WEBSOCKET] Fatal error in heartbeat: {e}",
                exc_info=True
            )
            self.record_error(e)
    
    async def _wait_for_pong(self) -> None:
        """Wait for pong response."""
        # This is a simplified implementation
        # In production, you'd track the actual pong message
        last_pong = self.state.last_heartbeat_response_at
        
        while True:
            await asyncio.sleep(0.1)
            
            if self.state.last_heartbeat_response_at != last_pong:
                # New pong received
                return
            
            if not self._websocket or self._websocket.closed:
                raise ConnectionError("WebSocket closed")
