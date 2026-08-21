"""
CMP Database Session Management.

Provides async SQLAlchemy engine, session factory, and database utilities
for AWS RDS PostgreSQL 16+ with connection pooling.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from models.base import Base


# Create async engine with connection pooling
# Note: AsyncEngine uses AsyncAdaptedQueuePool by default, no need to specify poolclass
engine: AsyncEngine = create_async_engine(
    settings.database_url_async,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,  # Base connection pool size
    max_overflow=20,  # Additional connections allowed beyond pool_size
    pool_timeout=30,  # Timeout for acquiring a connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.

    Yields:
        AsyncSession: Database session for the request

    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in SQLAlchemy models.
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use only in development/testing.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """Close database engine and dispose of all connections."""
    await engine.dispose()
