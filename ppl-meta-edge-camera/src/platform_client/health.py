"""Health monitoring module."""
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor application health status."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.start_time = datetime.now()
        self.camera_status = "inactive"
        self.streaming_status = "inactive"
        self.registration_status = "not_registered"
        self.last_error: str = ""
        self.error_count = 0
        
    def set_camera_status(self, status: str):
        """Set camera status."""
        self.camera_status = status
        logger.debug(f"Camera status: {status}")
    
    def set_streaming_status(self, status: str):
        """Set streaming status."""
        self.streaming_status = status
        logger.debug(f"Streaming status: {status}")
    
    def set_registration_status(self, status: str):
        """Set registration status."""
        self.registration_status = status
        logger.debug(f"Registration status: {status}")
    
    def record_error(self, error: str):
        """Record an error."""
        self.last_error = error
        self.error_count += 1
        logger.error(f"Error recorded: {error}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status.
        
        Returns:
            Dict with health status information
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Overall health is ok if camera is active
        is_healthy = self.camera_status == "active"
        
        return {
            "status": "ok" if is_healthy else "error",
            "uptime_seconds": uptime,
            "camera": self.camera_status,
            "streaming": self.streaming_status,
            "registration": self.registration_status,
            "error_count": self.error_count,
            "last_error": self.last_error if self.last_error else None,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_detailed_status(self, camera_stats: Dict = None) -> Dict[str, Any]:
        """
        Get detailed status including camera statistics.
        
        Args:
            camera_stats: Camera statistics from CameraCapture
            
        Returns:
            Dict with detailed status information
        """
        health = self.get_health_status()
        
        if camera_stats:
            health["camera_stats"] = camera_stats
        
        return health
