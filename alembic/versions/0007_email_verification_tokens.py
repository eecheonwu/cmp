"""Create email_verification_tokens table for email verification tokens

Implements Task 1 — Email Verification Tokens Schema:
- email_verification_tokens table for 60-min TTL single-use tokens (ADR-005)
- Indexes on email and expires_at

Revision ID: 0007_email_verification_tokens
Revises: 0006_security_audit_logs
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_email_verification_tokens"
down_revision: Union[str, None] = "0006_security_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_verification_tokens table and indexes."""
    op.create_table(
        "email_verification_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            comment="Target patient email address",
        ),
        sa.Column(
            "token_hash",
            sa.String(255),
            nullable=False,
            comment="bcrypt hash of the raw verification token",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Verification attempt count (max 5)",
        ),
        sa.Column(
            "is_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether token has been consumed for password creation",
        ),
        sa.Column(
            "is_expired",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether token has been manually expired/superseded",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Token expiry timestamp (60-minute TTL)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Token creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Token update timestamp (UTC)",
        ),
    )

    # Index on email for fast lookups
    op.create_index(
        "ix_email_verification_tokens_email",
        "email_verification_tokens",
        ["email"],
    )

    # Index on expires_at for expiry cleanup
    op.create_index(
        "ix_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop email_verification_tokens table and indexes."""
    op.drop_index("ix_email_verification_tokens_expires_at", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_email", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
