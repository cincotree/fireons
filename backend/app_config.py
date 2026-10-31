import os
from functools import lru_cache

from pydantic import Field

from secrets_source import SecretsManagerSettings


class AppSettings(SecretsManagerSettings):
    secret_key: str = Field(min_length=1)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:3000,http://localhost:3020"
    ingestion_test_enabled: bool = True
    ingestion_enabled: bool = False
    invite_only: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_ignore_empty = True
        extra = "ignore"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_app_settings() -> AppSettings:
    if os.getenv("TESTING", "").lower() == "true":
        return AppSettings(_env_file=".env.test")
    return AppSettings()
