from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from database.config import Settings
from database.session import engine_options

NEON_URL = "postgres://app:pw@ep-1.example.neon.tech/fireons"


def _settings(**overrides) -> Settings:
    values = {"database_url": None, "testing": False}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_database_url_uses_async_driver_and_requires_tls():
    url = make_url(_settings(database_url=NEON_URL).async_database_url)
    assert url.drivername == "postgresql+psycopg"
    assert url.query["sslmode"] == "require"


def test_explicit_sslmode_is_preserved():
    url = make_url(_settings(database_url=NEON_URL + "?sslmode=disable").async_database_url)
    assert url.query["sslmode"] == "disable"


def test_null_pool():
    assert engine_options(_settings(db_null_pool=True)) == {"poolclass": NullPool}
