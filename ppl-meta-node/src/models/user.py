import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import Boolean

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # For external provider IDs
    guid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    mobile_phone = Column(String, unique=True, index=True, nullable=True)
    is_phone_verified = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)
    given_name = Column(String)
    family_name = Column(String)
    name = Column(String)
    picture = Column(String)
    is_active = Column(Boolean, default=True)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login = Column(DateTime)
    logins_count = Column(Integer, default=0)
    roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert User model to dictionary with proper UUID serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "guid": str(self.guid),  # Convert UUID to string
            "username": self.username,
            "email": self.email,
            "email_verified": self.email_verified,
            "mobile_phone": self.mobile_phone,
            "is_phone_verified": self.is_phone_verified,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "name": self.name,
            "picture": self.picture,
            "is_active": self.is_active,
            "blocked": self.blocked,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "logins_count": self.logins_count,
        }


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    action = Column(String, nullable=False)  # e.g., "register", "login"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
