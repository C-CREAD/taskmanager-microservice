import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_name: str = "User Service"
    app_version: str = "1.0.0"
    debug: bool = os.getenv('DEBUG')

    # Database
    db_name: str = os.getenv('DB_NAME', 'user_service')
    db_user: str = os.getenv('DB_USER')
    db_password: str = os.getenv('DB_PASSWORD')
    db_host: str = os.getenv('DB_HOST')
    db_port: int = os.getenv('DB_PORT')

    @property
    def database_url(self) -> str:
        """Build database URL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Security
    secret_key: str = os.getenv('SECRET_KEY')
    algorithm: str = os.getenv('ALGORITHM')
    access_token_expire_minutes: int = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')
    refresh_token_expire_days: int = os.getenv('REFRESH_TOKEN_EXPIRE_DAYS')

    # CORS
    allowed_origins: list = os.getenv('ALLOWED_ORIGINS')


    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()