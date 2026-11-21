from sqlalchemy.pool import NullPool

from database.config import Settings
from database.session import engine_options


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, database_url="postgresql+psycopg://app:pw@db.example.com/fireons", **overrides)


def test_null_pool():
    assert engine_options(_settings(db_null_pool=True)) == {"poolclass": NullPool}


def test_pooled_engine_checks_connections_before_use():
    assert engine_options(_settings())["pool_pre_ping"] is True


def test_plain_postgres_urls_use_the_psycopg_driver():
    for scheme in ("postgresql", "postgres"):
        settings = Settings(_env_file=None, database_url=f"{scheme}://u:p@db.example.com/fireons?sslmode=require")
        assert settings.database_url == "postgresql+psycopg://u:p@db.example.com/fireons?sslmode=require"


def test_explicit_driver_is_left_alone():
    assert _settings().database_url == "postgresql+psycopg://app:pw@db.example.com/fireons"


def test_small_pool_settings_reach_the_engine():
    options = engine_options(_settings(db_null_pool=False, pool_size=1, max_overflow=1))

    assert options["pool_size"] == 1
    assert options["max_overflow"] == 1
    assert options["pool_pre_ping"] is True
    assert "poolclass" not in options
