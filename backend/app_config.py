import os
from functools import lru_cache

from pydantic_settings import BaseSettings

from database.config import Settings as DatabaseSettings

DEVELOPMENT_SECRET_KEY = "your-secret-key-here-change-in-production"
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:3020"


class ConfigurationError(RuntimeError):
    pass


class AppSettings(BaseSettings):
    app_env: str = "development"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = DEFAULT_CORS_ORIGINS
    origin_verify_secret: str = ""
    ingestion_test_enabled: bool | None = None
    api_docs_enabled: bool | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_ignore_empty = True
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def jwt_secret_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        if self.is_production:
            raise ConfigurationError("SECRET_KEY must be set when APP_ENV=production")
        return DEVELOPMENT_SECRET_KEY

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ingestion_test_router_enabled(self) -> bool:
        if self.ingestion_test_enabled is None:
            return not self.is_production
        return self.ingestion_test_enabled

    @property
    def api_docs_routes_enabled(self) -> bool:
        if self.api_docs_enabled is None:
            return not self.is_production
        return self.api_docs_enabled


def validate_startup_settings(app_settings: AppSettings, database_settings: DatabaseSettings) -> None:
    if not app_settings.is_production:
        return

    missing = []
    if not app_settings.secret_key or app_settings.secret_key == DEVELOPMENT_SECRET_KEY:
        missing.append("SECRET_KEY")
    if not app_settings.origin_verify_secret:
        missing.append("ORIGIN_VERIFY_SECRET")
    if not database_settings.database_url:
        missing.append("DATABASE_URL")
    if not app_settings.cors_origin_list:
        missing.append("CORS_ORIGINS")

    if missing:
        raise ConfigurationError(
            "Refusing to start with APP_ENV=production. Missing required settings: " + ", ".join(missing)
        )


@lru_cache
def get_app_settings() -> AppSettings:
    if os.getenv("TESTING", "").lower() == "true":
        return AppSettings(_env_file=".env.test")
    return AppSettings()
