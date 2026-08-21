"""Make email column NOT NULL in users table

Implements Checkpoint 5 — Edge Cases & Deprecation (Vertical Slice 5):
- Enforces NOT NULL constraint on users.email column per ADR-005
- Backfills any legacy NULL email records with placeholder emails

Revision ID: 0009_make_email_not_null_in_users
Revises: 0008_add_email_verification_to_users
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_email_not_null_in_users"
down_revision: Union[str, None] = "0008_add_email_verify_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill NULL email addresses and alter email column to NOT NULL."""
    # Backfill legacy records if any exist with NULL email
    op.execute(
        "UPDATE users SET email = 'unspecified_' || id || '@placeholder.cmp' WHERE email IS NULL"
    )

    # Alter column to NOT NULL
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(255),
        nullable=False,
    )


def downgrade() -> None:
    """Revert email column to nullable=True."""
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(255),
        nullable=True,
    )
