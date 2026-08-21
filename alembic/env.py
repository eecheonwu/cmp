"""
CMP Alembic Environment Configuration.

Configures Alembic to use async SQLAlchemy with PostgreSQL 16+ (AWS RDS).
Supports both online (connection-based) and offline (SQL script) migrations.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
# Import directly from model files for Docker compatibility
import sys
sys.path.insert(0, '/app')

# Import from the mounted models directory
from models.base import Base  # noqa: E402, F401
from models.user import User, PatientProfile, VerificationOTP  # noqa: E402, F401
from models.appointment import Appointment, DoctorAvailability  # noqa: E402, F401
from models.clinical_record import ClinicalRecord  # noqa: E402, F401

# Target metadata for autogenerate
target_metadata = Base.metadata

# Database URL (overridden by environment variable in production)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cmp_user:cmp_password@postgres:5432/cmp_db",
)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine. Skips
    engine creation. Emits SQL script as output.
    """
    url = config.get_main_option("sqlalchemy.url", DATABASE_URL)
    # Strip async driver prefix for offline SQL generation
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a live database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.

    Creates a temporary async engine from the configured URL, runs
    migrations, and disposes the engine.
    """
    url = config.get_main_option("sqlalchemy.url", DATABASE_URL)
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (sync wrapper around async)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()