"""Add updated_at column to email_verification_tokens table

Revision ID: 0010_add_updated_at_email_toks
Revises: 0009_email_not_null_in_users
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_add_updated_at_email_toks"
down_revision: Union[str, None] = "0009_email_not_null_in_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at column to email_verification_tokens table if missing."""
    op.add_column(
        "email_verification_tokens",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Token update timestamp (UTC)",
        ),
    )


def downgrade() -> None:
    """Remove updated_at column from email_verification_tokens table."""
    op.drop_column("email_verification_tokens", "updated_at")
