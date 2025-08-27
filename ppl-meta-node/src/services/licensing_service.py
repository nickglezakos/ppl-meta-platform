"""
PPL Meta Node - Licensing Integration Service

This service handles communication with the bootcore licensing service and
manages local platform identity and license validation.
"""

import hashlib
import json
import logging
import platform
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from src.config import settings

logger = logging.getLogger(__name__)


class LicensingService:
    """Service for managing licensing integration with bootcore service."""

    def __init__(self):
        self.bootcore_url = settings.BOOTCORE_SERVICE_URL
        self.platform_instance_id = None
        self.cached_license_info = None
        self.cache_expiry = None

    async def get_platform_identity(self) -> Dict[str, Any]:
        """Get or create platform identity for this installation."""
        if self.platform_instance_id:
            return {"instance_id": self.platform_instance_id}

        # Generate platform identity
        machine_id = self._generate_machine_fingerprint()

        platform_data = {
            "machine_fingerprint": machine_id,
            "system_info": self._get_system_info(),
            "installation_type": "local_node",
            "node_service_version": settings.APP_VERSION,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bootcore_url}/api/v1/platform/register",
                    json=platform_data,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    self.platform_instance_id = data.get("instance_id")
                    logger.info(
                        f"Platform registered with ID: {self.platform_instance_id}"
                    )
                    return data
                else:
                    logger.error(f"Failed to register platform: {response.status_code}")
                    # Generate local fallback instance ID
                    self.platform_instance_id = str(uuid.uuid4())
                    return {
                        "instance_id": self.platform_instance_id,
                        "status": "offline",
                    }

        except Exception as e:
            logger.error(f"Error connecting to bootcore service: {e}")
            # Generate local fallback instance ID
            self.platform_instance_id = str(uuid.uuid4())
            return {"instance_id": self.platform_instance_id, "status": "offline"}

    async def get_license_status(self) -> Dict[str, Any]:
        """Get current license status from bootcore service."""
        if not self.platform_instance_id:
            await self.get_platform_identity()

        # Check cache first
        if (
            self.cached_license_info
            and self.cache_expiry
            and datetime.now() < self.cache_expiry
        ):
            return self.cached_license_info

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.bootcore_url}/api/v1/license/status",
                    params={"instance_id": self.platform_instance_id},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    license_data = response.json()
                    # Cache for 5 minutes
                    self.cached_license_info = license_data
                    self.cache_expiry = datetime.now() + timedelta(minutes=5)
                    return license_data
                else:
                    logger.warning(
                        f"License status check failed: {response.status_code}"
                    )
                    return {"status": "unknown", "error": "Service unavailable"}

        except Exception as e:
            logger.error(f"Error checking license status: {e}")
            return {"status": "offline", "error": str(e)}

    async def validate_user_limit(self, current_user_count: int) -> bool:
        """Check if current user count is within license limits."""
        license_info = await self.get_license_status()

        if license_info.get("status") == "active":
            max_users = license_info.get("max_users", 1)  # Default to 1 for trial
            return current_user_count <= max_users

        # If license check fails, allow operation but log warning
        logger.warning("License validation failed, allowing operation")
        return True

    async def get_license_info_for_user_creation(self) -> Dict[str, Any]:
        """Get license information specifically for user creation validation."""
        license_info = await self.get_license_status()

        return {
            "max_users": license_info.get("max_users", 1),
            "license_type": license_info.get("license_type", "trial"),
            "status": license_info.get("status", "unknown"),
            "expires_at": license_info.get("expires_at"),
            "features": license_info.get("features", []),
        }

    async def register_owner(self, user_data: Dict[str, Any]) -> bool:
        """Register the first user as the platform owner with bootcore."""
        if not self.platform_instance_id:
            await self.get_platform_identity()

        owner_data = {
            "instance_id": self.platform_instance_id,
            "email": user_data.get("email"),
            "username": user_data.get("username"),
            "full_name": user_data.get("full_name", ""),
            "role": "owner",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bootcore_url}/api/v1/users/register-owner",
                    json=owner_data,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info(
                        f"Owner registered with bootcore: {user_data.get('email')}"
                    )
                    return True
                else:
                    logger.error(f"Failed to register owner: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error registering owner with bootcore: {e}")
            return False

    def _generate_machine_fingerprint(self) -> str:
        """Generate a unique machine fingerprint for licensing."""
        # Collect system information
        system_info = [
            platform.machine(),
            platform.processor(),
            platform.system(),
            platform.release(),
        ]

        # Add MAC address if available
        try:
            import psutil

            network_interfaces = psutil.net_if_addrs()
            for interface, addresses in network_interfaces.items():
                for addr in addresses:
                    if (
                        addr.family == psutil.AF_LINK
                        and addr.address != "00:00:00:00:00:00"
                    ):
                        system_info.append(addr.address)
                        break
                if len([x for x in system_info if ":" in x]) > 0:  # Found MAC address
                    break
        except ImportError:
            logger.warning("psutil not available, using basic fingerprint")

        # Create hash
        fingerprint_string = "|".join(system_info)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:32]

    def _get_system_info(self) -> Dict[str, str]:
        """Get detailed system information."""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "node_service_version": settings.APP_VERSION,
        }


# Global licensing service instance
licensing_service = LicensingService()


async def get_licensing_service() -> LicensingService:
    """Get the global licensing service instance."""
    return licensing_service


async def init_licensing_service() -> None:
    """Initialize the licensing service on startup."""
    global licensing_service
    try:
        await licensing_service.get_platform_identity()
        logger.info("Licensing service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize licensing service: {e}")
