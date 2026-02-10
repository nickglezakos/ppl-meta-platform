"""WebSocket client for edge camera platform communication."""
import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class PlatformWebSocketClient:
    """WebSocket client for receiving commands from platform."""
    
    def __init__(
        self,
        cameras_url: str,
        device_id: str,
        api_key: Optional[str] = None
    ):
        """
        Initialize WebSocket client.
        
        Args:
            cameras_url: Cameras service URL (e.g., http://localhost:8005)
            device_id: Edge camera device ID
            api_key: JWT token for authentication
        """
        # Convert http://localhost:8005 -> ws://localhost:8005
        ws_url = cameras_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{ws_url}/api/v1/cameras/edge/{device_id}/ws"
        self.device_id = device_id
        self.api_key = api_key
        
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False
        
        # Command handlers
        self.command_handlers: Dict[str, Callable] = {}
        
        # Reconnection settings
        self.reconnect_interval = 5  # seconds
        self.max_reconnect_attempts = None  # Infinite retries
        
    def register_command_handler(self, command: str, handler: Callable):
        """Register a handler for a specific command."""
        self.command_handlers[command] = handler
        logger.info(f"Registered handler for command: {command}")
    
    async def connect(self):
        """Establish WebSocket connection to platform."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            logger.info(f"Connecting to platform WebSocket: {self.ws_url}")
            
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            logger.info(f"✅ Connected to platform WebSocket")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to platform WebSocket: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self.is_running = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self.is_connected = False
        logger.info("WebSocket disconnected")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]):
        """Send a message to the platform."""
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send message - not connected")
            return False
        
        message = {
            "type": message_type,
            **data
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent message: {message_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_heartbeat(self):
        """Send heartbeat to platform."""
        await self.send_message("heartbeat", {
            "device_id": self.device_id,
            "status": "alive"
        })
    
    async def send_status(self, status: Dict[str, Any]):
        """Send status update to platform."""
        await self.send_message("status", {
            "device_id": self.device_id,
            "status": status
        })
    
    async def send_ack(self, command: str, success: bool, message: str = ""):
        """Send command acknowledgment to platform."""
        await self.send_message("ack", {
            "command": command,
            "success": success,
            "message": message
        })
    
    async def send_error(self, error: str):
        """Send error message to platform."""
        await self.send_message("error", {
            "device_id": self.device_id,
            "error": error
        })
    
    async def handle_command(self, command_data: Dict[str, Any]):
        """Handle incoming command from platform."""
        command = command_data.get("command")
        params = command_data.get("params", {})
        
        logger.info(f"📨 Received command: {command}")
        
        handler = self.command_handlers.get(command)
        
        if handler:
            try:
                # Execute command handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(params)
                else:
                    result = handler(params)
                
                # Send acknowledgment
                await self.send_ack(command, True, "Command executed successfully")
                logger.info(f"✅ Command '{command}' executed successfully")
                
            except Exception as e:
                logger.error(f"❌ Command '{command}' failed: {e}")
                await self.send_ack(command, False, str(e))
        else:
            logger.warning(f"⚠️ No handler registered for command: {command}")
            await self.send_ack(command, False, f"Unknown command: {command}")
    
    async def receive_loop(self):
        """Main loop for receiving messages from platform."""
        while self.is_running:
            try:
                if not self.websocket:
                    logger.warning("WebSocket not connected in receive loop")
                    await asyncio.sleep(1)
                    continue
                
                # Receive message
                message = await self.websocket.recv()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "command":
                    await self.handle_command(data)
                elif message_type == "ping":
                    await self.send_message("pong", {})
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(1)
    
    async def heartbeat_loop(self):
        """Periodic heartbeat loop."""
        while self.is_running:
            if self.is_connected:
                await self.send_heartbeat()
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def start(self):
        """Start WebSocket client with auto-reconnection."""
        self.is_running = True
        
        while self.is_running:
            try:
                await self.connect()
                
                # Start loops
                receive_task = asyncio.create_task(self.receive_loop())
                heartbeat_task = asyncio.create_task(self.heartbeat_loop())
                
                # Wait for either task to complete (connection lost)
                done, pending = await asyncio.wait(
                    [receive_task, heartbeat_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Connection lost, try to reconnect
                if self.is_running:
                    logger.warning(f"Connection lost, reconnecting in {self.reconnect_interval}s...")
                    await asyncio.sleep(self.reconnect_interval)
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.is_running:
                    logger.info(f"Retrying in {self.reconnect_interval}s...")
                    await asyncio.sleep(self.reconnect_interval)
    
    async def stop(self):
        """Stop WebSocket client."""
        logger.info("Stopping WebSocket client...")
        await self.disconnect()
