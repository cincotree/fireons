"""
Database configuration settings.
"""

import os
from functools import lru_cache

from pydantic import field_validator

from secrets_source import SecretsManagerSettings


class Settings(SecretsManagerSettings):
    """Database configuration settings."""

    database_url: str

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    db_null_pool: bool = False

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    if os.getenv("TESTING", "").lower() == "true":
        return Settings(_env_file=".env.test")
    return Settings()
