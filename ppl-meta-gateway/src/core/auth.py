"""Authentication utilities for Gateway."""
from fastapi import Request, HTTPException, Depends
from jose import JWTError, jwt
from typing import Dict, Any

# JWT Configuration (should match Node service config)
JWT_SECRET_KEY = "ppl-meta-secret-key-development-only-change-in-production"
JWT_ALGORITHM = "HS256"


def extract_user_from_token(request: Request) -> Dict[str, Any]:
    """Extract user information from JWT token in Authorization header."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get Authorization header
        auth_header = request.headers.get("authorization")
        
        # 🔍 DEBUG: Log what we're receiving
        logger.info(f"🔐 [AUTH-CHECK] Path: {request.url.path}, Auth header: {'Present ('+str(len(auth_header))+' chars)' if auth_header else 'MISSING'}")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"🔐 [AUTH-FAIL] Path: {request.url.path}, Reason: {'Missing header' if not auth_header else 'Invalid format (not Bearer)'}")
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        # Extract token
        token = auth_header.split(" ")[1]

        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")


async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency to get current authenticated user."""
    return extract_user_from_token(request)
