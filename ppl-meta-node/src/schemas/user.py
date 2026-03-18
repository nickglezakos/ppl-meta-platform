import uuid
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[str] = None
    guid: Union[str, uuid.UUID]  # Accept both UUID and string
    username: str
    email: EmailStr
    email_verified: bool = False
    mobile_phone: Optional[str] = None
    is_phone_verified: bool = False
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True
    blocked: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    logins_count: int = 0

    @field_validator("guid", mode="before")
    @classmethod
    def validate_guid(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserRead(UserBase):
    pass


class UserActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    action: str
    timestamp: datetime


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str  # Minimum length validation handled in service


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class AdminSetPassword(BaseModel):
    new_password: str
    send_email: bool = False
