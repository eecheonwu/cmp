"""Create notifications_log table for delivery tracking

Implements Task 1.5 — Notification & Supporting Schema:

- notifications_log table for tracking delivery attempts and status
- Indexes for recipient-based queries and provider status monitoring

Revision ID: 0003_notifications_log
Revises: 0002_auth_schema
Create Date: 2026-07-08 20:50:00.000000+01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0003_notifications_log"
down_revision: Union[str, None] = "0002_auth_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create notifications_log table for delivery tracking."""
    op.create_table(
        "notifications_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "recipient",
            sa.String(255),
            nullable=False,
            comment="Recipient phone number or identifier",
        ),
        sa.Column(
            "delivery_type",
            sa.String(20),
            nullable=False,
            comment="Delivery channel: 'whatsapp' or 'sms'",
        ),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider used: 'whatsapp', 'termii', or 'infobip'",
        ),
        sa.Column(
            "template_name",
            sa.String(100),
            nullable=False,
            comment="Template identifier for the message",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            comment="Delivery status: 'pending', 'sent', 'failed', 'delivered'",
        ),
        sa.Column(
            "error_code",
            sa.String(100),
            nullable=True,
            comment="Error code if delivery failed",
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Timestamp when notification was sent",
        ),
        sa.Column(
            "delivery_attempts",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
            comment="Number of delivery attempts made",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Notification log creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Notification log update timestamp (UTC)",
        ),
    )

    # Index on recipient + sent_at for rate-limit and history queries
    op.create_index(
        "ix_notifications_log_recipient_sent_at",
        "notifications_log",
        ["recipient", "sent_at"],
    )

    # Index on provider + status for monitoring delivery success rates
    op.create_index(
        "ix_notifications_log_provider_status",
        "notifications_log",
        ["provider", "status"],
    )


def downgrade() -> None:
    """Drop notifications_log table and indexes."""
    op.drop_index("ix_notifications_log_recipient_sent_at", table_name="notifications_log")
    op.drop_index("ix_notifications_log_provider_status", table_name="notifications_log")
    op.drop_table("notifications_log")