import asyncio

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from sqlalchemy import text
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


async def test_pg_trgm_extension_is_installed(engine):
    async with engine.connect() as conn:
        installed = await conn.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')")
        )
    assert installed is True


async def test_name_search_index_is_a_gin_trigram_index(engine):
    async with engine.connect() as conn:
        definition = await conn.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_financial_professionals_name_trgm'")
        )
    assert definition is not None
    assert "USING gin" in definition
    assert "gin_trgm_ops" in definition


async def test_trigram_index_is_usable_for_substring_search(engine):
    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL enable_seqscan = off"))
        plan = (
            await conn.execute(
                text(
                    "EXPLAIN SELECT id FROM financial_professionals WHERE name_normalized LIKE '%mehta%'"
                )
            )
        ).all()
    assert "ix_financial_professionals_name_trgm" in "\n".join(row[0] for row in plan)
