"""Add is_email_verified and email_verified_at to users table

Implements Task 2 — Patient Registration with Email (Vertical Slice 2):
- is_email_verified (BOOLEAN, NOT NULL, DEFAULT FALSE)
- email_verified_at (TIMESTAMPTZ, NULLABLE)

Revision ID: 0008_add_email_verification_to_users
Revises: 0007_email_verification_tokens
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_add_email_verify_to_users"
down_revision: Union[str, None] = "0007_email_verification_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_email_verified and email_verified_at columns to users table."""
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether patient email address is verified",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when email was verified",
        ),
    )


def downgrade() -> None:
    """Remove is_email_verified and email_verified_at columns from users table."""
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "is_email_verified")
