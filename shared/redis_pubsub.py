"""
Redis Pub/Sub Manager for PPL Meta Platform
Handles real-time event broadcasting for instant detection and other events
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """
    Manages Redis Pub/Sub connections for real-time event broadcasting.
    
    Usage:
        # Publisher (cameras service):
        await pubsub.publish('instant-detection', {...})
        
        # Subscriber (media service, gateway, etc.):
        async def handler(data):
            print(f"Received: {data}")
        
        await pubsub.subscribe('instant-detection', handler)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        decode_responses: bool = True
    ):
        self.redis_url = redis_url
        self.decode_responses = decode_responses
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._subscriber_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=self.decode_responses,
                encoding="utf-8"
            )
            logger.info(f"✅ Redis Pub/Sub connected to {self.redis_url}")
    
    async def disconnect(self):
        """Close Redis connection"""
        # Cancel all subscriber tasks
        for task in self._subscriber_tasks.values():
            task.cancel()
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
            logger.info("✅ Redis Pub/Sub disconnected")
    
    async def publish(
        self,
        channel: str,
        data: Dict[str, Any],
        add_timestamp: bool = True
    ) -> int:
        """
        Publish message to a Redis channel.
        
        Args:
            channel: Channel name (e.g., 'instant-detection')
            data: Dictionary to publish
            add_timestamp: Whether to add 'published_at' timestamp
            
        Returns:
            Number of subscribers that received the message
        """
        await self.connect()
        
        if add_timestamp and 'published_at' not in data:
            data['published_at'] = datetime.utcnow().isoformat()
        
        message = json.dumps(data)
        
        try:
            subscriber_count = await self.redis.publish(channel, message)
            logger.debug(
                f"📤 Published to '{channel}': {len(message)} bytes → {subscriber_count} subscribers"
            )
            return subscriber_count
        except Exception as e:
            logger.error(f"❌ Failed to publish to '{channel}': {e}")
            raise
    
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Dict[str, Any]], Any],
        error_handler: Optional[Callable[[Exception], Any]] = None
    ):
        """
        Subscribe to a Redis channel and process messages.
        
        Args:
            channel: Channel name to subscribe to
            handler: Async function to process each message
            error_handler: Optional error handling function
        """
        await self.connect()
        
        # Create new pubsub instance for this subscription
        pubsub = self.redis.pubsub()
        
        try:
            await pubsub.subscribe(channel)
            logger.info(f"✅ Subscribed to channel '{channel}'")
            
            # Start listening loop
            task = asyncio.create_task(
                self._listen_loop(pubsub, channel, handler, error_handler)
            )
            self._subscriber_tasks[channel] = task
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to '{channel}': {e}")
            raise
    
    async def _listen_loop(
        self,
        pubsub: aioredis.client.PubSub,
        channel: str,
        handler: Callable,
        error_handler: Optional[Callable]
    ):
        """Internal loop that processes messages from a subscription"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        logger.debug(f"📥 Received from '{channel}': {len(message['data'])} bytes")
                        
                        # Call handler (can be sync or async)
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON from '{channel}': {e}")
                        if error_handler:
                            await error_handler(e)
                    except Exception as e:
                        logger.error(f"❌ Error processing message from '{channel}': {e}")
                        if error_handler:
                            await error_handler(e)
                        
        except asyncio.CancelledError:
            logger.info(f"🛑 Subscription to '{channel}' cancelled")
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception as e:
            logger.error(f"❌ Listen loop error for '{channel}': {e}")
            if error_handler:
                await error_handler(e)
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        if channel in self._subscriber_tasks:
            self._subscriber_tasks[channel].cancel()
            del self._subscriber_tasks[channel]
            logger.info(f"✅ Unsubscribed from '{channel}'")


# Singleton instance
_pubsub_manager: Optional[RedisPubSubManager] = None


def get_pubsub_manager(redis_url: str = "redis://localhost:6379/0") -> RedisPubSubManager:
    """Get or create singleton RedisPubSubManager instance"""
    global _pubsub_manager
    if _pubsub_manager is None:
        _pubsub_manager = RedisPubSubManager(redis_url=redis_url)
    return _pubsub_manager
