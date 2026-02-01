"""Landing page for edge camera setup and information."""
import logging
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import socket
from pathlib import Path

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_local_ip() -> str:
    """Get local IP address of the edge camera."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"Could not determine local IP: {e}")
        return "localhost"


def get_device_id() -> str:
    """Get device ID from config or hostname."""
    config = ConfigManager.get_config()
    device_id = config.get("device_id")
    
    if not device_id:
        # Fallback to hostname
        hostname = socket.gethostname()
        device_id = f"edge-camera-{hostname}"
    
    return device_id


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve landing page with connection information."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = ConfigManager.get_config()
    
    # Check if platform is configured
    is_configured = bool(config.get("discovery_service_ip"))
    status_color = "green" if is_configured else "orange"
    status_text = "✅ Connected to Platform" if is_configured else "⚫ Waiting for Configuration"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PPL Meta Edge Camera - Setup</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            
            .camera-icon {{
                font-size: 64px;
                margin-bottom: 10px;
            }}
            
            h1 {{
                color: #333;
                font-size: 28px;
                margin-bottom: 10px;
            }}
            
            .status {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                background: #f0f0f0;
                color: #666;
                margin-top: 10px;
            }}
            
            .status.configured {{
                background: #d4edda;
                color: #155724;
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
            
            .info-row:last-child {{
                border-bottom: none;
            }}
            
            .info-label {{
                font-weight: 600;
                color: #666;
            }}
            
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
                transition: background 0.3s;
            }}
            
            .copy-btn:hover {{
                background: #5568d3;
            }}
            
            .instructions {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            
            .instructions h2 {{
                color: #856404;
                font-size: 18px;
                margin-bottom: 12px;
            }}
            
            .instructions ol {{
                margin-left: 20px;
                color: #856404;
            }}
            
            .instructions li {{
                margin: 8px 0;
                line-height: 1.6;
            }}
            
            .api-endpoints {{
                margin: 20px 0;
            }}
            
            .api-endpoints h3 {{
                color: #333;
                font-size: 16px;
                margin-bottom: 12px;
            }}
            
            .endpoint {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 6px;
                margin: 8px 0;
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }}
            
            .endpoint-label {{
                color: #667eea;
                font-weight: bold;
                margin-right: 8px;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #999;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="camera-icon">🎥</div>
                <h1>PPL Meta Edge Camera</h1>
                <div class="status {'configured' if is_configured else ''}">{status_text}</div>
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
            
            {'<div class="instructions">' if not is_configured else ''}
                {'<h2>📝 Setup Instructions</h2>' if not is_configured else ''}
                {'<ol>' if not is_configured else ''}
                    {'<li>Note the <strong>IP Address</strong> above: <code>' + ip_address + '</code></li>' if not is_configured else ''}
                    {'<li>Open your PPL Meta Platform web interface</li>' if not is_configured else ''}
                    {'<li>Navigate to <strong>Cameras → Add Edge Camera</strong></li>' if not is_configured else ''}
                    {'<li>Enter the IP address and click <strong>Test Connection</strong></li>' if not is_configured else ''}
                    {'<li>Click <strong>Add Camera</strong> to register</li>' if not is_configured else ''}
                    {'<li>Configure platform connection in the management screen</li>' if not is_configured else ''}
                {'</ol>' if not is_configured else ''}
            {'</div>' if not is_configured else ''}
            
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
                <p style="margin-top: 8px; font-size: 12px;">
                    For support, visit <a href="https://github.com/nickglezakos/ppl-meta-platform" style="color: #667eea;">GitHub</a>
                </p>
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


@router.get("/api/identify")
async def identify():
    """Identify endpoint for edge camera discovery."""
    ip_address = get_local_ip()
    device_id = get_device_id()
    config = ConfigManager.get_config()
    
    return {
        "service": "ppl-edge-camera",
        "device_id": device_id,
        "ip": ip_address,
        "management_port": 9001,
        "stream_port": 8554,
        "status": "configured" if config.get("discovery_service_ip") else "unconfigured",
        "version": "1.0.0"
    }
