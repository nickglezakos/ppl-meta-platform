import logging

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Security hardening (Proposal §10.2 C3/C4): known default secrets that
# must never be used in production.
KNOWN_DEFAULT_SECRETS = {
    "", "default-secret-key-change-in-production",
    "change-this-secret-key", "your-secret-key-here",
}


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "PPL Meta Node - User Management Service"
    APP_VERSION: str = "1.0.1"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    LOG_FORMAT: str = "console"
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database Settings
    DATABASE_URL: str = "sqlite:///./test.db"

    # Security Settings
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RESET_PASSWORD_SECRET: str = ""

    # Mail Settings
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""
    MAIL_FROM_NAME: str = "PPL Meta Node"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # SMTP Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Service Communication
    PPL_MEDIA_SERVICE_URL: str = "http://localhost:8000"
    MEDIA_SERVICE_URL: str = "http://localhost:8000"
    GATEWAY_SERVICE_URL: str = "http://localhost:8080"
    BOOTCORE_SERVICE_URL: str = "http://localhost:8007"
    COMMUNICATIONS_SERVICE_URL: str = "http://localhost:8009"
    FRONTEND_URL: str = "http://localhost:3000"
    SERVICE_SECRET: str = ""
    AUTHORITY_SERVICE_ENABLED: bool = False
    AUTHORITY_SERVICE_URL: str = "https://authority.eyenet-vision.com"
    AUTHORITY_INSTALLATION_UUID: str = ""
    AUTHORITY_APPLICATION_KEY: str = ""
    AUTHORITY_TIMEOUT_SECONDS: float = 10.0
    AUTHORITY_REVALIDATION_INTERVAL_SECONDS: int = 300

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Platform IP Configuration
    PLATFORM_IP: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

    def model_post_init(self, __context=None):
        """Validate critical settings after initialization.

        Security hardening (Proposal §10.2 C3/C4): warns if SECRET_KEY,
        JWT_SECRET, or RESET_PASSWORD_SECRET are set to known defaults.
        """
        super().model_post_init(__context)

        if not self.SECRET_KEY or self.SECRET_KEY in KNOWN_DEFAULT_SECRETS:
            logger.warning(
                "SECRET_KEY is a known default. Set a unique SECRET_KEY "
                "environment variable for production."
            )
            if not self.SECRET_KEY:
                self.SECRET_KEY = "default-secret-key-change-in-production"

        if self.JWT_SECRET in KNOWN_DEFAULT_SECRETS:
            logger.warning(
                "JWT_SECRET is a known default. Set a unique JWT_SECRET "
                "environment variable for production."
            )

        if self.RESET_PASSWORD_SECRET in KNOWN_DEFAULT_SECRETS:
            logger.warning(
                "RESET_PASSWORD_SECRET is a known default."
            )

        if not self.DATABASE_URL:
            logger.error("DATABASE_URL not set")
            raise ValueError("DATABASE_URL is required")

        logger.info("Configuration loaded - Database: %s", self.DATABASE_URL)
        logger.info("Service will run on %s:%s", self.HOST, self.PORT)

    def is_mail_configured(self) -> bool:
        """Check if mail configuration is properly set."""
        return bool(
            self.MAIL_USERNAME and self.MAIL_PASSWORD
            and self.MAIL_FROM and self.MAIL_SERVER
        )

    def log_configuration(self):
        """Log the current configuration (excluding sensitive data)."""
        logger.info("App: %s v%s", self.APP_NAME, self.APP_VERSION)
        logger.info("Environment: %s", self.DEBUG)
        logger.info("Server: %s:%s", self.HOST, self.PORT)
        logger.info("Mail configured: %s", self.is_mail_configured())

    def get_database_url(self) -> str:
        """Get the database URL for connections."""
        return self.DATABASE_URL

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
        except ValueError as e:
            logger.error("Database URL validation failed: %s", e)
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
                    if parsed.password else url
                ),
            }
        except ValueError:
            return {"error": "Failed to parse database URL"}


settings = Settings()