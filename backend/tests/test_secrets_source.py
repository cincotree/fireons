import json
import sys
from types import SimpleNamespace

import pytest

from app_config import AppSettings
from database.config import Settings as DatabaseSettings
from secrets_source import ENV_VAR, fetch_secret, secret_id_for

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
    monkeypatch.setenv(ENV_VAR, "production")

    assert AppSettings(_env_file=None).secret_key == "from-secrets-manager"
    assert DatabaseSettings(_env_file=None).database_url == SECRET["DATABASE_URL"]
    assert secrets_manager == [secret_id_for("production")]


def test_env_vars_take_precedence(monkeypatch, secrets_manager):
    monkeypatch.setenv(ENV_VAR, "production")
    monkeypatch.setenv("SECRET_KEY", "from-env")

    assert AppSettings(_env_file=None).secret_key == "from-env"


def test_secrets_manager_unused_without_env(monkeypatch, secrets_manager):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setenv("SECRET_KEY", "from-env")

    assert AppSettings(_env_file=None).secret_key == "from-env"
    assert secrets_manager == []


def test_unreadable_secret_gives_clear_error(monkeypatch, secrets_manager):
    monkeypatch.setenv(ENV_VAR, "production")
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=lambda service: SimpleNamespace(get_secret_value=lambda SecretId: {})),
    )

    with pytest.raises(RuntimeError, match=secret_id_for("production")):
        AppSettings(_env_file=None)
