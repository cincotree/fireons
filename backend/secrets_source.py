import json
import os
from collections.abc import Mapping
from functools import lru_cache

from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource

SECRET_ID_ENV = "SECRETS_MANAGER_SECRET_ID"


@lru_cache
def fetch_secret(secret_id: str) -> dict[str, str]:
    import boto3

    try:
        response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)
        values = json.loads(response["SecretString"])
    except Exception as error:
        raise RuntimeError(f"Could not read secret {secret_id!r} from AWS Secrets Manager: {error}") from error
    if not isinstance(values, dict):
        raise RuntimeError(f"Secret {secret_id!r} must be a JSON object of KEY: value pairs")
    return {key: str(value) for key, value in values.items()}


class SecretsManagerSource(EnvSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], secret_id: str):
        self.secret_id = secret_id
        super().__init__(settings_cls, case_sensitive=False)

    def _load_env_vars(self) -> Mapping[str, str | None]:
        return {key.lower(): value for key, value in fetch_secret(self.secret_id).items()}


class SecretsManagerSettings(BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources: tuple[PydanticBaseSettingsSource, ...] = (init_settings, env_settings, dotenv_settings)
        secret_id = os.getenv(SECRET_ID_ENV)
        if secret_id:
            sources += (SecretsManagerSource(settings_cls, secret_id),)
        return sources + (file_secret_settings,)
