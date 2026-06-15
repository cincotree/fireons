"""
Database configuration settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Database configuration settings."""

    # PostgreSQL connection settings
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fireons_development"

    # Full database URL (overrides individual fields if set)
    database_url: str | None = None

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    # For testing
    testing: bool = False
    test_database_url: str | None = None

    @property
    def _effective_db_name(self) -> str:
        if self.testing:
            if not self.postgres_db:
                raise ValueError(
                    "POSTGRES_DB must be specified in .env.test when TESTING=true"
                )
            return self.postgres_db
        return self.postgres_db

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+psycopg://")
        if self.testing and self.test_database_url:
            return self.test_database_url

        db_name = self._effective_db_name
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.testing and self.test_database_url:
            return self.test_database_url.replace("+psycopg", "")

        db_name = self._effective_db_name
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{db_name}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    import os
    if os.getenv("TESTING", "").lower() == "true":
        return Settings(_env_file=".env.test")
    return Settings()
