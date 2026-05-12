import re
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.mail import send_email
from src.models.user import User
from src.models.user import User as UserModel
from src.models.user import UserAction
from src.schemas.user import UserCreate

# Import licensing service for user creation validation
try:
    from src.services.licensing_service import licensing_service

    LICENSING_AVAILABLE = True
except ImportError:
    LICENSING_AVAILABLE = False

try:
    from src.services.authority_service import authority_service

    AUTHORITY_AVAILABLE = True
except ImportError:
    AUTHORITY_AVAILABLE = False

from src.services.role_service import ensure_exact_system_roles

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
RESET_PASSWORD_SECRET = settings.RESET_PASSWORD_SECRET
RESET_PASSWORD_EXPIRE_HOURS = 1


# USER SERVICE FUNCTIONS


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_user(db: Session, user: UserCreate) -> UserModel:
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def create_user_with_licensing(db: Session, user: UserCreate) -> UserModel:
    """Create a user with licensing validation and owner registration."""

    # Check if this is the first user (becomes the owner)
    user_count = db.query(UserModel).count()
    is_first_user = user_count == 0

    # If licensing is available, validate user limits (except for first user)
    if LICENSING_AVAILABLE and not is_first_user:
        try:
            current_user_count = (
                db.query(UserModel).filter(UserModel.is_active == True).count()
            )
            is_valid = await licensing_service.validate_user_limit(
                current_user_count + 1
            )

            if not is_valid:
                license_info = (
                    await licensing_service.get_license_info_for_user_creation()
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"License limit reached. Maximum users: {license_info.get('max_users', 1)}",
                )
        except HTTPException as e:
            # Log warning but allow user creation if licensing service is unavailable
            print(f"Licensing validation failed: {e}")

    # Create the user
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # If this is the first user, only grant owner after authority activation succeeds.
    if is_first_user:
        authority_result = {"configured": False, "approved": False}
        if AUTHORITY_AVAILABLE:
            authority_result = await authority_service.activate_owner_candidate(db, user.email)

        if authority_result.get("configured") and authority_result.get("approved"):
            ensure_exact_system_roles(db, user.email, {"owner", "admin", "user"})
            if LICENSING_AVAILABLE:
                try:
                    user_data = {
                        "email": user.email,
                        "username": user.username,
                        "full_name": getattr(user, "full_name", ""),
                        "role": "owner",
                    }
                    await licensing_service.register_owner(user_data)
                except RuntimeError as e:
                    # Log error but don't fail user creation
                    print(f"Failed to register owner with licensing service: {e}")
        elif authority_result.get("configured"):
            ensure_exact_system_roles(db, user.email, {"user"})
            print(
                "Authority service did not approve first-user owner registration: "
                f"{authority_result.get('reason', 'unknown_reason')}"
            )

    return db_user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


def get_user_by_id(db: Session, user_id: int) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_guid(db: Session, guid) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.guid == guid).first()


def get_user_by_email(db: Session, email: str) -> UserModel | None:
    return db.query(UserModel).filter(UserModel.email == email).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[UserModel]:
    return db.query(UserModel).offset(skip).limit(limit).all()


def verify_user_email(db: Session, user_id: int) -> None:
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user:
        user.email_verified = True
        db.commit()


# LOGGER / NOTIFICATION SERVICE FUNCTIONS


def log_user_action(db: Session, username: str, email: str, action: str):
    user_action = UserAction(username=username, email=email, action=action)
    db.add(user_action)
    db.commit()


async def notify_admin_for_action(username: str, email: str, action: str):
    admin_email = "nick.glezakos@gmail.com"
    if email == admin_email:
        return
    email_body = f"""
        <h3>User Action Notification</h3>
        <p>User <b>{username}</b> ({email}) performed action: <b>{action}</b> at {datetime.now().isoformat()} UTC.</p>
    """
    await send_email(
        subject=f"User Action: {action}", email_to=admin_email, body=email_body
    )


# PASSWORD SERVICE FUNCTIONS


def is_strong_password(password: str) -> bool:
    # Αt least 8 chars, 1 digit, 1 uppercase, 1 lowercase, 1 special char
    return (
        len(password) >= 8
        and re.search(r"\d", password)
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )


def update_user_password(
    db: Session, user_id: int, old_password: str, new_password: str
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return None, "User not found"
    if not pwd_context.verify(old_password, user.hashed_password):
        return None, "Old password is incorrect"
    if not is_strong_password(new_password):
        return None, "Password is not strong enough"
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    db.refresh(user)
    return user, None


def create_password_reset_token(user_id: int, email: str) -> str:
    """
    Creates and returns a JWT token for password reset.
    """
    expire = datetime.now() + timedelta(hours=RESET_PASSWORD_EXPIRE_HOURS)
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "action": "reset_password",
    }
    encoded_jwt = jwt.encode(to_encode, RESET_PASSWORD_SECRET, algorithm="HS256")
    return encoded_jwt


def verify_password_reset_token(token: str):
    """
    Verifies a password reset token and returns the payload if valid, else None.
    """
    try:
        payload = jwt.decode(token, RESET_PASSWORD_SECRET, algorithms=["HS256"])
        if payload.get("action") != "reset_password":
            return None
        return payload
    except JWTError:
        return None


def set_new_password(db, user_id: int, new_password: str):
    """
    Sets a new password for the user with the given user_id.
    Returns (user, None) on success, (None, error_message) on failure.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        return None, "User not found"
    if len(new_password) < 8:
        return None, "Password is not strong enough"
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    db.refresh(user)
    return user, None


def admin_required(current_user: User = Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
