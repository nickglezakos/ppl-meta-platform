from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.models.user import Base

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    capabilities = relationship("RoleCapability", back_populates="role", cascade="all, delete-orphan")

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="_user_role_uc"),)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

class Capability(Base):
    __tablename__ = "capabilities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # Relationship to RoleCapability for many-to-many with Role
    roles = relationship("RoleCapability", back_populates="capability", cascade="all, delete-orphan")

class RoleCapability(Base):
    __tablename__ = "role_capabilities"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    capability_id = Column(Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("role_id", "capability_id", name="_role_capability_uc"),)

    # Optional: relationships for easier access
    role = relationship("Role", back_populates="capabilities")
    capability = relationship("Capability", back_populates="roles")