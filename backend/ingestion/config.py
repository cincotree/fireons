from functools import lru_cache

from secrets_source import SecretsManagerSettings


class Settings(SecretsManagerSettings):
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def active_model(self) -> str:
        return self.openrouter_model

    @property
    def llm_configured(self) -> bool:
        return bool(self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
