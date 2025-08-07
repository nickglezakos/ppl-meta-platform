"""
Database configuration and connection management for PPL Meta Cameras.
"""

import asyncio
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config import get_config

config = get_config()

# Create the database engine
engine = create_engine(
    config.DATABASE_URL,
    echo=config.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async engine for async operations
async_engine = create_async_engine(
    config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=config.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Declarative base for models
Base = declarative_base()


def get_db() -> SessionLocal:
    """Get database session (synchronous)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_connection() -> bool:
    """Test database connection."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


async def create_tables():
    """Create all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Health check function
def check_db_health() -> dict:
    """Check database health for health endpoint."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}
