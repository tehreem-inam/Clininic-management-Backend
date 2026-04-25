# app/database/__init__.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from app.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Naming convention for deterministic constraint/index names
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

DATABASE_URL: Optional[str] = getattr(settings, "DATABASE_URL", None)

if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set; DB engine will be created with a None URL")

# Create async engine; keep echo enabled only when DEBUG
engine = create_async_engine(
    DATABASE_URL,
    echo=(getattr(settings, "LOG_LEVEL", "INFO") == "DEBUG"),
    future=True,
)

async_session_factory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declarative base with metadata that includes naming_convention
Base = declarative_base(metadata=metadata)


async def get_db():
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Create all tables dynamically (helper for local development).

    Note: For production deployments, prefer running Alembic migrations
    and keep `AUTO_CREATE_TABLES` disabled.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_sync_database_url() -> Optional[str]:
    """Return a sync DB URL for Alembic or tooling that requires a sync driver.

    If the async driver is present (e.g. `+asyncpg`) this replaces it with
    a common sync driver (e.g. `+psycopg`). Returns None when no URL configured.
    """
    if not DATABASE_URL:
        return None
    return DATABASE_URL.replace("+asyncpg", "+psycopg")


__all__ = [
    "engine",
    "async_session_factory",
    "Base",
    "get_db",
    "init_db",
    "get_sync_database_url",
]
