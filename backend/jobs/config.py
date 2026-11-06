from functools import lru_cache

from pydantic_settings import BaseSettings


class ExchangeRateSyncSettings(BaseSettings):
    exchange_rate_sync_enabled: bool = True
    exchange_rate_api_url: str = "https://open.er-api.com/v6/latest/{base}"
    exchange_rate_base_currency: str = "USD"
    exchange_rate_quote_currency: str = "INR"
    exchange_rate_sync_hour_utc: int = 20
    exchange_rate_sync_minute_utc: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_exchange_rate_sync_settings() -> ExchangeRateSyncSettings:
    import os

    if os.getenv("TESTING", "").lower() == "true":
        return ExchangeRateSyncSettings(_env_file=".env.test", exchange_rate_sync_enabled=False)
    return ExchangeRateSyncSettings()


class JobsSettings(BaseSettings):
    app_env: str = ""
    project: str = "fireons"
    jobs_run_locally: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def jobs_name(self) -> str:
        if not self.app_env:
            raise RuntimeError("APP_ENV is not set, so Fargate jobs are not configured")
        return f"{self.project}-{self.app_env}-jobs"


@lru_cache
def get_jobs_settings() -> JobsSettings:
    import os

    if os.getenv("TESTING", "").lower() == "true":
        return JobsSettings(_env_file=".env.test")
    return JobsSettings()
