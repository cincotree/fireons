import json
import sys
from types import SimpleNamespace

import pytest

from app_config import AppSettings
from database.config import Settings as DatabaseSettings
from secrets_source import SECRET_ID_ENV, fetch_secret

SECRET = {"SECRET_KEY": "from-secrets-manager", "DATABASE_URL": "postgresql://app:pw@db.example.com/fireons"}


@pytest.fixture
def secrets_manager(monkeypatch):
    calls = []

    def client(service):
        assert service == "secretsmanager"

        def get_secret_value(SecretId):
            calls.append(SecretId)
            return {"SecretString": json.dumps(SECRET)}

        return SimpleNamespace(get_secret_value=get_secret_value)

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=client))
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fetch_secret.cache_clear()
    yield calls
    fetch_secret.cache_clear()


def test_settings_read_from_one_secret_fetch(monkeypatch, secrets_manager):
    monkeypatch.setenv(SECRET_ID_ENV, "fireons/prod")

    assert AppSettings(_env_file=None).secret_key == "from-secrets-manager"
    assert DatabaseSettings(_env_file=None).database_url == SECRET["DATABASE_URL"]
    assert secrets_manager == ["fireons/prod"]


def test_env_vars_take_precedence(monkeypatch, secrets_manager):
    monkeypatch.setenv(SECRET_ID_ENV, "fireons/prod")
    monkeypatch.setenv("SECRET_KEY", "from-env")

    assert AppSettings(_env_file=None).secret_key == "from-env"


def test_secrets_manager_unused_without_secret_id(monkeypatch, secrets_manager):
    monkeypatch.delenv(SECRET_ID_ENV, raising=False)
    monkeypatch.setenv("SECRET_KEY", "from-env")

    assert AppSettings(_env_file=None).secret_key == "from-env"
    assert secrets_manager == []
