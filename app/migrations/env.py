from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv

# Import your Base + all models
from app.database import Base
import app.models.schema  # This makes sure all models are imported

# This is the Alembic Config object
config = context.config

# Load .env (if present) so developers can keep DB credentials out of the INI
load_dotenv()

# If DATABASE_URL present in env, set it as the sqlalchemy.url for Alembic
env_db_url = os.environ.get("DATABASE_URL")
if env_db_url:
    # Alembic's autogenerate and offline/online APIs expect a sync DBAPI.
    # If the project uses an async driver like asyncpg, replace it with
    # a sync driver for migration operations (psycopg). This avoids
    # 'greenlet_spawn has not been called' errors when Alembic tries to
    # open a synchronous connection.
    sync_db_url = env_db_url.replace("+asyncpg", "+psycopg")
    config.set_main_option("sqlalchemy.url", sync_db_url)

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set target metadata — REQUIRED for autogenerate
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations without a live DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations with a real DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()


# Alembic entry point
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
