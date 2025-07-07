import logging
import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "PPL Meta Node - User Management Service"
    APP_VERSION: str = "1.0.1"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database Settings
    DATABASE_URL: str = "sqlite:///./test.db"

    # Security Settings
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RESET_PASSWORD_SECRET: str = ""

    # Mail Settings
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""
    MAIL_FROM_NAME: str = "PPL Meta Node"

    # SMTP Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Service Communication
    PPL_MEDIA_SERVICE_URL: str = "http://localhost:8000"
    MEDIA_SERVICE_URL: str = "http://localhost:8000"
    GATEWAY_SERVICE_URL: str = "http://localhost:8080"
    SERVICE_SECRET: str = ""

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Additional standardized mail settings (already has main ones)
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    class Config:
        env_file = ".env"

    def model_post_init(self, __context=None):
        """Validate critical settings after initialization."""
        if not self.SECRET_KEY:
            logger.warning(
                "SECRET_KEY not set, using default (not secure for production)"
            )
            self.SECRET_KEY = "default-secret-key-change-in-production"

        if not self.DATABASE_URL:
            logger.error("DATABASE_URL not set")
            raise ValueError("DATABASE_URL is required")

        logger.info("Configuration loaded - Database: %s", self.DATABASE_URL)
        logger.info("Service will run on %s:%s", self.HOST, self.PORT)

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
        logger.info("Environment: %s", self.DEBUG)
        logger.info("Server: %s:%s", self.HOST, self.PORT)
        logger.info("Mail configured: %s", self.is_mail_configured())


settings = Settings()

# Validate settings after creation
if hasattr(settings, "model_post_init"):
    settings.model_post_init()
