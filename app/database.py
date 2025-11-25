# app/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine
)
from sqlalchemy.orm import sessionmaker , declarative_base
from app.settings import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

async_session_factory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False
)
Base = declarative_base()


async def get_db():
    async with async_session_factory() as session:
        yield session


#  ADD THIS FUNCTION
async def init_db():
    """Create all tables dynamically (no Alembic needed for MVP)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
