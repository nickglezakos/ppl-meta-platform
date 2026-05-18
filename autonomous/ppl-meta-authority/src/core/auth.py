import os

from fastapi import Header, HTTPException, status

from core.storage import get_authority_session

ADMIN_TOKEN_ENV = "AUTHORITY_ADMIN_TOKEN"
BOOTSTRAP_ADMIN_ENABLED_ENV = "AUTHORITY_BOOTSTRAP_ADMIN_ENABLED"


def require_admin_token(authorization: str | None = Header(default=None)) -> None:
    configured_token = os.getenv(ADMIN_TOKEN_ENV)
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authority admin token is not configured",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_token = authorization.removeprefix("Bearer ").strip()
    if provided_token != configured_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


def get_authority_session_from_header(authorization: str | None) -> dict[str, str] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    provided_token = authorization.removeprefix("Bearer ").strip()
    return get_authority_session(provided_token)


def require_authority_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = get_authority_session_from_header(authorization)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authority session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def require_platform_admin(authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = get_authority_session_from_header(authorization)
    if session is not None:
        if session["role_name"] != "platform_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin role required",
            )
        return session

    require_admin_token(authorization)
    return {
        "user_uuid": "bootstrap-admin-token",
        "email": "bootstrap-admin-token",
        "display_name": "Bootstrap Admin Token",
        "role_name": "platform_admin",
        "status": "active",
        "reseller_uuid": None,
    }


def require_reseller_or_platform_admin(authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = get_authority_session_from_header(authorization)
    if session is not None:
        if session["role_name"] not in {"platform_admin", "reseller"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reseller or platform admin role required",
            )
        return session

    require_admin_token(authorization)
    return {
        "user_uuid": "bootstrap-admin-token",
        "email": "bootstrap-admin-token",
        "display_name": "Bootstrap Admin Token",
        "role_name": "platform_admin",
        "status": "active",
        "reseller_uuid": None,
    }


def bootstrap_admin_enabled() -> bool:
    return os.getenv(BOOTSTRAP_ADMIN_ENABLED_ENV, "false").strip().lower() in {"1", "true", "yes", "on"}