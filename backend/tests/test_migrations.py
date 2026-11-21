import asyncio

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base
from tests.conftest import TEST_DATABASE_URL


def _alembic_config() -> Config:
    return Config("alembic.ini")


async def _schema_diff() -> list:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: compare_metadata(MigrationContext.configure(sync_connection), Base.metadata)
            )
    finally:
        await engine.dispose()


def test_migrations_build_the_schema_the_models_describe(engine, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    from database.config import get_settings

    get_settings.cache_clear()
    try:
        asyncio.run(_drop_all())
        command.upgrade(_alembic_config(), "head")
        assert asyncio.run(_schema_diff()) == []
        command.downgrade(_alembic_config(), "base")
        command.upgrade(_alembic_config(), "head")
    finally:
        get_settings.cache_clear()


async def _drop_all() -> None:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()
