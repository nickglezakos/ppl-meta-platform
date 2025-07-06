import logging
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuration settings for the PPL Meta Media Service."""

    # Application configuration
    APP_NAME: str = Field(default="ppl-meta-media", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.2", env="APP_VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")

    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Database configuration
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: Optional[str] = Field(default="ppl_media_db", env="DB_NAME")
    DB_USER: Optional[str] = Field(default="postgres", env="DB_USER")
    DB_PASSWORD: Optional[str] = Field(default="postgres", env="DB_PASSWORD")

    # Security
    SECRET_KEY: Optional[str] = Field(default=None, env="SECRET_KEY")
    JWT_SECRET: Optional[str] = Field(default=None, env="JWT_SECRET")

    # Media processing configuration
    STORAGE_PATH: str = Field(default="/tmp/ppl-meta-uploads", env="STORAGE_PATH")
    UPLOAD_DIR: str = Field(default="/tmp/ppl-meta-uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: str = Field(default="50MB", env="MAX_FILE_SIZE")
    ALLOWED_EXTENSIONS: str = Field(
        default="jpg,jpeg,png,gif,mp4,avi,mov", env="ALLOWED_EXTENSIONS"
    )

    # External services
    USER_SERVICE_URL: str = Field(
        default="http://localhost:8001", env="USER_SERVICE_URL"
    )
    GATEWAY_SERVICE_URL: str = Field(
        default="http://localhost:8080", env="GATEWAY_SERVICE_URL"
    )
    VISION_SERVICE_URL: Optional[str] = Field(default=None, env="VISION_SERVICE_URL")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):  # noqa: N805
        """Parse DEBUG environment variable."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    def get_database_url(self) -> str:
        """Get database URL from DATABASE_URL or construct from components."""
        if self.DATABASE_URL:
            # Replace postgresql:// with postgresql+psycopg:// for psycopg
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        else:
            return (
                f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )

    def log_configuration(self):
        """Log the current configuration (excluding sensitive data)."""
        logger.info("App: %s v%s", self.APP_NAME, self.APP_VERSION)
        logger.info("Environment: %s", self.ENVIRONMENT)
        logger.info("Debug mode: %s", self.DEBUG)
        logger.info("Server: %s:%s", self.HOST, self.PORT)
        logger.info("Database: %s:%s/%s", self.DB_HOST, self.DB_PORT, self.DB_NAME)
        logger.info("Storage path: %s", self.STORAGE_PATH)
        logger.info("Max file size: %s", self.MAX_FILE_SIZE)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create global settings instance
settings = Settings()


def get_config():
    """Get the configuration instance."""
    return settings


# For backward compatibility
config = settings
