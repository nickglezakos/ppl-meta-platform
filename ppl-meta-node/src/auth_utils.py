"""Authentication and authorization utilities shared across API modules."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.config import settings
from src.database import get_db
from src.models.role import Capability, Role, RoleCapability, UserRole
from src.services.user_service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_value = payload.get("sub")
        if user_id_value is None:
            raise credentials_exception
        try:
            user_id = int(user_id_value)
        except (TypeError, ValueError) as exc:
            raise credentials_exception from exc
    except JWTError as exc:
        raise credentials_exception from exc
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


def get_user_role_names(db: Session, user_id: int) -> list[str]:
    """Return distinct role names assigned to the user."""
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def get_user_capability_names(db: Session, user_id: int) -> set[str]:
    """Return distinct capability names granted to the user through roles."""
    rows = (
        db.query(Capability.name)
        .join(RoleCapability, RoleCapability.capability_id == Capability.id)
        .join(Role, Role.id == RoleCapability.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def require_capability(capability_name: str):
    """Build a dependency that enforces a capability on the current user."""

    def dependency(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        capability_names = get_user_capability_names(db, current_user.id)
        if capability_name not in capability_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required capability: {capability_name}",
            )
        return current_user

    return dependency
