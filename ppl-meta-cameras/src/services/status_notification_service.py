"""
Camera Status Notification Service

Provides real-time camera status updates using Redis Pub/Sub.
Workers publish status changes, clients subscribe via WebSocket.

Architecture:
- CameraWorker publishes status changes to Redis
- StatusNotificationService subscribes to Redis channels
- WebSocket endpoint delivers real-time updates to clients
- No polling needed - event-driven architecture
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Set, List
from enum import Enum

import redis.asyncio as redis


logger = logging.getLogger(__name__)


class CameraStatusEvent(str, Enum):
    """Camera status event types."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    STREAMING_STARTED = "streaming_started"
    STREAMING_STOPPED = "streaming_stopped"


class StatusNotificationService:
    """
    Manages camera status notifications using Redis Pub/Sub.
    
    Features:
    - Real-time status updates
    - No polling required
    - Scales horizontally (multiple service instances)
    - Persistent connection pool
    - Automatic reconnection on failure
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        """
        Initialize status notification service.
        
        Args:
            redis_url: Redis connection URL (default uses DB 1 to avoid Celery conflicts)
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.connected = False
        
        # Track active subscriptions
        self.active_channels: Set[str] = set()
        
        logger.info(f"📢 StatusNotificationService initialized (redis: {redis_url})")
    
    async def connect(self):
        """Connect to Redis and initialize pub/sub."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            
            # Force actual connection by pinging
            await self.redis_client.ping()
            
            # Do a test publish to ensure pub/sub works
            await self.redis_client.publish("camera:status:test", json.dumps({"test": "connection"}))
            
            self.connected = True
            logger.info("✅ Connected to Redis for status notifications")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            logger.warning("Status notifications will be disabled")
            self.connected = False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.pubsub:
            try:
                await self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pubsub: {e}")
        
        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
        
        self.connected = False
        logger.info("🔌 Disconnected from Redis")
    
    async def publish_status_change(
        self,
        device_id: str,
        event: CameraStatusEvent,
        details: Optional[Dict] = None
    ):
        """
        Publish a camera status change event.
        
        Args:
            device_id: Camera device identifier
            event: Status event type
            details: Optional additional details
        """
        if not self.connected:
            logger.debug(f"Redis not connected, skipping publish for {device_id}")
            return
        
        try:
            channel = f"camera:status:{device_id}"
            
            message = {
                "device_id": device_id,
                "event": event.value,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            }
            
            message_json = json.dumps(message)
            
            # Try to publish, reconnect once if needed
            try:
                # Publish to device-specific channel
                await self.redis_client.publish(channel, message_json)
                
                # Also publish to global channel for monitoring
                await self.redis_client.publish("camera:status:all", message_json)
            except (ConnectionError, TimeoutError, OSError, RuntimeError) as conn_err:
                logger.warning(f"⚠️ Redis connection lost, attempting reconnect: {conn_err}")
                # Try to reconnect
                await self.connect()
                if self.connected:
                    logger.info(f"✅ Reconnected, retrying publish...")
                    # Retry publish
                    await self.redis_client.publish(channel, message_json)
                    await self.redis_client.publish("camera:status:all", message_json)
                    logger.info("✅ Reconnected and published after connection loss")
                else:
                    raise
            
            logger.debug(f"📢 Published status: {device_id} → {event.value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish status for {device_id}: {e}", exc_info=True)
            # Try to reconnect
            try:
                await self.connect()
            except:
                pass
    
    async def publish_segment_batch_ready(
        self,
        device_id: str,
        session_uuid: str,
        segment_count: int,
        segments: List[str]
    ):
        """
        Publish event when a batch of segments is ready for upload.
        
        Args:
            device_id: Camera device identifier
            session_uuid: Recording session UUID
            segment_count: Number of segments in batch
            segments: List of segment file paths
        """
        if not self.connected:
            logger.debug(f"Redis not connected, skipping segment batch event for {device_id}")
            return
        
        try:
            channel = f"camera:segments:{device_id}"
            
            message = {
                "device_id": device_id,
                "session_uuid": session_uuid,
                "event": "batch_ready",
                "segment_count": segment_count,
                "segments": segments,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            message_json = json.dumps(message)
            
            # Try to publish, reconnect once if needed
            try:
                await self.redis_client.publish(channel, message_json)
                logger.info(
                    f"📤 Published segment batch ready: {device_id} "
                    f"({segment_count} segments, session {session_uuid})"
                )
            except (ConnectionError, TimeoutError, OSError, RuntimeError) as conn_err:
                logger.warning(f"⚠️ Redis connection lost, attempting reconnect: {conn_err}")
                await self.connect()
                if self.connected:
                    await self.redis_client.publish(channel, message_json)
                    logger.info("✅ Reconnected and published segment batch event")
                else:
                    raise
            
        except Exception as e:
            logger.error(f"❌ Failed to publish segment batch event for {device_id}: {e}")
            try:
                await self.connect()
            except:
                pass
    
    async def subscribe_to_camera(self, device_id: str) -> redis.client.PubSub:
        """
        Subscribe to status updates for a specific camera.
        
        Args:
            device_id: Camera device identifier
            
        Returns:
            PubSub object for receiving messages
        """
        if not self.connected:
            raise RuntimeError("Redis not connected")
        
        channel = f"camera:status:{device_id}"
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        self.active_channels.add(channel)
        logger.info(f"📺 Subscribed to {channel}")
        
        return pubsub
    
    async def subscribe_to_all_cameras(self) -> redis.client.PubSub:
        """
        Subscribe to status updates for all cameras.
        
        Returns:
            PubSub object for receiving messages
        """
        if not self.connected:
            raise RuntimeError("Redis not connected")
        
        channel = "camera:status:all"
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        self.active_channels.add(channel)
        logger.info(f"📺 Subscribed to all camera statuses")
        
        return pubsub
    
    async def get_camera_status(self, device_id: str) -> Optional[Dict]:
        """
        Get current cached status for a camera.
        
        Args:
            device_id: Camera device identifier
            
        Returns:
            Status dict or None if not found
        """
        if not self.connected:
            return None
        
        try:
            key = f"camera:current_status:{device_id}"
            status_json = await self.redis_client.get(key)
            
            if status_json:
                return json.loads(status_json)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached status for {device_id}: {e}")
            return None
    
    async def cache_camera_status(
        self,
        device_id: str,
        status: str,
        details: Optional[Dict] = None,
        ttl: int = 300
    ):
        """
        Cache current camera status in Redis.
        
        Args:
            device_id: Camera device identifier
            status: Current status
            details: Optional additional details
            ttl: Time to live in seconds (default 5 minutes)
        """
        if not self.connected:
            return
        
        try:
            key = f"camera:current_status:{device_id}"
            
            status_data = {
                "device_id": device_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            }
            
            status_json = json.dumps(status_data)
            
            await self.redis_client.setex(key, ttl, status_json)
            
        except Exception as e:
            logger.error(f"Error caching status for {device_id}: {e}")


# Singleton instance
_status_service: Optional[StatusNotificationService] = None


def get_status_service() -> StatusNotificationService:
    """Get singleton status notification service instance."""
    global _status_service
    if _status_service is None:
        _status_service = StatusNotificationService()
    return _status_service


async def initialize_status_service():
    """Initialize and connect status notification service."""
    service = get_status_service()
    await service.connect()
    return service


async def shutdown_status_service():
    """Shutdown status notification service."""
    global _status_service
    if _status_service:
        await _status_service.disconnect()
        _status_service = None
