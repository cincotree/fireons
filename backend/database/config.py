"""
Database configuration settings.
"""

from functools import lru_cache

from sqlalchemy.engine import make_url

from secrets_source import SecretsManagerSettings

ASYNC_DRIVER = "postgresql+psycopg"


def _normalize_database_url(url: str) -> str:
    parsed = make_url(url).set(drivername=ASYNC_DRIVER)
    if "sslmode" not in parsed.query:
        parsed = parsed.update_query_dict({"sslmode": "require"})
    return parsed.render_as_string(hide_password=False)


class Settings(SecretsManagerSettings):
    """Database configuration settings."""

    database_url: str | None = None

    # PostgreSQL connection settings
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fireons_development"

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    db_null_pool: bool = False
    db_create_tables_on_startup: bool = True

    # For testing
    testing: bool = False
    test_database_url: str | None = None

    @property
    def _effective_db_name(self) -> str:
        """Get the effective database name (uses exact name from env in testing mode)."""
        if self.testing:
            if not self.postgres_db:
                raise ValueError(
                    "POSTGRES_DB must be specified in .env.test when TESTING=true"
                )
            return self.postgres_db
        return self.postgres_db

    def _url_from_parts(self) -> str:
        return (
            f"{ASYNC_DRIVER}://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self._effective_db_name}"
        )

    @property
    def async_database_url(self) -> str:
        """Get the async database URL for SQLAlchemy."""
        if self.testing and self.test_database_url:
            return self.test_database_url
        if self.database_url:
            return _normalize_database_url(self.database_url)
        return self._url_from_parts()

    @property
    def sync_database_url(self) -> str:
        """Get the sync database URL for Alembic migrations."""
        return make_url(self.async_database_url).set(drivername="postgresql").render_as_string(
            hide_password=False
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
