from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    id: int
    user_id: Optional[str]
    guid: str
    username: str
    email: EmailStr
    email_verified: bool
    mobile_phone: Optional[str]
    is_phone_verified: bool
    given_name: Optional[str]
    family_name: Optional[str]
    name: Optional[str]
    picture: Optional[str]
    is_active: bool
    blocked: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    logins_count: int

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserRead(UserBase):
    pass

class UserActionRead(BaseModel):
    id: int
    username: str
    email: str
    action: str
    timestamp: datetime

    class Config:
        orm_mode = True

class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: constr(min_length=8)  # Enforce minimum length

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: constr(min_length=8)