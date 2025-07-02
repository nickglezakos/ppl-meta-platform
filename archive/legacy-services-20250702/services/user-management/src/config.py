import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "PPL Meta Node - User Management Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./test.db"
    
    # Security Settings
    SECRET_KEY: str = ""
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
    
    # Service Communication
    PPL_MEDIA_SERVICE_URL: str = "http://localhost:8000"
    SERVICE_SECRET: str = ""

    class Config:
        env_file = ".env"

settings = Settings()