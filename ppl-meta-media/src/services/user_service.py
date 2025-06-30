"""
User Management service client for inter-service communication.
"""
import httpx
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
import os

logger = logging.getLogger(__name__)

class UserServiceClient:
    """Client for communicating with User Management microservice."""
    
    def __init__(self):
        self.base_url = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
        self.api_prefix = "/api/v1"
        self.timeout = int(os.getenv("USER_SERVICE_TIMEOUT", "30"))
        
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token with User Management service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/auth/validate",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    return None
                else:
                    logger.error(f"User service validation failed: {response.status_code}")
                    return None
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to User Management service: {e}")
            return None
    
    async def get_user_info(self, user_id: str, token: str) -> Optional[Dict[str, Any]]:
        """Get user information from User Management service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/users/{user_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user info: {response.status_code}")
                    return None
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to User Management service: {e}")
            return None
    
    async def check_user_permissions(self, user_id: str, resource: str, action: str, token: str) -> bool:
        """Check if user has permission for specific resource and action."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {token}"}
                params = {
                    "resource": resource,
                    "action": action
                }
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/users/{user_id}/permissions",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("has_permission", False)
                else:
                    logger.error(f"Failed to check permissions: {response.status_code}")
                    return False
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to User Management service: {e}")
            return False

# Global instance
user_service_client = UserServiceClient()
