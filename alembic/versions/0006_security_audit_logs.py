"""Create security_audit_logs table for immutable audit logging

Implements Task 1.4 — Clinical Records Schema:
- security_audit_logs table for tracking all sensitive operations (NFR-007)
- Index on user_id + timestamp for efficient audit queries

Revision ID: 0006_security_audit_logs
Revises: 0005_clinical_records
Create Date: 2026-07-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_security_audit_logs"
down_revision: Union[str, None] = "0005_clinical_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create security_audit_logs table for immutable audit logging."""
    op.create_table(
        "security_audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who performed action (no FK for immutability)",
        ),
        sa.Column(
            "action_type",
            sa.String(100),
            nullable=False,
            comment="Action type: READ_CLINICAL_RECORD, WRITE_CLINICAL_RECORD, OVERRIDE_BOOKING, etc.",
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Patient ID affected by action",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="IPv4 or IPv6 address of requester",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Action timestamp (UTC)",
        ),
        sa.Column(
            "action_details",
            sa.Text(),
            nullable=False,
            comment="JSON details of the action",
        ),
    )

    # Index on user_id + timestamp for audit queries
    op.create_index(
        "ix_security_audit_logs_user_timestamp",
        "security_audit_logs",
        ["user_id", "timestamp"],
    )


def downgrade() -> None:
    """Drop security_audit_logs table and indexes."""
    op.drop_index("ix_security_audit_logs_user_timestamp", table_name="security_audit_logs")
    op.drop_table("security_audit_logs")