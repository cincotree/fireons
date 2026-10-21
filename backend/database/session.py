"""
Async database session management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from database.config import Settings, get_settings
from database.models import Base

# Global engine and session factory
_engine = None
_async_session_factory = None


def engine_options(settings: Settings) -> dict:
    if settings.db_null_pool:
        return {"poolclass": NullPool}
    return {
        "pool_pre_ping": True,
        "pool_size": settings.pool_size,
        "max_overflow": settings.max_overflow,
        "pool_timeout": settings.pool_timeout,
    }


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,  # Set to True for SQL debugging
            **engine_options(settings),
        )
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


# Convenience alias
def AsyncSessionLocal():
    """Create a new async session."""
    factory = get_session_factory()
    return factory()


async def drop_db():
    """
    Drop all tables in the database.

    WARNING: This is destructive and should only be used in testing.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting an async database session.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting a database session.

    Usage:
        async with session_context() as session:
            result = await session.execute(...)
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def reset_engine():
    """
    Reset the engine and session factory.

    Useful for testing when switching databases.
    """
    global _engine, _async_session_factory
    if _engine:
        # Note: In async context, you'd need to await engine.dispose()
        pass
    _engine = None
    _async_session_factory = None
