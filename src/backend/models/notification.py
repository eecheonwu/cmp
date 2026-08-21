"""
CMP NotificationLog model.

Implements:
- notifications_log table for tracking delivery attempts and status
- Used for idempotency and delivery monitoring
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class NotificationLog(BaseModel):
    """
    Log of notification delivery attempts.

    Tracks all notification sends across providers for:
    - Delivery status monitoring
    - Idempotency (prevent duplicate sends)
    - Failover chain analysis
    """

    __tablename__ = "notifications_log"

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Recipient phone number or identifier",
    )
    delivery_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Delivery channel: 'whatsapp' or 'sms'",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Provider used: 'whatsapp', 'termii', or 'infobip'",
    )
    template_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Template identifier for the message",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Delivery status: 'pending', 'sent', 'failed', 'delivered'",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Error code if delivery failed",
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when notification was sent",
    )
    delivery_attempts: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of delivery attempts made",
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog(id={self.id}, recipient={self.recipient}, "
            f"provider={self.provider}, status={self.status})>"
        )
