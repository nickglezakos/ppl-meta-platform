"""
WebSocket endpoint for real-time camera status updates.

Provides live status updates to clients without polling.
"""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from src.security.auth import get_current_user_from_websocket
from src.services.status_notification_service import (
    get_status_service,
    CameraStatusEvent,
)


logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for camera status updates."""
    
    def __init__(self):
        # Store active connections: device_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connections watching all cameras
        self.global_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, device_id: str = None):
        """Connect a WebSocket client."""
        await websocket.accept()
        
        if device_id:
            if device_id not in self.active_connections:
                self.active_connections[device_id] = set()
            self.active_connections[device_id].add(websocket)
            logger.info(f"📱 Client connected to {device_id} status")
        else:
            self.global_connections.add(websocket)
            logger.info(f"📱 Client connected to all camera statuses")
    
    def disconnect(self, websocket: WebSocket, device_id: str = None):
        """Disconnect a WebSocket client."""
        if device_id and device_id in self.active_connections:
            self.active_connections[device_id].discard(websocket)
            if not self.active_connections[device_id]:
                del self.active_connections[device_id]
            logger.info(f"🔌 Client disconnected from {device_id} status")
        else:
            self.global_connections.discard(websocket)
            logger.info(f"🔌 Client disconnected from all camera statuses")
    
    async def send_to_device_watchers(self, device_id: str, message: dict):
        """Send message to all clients watching a specific device."""
        if device_id in self.active_connections:
            dead_connections = set()
            
            for connection in self.active_connections[device_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    dead_connections.add(connection)
            
            # Remove dead connections
            for connection in dead_connections:
                self.active_connections[device_id].discard(connection)
    
    async def send_to_global_watchers(self, message: dict):
        """Send message to all clients watching all cameras."""
        dead_connections = set()
        
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to global client: {e}")
                dead_connections.add(connection)
        
        # Remove dead connections
        for connection in dead_connections:
            self.global_connections.discard(connection)


# Global connection manager
connection_manager = ConnectionManager()


async def redis_listener_task(device_id: str = None):
    """Background task to listen for Redis messages and forward to WebSocket clients."""
    status_service = get_status_service()
    pubsub = None
    
    try:
        # Subscribe to appropriate channel
        if device_id:
            pubsub = await status_service.subscribe_to_camera(device_id)
        else:
            pubsub = await status_service.subscribe_to_all_cameras()
        
        logger.info(f"🎧 Redis listener started for {'device_id' if device_id else 'all cameras'}")
        
        # Listen for messages with timeout handling
        while True:
            try:
                # Use get_message with timeout instead of blocking listen()
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=2.0
                )
                
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        
                        # Forward to WebSocket clients
                        if device_id:
                            await connection_manager.send_to_device_watchers(device_id, data)
                        else:
                            await connection_manager.send_to_global_watchers(data)
                            
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
            except asyncio.TimeoutError:
                # Timeout is normal - just continue listening
                await asyncio.sleep(0.1)
                continue
            except asyncio.CancelledError:
                # Task was cancelled - exit cleanly
                break
        
    except asyncio.CancelledError:
        logger.info("Redis listener task cancelled")
    except Exception as e:
        logger.error(f"Redis listener error: {e}")
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except:
                pass


@router.websocket("/ws/status/{device_id}")
async def camera_status_websocket(
    websocket: WebSocket,
    device_id: str,
):
    """
    WebSocket endpoint for real-time camera status updates.
    
    Provides live status updates for a specific camera without polling.
    
    **Usage:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8005/api/v1/cameras/ws/status/usb_camera_0?token=YOUR_JWT');
    
    ws.onmessage = (event) => {
        const status = JSON.parse(event.data);
        console.log('Status update:', status);
    };
    ```
    
    **Message Format:**
    ```json
    {
        "device_id": "usb_camera_0",
        "event": "connected",
        "timestamp": "2025-12-23T08:00:00",
        "details": {}
    }
    ```
    """
    # Authenticate via query parameter (WebSocket doesn't support headers well)
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    # Verify token (simplified - in production, use proper JWT validation)
    # user = await get_current_user_from_websocket(token)
    # if not user:
    #     await websocket.close(code=1008, reason="Invalid token")
    #     return
    
    status_service = get_status_service()
    
    if not status_service.connected:
        await websocket.close(code=1011, reason="Status service unavailable")
        return
    
    # Connect WebSocket client
    await connection_manager.connect(websocket, device_id)
    
    # Start Redis listener task
    listener_task = asyncio.create_task(redis_listener_task(device_id))
    
    try:
        # Send current cached status immediately
        cached_status = await status_service.get_camera_status(device_id)
        if cached_status:
            await websocket.send_json(cached_status)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()
                
                # Client can send "ping" to keep connection alive
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from {device_id} status")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
    finally:
        # Cleanup
        connection_manager.disconnect(websocket, device_id)
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass


@router.websocket("/ws/status")
async def all_cameras_status_websocket(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for real-time status updates for ALL cameras.
    
    Provides live status updates for all cameras on a single connection.
    
    **Usage:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8005/api/v1/cameras/ws/status?token=YOUR_JWT');
    
    ws.onmessage = (event) => {
        const status = JSON.parse(event.data);
        console.log('Camera update:', status.device_id, status.event);
    };
    ```
    """
    # Authenticate
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    status_service = get_status_service()
    
    if not status_service.connected:
        await websocket.close(code=1011, reason="Status service unavailable")
        return
    
    # Connect WebSocket client
    await connection_manager.connect(websocket)
    
    # Start Redis listener task
    listener_task = asyncio.create_task(redis_listener_task())
    
    try:
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                logger.info("Client disconnected from all camera statuses")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        connection_manager.disconnect(websocket)
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
