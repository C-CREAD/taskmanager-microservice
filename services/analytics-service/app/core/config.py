from functools import lru_cache
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "TaskForge Analytics Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/analytics_db"

    REDIS_URL: str = "redis://localhost:6379/3"
    CELERY_BROKER_URL: str = "redis://localhost:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"

    JWT_SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-characters"
    JWT_ALGORITHM: str = "HS256"

    TASK_SERVICE_URL: str = "http://localhost:8002"
    USER_SERVICE_URL: str = "http://localhost:8001"

    CACHE_TTL_SECONDS: int = 300  # 5 minutes

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


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
