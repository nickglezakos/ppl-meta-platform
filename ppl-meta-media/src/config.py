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
    LOG_FORMAT: str = Field(default="console", env="LOG_FORMAT")

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

    # Standardized Mail Configuration (consistent across all services)
    MAIL_USERNAME: str = Field(default="", env="MAIL_USERNAME")
    MAIL_PASSWORD: str = Field(default="", env="MAIL_PASSWORD")
    MAIL_FROM: str = Field(default="", env="MAIL_FROM")
    MAIL_SERVER: str = Field(default="", env="MAIL_SERVER")
    MAIL_PORT: int = Field(default=587, env="MAIL_PORT")
    MAIL_FROM_NAME: str = Field(default="PPL Meta Media", env="MAIL_FROM_NAME")
    MAIL_STARTTLS: bool = Field(default=True, env="MAIL_STARTTLS")
    MAIL_SSL_TLS: bool = Field(default=False, env="MAIL_SSL_TLS")
    USE_CREDENTIALS: bool = Field(default=True, env="USE_CREDENTIALS")
    VALIDATE_CERTS: bool = Field(default=True, env="VALIDATE_CERTS")

    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

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

    def is_mail_configured(self) -> bool:
        """Check if mail configuration is properly set."""
        return bool(
            self.MAIL_USERNAME
            and self.MAIL_PASSWORD
            and self.MAIL_FROM
            and self.MAIL_SERVER
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
        logger.info("Mail configured: %s", self.is_mail_configured())

    def validate_database_url(self) -> bool:
        """Validate the database connection string format and components."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.get_database_url())

            if not parsed.scheme.startswith("postgresql"):
                logger.error("Database URL must use postgresql:// scheme")
                return False

            if not parsed.username:
                logger.error("Database URL missing username")
                return False

            if not parsed.password:
                logger.error("Database URL missing password")
                return False

            if not parsed.hostname:
                logger.error("Database URL missing hostname")
                return False

            if not parsed.path or parsed.path == "/":
                logger.error("Database URL missing database name")
                return False

            logger.info("Database URL validation passed")
            return True

        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return False

    def get_database_info(self) -> dict:
        """Get database connection information for debugging."""
        url = self.get_database_url()
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "username": parsed.username,
                "database": parsed.path.lstrip("/"),
                "url_masked": (
                    url.replace(parsed.password or "", "*****")
                    if parsed.password
                    else url
                ),
            }
        except Exception:
            return {"error": "Failed to parse database URL"}

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="allow"
    )


# Create global settings instance
settings = Settings()


def get_config():
    """Get the configuration instance."""
    return settings


# For backward compatibility
config = settings
