"""Add created_at and updated_at to notifications_log table

Revision ID: 0011_add_timestamps_to_notif_log
Revises: 0010_add_updated_at_email_toks
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_add_timestamps_to_notif_log"
down_revision: Union[str, None] = "0010_add_updated_at_email_toks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_at and updated_at columns to notifications_log table if missing."""
    op.add_column(
        "notifications_log",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Notification log creation timestamp (UTC)",
        ),
    )
    op.add_column(
        "notifications_log",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Notification log update timestamp (UTC)",
        ),
    )


def downgrade() -> None:
    """Remove created_at and updated_at columns from notifications_log table."""
    op.drop_column("notifications_log", "updated_at")
    op.drop_column("notifications_log", "created_at")
