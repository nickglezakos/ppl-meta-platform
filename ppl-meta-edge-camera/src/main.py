"""Edge camera application - Main entry point."""
import asyncio
import logging
import signal
import sys
import time
import threading
import socket
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Response, Depends, Query
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

from config import get_config
from camera import CameraCapture, FrameEncoder
from streaming import StreamingClient, FrameBuffer
from platform import HealthMonitor, RegistrationClient
from platform.websocket_client import PlatformWebSocketClient
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
    """Get device ID from config or hostname."""
    config = get_config()
    device_id = config.device.id if config.device else None
    
    if not device_id:
        hostname = socket.gethostname()
        device_id = f"edge-camera-{hostname}"
    
    return device_id


@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page with connection information."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = get_config()
    
    is_configured = bool(config.platform.discovery_url)
    status_text = "✅ Connected to Platform" if is_configured else "⚫ Waiting for Configuration"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PPL Meta Edge Camera - Setup</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 600px;
                width: 100%;
                padding: 40px;
            }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .camera-icon {{ font-size: 64px; margin-bottom: 10px; }}
            h1 {{ color: #333; font-size: 28px; margin-bottom: 10px; }}
            .status {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                background: {'#d4edda' if is_configured else '#f0f0f0'};
                color: {'#155724' if is_configured else '#666'};
                margin-top: 10px;
            }}
            .info-section {{
                background: #f8f9fa;
                border-radius: 12px;
                padding: 24px;
                margin: 20px 0;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e0e0e0;
            }}
            .info-row:last-child {{ border-bottom: none; }}
            .info-label {{ font-weight: 600; color: #666; }}
            .info-value {{
                font-family: 'Courier New', monospace;
                color: #333;
                font-weight: 500;
            }}
            .copy-btn {{
                background: #667eea;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                margin-left: 8px;
            }}
            .copy-btn:hover {{ background: #5568d3; }}
            .instructions {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                {'display: none;' if is_configured else ''}
            }}
            .instructions h2 {{ color: #856404; font-size: 18px; margin-bottom: 12px; }}
            .instructions ol {{ margin-left: 20px; color: #856404; }}
            .instructions li {{ margin: 8px 0; line-height: 1.6; }}
            .api-endpoints {{ margin: 20px 0; }}
            .api-endpoints h3 {{ color: #333; font-size: 16px; margin-bottom: 12px; }}
            .endpoint {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 6px;
                margin: 8px 0;
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }}
            .endpoint-label {{ color: #667eea; font-weight: bold; margin-right: 8px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #999; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="camera-icon">🎥</div>
                <h1>PPL Meta Edge Camera</h1>
                <div class="status">{status_text}</div>
            </div>
            
            <div class="info-section">
                <div class="info-row">
                    <span class="info-label">Device ID:</span>
                    <span class="info-value">
                        {device_id}
                        <button class="copy-btn" onclick="copyToClipboard('{device_id}')">Copy</button>
                    </span>
                </div>
                <div class="info-row">
                    <span class="info-label">IP Address:</span>
                    <span class="info-value">
                        {ip_address}
                        <button class="copy-btn" onclick="copyToClipboard('{ip_address}')">Copy</button>
                    </span>
                </div>
                <div class="info-row">
                    <span class="info-label">Management Port:</span>
                    <span class="info-value">9001</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Streaming Port:</span>
                    <span class="info-value">8554 (RTSP)</span>
                </div>
            </div>
            
            <div class="instructions">
                <h2>📝 Setup Instructions</h2>
                <ol>
                    <li>Note the <strong>IP Address</strong> above: <code>{ip_address}</code></li>
                    <li>Open your PPL Meta Platform web interface</li>
                    <li>Navigate to <strong>Cameras → Add Edge Camera</strong></li>
                    <li>Enter the IP address and click <strong>Test Connection</strong></li>
                    <li>Click <strong>Add Camera</strong> to register</li>
                    <li>Configure platform connection in the management screen</li>
                </ol>
            </div>
            
            <div class="api-endpoints">
                <h3>🔌 Available Endpoints</h3>
                <div class="endpoint">
                    <span class="endpoint-label">Management API:</span>
                    http://{ip_address}:9001/api
                </div>
                <div class="endpoint">
                    <span class="endpoint-label">Stream URL:</span>
                    rtsp://{ip_address}:8554/stream
                </div>
                <div class="endpoint">
                    <span class="endpoint-label">Health Check:</span>
                    http://{ip_address}:9001/health
                </div>
                <div class="endpoint">
                    <span class="endpoint-label">Identify:</span>
                    http://{ip_address}:9001/api/identify
                </div>
            </div>
            
            <div class="footer">
                <p>PPL Meta Edge Camera v1.0.0</p>
            </div>
        </div>
        
        <script>
            function copyToClipboard(text) {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert('Copied to clipboard: ' + text);
                }}).catch(err => {{
                    console.error('Failed to copy:', err);
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
