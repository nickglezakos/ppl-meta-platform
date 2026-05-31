"""Database configuration for PPL Meta Presence."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import config

engine = create_engine(
    config.DATABASE_URL,
    echo=config.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def test_connection() -> bool:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False