"""Edge camera application - Main entry point."""
import asyncio
import logging
import signal
import sys
import time
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import uvicorn

from config import get_config
from camera import CameraCapture, FrameEncoder
from streaming import StreamingClient, FrameBuffer
from platform import HealthMonitor, RegistrationClient
from platform.websocket_client import PlatformWebSocketClient

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


@app.get("/")
async def root():
    """Root endpoint."""
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
    global streaming_client
    
    if streaming_client is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Streaming client not initialized"}
        )
    
    if streaming_client.is_streaming:
        return {"status": "already_streaming", "message": "Streaming already active"}
    
    streaming_client.start()
    health_monitor.set_streaming_status("active")
    logger.info("✅ Edge camera streaming started")
    
    return {"status": "streaming", "message": "Streaming started successfully"}


@app.post("/stop-stream")
async def stop_stream():
    """Stop streaming frames to platform."""
    global streaming_client
    
    if streaming_client is None or not streaming_client.is_streaming:
        return {"status": "not_streaming", "message": "Streaming not active"}
    
    streaming_client.stop()
    health_monitor.set_streaming_status("stopped")
    logger.info("Edge camera streaming stopped")
    
    return {"status": "stopped", "message": "Streaming stopped successfully"}


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Setup logging
    config = get_config()
    setup_logging(
        level=config.logging.level,
        log_format=config.logging.format
    )
    
    logger = logging.getLogger(__name__)
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
