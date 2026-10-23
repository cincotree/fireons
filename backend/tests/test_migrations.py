import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from tests.conftest import TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parent.parent


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


def test_models_and_migrations_are_in_sync(setup_test_database):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
