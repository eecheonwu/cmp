"""
CMP AuditLog model.

Implements audit logging for:
- Staff override cancellations (Tier 3)
- Clinical record access
- System administrative actions
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class AuditLog(BaseModel):
    """
    Audit log for tracking sensitive operations.

    Used for:
    - Staff override cancellations (Tier 3)
    - Clinical record access
    - Administrative actions
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK → users.id (user who performed action)",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Action performed (e.g., 'cancel_appointment_override')",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of resource affected (e.g., 'appointment', 'clinical_record')",
    )
    resource_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="ID of the resource affected",
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional details about the action",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"resource={self.resource_type}:{self.resource_id})>"
        )
