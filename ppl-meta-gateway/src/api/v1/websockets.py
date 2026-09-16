"""
WebSocket endpoints for real-time data streaming
"""

import asyncio
import json
from typing import Optional, Set
from urllib.parse import urlencode

import os

import redis.asyncio as aioredis
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])

# Camera status WS lives at /api/v1/cameras/ws/... (no /ws prefix).
cameras_status_proxy_router = APIRouter(tags=["camera-status-ws-proxy"])


def _cameras_service_base() -> str:
    return os.getenv("CAMERAS_SERVICE_URL", "http://ppl-meta-cameras:8005").rstrip("/")


def _cameras_ws_upstream(path_suffix: str, query_params) -> str:
    """Build ws://cameras-service URL for status websocket proxying."""
    base = _cameras_service_base()
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://") :]
    else:
        ws_base = base
    query = urlencode([(k, v) for k, v in query_params.items()])
    url = f"{ws_base}/api/v1/cameras{path_suffix}"
    return f"{url}?{query}" if query else url


async def _proxy_camera_status_websocket(client_ws: WebSocket, path_suffix: str) -> None:
    """Bidirectional proxy between browser and cameras status websocket."""
    await client_ws.accept()
    upstream_url = _cameras_ws_upstream(path_suffix, client_ws.query_params)
    logger.info(f"Proxying camera status WS -> {upstream_url.split('?')[0]}")

    try:
        async with websockets.connect(upstream_url, open_timeout=10) as upstream_ws:

            async def client_to_upstream() -> None:
                try:
                    while True:
                        message = await client_ws.receive_text()
                        await upstream_ws.send(message)
                except WebSocketDisconnect:
                    await upstream_ws.close()
                except Exception:
                    try:
                        await upstream_ws.close()
                    except Exception:
                        pass

            async def upstream_to_client() -> None:
                try:
                    async for message in upstream_ws:
                        if isinstance(message, bytes):
                            await client_ws.send_bytes(message)
                        else:
                            await client_ws.send_text(message)
                except Exception:
                    try:
                        await client_ws.close()
                    except Exception:
                        pass

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except Exception as e:
        logger.error(f"Camera status WS proxy error: {e}")
        try:
            await client_ws.close(code=1011)
        except Exception:
            pass


@cameras_status_proxy_router.websocket("/cameras/ws/status")
async def proxy_all_cameras_status_ws(websocket: WebSocket):
    """Proxy /api/v1/cameras/ws/status to the cameras service."""
    await _proxy_camera_status_websocket(websocket, "/ws/status")


@cameras_status_proxy_router.websocket("/cameras/ws/status/{device_id}")
async def proxy_one_camera_status_ws(websocket: WebSocket, device_id: str):
    """Proxy /api/v1/cameras/ws/status/{device_id} to the cameras service."""
    await _proxy_camera_status_websocket(websocket, f"/ws/status/{device_id}")


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
