from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from database.config import Settings
from database.session import engine_options

POOLED = "postgres://app:pw@ep-1-pooler.example.neon.tech/fireons"
DIRECT = "postgresql://app:pw@ep-1.example.neon.tech/fireons"


def _settings(**overrides) -> Settings:
    values = {"database_url": None, "database_url_direct": None, "testing": False}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_database_url_uses_async_driver_and_requires_tls():
    url = make_url(_settings(database_url=POOLED).async_database_url)
    assert url.drivername == "postgresql+psycopg"
    assert url.query["sslmode"] == "require"


def test_explicit_sslmode_is_preserved():
    url = make_url(_settings(database_url=POOLED + "?sslmode=disable").async_database_url)
    assert url.query["sslmode"] == "disable"


def test_migrations_prefer_direct_url():
    assert make_url(_settings(database_url=POOLED, database_url_direct=DIRECT).migration_database_url).host == "ep-1.example.neon.tech"
    assert make_url(_settings(database_url=POOLED).migration_database_url).host == "ep-1-pooler.example.neon.tech"


def test_null_pool_without_prepared_statements():
    options = engine_options(_settings(db_null_pool=True, db_disable_prepared_statements=True))
    assert options == {"poolclass": NullPool, "connect_args": {"prepare_threshold": None}}
