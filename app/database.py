# app/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from app.settings import settings

# Naming convention for deterministic constraint/index names (recommended)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
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


#  ADD THIS FUNCTION
async def init_db():
    """Create all tables dynamically (no Alembic needed for MVP)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
