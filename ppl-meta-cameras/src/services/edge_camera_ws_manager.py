"""WebSocket manager for edge camera connections."""
import asyncio
import json
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class EdgeCameraWebSocketManager:
    """Manages WebSocket connections from edge cameras."""
    
    def __init__(self):
        # device_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # device_id -> last heartbeat timestamp
        self.heartbeats: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        
    async def connect(self, device_id: str, websocket: WebSocket):
        """Register a new edge camera WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            # Disconnect existing connection if any
            if device_id in self.active_connections:
                old_ws = self.active_connections[device_id]
                try:
                    await old_ws.close()
                except Exception:
                    pass
            
            self.active_connections[device_id] = websocket
            self.heartbeats[device_id] = datetime.utcnow()
        
        logger.info(f"✅ Edge camera {device_id} connected via WebSocket")
        
    async def disconnect(self, device_id: str):
        """Remove edge camera connection."""
        async with self._lock:
            if device_id in self.active_connections:
                del self.active_connections[device_id]
            if device_id in self.heartbeats:
                del self.heartbeats[device_id]
        
        logger.info(f"🔌 Edge camera {device_id} disconnected")
    
    async def send_command(self, device_id: str, command: str, params: Optional[Dict] = None) -> bool:
        """
        Send a command to an edge camera.
        
        Args:
            device_id: Edge camera identifier
            command: Command name (connect, disconnect, start-stream, stop-stream)
            params: Optional command parameters
            
        Returns:
            True if command sent successfully, False otherwise
        """
        websocket = self.active_connections.get(device_id)
        
        if not websocket:
            logger.warning(f"⚠️ Edge camera {device_id} not connected, cannot send command: {command}")
            return False
        
        message = {
            "type": "command",
            "command": command,
            "params": params or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await websocket.send_json(message)
            logger.info(f"📤 Sent command '{command}' to edge camera {device_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send command to {device_id}: {e}")
            await self.disconnect(device_id)
            return False
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected edge cameras."""
        disconnected = []
        
        for device_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(device_id)
        
        # Clean up disconnected cameras
        for device_id in disconnected:
            await self.disconnect(device_id)
    
    def is_connected(self, device_id: str) -> bool:
        """Check if edge camera is currently connected."""
        return device_id in self.active_connections
    
    def get_connected_cameras(self) -> Set[str]:
        """Get set of all connected edge camera device IDs."""
        return set(self.active_connections.keys())
    
    async def update_heartbeat(self, device_id: str):
        """Update last heartbeat timestamp for edge camera."""
        async with self._lock:
            self.heartbeats[device_id] = datetime.utcnow()
    
    async def handle_message(self, device_id: str, message: Dict):
        """
        Handle incoming message from edge camera.
        
        Args:
            device_id: Edge camera identifier
            message: Message data
        """
        msg_type = message.get("type")
        
        if msg_type == "heartbeat":
            await self.update_heartbeat(device_id)
            logger.debug(f"💓 Heartbeat from {device_id}")
            
        elif msg_type == "status":
            # Edge camera status update
            status = message.get("status", {})
            logger.info(f"📊 Status update from {device_id}: {status}")
            
        elif msg_type == "error":
            error = message.get("error", "Unknown error")
            logger.error(f"❌ Error from {device_id}: {error}")
            
        elif msg_type == "ack":
            # Command acknowledgment
            command = message.get("command")
            success = message.get("success", False)
            logger.info(f"✅ ACK from {device_id} for command '{command}': {success}")
            
        else:
            logger.warning(f"⚠️ Unknown message type from {device_id}: {msg_type}")


# Global singleton instance
_ws_manager: Optional[EdgeCameraWebSocketManager] = None


def get_ws_manager() -> EdgeCameraWebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = EdgeCameraWebSocketManager()
    return _ws_manager
