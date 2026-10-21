from sqlalchemy.pool import NullPool

from database.config import Settings
from database.session import engine_options


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, database_url="postgresql+psycopg://app:pw@db.example.com/fireons", **overrides)


def test_null_pool():
    assert engine_options(_settings(db_null_pool=True)) == {"poolclass": NullPool}


def test_pooled_engine_checks_connections_before_use():
    assert engine_options(_settings())["pool_pre_ping"] is True
