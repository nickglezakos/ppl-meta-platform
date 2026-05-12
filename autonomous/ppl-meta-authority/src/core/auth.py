import os

from fastapi import Header, HTTPException, status

ADMIN_TOKEN_ENV = "AUTHORITY_ADMIN_TOKEN"


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