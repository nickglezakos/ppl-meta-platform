"""Database models for PPL Meta Matrix Service.

Four tables:
- matrix_groups: Matrix group definitions
- matrix_installation_memberships: Installations belonging to groups
- matrix_users: Cross-installation user directory (SSO-like)
- matrix_user_capabilities: Per-user Matrix-level permissions
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class MatrixGroup(Base):
    __tablename__ = "matrix_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    licence_multi_install = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class MatrixInstallationMembership(Base):
    __tablename__ = "matrix_installation_memberships"
    __table_args__ = (
        UniqueConstraint("matrix_group_id", "installation_uuid"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_group_id = Column(
        UUID(as_uuid=True), ForeignKey("matrix_groups.id", ondelete="CASCADE"), nullable=False
    )
    installation_uuid = Column(String(255), nullable=False)
    installation_name = Column(String(255), nullable=True)
    node_url = Column(String(512), nullable=False)
    added_at = Column(DateTime(timezone=True), default=_utcnow)


class MatrixUser(Base):
    __tablename__ = "matrix_users"
    __table_args__ = (
        UniqueConstraint("matrix_group_id", "user_email"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_group_id = Column(
        UUID(as_uuid=True), ForeignKey("matrix_groups.id", ondelete="CASCADE"), nullable=False
    )
    user_email = Column(String(255), nullable=False)
    home_installation_uuid = Column(String(255), nullable=False)
    home_node_url = Column(String(512), nullable=False)
    display_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class MatrixUserCapability(Base):
    __tablename__ = "matrix_user_capabilities"
    __table_args__ = (
        UniqueConstraint("matrix_user_id", "capability"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_user_id = Column(
        Integer, ForeignKey("matrix_users.id", ondelete="CASCADE"), nullable=False
    )
    capability = Column(String(100), nullable=False)
    granted_by_user_id = Column(Integer, nullable=False)
    granted_at = Column(DateTime(timezone=True), default=_utcnow)


class MatrixReportCache(Base):
    """Cached aggregated report results for a Matrix group."""
    __tablename__ = "matrix_report_cache"
    __table_args__ = (
        UniqueConstraint("matrix_group_id", "report_type", "query_params"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_group_id = Column(
        UUID(as_uuid=True), ForeignKey("matrix_groups.id", ondelete="CASCADE"), nullable=False
    )
    report_type = Column(String(100), nullable=False)
    query_params = Column(String(512), nullable=False)  # JSON string of query params
    result_data = Column(Text, nullable=False)  # JSON string of result
    cached_at = Column(DateTime(timezone=True), default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)


# Engine and session factory
DATABASE_URL = "sqlite:///ppl-meta-matrix.db"  # Dev default — PostgreSQL in production
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()