from functools import lru_cache
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Task Management User Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/users_db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-characters"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """
        Accept any of these formats:
          - A real Python list (already parsed):  ["http://..."]
          - A JSON array string:                  '["http://...","http://..."]'
          - A comma-separated string:             'http://...,http://...'
        """
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
