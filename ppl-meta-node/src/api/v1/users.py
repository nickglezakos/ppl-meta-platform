"""Users API v1 - User management endpoints with inter-service communication support."""

from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from src.database import get_db
from src.mail import send_email
from src.config import settings

from src.schemas.user import (
    UserActionRead,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserPasswordUpdate,
    UserCreate,
    UserRead
)
from src.models.user import UserAction, User
from src.services.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    get_user_by_guid,
    update_user_password,
    create_password_reset_token,
    verify_password_reset_token,
    set_new_password,
    log_user_action,
    verify_user_email
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/v1/users", tags=["users-v1"])
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
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user

def verify_service_token(authorization: str = Header(None)):
    """Verify inter-service communication token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authorization header missing"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    if token != settings.SERVICE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token"
        )
    return True

# ===== AUTHENTICATION ENDPOINTS =====

@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    created_user = create_user(db, user)
    log_user_action(db, created_user.username, created_user.email, "register")
 
    # Generate a verification token (JWT)
    verification_token = create_access_token(
        data={"sub": created_user.id, "email": created_user.email, "action": "verify_email"},
        expires_delta=timedelta(hours=24)
    )
    verification_link = f"http://{settings.HOST}:{settings.PORT}/api/v1/users/verify-email?token={verification_token}"
    email_body = f"""
        <h3>Welcome, {created_user.username}!</h3>
        <p>Please verify your email by clicking the link below:</p>
        <a href="{verification_link}">Verify Email</a>
    """
    await send_email(
        subject="Verify your email address",
        email_to=created_user.email,
        body=email_body
    )
    return created_user

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify user email address."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        action: str = payload.get("action")
        if user_id is None or action != "verify_email":
            raise HTTPException(status_code=400, detail="Invalid verification token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        return {"detail": "Email already verified."}
    
    verify_user_email(db, user_id)

    # Send thank you email after verification
    thank_you_body = f"""
        <h3>Thank you, {user.username}!</h3>
        <p>Your email has been successfully verified. You can now use all features of our service.</p>
    """
    await send_email(
        subject="Thank you for verifying your email",
        email_to=user.email,
        body=thank_you_body
    )

    return {"detail": "Email successfully verified."}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login."""
    user = get_user_by_email(db, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.id})
    log_user_action(db, user.username, user.email, "login")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(current_user: UserRead = Depends(get_current_user), db: Session = Depends(get_db)):
    """User logout (stateless)."""
    log_user_action(db, current_user.username, current_user.email, "logout")
    return {"msg": "Logout successful. Please delete your token client-side."}

# ===== INTER-SERVICE AUTHENTICATION ENDPOINTS =====

@router.post("/validate-token")
async def validate_token(
    token_data: Dict[str, str],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_token)
):
    """Validate JWT token for inter-service communication."""
    token = token_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "email_verified": user.email_verified
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.get("/user-info/{user_id}")
async def get_user_info_for_service(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_token)
):
    """Get user information for inter-service communication."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "guid": user.guid,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }

@router.get("/user-permissions/{user_id}")
async def get_user_permissions_for_service(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_token)
):
    """Get user permissions for inter-service communication."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user roles and capabilities
    user_roles = []
    user_capabilities = []
    
    for user_role in user.roles:
        role = user_role.role
        user_roles.append({
            "role_id": role.id,
            "role_name": role.name,
            "role_description": role.description
        })
        
        for role_capability in role.capabilities:
            capability = role_capability.capability
            if capability.name not in [c["name"] for c in user_capabilities]:
                user_capabilities.append({
                    "name": capability.name,
                    "description": capability.description
                })
    
    return {
        "user_id": user.id,
        "roles": user_roles,
        "capabilities": user_capabilities
    }

# ===== USER MANAGEMENT ENDPOINTS =====

@router.get("/{user_id}", response_model=UserRead)
def api_get_user_by_id(user_id: int, db: Session = Depends(get_db), current_user: UserRead = Depends(get_current_user)):
    """Get user by ID."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/guid/{guid}", response_model=UserRead)
def api_get_user_by_guid(guid: str, db: Session = Depends(get_db), current_user: UserRead = Depends(get_current_user)):
    """Get user by GUID."""
    user = get_user_by_guid(db, guid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=list[UserRead])
def api_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """List users with pagination."""
    users = list_users(db, skip=skip, limit=limit)
    return users

@router.get("/actions/", response_model=list[UserActionRead])
def api_list_user_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """List user actions with pagination."""
    actions = db.query(UserAction).offset(skip).limit(limit).all()
    return actions

@router.post("/update-password")
async def update_password(
    password_update: UserPasswordUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user password."""
    user = get_user_by_id(db, current_user.id)
    if not user or not pwd_context.verify(password_update.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    update_user_password(db, current_user.id, password_update.new_password)
    log_user_action(db, current_user.username, current_user.email, "password_update")
    return {"detail": "Password updated successfully"}

@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset."""
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = create_password_reset_token(db, request.email)
    reset_link = f"http://{settings.HOST}:{settings.PORT}/api/v1/users/reset-password?token={token}"
    
    email_body = f"""
        <h3>Password Reset Request</h3>
        <p>Click the link below to reset your password:</p>
        <a href="{reset_link}">Reset Password</a>
        <p>This link will expire in 1 hour.</p>
    """
    
    await send_email(
        subject="Password Reset Request",
        email_to=request.email,
        body=email_body
    )
    
    return {"detail": "Password reset email sent"}

@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password with token."""
    email = verify_password_reset_token(db, request.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    set_new_password(db, email, request.new_password)
    log_user_action(db, user.username, user.email, "password_reset")
    
    return {"detail": "Password reset successfully"}
