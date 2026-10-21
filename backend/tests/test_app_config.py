import os
import subprocess
import sys
from pathlib import Path

import pytest

from app_config import (
    DEVELOPMENT_SECRET_KEY,
    AppSettings,
    ConfigurationError,
    validate_startup_settings,
)
from database.config import Settings as DatabaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROD_DATABASE_URL = "postgresql://app:pw@db.example.com/fireons"


def _app_settings(**overrides) -> AppSettings:
    values = {
        "app_env": "production",
        "secret_key": "a" * 64,
        "origin_verify_secret": "cloudfront-secret",
        "cors_origins": "https://app.fireons.com",
    }
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def _database_settings(database_url: str | None = PROD_DATABASE_URL) -> DatabaseSettings:
    return DatabaseSettings(_env_file=None, database_url=database_url)


class TestValidateStartupSettings:
    def test_production_with_all_required_settings_passes(self):
        validate_startup_settings(_app_settings(), _database_settings())

    def test_missing_secret_key_fails(self):
        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            validate_startup_settings(_app_settings(secret_key=""), _database_settings())

    def test_public_development_secret_key_fails(self):
        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            validate_startup_settings(
                _app_settings(secret_key=DEVELOPMENT_SECRET_KEY), _database_settings()
            )

    def test_missing_origin_verify_secret_fails(self):
        with pytest.raises(ConfigurationError, match="ORIGIN_VERIFY_SECRET"):
            validate_startup_settings(_app_settings(origin_verify_secret=""), _database_settings())

    def test_missing_database_url_fails(self):
        with pytest.raises(ConfigurationError, match="DATABASE_URL"):
            validate_startup_settings(_app_settings(), _database_settings(database_url=None))

    def test_empty_cors_origins_fails(self):
        with pytest.raises(ConfigurationError, match="CORS_ORIGINS"):
            validate_startup_settings(_app_settings(cors_origins=" , "), _database_settings())

    def test_reports_every_missing_setting(self):
        with pytest.raises(ConfigurationError) as excinfo:
            validate_startup_settings(
                _app_settings(secret_key="", origin_verify_secret=""),
                _database_settings(database_url=None),
            )
        message = str(excinfo.value)
        assert "SECRET_KEY" in message
        assert "ORIGIN_VERIFY_SECRET" in message
        assert "DATABASE_URL" in message

    def test_development_requires_nothing(self):
        validate_startup_settings(
            _app_settings(app_env="development", secret_key="", origin_verify_secret=""),
            _database_settings(database_url=None),
        )


class TestAppSettings:
    def test_development_falls_back_to_default_secret(self):
        settings = _app_settings(app_env="development", secret_key="")
        assert settings.jwt_secret_key == DEVELOPMENT_SECRET_KEY

    def test_production_never_falls_back_to_default_secret(self):
        settings = _app_settings(secret_key="")
        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            _ = settings.jwt_secret_key

    def test_app_env_is_case_insensitive(self):
        assert _app_settings(app_env=" Production ").is_production

    def test_cors_origins_parsed_from_comma_separated_list(self):
        settings = _app_settings(cors_origins="https://app.fireons.com, https://fireons.com ,")
        assert settings.cors_origin_list == ["https://app.fireons.com", "https://fireons.com"]

    def test_default_cors_origins_are_local_dev_servers(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        assert AppSettings(_env_file=None).cors_origin_list == ["http://localhost:3000", "http://localhost:3020"]

    def test_empty_environment_values_fall_back_to_defaults(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("INGESTION_TEST_ENABLED", "")
        monkeypatch.setenv("API_DOCS_ENABLED", "")
        settings = AppSettings(_env_file=None)
        assert settings.ingestion_test_router_enabled is False
        assert settings.api_docs_routes_enabled is False

    def test_cors_origins_read_from_environment(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://app.fireons.com")
        assert AppSettings(_env_file=None).cors_origin_list == ["https://app.fireons.com"]

    def test_debug_surfaces_default_off_in_production(self):
        settings = _app_settings()
        assert settings.ingestion_test_router_enabled is False
        assert settings.api_docs_routes_enabled is False

    def test_debug_surfaces_default_on_in_development(self):
        settings = _app_settings(app_env="development")
        assert settings.ingestion_test_router_enabled is True
        assert settings.api_docs_routes_enabled is True

    def test_debug_surfaces_can_be_overridden_explicitly(self):
        prod = _app_settings(ingestion_test_enabled=True, api_docs_enabled=True)
        dev = _app_settings(app_env="development", ingestion_test_enabled=False, api_docs_enabled=False)
        assert prod.ingestion_test_router_enabled and prod.api_docs_routes_enabled
        assert not dev.ingestion_test_router_enabled and not dev.api_docs_routes_enabled


def _import_app_with_env(env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"TESTING", "SSM_PREFIX", "ORIGIN_VERIFY_SECRET", "DATABASE_URL", "SECRET_KEY"}
    }
    return subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=cwd,
        env={**base_env, "PYTHONPATH": str(BACKEND_DIR), **env},
        capture_output=True,
        text=True,
        timeout=120,
    )


class TestProductionStartup:
    PROD_ENV = {
        "APP_ENV": "production",
        "SECRET_KEY": "b" * 64,
        "ORIGIN_VERIFY_SECRET": "cloudfront-secret",
        "DATABASE_URL": PROD_DATABASE_URL,
        "CORS_ORIGINS": "https://app.fireons.com",
    }

    def test_app_starts_with_production_env(self, tmp_path):
        result = _import_app_with_env(self.PROD_ENV, tmp_path)
        assert result.returncode == 0, result.stderr

    def test_app_refuses_to_start_without_secret_key(self, tmp_path):
        env = {key: value for key, value in self.PROD_ENV.items() if key != "SECRET_KEY"}
        result = _import_app_with_env(env, tmp_path)
        assert result.returncode != 0
        assert "ConfigurationError" in result.stderr
        assert "SECRET_KEY" in result.stderr
