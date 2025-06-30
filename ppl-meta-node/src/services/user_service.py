import re
import os

from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.config import settings
from src.database import get_db
from src.mail import send_email
from src.models.user import User as UserModel, UserAction, User
from src.schemas.user import UserCreate

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
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    except JWTError:
        raise credentials_exception
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
        subject=f"User Action: {action}",
        email_to=admin_email,
        body=email_body
    )


# PASSWORD SERVICE FUNCTIONS

def is_strong_password(password: str) -> bool:
    # Αt least 8 chars, 1 digit, 1 uppercase, 1 lowercase, 1 special char
    return (
        len(password) >= 8 and
        re.search(r"\d", password) and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def update_user_password(db: Session, user_id: int, old_password: str, new_password: str):
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
        "action": "reset_password"
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