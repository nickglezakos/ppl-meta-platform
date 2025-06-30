import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class Config:
    """Configuration class for the application."""
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", 5432)
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    # Application configuration
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    @classmethod
    def get_database_url(cls):
        """Get the database URL, either from DATABASE_URL or construct from components."""
        if cls.DATABASE_URL:
            # Replace postgresql:// with postgresql+psycopg:// for psycopg driver
            url = cls.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        else:
            return f"postgresql+psycopg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

# Create config instance
config = Config()

def get_config():
    """Get the configuration instance."""
    return config