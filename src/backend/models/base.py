"""
CMP Base Declarative Model.

Provides the common base model for all CMP database entities with:
- UUID primary key (using gen_random_uuid())
- created_at / updated_at timestamp columns
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all CMP database models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
        comment="Record last update timestamp (UTC)",
    )


class BaseModel(Base, TimestampMixin):
    """
    Abstract base model for all CMP entities.

    Provides:
    - id: UUID primary key (auto-generated via gen_random_uuid())
    - created_at: auto-set on insert
    - updated_at: auto-set on insert and update
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Primary key (UUID v4)",
    )
