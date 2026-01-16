"""
Configuration settings for the PPL Meta Communications Service.
"""
import logging
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuration settings for the PPL Meta Communications Service."""

    # Application configuration
    APP_NAME: str = Field(default="ppl-meta-communications", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")

    # Server configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8009, env="PORT")

    # Database configuration
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DB_HOST: str = Field(default="localhost", env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: str = Field(default="ppl_communications_db", env="DB_NAME")
    DB_USER: str = Field(default="postgres", env="DB_USER")
    DB_PASSWORD: str = Field(default="postgres", env="DB_PASSWORD")

    # Security
    SECRET_KEY: str = Field(default="change-this-secret-key", env="SECRET_KEY")
    JWT_SECRET: Optional[str] = Field(default=None, env="JWT_SECRET")

    # Email Configuration (SMTP)
    MAIL_ENABLED: bool = Field(default=False, env="MAIL_ENABLED")
    MAIL_SERVER: str = Field(default="smtp.gmail.com", env="MAIL_SERVER")
    MAIL_PORT: int = Field(default=587, env="MAIL_PORT")
    MAIL_USERNAME: str = Field(default="", env="MAIL_USERNAME")
    MAIL_PASSWORD: str = Field(default="", env="MAIL_PASSWORD")
    MAIL_FROM: str = Field(default="noreply@pplmeta.com", env="MAIL_FROM")
    MAIL_FROM_NAME: str = Field(default="PPL Meta Platform", env="MAIL_FROM_NAME")
    MAIL_STARTTLS: bool = Field(default=True, env="MAIL_STARTTLS")
    MAIL_SSL_TLS: bool = Field(default=False, env="MAIL_SSL_TLS")
    USE_CREDENTIALS: bool = Field(default=True, env="USE_CREDENTIALS")

    # Webhook Configuration
    WEBHOOK_ENABLED: bool = Field(default=True, env="WEBHOOK_ENABLED")
    WEBHOOK_TIMEOUT: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    WEBHOOK_MAX_RETRIES: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    WEBHOOK_RETRY_DELAY: int = Field(default=5, env="WEBHOOK_RETRY_DELAY")

    # Push Notification Configuration (Firebase)
    PUSH_ENABLED: bool = Field(default=False, env="PUSH_ENABLED")
    FCM_SERVER_KEY: Optional[str] = Field(default=None, env="FCM_SERVER_KEY")
    FCM_PROJECT_ID: Optional[str] = Field(default=None, env="FCM_PROJECT_ID")
    
    # APNS Configuration (Apple Push Notifications)
    APNS_ENABLED: bool = Field(default=False, env="APNS_ENABLED")
    APNS_KEY_PATH: Optional[str] = Field(default=None, env="APNS_KEY_PATH")
    APNS_KEY_ID: Optional[str] = Field(default=None, env="APNS_KEY_ID")
    APNS_TEAM_ID: Optional[str] = Field(default=None, env="APNS_TEAM_ID")
    APNS_TOPIC: Optional[str] = Field(default=None, env="APNS_TOPIC")

    # Audit Logging Configuration
    AUDIT_LOG_ENABLED: bool = Field(default=True, env="AUDIT_LOG_ENABLED")
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=90, env="AUDIT_LOG_RETENTION_DAYS")

    # Installation/Tenant Configuration (for edge deployment multi-tenancy)
    INSTALLATION_ID: Optional[str] = Field(default=None, env="INSTALLATION_ID")
    TENANT_NAME: Optional[str] = Field(default=None, env="TENANT_NAME")

    # Redis Configuration (for queuing and rate limiting)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_ENABLED: bool = Field(default=True, env="REDIS_ENABLED")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    EMAIL_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="EMAIL_RATE_LIMIT_PER_MINUTE")
    WEBHOOK_RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="WEBHOOK_RATE_LIMIT_PER_MINUTE")

    # External Services
    USER_SERVICE_URL: str = Field(default="http://localhost:8001", env="USER_SERVICE_URL")
    DISCOVERY_SERVICE_URL: str = Field(default="http://localhost:8006", env="DISCOVERY_SERVICE_URL")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG environment variable."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    def get_database_url(self) -> str:
        """Get database URL from DATABASE_URL or construct from components."""
        if self.DATABASE_URL:
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
        return self.MAIL_ENABLED and bool(
            self.MAIL_USERNAME
            and self.MAIL_PASSWORD
            and self.MAIL_FROM
            and self.MAIL_SERVER
        )

    def log_configuration(self):
        """Log current configuration (without sensitive data)."""
        logger.info("=== Communications Service Configuration ===")
        logger.info(f"APP_NAME: {self.APP_NAME}")
        logger.info(f"APP_VERSION: {self.APP_VERSION}")
        logger.info(f"ENVIRONMENT: {self.ENVIRONMENT}")
        logger.info(f"PORT: {self.PORT}")
        logger.info(f"DEBUG: {self.DEBUG}")
        logger.info(f"EMAIL_ENABLED: {self.MAIL_ENABLED}")
        logger.info(f"WEBHOOK_ENABLED: {self.WEBHOOK_ENABLED}")
        logger.info(f"PUSH_ENABLED: {self.PUSH_ENABLED}")
        logger.info(f"AUDIT_LOG_ENABLED: {self.AUDIT_LOG_ENABLED}")
        logger.info(f"Database: {self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")
        logger.info("=" * 50)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env without validation errors


# Global settings instance
_settings: Optional[Settings] = None


def get_config() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
