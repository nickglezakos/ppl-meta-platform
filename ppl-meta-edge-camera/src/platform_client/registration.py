"""Platform registration client."""
import logging
import requests
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class RegistrationClient:
    """Handle device registration with discovery service."""
    
    def __init__(self, discovery_url: str, device_config: Dict[str, Any]):
        """
        Initialize registration client.
        
        Args:
            discovery_url: Discovery service URL
            device_config: Device configuration dict
        """
        self.discovery_url = discovery_url.rstrip('/')
        self.device_config = device_config
        self.is_registered = False
        self.registration_data: Optional[Dict] = None
        
    def register(self) -> bool:
        """
        Register device with discovery service.
        
        Returns:
            True if registration successful, False otherwise
        """
        try:
            logger.info(f"Registering device with discovery service: {self.discovery_url}")
            
            payload = {
                "name": f"Edge Camera - {self.device_config['id']}",  # Required: human-readable name
                "service_name": f"edge-camera-{self.device_config['id']}",
                "service_type": "edge",  # Required: must be 'backend', 'frontend', or 'edge'
                "host": "edge-device",  # Edge device, not accessible from platform
                "port": 0,  # No inbound connections
                "version": "1.0.0",  # Required: service version
                "metadata": {
                    "device_id": self.device_config['id'],
                    "device_name": self.device_config['name'],
                    "location": self.device_config['location'],
                    "device_type": self.device_config.get('type', 'usb'),
                    "capabilities": ["video_capture", "streaming"],
                    "status": "active"
                }
            }
            
            response = requests.post(
                f"{self.discovery_url}/api/v1/services/register",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.registration_data = response.json()
                self.is_registered = True
                logger.info(f"Device registered successfully: {self.registration_data}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Registration request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            return False
    
    def deregister(self) -> bool:
        """
        Deregister device from discovery service.
        
        Returns:
            True if deregistration successful, False otherwise
        """
        if not self.is_registered or not self.registration_data:
            logger.warning("Device not registered, skipping deregistration")
            return True
        
        try:
            service_name = f"edge-camera-{self.device_config['id']}"
            logger.info(f"Deregistering device: {service_name}")
            
            response = requests.delete(
                f"{self.discovery_url}/api/v1/services/{service_name}",
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                self.is_registered = False
                self.registration_data = None
                logger.info("Device deregistered successfully")
                return True
            else:
                logger.warning(f"Deregistration returned: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error during deregistration: {e}")
            return False
    
    def heartbeat(self) -> bool:
        """
        Send heartbeat to discovery service.
        
        Returns:
            True if heartbeat successful, False otherwise
        """
        if not self.is_registered:
            logger.warning("Cannot send heartbeat - device not registered")
            return False
        
        try:
            service_name = f"edge-camera-{self.device_config['id']}"
            
            response = requests.post(
                f"{self.discovery_url}/api/v1/services/{service_name}/heartbeat",
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug("Heartbeat sent successfully")
                return True
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"Heartbeat error: {e}")
            return False
    
    def ensure_registered(self, max_retries: int = 3) -> bool:
        """
        Ensure device is registered, retry if needed.
        
        Args:
            max_retries: Maximum registration attempts
            
        Returns:
            True if registered, False otherwise
        """
        if self.is_registered:
            return True
        
        for attempt in range(max_retries):
            if self.register():
                return True
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying registration in {wait_time}s...")
                time.sleep(wait_time)
        
        return False
