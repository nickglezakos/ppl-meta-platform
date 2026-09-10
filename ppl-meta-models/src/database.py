"""SQLite/Postgres catalog store for ppl-meta-models."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import config

connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
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
    # Import models so metadata is populated.
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()


def _migrate_sqlite_columns() -> None:
    """Add Phase B columns to existing SQLite DBs (create_all does not ALTER)."""
    if not config.DATABASE_URL.startswith("sqlite"):
        return
    alters = [
        ("mv_assignments", "recipe_id", "VARCHAR(128) DEFAULT ''"),
        ("mv_assignment_history", "recipe_id", "VARCHAR(128) DEFAULT ''"),
    ]
    with engine.begin() as connection:
        for table, column, coltype in alters:
            rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
            names = {row[1] for row in rows}
            if column not in names:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
                )


def test_connection() -> bool:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
