from functools import lru_cache
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Task Management Notification Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/notifications_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/2"
    CELERY_BROKER_URL: str = "redis://localhost:6379/2"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-characters"
    JWT_ALGORITHM: str = "HS256"

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "d"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "TaskManagement"
    SMTP_FROM_EMAIL: str = "noreply@taskmanagement.io"
    SMTP_USE_TLS: bool = True

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Internal services
    USER_SERVICE_URL: str = "http://localhost:8001"
    TASK_SERVICE_URL: str = "http://localhost:8002"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
