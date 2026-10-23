from functools import lru_cache

from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    public_read_limit_per_minute: int = 240

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_api_settings() -> ApiSettings:
    return ApiSettings()
