import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import database.session as session_module
from database.config import Settings
from database.session import engine_options

NEON_POOLED = "postgresql://app:s3cret@ep-cool-1-pooler.ap-southeast-1.aws.neon.tech/fireons"
NEON_DIRECT = "postgres://app:s3cret@ep-cool-1.ap-southeast-1.aws.neon.tech/fireons"


def _settings(**overrides) -> Settings:
    values = {
        "database_url": None,
        "database_url_direct": None,
        "testing": False,
        "test_database_url": None,
        "postgres_user": "postgres",
        "postgres_password": "postgres",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_db": "fireons_development",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class TestDatabaseUrl:
    def test_falls_back_to_per_part_settings(self):
        assert (
            _settings().async_database_url
            == "postgresql+psycopg://postgres:postgres@localhost:5432/fireons_development"
        )

    def test_database_url_uses_async_driver_and_requires_tls(self):
        url = make_url(_settings(database_url=NEON_POOLED).async_database_url)
        assert url.drivername == "postgresql+psycopg"
        assert url.host == "ep-cool-1-pooler.ap-southeast-1.aws.neon.tech"
        assert url.password == "s3cret"
        assert url.query["sslmode"] == "require"

    def test_postgres_scheme_is_accepted(self):
        url = make_url(_settings(database_url=NEON_DIRECT).async_database_url)
        assert url.drivername == "postgresql+psycopg"

    def test_explicit_sslmode_is_preserved(self):
        settings = _settings(database_url="postgresql://u:p@localhost/db?sslmode=disable")
        assert make_url(settings.async_database_url).query["sslmode"] == "disable"

    def test_other_query_parameters_are_preserved(self):
        settings = _settings(database_url=NEON_POOLED + "?channel_binding=require")
        query = make_url(settings.async_database_url).query
        assert query["channel_binding"] == "require"
        assert query["sslmode"] == "require"

    def test_migrations_prefer_direct_url(self):
        settings = _settings(database_url=NEON_POOLED, database_url_direct=NEON_DIRECT)
        url = make_url(settings.migration_database_url)
        assert url.host == "ep-cool-1.ap-southeast-1.aws.neon.tech"
        assert url.query["sslmode"] == "require"

    def test_migrations_fall_back_to_database_url(self):
        url = make_url(_settings(database_url=NEON_POOLED).migration_database_url)
        assert url.host == "ep-cool-1-pooler.ap-southeast-1.aws.neon.tech"

    def test_sync_url_uses_sync_driver(self):
        url = make_url(_settings(database_url_direct=NEON_DIRECT).sync_database_url)
        assert url.drivername == "postgresql"
        assert url.query["sslmode"] == "require"

    def test_testing_url_takes_priority(self):
        settings = _settings(
            testing=True,
            test_database_url="postgresql+psycopg://t:t@localhost/fireons_test",
            database_url=NEON_POOLED,
        )
        assert settings.async_database_url == "postgresql+psycopg://t:t@localhost/fireons_test"

    def test_database_url_read_from_environment(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", NEON_POOLED)
        monkeypatch.setenv("DATABASE_URL_DIRECT", NEON_DIRECT)
        settings = Settings(_env_file=None)
        assert settings.database_url == NEON_POOLED
        assert settings.database_url_direct == NEON_DIRECT


class TestEngineOptions:
    def test_default_uses_queue_pool_settings(self):
        assert engine_options(_settings()) == {"pool_size": 5, "max_overflow": 10, "pool_timeout": 30}

    def test_null_pool_and_pooler_mode(self):
        options = engine_options(_settings(db_null_pool=True, db_disable_prepared_statements=True))
        assert options == {"poolclass": NullPool, "connect_args": {"prepare_threshold": None}}

    @pytest.mark.asyncio
    async def test_engine_builds_with_lambda_options(self):
        settings = _settings(
            database_url=NEON_POOLED, db_null_pool=True, db_disable_prepared_statements=True
        )
        engine = create_async_engine(settings.async_database_url, **engine_options(settings))
        try:
            assert isinstance(engine.pool, NullPool)
        finally:
            await engine.dispose()


@pytest.mark.asyncio
class TestInitDb:
    async def test_skips_create_all_when_disabled(self, monkeypatch):
        def fail_get_engine():
            raise AssertionError("init_db must not touch the database")

        monkeypatch.setattr(
            session_module, "get_settings", lambda: _settings(db_create_tables_on_startup=False)
        )
        monkeypatch.setattr(session_module, "get_engine", fail_get_engine)

        await session_module.init_db()

    async def test_creates_tables_by_default(self, monkeypatch):
        calls = []

        class FakeConnection:
            async def run_sync(self, fn):
                calls.append(fn)

        class FakeBegin:
            async def __aenter__(self):
                return FakeConnection()

            async def __aexit__(self, *exc):
                return False

        class FakeEngine:
            def begin(self):
                return FakeBegin()

        monkeypatch.setattr(session_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(session_module, "get_engine", lambda: FakeEngine())

        await session_module.init_db()

        assert calls == [session_module.Base.metadata.create_all]
