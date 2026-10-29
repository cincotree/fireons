import os
from functools import lru_cache

from pydantic import Field, model_validator

from secrets_source import SecretsManagerSettings


class AppSettings(SecretsManagerSettings):
    secret_key: str = Field(min_length=1)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:3000,http://localhost:3020"
    ingestion_test_enabled: bool = True
    ingestion_enabled: bool = False
    captcha_enabled: bool = False
    turnstile_secret_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_ignore_empty = True
        extra = "ignore"

    @model_validator(mode="after")
    def require_turnstile_secret_when_captcha_enabled(self):
        if self.captcha_enabled and not self.turnstile_secret_key:
            raise ValueError("TURNSTILE_SECRET_KEY is required when CAPTCHA_ENABLED is true")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_app_settings() -> AppSettings:
    if os.getenv("TESTING", "").lower() == "true":
        return AppSettings(_env_file=".env.test")
    return AppSettings()
