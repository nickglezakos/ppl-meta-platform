"""
Database configuration for PPL Meta Communications Service.
"""
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from .config import get_config

# Set up logging
logger = logging.getLogger(__name__)

# Initialize configuration
config = get_config()

# Create SQLAlchemy engine
engine = create_engine(
    config.get_database_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=config.DEBUG  # Log SQL queries in debug mode
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session.
    Use this in your API endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all tables in the database."""
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped successfully")


def test_connection():
    """Test the database connection."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_db_info():
    """Get database information."""
    try:
        with engine.connect() as connection:
            # Get PostgreSQL version
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.fetchone()[0]
            
            # Get current database name
            db_result = connection.execute(text("SELECT current_database()"))
            current_db = db_result.fetchone()[0]
            
            # Get current user
            user_result = connection.execute(text("SELECT current_user"))
            current_user = user_result.fetchone()[0]
            
            return {
                "version": version,
                "database": current_db,
                "user": current_user,
                "status": "connected"
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
