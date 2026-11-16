"""
MediFlow Database Engine and Session Factory
Provides async SQLAlchemy engine, session factory, and base model.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from mediflow.core.config import get_settings

settings = get_settings()

# Naming convention for constraints — required for Alembic autogenerate
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    metadata = metadata


def create_engine() -> object:
    """Create and return the async SQLAlchemy engine."""
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
        echo=settings.debug,
    )


engine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> dict[str, str]:
    """
    Verify the database connection is working.
    Returns status info or raises on failure.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT version(), current_database(), current_user")
        )
        row = result.fetchone()
        return {
            "status": "healthy",
            "postgres_version": row[0] if row else "unknown",
            "database": row[1] if row else "unknown",
            "user": row[2] if row else "unknown",
        }


async def check_pgvector_extension() -> dict[str, str]:
    """Check whether pgvector extension is installed."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
            )
        )
        row = result.fetchone()
        if row:
            return {"status": "installed", "version": row[1]}
        return {"status": "not_installed", "version": None}
