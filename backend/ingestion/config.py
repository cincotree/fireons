from functools import lru_cache

from secrets_source import SecretsManagerSettings


class Settings(SecretsManagerSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
