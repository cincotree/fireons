from functools import lru_cache
from typing import Literal

from secrets_source import SecretsManagerSettings


class Settings(SecretsManagerSettings):
    llm_provider: Literal["anthropic", "openrouter"] = "openrouter"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def active_model(self) -> str:
        if self.llm_provider == "openrouter":
            return self.openrouter_model
        return self.anthropic_model

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "openrouter":
            return bool(self.openrouter_api_key)
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
