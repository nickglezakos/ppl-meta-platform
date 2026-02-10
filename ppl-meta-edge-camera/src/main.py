"""Edge camera application - Main entry point."""
import asyncio
import logging
import signal
import sys
import time
import threading
import socket
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Response, Depends, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from config import get_config
from camera import CameraCapture, FrameEncoder
from streaming import StreamingClient, FrameBuffer
from platform_client import HealthMonitor, RegistrationClient
from platform_client.websocket_client import PlatformWebSocketClient
import management_api

# Global instances
camera: CameraCapture = None
encoder: FrameEncoder = None
buffer: FrameBuffer = None
streaming_client: StreamingClient = None
registration_client: RegistrationClient = None
health_monitor: HealthMonitor = None
ws_client: PlatformWebSocketClient = None
capture_thread: threading.Thread = None
is_running = False
logger = None


# Pydantic models for request/response
class ConfigUpdate(BaseModel):
    """Configuration update request."""
    updates: Dict[str, Any]


class PlatformConfigRequest(BaseModel):
    """Platform configuration request."""
    discovery_ip: str
    discovery_port: int = 8006
    cameras_port: int = 8005
    use_nginx: bool = False
    api_key: Optional[str] = None


class ControlRequest(BaseModel):
    """Control operation request."""
    action: Optional[str] = None
    scope: Optional[str] = "application"
    service: Optional[str] = None


def handle_connect_command(params):
    """Handle connect command from platform."""
    logger.info("📡 Received CONNECT command from platform")
    # Edge camera is always ready (capture running), just acknowledge
    return True


def handle_disconnect_command(params):
    """Handle disconnect command from platform."""
    logger.info("📡 Received DISCONNECT command from platform")
    # Stop streaming if active
    if streaming_client and streaming_client.is_streaming:
        streaming_client.stop()
        health_monitor.set_streaming_status("stopped")
    return True


def handle_start_stream_command(params):
    """Handle start-stream command from platform."""
    global streaming_client, is_running, capture_thread
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received START-STREAM command from platform")
    
    if streaming_client and not streaming_client.is_streaming:
        # Start capture thread if not already running
        if not is_running:
            is_running = True
            capture_thread = threading.Thread(target=capture_loop, daemon=True)
            capture_thread.start()
            logger.info("✅ Capture loop started")
        
        # Start streaming
        streaming_client.start()
        health_monitor.set_streaming_status("active")
        logger.info("✅ Streaming started via platform command")
        return True
    elif streaming_client and streaming_client.is_streaming:
        logger.info("⚠️ Streaming already active")
        return True
    else:
        logger.error("❌ Streaming client not initialized")
        return False


def handle_stop_stream_command(params):
    """Handle stop-stream command from platform."""
    global streaming_client, is_running, capture_thread
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received STOP-STREAM command from platform")
    
    if streaming_client and streaming_client.is_streaming:
        # Stop streaming first
        streaming_client.stop()
        health_monitor.set_streaming_status("stopped")
        logger.info("✅ Streaming stopped via platform command")
        
        # Stop capture loop to save resources
        if is_running:
            is_running = False
            if capture_thread:
                capture_thread.join(timeout=2)
            logger.info("✅ Capture loop stopped")
        
        return True
    else:
        logger.info("⚠️ Streaming not active")
        return True


async def handle_set_config_command(params):
    """Handle set-config command from platform."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received SET-CONFIG command from platform")
    
    try:
        # Update configuration using management API
        updated_config = await management_api.update_configuration(params)
        logger.info("✅ Configuration updated via platform command")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update configuration: {e}")
        return False


async def handle_get_logs_command(params):
    """Handle get-logs command from platform."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received GET-LOGS command from platform")
    
    try:
        lines = params.get("lines", 100)
        logs = await management_api.get_logs(lines=lines)
        
        # Send logs back to platform via WebSocket
        if ws_client:
            await ws_client.send_message("logs", logs)
        
        logger.info(f"✅ Sent {len(logs.get('logs', []))} log lines to platform")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to get logs: {e}")
        return False


async def handle_restart_command(params):
    """Handle restart command from platform."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received RESTART command from platform")
    
    try:
        scope = params.get("scope", "application")
        logger.info(f"🔄 Restarting {scope}...")
        
        # Send acknowledgment before restarting
        if ws_client:
            await ws_client.send_ack("restart", True, f"Restarting {scope}")
        
        # Delay restart to allow acknowledgment to be sent
        await asyncio.sleep(1)
        
        # Restart
        await management_api.restart_application(scope=scope)
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to restart: {e}")
        return False


async def handle_network_test_command(params):
    """Handle network-test command from platform."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Received NETWORK-TEST command from platform")
    
    try:
        diagnostics = await management_api.network_diagnostics()
        
        # Send diagnostics back to platform
        if ws_client:
            await ws_client.send_message("network_test_results", diagnostics)
        
        logger.info("✅ Network test completed and sent to platform")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to run network test: {e}")
        return False


def setup_logging(level: str = "INFO", log_format: str = None):
    """Setup application logging."""
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def capture_loop():
    """Main camera capture loop running in separate thread."""
    global is_running, camera, encoder, buffer, health_monitor
    
    logger = logging.getLogger(__name__)
    logger.info("Capture loop started")
    
    frame_interval = 1.0 / camera.fps  # Time between frames
    
    while is_running:
        try:
            start_time = time.time()
            
            # Capture frame
            success, frame = camera.read_frame()
            
            if success and frame is not None:
                # Encode frame
                timestamp = time.time()
                encoded_data = encoder.encode_frame_with_metadata(
                    frame,
                    timestamp,
                    camera.frame_count
                )
                
                if encoded_data:
                    # Add to buffer for streaming
                    buffer.put(encoded_data)
                else:
                    logger.warning("Failed to encode frame")
            else:
                logger.warning("Failed to capture frame")
                health_monitor.record_error("Frame capture failed")
            
            # Maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
            health_monitor.record_error(f"Capture loop error: {e}")
            time.sleep(1)
    
    logger.info("Capture loop stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global camera, encoder, buffer, streaming_client, registration_client, health_monitor, ws_client, capture_thread, is_running
    
    # Set application start time for uptime tracking
    management_api.set_app_start_time()
    
    logger = logging.getLogger(__name__)
    config = get_config()
    
    # Initialize components
    logger.info("Initializing edge camera application")
    
    # Health monitor
    health_monitor = HealthMonitor()
    
    # Camera
    camera = CameraCapture(
        device_id=config.camera.device_id,
        width=config.camera.resolution.width,
        height=config.camera.resolution.height,
        fps=config.camera.fps
    )
    
    # Encoder
    encoder = FrameEncoder(
        encoding=config.stream.encoding,
        quality=config.stream.quality
    )
    
    # Buffer
    buffer = FrameBuffer(max_size=config.camera.buffer_size)
    
    # Streaming client
    streaming_client = StreamingClient(
        cameras_url=config.platform.cameras_url,
        device_id=config.device.id,
        buffer=buffer,
        api_key=config.platform.api_key
    )
    
    # Registration client (discovery service)
    registration_client = RegistrationClient(
        discovery_url=config.platform.discovery_url,
        device_config=config.device.model_dump()
    )
    
    # WebSocket client for platform commands
    ws_client = PlatformWebSocketClient(
        cameras_url=config.platform.cameras_url,
        device_id=config.device.id,
        api_key=config.platform.api_key
    )
    
    # Register command handlers
    ws_client.register_command_handler("connect", handle_connect_command)
    ws_client.register_command_handler("disconnect", handle_disconnect_command)
    ws_client.register_command_handler("start-stream", handle_start_stream_command)
    ws_client.register_command_handler("stop-stream", handle_stop_stream_command)
    # New command handlers for remote management
    ws_client.register_command_handler("set-config", handle_set_config_command)
    ws_client.register_command_handler("get-logs", handle_get_logs_command)
    ws_client.register_command_handler("restart", handle_restart_command)
    ws_client.register_command_handler("network-test", handle_network_test_command)
    
    # Start camera
    if camera.start():
        logger.info("Camera started successfully")
        health_monitor.set_camera_status("active")
        
        # Register with discovery service (ecosystem-wide registration)
        logger.info("Registering edge camera with discovery service...")
        if registration_client.register():
            logger.info("✅ Edge camera registered with discovery service")
            health_monitor.set_registration_status("registered")
        else:
            logger.warning("⚠️ Failed to register with discovery service (will retry)")
            health_monitor.set_registration_status("failed")
        
        # DO NOT start capture thread yet - wait for start-stream command
        # This prevents buffer warnings when camera is idle
        
        # Start WebSocket client for platform commands (runs in background)
        asyncio.create_task(ws_client.start())
        logger.info("✅ WebSocket client started - waiting for platform commands")
        
        logger.info("Edge camera ready - capture will start when user starts streaming")
    else:
        logger.error("Failed to start camera")
        health_monitor.set_camera_status("error")
        health_monitor.record_error("Camera initialization failed")
    
    logger.info("Edge camera application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down edge camera application")
    
    # Stop WebSocket client
    if ws_client:
        await ws_client.stop()
    
    # Stop capture loop
    is_running = False
    if capture_thread:
        capture_thread.join(timeout=5)
    
    # Stop streaming
    if streaming_client:
        streaming_client.stop()
    
    # Deregister
    if registration_client:
        registration_client.deregister()
    
    # Stop camera
    if camera:
        camera.stop()
    
    logger.info("Edge camera application stopped")


# Create FastAPI app
app = FastAPI(
    title="Edge Camera",
    description="Edge camera application for streaming to ppl-meta platform",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if health_monitor is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Application not initialized"}
        )
    
    health_status = health_monitor.get_health_status()
    status_code = 200 if health_status["status"] == "ok" else 503
    
    return JSONResponse(status_code=status_code, content=health_status)


@app.get("/status")
async def get_status():
    """Get detailed status."""
    if health_monitor is None or camera is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Application not initialized"}
        )
    
    camera_stats = camera.get_stats() if camera else None
    detailed_status = health_monitor.get_detailed_status(camera_stats)
    
    # Add streaming stats
    if streaming_client:
        detailed_status["streaming_stats"] = streaming_client.get_stats()
    
    return JSONResponse(content=detailed_status)


@app.get("/config")
async def get_configuration():
    """Get current configuration."""
    config = get_config()
    return JSONResponse(content=config.model_dump())

def get_local_ip() -> str:
    """Get local IP address of the edge camera."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def get_device_id() -> str:
    """Get device ID from config or generate from MAC address."""
    config = get_config()
    device_id = config.device.id if config.device else None
    
    if not device_id:
        # Generate unique ID from MAC address
        mac = uuid.getnode()
        mac_hex = f"{mac:012x}"  # Convert to 12-char hex string
        # Use last 8 characters of MAC for shorter ID
        device_id = f"edge-camera-{mac_hex[-8:]}"
    
    return device_id


@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page with connection information."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = get_config()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eyenet Vision Edge Camera</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: #121212;
                min-height: 100vh;
                color: #E0E0E0;
            }}
            .header {{
                background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
                padding: 24px 32px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.5);
            }}
            .header-content {{
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                align-items: center;
                gap: 16px;
            }}
            .logo {{
                height: 40px;
                width: auto;
            }}
            .logo img {{
                height: 100%;
                width: auto;
            }}
            .header-title {{
                flex: 1;
            }}
            .header-title h1 {{
                color: white;
                font-size: 22px;
                font-weight: 600;
                margin-bottom: 4px;
            }}
            .header-title p {{
                color: rgba(255,255,255,0.9);
                font-size: 14px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 32px;
            }}
            .card {{
                background: #1E1E1E;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                padding: 24px;
                margin-bottom: 24px;
                border: 1px solid #2A2A2A;
            }}
            .card-title {{
                font-size: 18px;
                font-weight: 600;
                color: #E0E0E0;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .card-icon {{
                font-size: 24px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 16px;
            }}
            .info-item {{
                padding: 16px;
                background: #2A2A2A;
                border-radius: 8px;
                border-left: 4px solid #2196F3;
            }}
            .info-label {{
                font-size: 12px;
                color: #9E9E9E;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }}
            .info-value {{
                font-family: 'Courier New', monospace;
                font-size: 16px;
                color: #E0E0E0;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .copy-btn {{
                background: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
                transition: background 0.2s;
            }}
            .copy-btn:hover {{
                background: #1976D2;
            }}
            .copy-btn:active {{
                transform: scale(0.95);
            }}
            .instructions {{
                background: #2A2012;
                border-left: 4px solid #FF9800;
                padding: 20px;
                border-radius: 8px;
            }}
            .instructions-title {{
                color: #FFB74D;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .instructions ol {{
                margin-left: 20px;
                color: #FFCC80;
                line-height: 1.8;
            }}
            .instructions li {{
                margin: 8px 0;
            }}
            .instructions code {{
                background: rgba(255,255,255,0.1);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                color: #E0E0E0;
            }}
            .endpoint-grid {{
                display: grid;
                gap: 12px;
            }}
            .endpoint {{
                background: #2A2A2A;
                padding: 16px;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .endpoint-label {{
                color: #64B5F6;
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .endpoint-url {{
                font-family: 'Courier New', monospace;
                font-size: 14px;
                color: #E0E0E0;
                word-break: break-all;
            }}
            .footer {{
                text-align: center;
                padding: 32px;
                color: #757575;
                font-size: 14px;
            }}
            .success-badge {{
                background: #1B5E20;
                color: #81C784;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">
                    <img src="/static/images/eyenet-logo.png" alt="Eyenet Logo">
                </div>
                <div class="header-title">
                    <h1>Eyenet Vision Edge Camera</h1>
                    <p>Device Management & Configuration</p>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="card">
                <h2 class="card-title">
                    <span class="card-icon">📱</span>
                    Device Information
                </h2>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Device ID</div>
                        <div class="info-value">
                            {device_id}
                            <button class="copy-btn" onclick="copyToClipboard('{device_id}')">Copy</button>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">IP Address</div>
                        <div class="info-value">
                            {ip_address}
                            <button class="copy-btn" onclick="copyToClipboard('{ip_address}')">Copy</button>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Management Port</div>
                        <div class="info-value">9001</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Camera Type</div>
                        <div class="info-value">Edge Camera (RPi)</div>
                    </div>
                </div>
            </div>
            
            <div class="instructions">
                <h2 class="instructions-title">
                    <span>📝</span>
                    Quick Setup Guide
                </h2>
                <ol>
                    <li>Note the <strong>IP Address</strong>: <code>{ip_address}</code></li>
                    <li>Open your <strong>PPL Meta Platform</strong> web interface</li>
                    <li>Navigate to <strong>Cameras → Add Edge Camera</strong></li>
                    <li>Enter <code>{ip_address}</code> and click <strong>Test Connection</strong></li>
                    <li>Click <strong>Add Camera</strong> to register this device</li>
                    <li>Configure streaming settings in the platform</li>
                </ol>
            </div>
            
            <div class="card">
                <h2 class="card-title">
                    <span class="card-icon">🔌</span>
                    API Endpoints
                </h2>
                <div class="endpoint-grid">
                    <div class="endpoint">
                        <div class="endpoint-label">Management API</div>
                        <div class="endpoint-url">http://{ip_address}:9001/api</div>
                    </div>
                    <div class="endpoint">
                        <div class="endpoint-label">Health Check</div>
                        <div class="endpoint-url">http://{ip_address}:9001/health</div>
                    </div>
                    <div class="endpoint">
                        <div class="endpoint-label">Device Status</div>
                        <div class="endpoint-url">http://{ip_address}:9001/status</div>
                    </div>
                    <div class="endpoint">
                        <div class="endpoint-label">Device Identification</div>
                        <div class="endpoint-url">http://{ip_address}:9001/api/identify</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Eyenet Vision Platform • Edge Camera v1.0.0</p>
            <p style="margin-top: 8px;">Device managed by Eyenet Cameras Service</p>
        </div>
        
        <script>
            function copyToClipboard(text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    const btn = event.target;
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.style.background = '#4CAF50';
                    setTimeout(() => {{
                        btn.textContent = originalText;
                        btn.style.background = '#2196F3';
                    }}, 2000);
                }}).catch(err => {{
                    alert('Failed to copy: ' + err);
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/api/identify")
async def identify():
    """Identify endpoint for edge camera discovery."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = get_config()
    
    return {
        "service": "ppl-edge-camera",
        "device_id": device_id,
        "ip": ip_address,
        "management_port": 9001,
        "stream_port": 8554,
        "status": "configured" if config.platform.discovery_url else "unconfigured",
        "version": "1.0.0"
    }


@app.get("/old_root")
async def old_root():
    """Legacy root endpoint."""
    return {
        "service": "edge-camera",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/connect")
async def connect():
    """Connect camera (mark as ready for streaming)."""
    if camera is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Camera not initialized"}
        )
    
    logger.info("Edge camera connected")
    return {"status": "connected", "message": "Edge camera ready for streaming"}


@app.post("/disconnect")
async def disconnect():
    """Disconnect camera (stop streaming if active)."""
    global streaming_client
    
    if streaming_client and streaming_client.is_streaming:
        streaming_client.stop()
        health_monitor.set_streaming_status("stopped")
    
    logger.info("Edge camera disconnected")
    return {"status": "disconnected", "message": "Edge camera disconnected"}


@app.post("/start-stream")
async def start_stream():
    """Start streaming frames to platform."""
    global streaming_client, health_monitor
    logger = logging.getLogger(__name__)
    
    if streaming_client is None:
        logger.error("Streaming client not initialized")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Streaming client not initialized"}
        )
    
    if streaming_client.is_streaming:
        logger.info("Streaming already active")
        return {"status": "already_streaming", "message": "Streaming already active"}
    
    streaming_client.start()
    if health_monitor:
        health_monitor.set_streaming_status("active")
    logger.info("✅ Edge camera streaming started")
    
    return {"status": "streaming", "message": "Streaming started successfully"}


@app.post("/stop-stream")
async def stop_stream():
    """Stop streaming frames to platform."""
    global streaming_client, health_monitor
    logger = logging.getLogger(__name__)
    
    if streaming_client is None or not streaming_client.is_streaming:
        logger.warning("Streaming not active")
        return {"status": "not_streaming", "message": "Streaming not active"}
    
    streaming_client.stop()
    if health_monitor:
        health_monitor.set_streaming_status("stopped")
    logger.info("Edge camera streaming stopped")
    
    return {"status": "stopped", "message": "Streaming stopped successfully"}


# ========================================
# Management API Endpoints
# ========================================

@app.get("/api/config")
async def get_config_api(token: str = Depends(management_api.verify_token)):
    """Get current configuration (Management API)."""
    config = await management_api.get_configuration()
    return JSONResponse(content=config)


@app.put("/api/config")
async def update_config_api(
    config_update: ConfigUpdate,
    token: str = Depends(management_api.verify_token)
):
    """Update configuration (Management API)."""
    updated_config = await management_api.update_configuration(config_update.updates)
    return JSONResponse(content=updated_config)


@app.post("/api/config/platform")
async def configure_platform_api(
    platform_config: PlatformConfigRequest,
    token: str = Depends(management_api.verify_token)
):
    """
    Configure platform connection (Management API).
    Similar to mobile camera configureFromUserInput().
    """
    updated_config = await management_api.configure_platform(
        discovery_ip=platform_config.discovery_ip,
        discovery_port=platform_config.discovery_port,
        cameras_port=platform_config.cameras_port,
        use_nginx=platform_config.use_nginx,
        api_key=platform_config.api_key
    )
    return JSONResponse(content={
        "status": "configured",
        "message": "Platform configuration updated",
        "config": updated_config
    })


@app.post("/api/control/start")
async def control_start_api(token: str = Depends(management_api.verify_token)):
    """Start streaming (Management API)."""
    return await start_stream()


@app.post("/api/control/stop")
async def control_stop_api(token: str = Depends(management_api.verify_token)):
    """Stop streaming (Management API)."""
    return await stop_stream()


@app.post("/api/control/restart")
async def control_restart_api(
    control_req: ControlRequest,
    token: str = Depends(management_api.verify_token)
):
    """Restart application or system (Management API)."""
    await management_api.restart_application(scope=control_req.scope)
    return JSONResponse(content={
        "status": "restarting",
        "scope": control_req.scope,
        "message": f"Restarting {control_req.scope}..."
    })


@app.post("/api/control/reconnect")
async def control_reconnect_api(
    control_req: ControlRequest,
    token: str = Depends(management_api.verify_token)
):
    """Reconnect to platform services (Management API)."""
    result = await management_api.reconnect_service(control_req.service)
    return JSONResponse(content=result)


@app.get("/api/logs")
async def get_logs_api(
    lines: int = Query(100, ge=1, le=1000),
    follow: bool = Query(False),
    token: str = Depends(management_api.verify_token)
):
    """Get application logs (Management API)."""
    logs = await management_api.get_logs(lines=lines, follow=follow)
    return JSONResponse(content=logs)


@app.get("/api/status")
async def get_status_api(token: str = Depends(management_api.verify_token)):
    """Get detailed status (Management API)."""
    status = await management_api.get_status(
        camera_instance=camera,
        streaming_client_instance=streaming_client,
        health_monitor_instance=health_monitor
    )
    return JSONResponse(content=status)


@app.get("/api/diagnostics/network")
async def network_diagnostics_api(token: str = Depends(management_api.verify_token)):
    """Run network diagnostics (Management API)."""
    diagnostics = await management_api.network_diagnostics()
    return JSONResponse(content=diagnostics)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def print_startup_banner():
    """Print startup banner with connection information."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = get_config()
    
    print("\n" + "="*70)
    print("🎥  PPL Meta Edge Camera - Started Successfully")
    print("="*70)
    print(f"\n📡  Connection Information:")
    print(f"    Device ID:       {device_id}")
    print(f"    IP Address:      {ip_address}")
    print(f"    Management Port: 9001")
    print(f"    Streaming Port:  8554")
    print(f"\n🌐  Access Points:")
    print(f"    Setup Page:      http://{ip_address}:9001")
    print(f"    Management API:  http://{ip_address}:9001/api")
    print(f"    Stream URL:      rtsp://{ip_address}:8554/stream")
    print(f"    Health Check:    http://{ip_address}:9001/health")
    print(f"\n📝  Quick Setup:")
    print(f"    1. Note the IP address above: {ip_address}")
    print(f"    2. Open PPL Meta Platform web interface")
    print(f"    3. Navigate to Cameras → Add Edge Camera")
    print(f"    4. Enter IP address and click 'Test Connection'")
    print(f"    5. Click 'Add Camera' to register")
    
    if config.platform.discovery_url:
        print(f"\n✅  Platform Status: CONFIGURED")
        print(f"    Discovery Service: {config.platform.discovery_url}")
    else:
        print(f"\n⚫  Platform Status: WAITING FOR CONFIGURATION")
        print(f"    Please configure platform connection via Management API")
    
    print("\n" + "="*70 + "\n")


def main():
    """Main entry point."""
    global logger
    
    # Setup logging
    config = get_config()
    setup_logging(
        level=config.logging.level,
        log_format=config.logging.format
    )
    
    logger = logging.getLogger(__name__)
    
    # Print startup banner
    print_startup_banner()
    
    logger.info("Starting Edge Camera Application")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run FastAPI app
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        log_level=config.logging.level.lower()
    )


if __name__ == "__main__":
    main()
