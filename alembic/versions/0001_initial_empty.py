"""Initial empty migration — Alembic baseline

Creates the Alembic versioning baseline. No schema changes yet;
subsequent migrations will add tables, enums, and constraints.

Revision ID: 0001_initial_empty
Revises: None
Create Date: 2026-07-07 21:30:00.000000+01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_empty"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline — no schema changes."""
    pass


def downgrade() -> None:
    """Baseline — no schema changes."""
    pass