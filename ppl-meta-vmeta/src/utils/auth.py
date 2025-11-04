"""
Authentication Utilities

JWT token verification and user extraction for MVR-People API.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import logging
import jwt
from typing import Optional, Dict
from datetime import datetime, timedelta

# Import settings to use same JWT configuration as node service
from config.settings import settings

logger = logging.getLogger(__name__)

# JWT Configuration (matches Node service configuration)
JWT_SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRATION_HOURS = settings.JWT_EXPIRATION_HOURS


async def verify_jwt_token(token: str) -> bool:
    """
    Verify JWT token signature and expiration.
    
    **Verification Steps:**
    1. Decode JWT token
    2. Check signature
    3. Check expiration
    4. Validate payload
    
    Args:
        token: JWT token string
        
    Returns:
        bool: True if token is valid
    """
    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Check expiration
        exp = payload.get('exp')
        if exp:
            exp_datetime = datetime.fromtimestamp(exp)
            if exp_datetime < datetime.now():
                logger.warning("Token expired")
                return False
        
        # Check required fields
        if 'sub' not in payload:  # Subject (user identifier)
            logger.warning("Token missing subject")
            return False
        
        return True
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired (ExpiredSignatureError)")
        return False
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return False
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return False


async def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Extract user information from JWT token.
    
    **Token Payload Structure:**
    ```json
    {
        "sub": "user@example.com",
        "user_uuid": "uuid-string",
        "email": "user@example.com",
        "is_admin": false,
        "exp": 1234567890
    }
    ```
    
    Args:
        token: JWT token string
        
    Returns:
        Optional[Dict]: User information or None if invalid
    """
    try:
        # Decode token (without verification - already verified)
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Extract user information
        user = {
            'email': payload.get('sub') or payload.get('email'),
            'user_uuid': payload.get('user_uuid'),
            'is_admin': payload.get('is_admin', False),
            'token': token,
        }
        
        return user
    
    except Exception as e:
        logger.error(f"Error extracting user from token: {e}")
        return None


def create_jwt_token(
    user_email: str,
    user_uuid: str,
    is_admin: bool = False
) -> str:
    """
    Create JWT token for user (for testing purposes).
    
    **Use Case:** Generate test tokens for API testing
    
    Args:
        user_email: User email address
        user_uuid: User UUID
        is_admin: Is user admin
        
    Returns:
        str: JWT token
    """
    payload = {
        'sub': user_email,
        'email': user_email,
        'user_uuid': user_uuid,
        'is_admin': is_admin,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )
    
    return token


# ============================================================================
# Export
# ============================================================================

__all__ = [
    "verify_jwt_token",
    "get_user_from_token",
    "create_jwt_token",
]
