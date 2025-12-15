"""
WebSocket endpoints for real-time data streaming
"""

import asyncio
import json
from typing import Set

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])


class ConnectionManager:
    """Manages WebSocket connections for instant detection broadcasts"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.redis_client: aioredis.Redis = None
        self.pubsub = None
        self.listener_task = None

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Start Redis listener if this is the first connection
        if len(self.active_connections) == 1 and self.listener_task is None:
            await self.start_redis_listener()

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

        # Stop Redis listener if no more connections
        if len(self.active_connections) == 0:
            await self.stop_redis_listener()

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections.discard(connection)

    async def start_redis_listener(self):
        """Start listening to Redis pub/sub for instant detection events"""
        try:
            self.redis_client = aioredis.from_url(
                "redis://localhost:6379", decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("instant-detection")

            logger.info("✅ Started Redis listener for instant-detection channel")

            # Start background task to listen for messages
            self.listener_task = asyncio.create_task(self._redis_listener())

        except Exception as e:
            logger.error(f"❌ Failed to start Redis listener: {e}")

    async def stop_redis_listener(self):
        """Stop Redis listener when no more WebSocket connections"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None

        if self.pubsub:
            await self.pubsub.unsubscribe("instant-detection")
            await self.pubsub.close()
            self.pubsub = None

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

        logger.info("✅ Stopped Redis listener")

    async def _redis_listener(self):
        """Background task that listens to Redis and broadcasts to WebSockets"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse Redis message
                        data = json.loads(message["data"])

                        # Broadcast to all WebSocket clients
                        await self.broadcast({
                            "type": "instant-detection",
                            "data": data
                        })

                        logger.debug(
                            f"📡 Broadcast instant detection: "
                            f"camera={data.get('camera_id')}, "
                            f"people={data.get('people_count')}"
                        )

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/instant-detection")
async def websocket_instant_detection(websocket: WebSocket):
    """
    WebSocket endpoint for real-time instant detection updates.
    
    Clients connect to this endpoint and receive push notifications
    whenever instant detection results are published to Redis.
    
    Message format:
    {
        "type": "instant-detection",
        "data": {
            "camera_id": "usb_camera_0",
            "timestamp": "2025-12-15T08:00:00+02:00",
            "people_count": 2,
            "demographics": {...},
            "metadata": {...}
        }
    }
    """
    await manager.connect(websocket)

    try:
        # Keep connection alive and handle client messages
        while True:
            # Wait for any messages from client (like ping/pong)
            try:
                data = await websocket.receive_text()
                # Echo back for ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)
