"""Management API for edge camera remote control."""
import logging
import subprocess
import time
import sys
import psutil
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import yaml

from config import get_config, set_config, load_config, AppConfig

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Application start time for uptime calculation
app_start_time = time.time()


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[str]:
    """
    Verify JWT token for API authentication.

    Security hardening (Proposal §10.2 C5): validates JWT signature
    using the platform's SECRET_KEY. Falls back to dev mode only when
    ENVIRONMENT=development and no API key is configured.
    """
    import os
    config = get_config()
    is_dev = os.environ.get("ENVIRONMENT") == "development"

    # Dev mode without API key: allow for local testing only
    if is_dev and not config.platform.api_key:
        logger.warning("⚠️ Development mode — API key not configured")
        if not credentials:
            return None
        token = credentials.credentials
        logger.debug("Dev mode: accepting token without validation")
        return token

    # Production or dev with API key: require valid authorization
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials

    # Try JWT validation against platform SECRET_KEY
    secret_key = os.environ.get("SECRET_KEY", "")
    if secret_key:
        try:
            import jwt as pyjwt
            pyjwt.decode(token, secret_key, algorithms=["HS256"])
            return token
        except Exception as exc:
            if not is_dev:
                raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
            # Dev fallback: accept token even if JWT validation fails
            logger.warning("Dev mode: JWT validation failed but accepting token: %s", exc)
            return token

    # Legacy fallback: simple API key comparison
    if token == config.platform.api_key:
        return token

    raise HTTPException(status_code=401, detail="Invalid API key or token")


async def get_configuration() -> Dict[str, Any]:
    """Get current configuration."""
    config = get_config()
    return config.model_dump()


async def update_configuration(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update configuration dynamically.
    
    Args:
        updates: Dictionary with configuration updates (nested keys with dots)
        
    Returns:
        Updated configuration
    """
    config = get_config()
    config_dict = config.model_dump()
    
    # Apply updates (supports nested keys like "platform.cameras_url")
    for key, value in updates.items():
        if '.' in key:
            # Handle nested keys
            parts = key.split('.')
            current = config_dict
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            config_dict[key] = value
    
    # Create new config instance
    new_config = AppConfig(**config_dict)
    set_config(new_config)
    
    # Optionally persist to YAML file
    try:
        await persist_configuration(config_dict)
        logger.info("✅ Configuration updated and persisted")
    except Exception as e:
        logger.warning(f"⚠️ Configuration updated but not persisted: {e}")
    
    return new_config.model_dump()


async def persist_configuration(config_dict: Dict[str, Any]):
    """Persist configuration to YAML file."""
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "config" / "default.yaml"
    
    with open(config_path, 'w') as f:
        yaml.safe_dump(config_dict, f, default_flow_style=False)
    
    logger.info(f"Configuration persisted to {config_path}")


async def configure_platform(
    discovery_ip: str,
    discovery_port: int = 8006,
    cameras_port: int = 8005,
    use_nginx: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Configure platform connection (similar to mobile camera's configureFromUserInput).
    
    Args:
        discovery_ip: IP address of discovery service
        discovery_port: Port of discovery service
        cameras_port: Port of cameras service
        use_nginx: If True, use nginx proxy URLs
        api_key: Optional JWT API key
        
    Returns:
        Updated configuration
    """
    if use_nginx:
        # Use nginx proxy paths
        cameras_url = f"http://{discovery_ip}/cameras"
        discovery_url = f"http://{discovery_ip}/discovery"
    else:
        # Direct service URLs
        cameras_url = f"http://{discovery_ip}:{cameras_port}"
        discovery_url = f"http://{discovery_ip}:{discovery_port}"
    
    updates = {
        "platform.cameras_url": cameras_url,
        "platform.discovery_url": discovery_url,
    }
    
    if api_key:
        updates["platform.api_key"] = api_key
    
    return await update_configuration(updates)


async def get_logs(lines: int = 100, follow: bool = False) -> Dict[str, Any]:
    """
    Get application logs.
    
    Args:
        lines: Number of log lines to return
        follow: If True, stream logs (not implemented yet)
        
    Returns:
        Dictionary with logs and metadata
    """
    log_lines = []
    
    # Try to read from log file if exists
    log_dir = Path("/var/log/edge-camera")
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if log_files:
            log_file = log_files[0]
            try:
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    log_lines = [line.strip() for line in log_lines]
                
                return {
                    "logs": log_lines,
                    "total_lines": len(log_lines),
                    "log_file": str(log_file),
                    "source": "file"
                }
            except Exception as e:
                logger.error(f"Failed to read log file: {e}")
    
    # Try journald (systemd)
    if is_systemd():
        try:
            result = subprocess.run(
                ["journalctl", "-u", "edge-camera", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                log_lines = result.stdout.strip().split('\n')
                return {
                    "logs": log_lines,
                    "total_lines": len(log_lines),
                    "log_file": "journald",
                    "source": "journald"
                }
        except Exception as e:
            logger.error(f"Failed to get journald logs: {e}")
    
    # Fallback: return message
    return {
        "logs": ["No logs available - check application logs directly"],
        "total_lines": 1,
        "log_file": None,
        "source": "none"
    }


async def get_status(camera_instance=None, streaming_client_instance=None, health_monitor_instance=None) -> Dict[str, Any]:
    """
    Get detailed application status.
    
    Args:
        camera_instance: Camera capture instance
        streaming_client_instance: Streaming client instance
        health_monitor_instance: Health monitor instance
        
    Returns:
        Detailed status dictionary
    """
    config = get_config()
    uptime_seconds = time.time() - app_start_time
    
    # Application info
    app_status = {
        "version": "2.24.31",
        "uptime_seconds": int(uptime_seconds),
        "status": "running"
    }
    
    # Camera info
    camera_status = {
        "connected": False,
        "device_id": config.camera.device_id,
        "resolution": f"{config.camera.resolution.width}x{config.camera.resolution.height}",
        "fps_configured": config.camera.fps,
        "fps_actual": 0.0
    }
    
    if camera_instance:
        camera_stats = camera_instance.get_stats() if hasattr(camera_instance, 'get_stats') else {}
        camera_status["connected"] = True
        camera_status["fps_actual"] = camera_stats.get("fps", 0.0)
        camera_status["frames_captured"] = camera_stats.get("frame_count", 0)
    
    # Streaming info
    streaming_status = {
        "active": False,
        "frames_sent": 0,
        "errors": 0
    }
    
    if streaming_client_instance:
        streaming_status["active"] = streaming_client_instance.is_streaming if hasattr(streaming_client_instance, 'is_streaming') else False
        if hasattr(streaming_client_instance, 'get_stats'):
            stats = streaming_client_instance.get_stats()
            streaming_status["frames_sent"] = stats.get("frames_sent", 0)
            streaming_status["errors"] = stats.get("errors", 0)
    
    # Platform connection info
    platform_status = {
        "websocket_connected": False,
        "registered": False,
        "last_heartbeat": None
    }
    
    if health_monitor_instance and hasattr(health_monitor_instance, 'get_health_status'):
        health = health_monitor_instance.get_health_status()
        platform_status["websocket_connected"] = health.get("websocket") == "ok"
        platform_status["registered"] = health.get("registration") == "registered"
    
    # System info
    system_status = {
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "memory_usage_mb": psutil.virtual_memory().used // (1024 * 1024),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage('/').percent,
    }
    
    # Try to get temperature (RPi specific)
    try:
        temp = get_system_temperature()
        if temp:
            system_status["temperature_c"] = temp
    except:
        pass
    
    return {
        "application": app_status,
        "camera": camera_status,
        "streaming": streaming_status,
        "platform": platform_status,
        "system": system_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def network_diagnostics() -> Dict[str, Any]:
    """
    Run network diagnostics to test connectivity to platform services.
    
    Returns:
        Dictionary with test results
    """
    config = get_config()
    tests = []
    
    # Test discovery service
    discovery_result = await test_service_health(
        "discovery",
        config.platform.discovery_url
    )
    tests.append(discovery_result)
    
    # Test cameras service
    cameras_result = await test_service_health(
        "cameras",
        config.platform.cameras_url
    )
    tests.append(cameras_result)
    
    return {
        "tests": tests,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "all_passed": all(t["reachable"] for t in tests)
    }


async def test_service_health(service_name: str, base_url: str) -> Dict[str, Any]:
    """Test if a service is reachable."""
    import aiohttp
    
    health_url = f"{base_url}/health"
    
    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                reachable = response.status == 200
                
                return {
                    "service": service_name,
                    "url": health_url,
                    "reachable": reachable,
                    "latency_ms": latency_ms,
                    "status_code": response.status
                }
    except Exception as e:
        return {
            "service": service_name,
            "url": health_url,
            "reachable": False,
            "latency_ms": None,
            "error": str(e)
        }


async def restart_application(scope: str = "application"):
    """
    Restart the application or system.
    
    Args:
        scope: "application" for app restart, "system" for full reboot
    """
    if scope == "application":
        logger.info("🔄 Restarting application...")
        
        if is_systemd():
            # Systemd will restart the service
            subprocess.run(["systemctl", "restart", "edge-camera"])
        else:
            # Docker or direct run - exit and let container runtime restart
            sys.exit(0)
    
    elif scope == "system":
        logger.info("🔄 Rebooting system...")
        try:
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reboot system: {e}"
            )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope: {scope}. Must be 'application' or 'system'"
        )


async def reconnect_service(service: str):
    """
    Reconnect to a platform service.
    
    Args:
        service: "websocket" or "registration"
    """
    if service == "websocket":
        logger.info("🔄 Reconnecting WebSocket...")
        # WebSocket client will handle reconnection automatically
        return {"status": "reconnecting", "service": "websocket"}
    
    elif service == "registration":
        logger.info("🔄 Re-registering with discovery service...")
        # Re-registration will happen automatically on next health check
        return {"status": "reconnecting", "service": "registration"}
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Must be 'websocket' or 'registration'"
        )


def is_systemd() -> bool:
    """Check if running under systemd."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "edge-camera"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False


def get_system_temperature() -> Optional[float]:
    """Get system temperature (RPi specific)."""
    try:
        # RPi temperature
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_str = f.read().strip()
            return float(temp_str) / 1000.0
    except:
        return None


def set_app_start_time():
    """Set application start time for uptime calculation."""
    global app_start_time
    app_start_time = time.time()
