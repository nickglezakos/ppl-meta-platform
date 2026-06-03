from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import config

security = HTTPBearer(auto_error=False)

JWT_SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "ppl-meta-secret-key-development-only-change-in-production",
)
JWT_ALGORITHM = "HS256"
ADMIN_ROLE_NAMES = {"admin", "owner"}
ADMIN_CAPABILITY_NAMES = {"presence.analytics.repair", "presence.config.manage"}


async def _fetch_node_user_info(user_id: str) -> dict[str, Any]:
    if not config.SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Presence service is missing SERVICE_SECRET for user resolution",
        )

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True) as client:
        response = await client.get(
            f"{config.NODE_SERVICE_URL}/users/user-info/{user_id}",
            headers={"Authorization": f"Bearer {config.SERVICE_SECRET}"},
        )

    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to resolve authenticated user information",
        )

    payload = response.json()
    return payload if isinstance(payload, dict) else {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    current_user = {
        "sub": payload.get("sub"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "permissions": payload.get("permissions", []),
        "token": token,
    }

    if current_user.get("sub") and (not current_user.get("email") or not current_user.get("username")):
        resolved_user = await _fetch_node_user_info(str(current_user["sub"]))
        current_user["email"] = current_user.get("email") or resolved_user.get("email")
        current_user["username"] = current_user.get("username") or resolved_user.get("username")

    return current_user


def _has_admin_access(current_user: Dict[str, Any]) -> bool:
    roles = {str(role).lower() for role in current_user.get("roles", [])}
    permissions = set(current_user.get("permissions", []))
    return bool(roles & ADMIN_ROLE_NAMES) or bool(permissions & ADMIN_CAPABILITY_NAMES)


async def _fetch_node_roles_and_permissions(user_id: str) -> dict[str, list[str]]:
    if not config.SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Presence service is missing SERVICE_SECRET for admin authorization",
        )

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=True) as client:
        response = await client.get(
            f"{config.NODE_SERVICE_URL}/users/user-permissions/{user_id}",
            headers={"Authorization": f"Bearer {config.SERVICE_SECRET}"},
        )

    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User permissions not found")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to resolve user permissions for admin authorization",
        )

    payload = response.json()
    return {
        "roles": [item.get("role_name") for item in payload.get("roles", []) if item.get("role_name")],
        "permissions": [item.get("name") for item in payload.get("capabilities", []) if item.get("name")],
    }


async def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if _has_admin_access(current_user):
        return current_user

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    resolved = await _fetch_node_roles_and_permissions(str(user_id))
    enriched_user = {
        **current_user,
        "roles": resolved["roles"],
        "permissions": resolved["permissions"],
    }
    if not _has_admin_access(enriched_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return enriched_user