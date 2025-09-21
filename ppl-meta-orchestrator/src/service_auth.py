"""
PPL Meta Orchestrator - Service Authentication
Handles JWT token generation for inter-service authentication
"""

import logging
import time
from typing import Optional

try:
    import jwt
except ImportError:
    # Fallback if PyJWT not installed
    jwt = None

from config import settings

logger = logging.getLogger(__name__)


class ServiceAuthManager:
    """Manages JWT tokens for service-to-service authentication."""

    def __init__(self):
        self.node_secret = settings.NODE_SERVICE_SECRET
        self.service_name = "orchestrator"
        self.algorithm = "HS256"

    def create_service_token(self, user_id: str, expires_hours: int = 24) -> str:
        """
        Create a JWT token for service-to-service authentication.
        This token will be accepted by other services using NODE_SECRET.
        """
        if jwt is None:
            raise ImportError("PyJWT library not installed")

        try:
            # Create simple payload matching Node service pattern
            payload = {
                "sub": str(user_id),  # Subject (user ID)
                "exp": int(time.time()) + (expires_hours * 3600),  # Expiration
            }

            # Sign the token with the shared secret
            token = jwt.encode(payload, self.node_secret, algorithm=self.algorithm)

            logger.debug(
                "Created service token for user %s, expires in %sh",
                user_id,
                expires_hours,
            )
            return token

        except Exception as e:
            logger.error("Failed to create service token: %s", e)
            raise

    def verify_service_token(self, token: str) -> Optional[dict]:
        """Verify a service token (for incoming requests)."""
        if jwt is None:
            logger.error("PyJWT library not installed")
            return None

        try:
            payload = jwt.decode(token, self.node_secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid service token: %s", e)
            return None


# Global instance
service_auth = ServiceAuthManager()

