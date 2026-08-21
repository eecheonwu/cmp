"""Create doctor_availability, appointments tables + enums

Implements Task 3.1 — Scheduling Schema:

- appointment_status enum: booked, cancelled, completed, no-show
- payment_status enum: pending, deposit_paid, fully_paid, waived, refunded
- doctor_availability table for time-bound shifts (FR-018)
- appointments table with status, payment_state, booking_source
- Indexes on doctor_id+start_datetime for conflict detection

Revision ID: 0004_scheduling_schema
Revises: 0003_notifications_log
Create Date: 2026-07-08 21:20:00.000000+01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0004_scheduling_schema"
down_revision: Union[str, None] = "0003_notifications_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create appointment_status, payment_status enums, doctor_availability, appointments tables."""
    # ── Enum: appointment_status ──────────────────────────────────────────────
    # Create enum type if it doesn't exist (using raw SQL for reliability)
    op.execute("""
        CREATE TYPE appointment_status AS ENUM ('booked', 'cancelled', 'completed', 'no-show');
    """)
    
    # Use a text column with check constraint instead of enum type
    appointment_status_enum = sa.String(50)
    appointment_status_check = sa.CheckConstraint(
        "status IN ('booked', 'cancelled', 'completed', 'no-show')",
        name="ck_appointments_status_valid",
    )

    # ── Enum: payment_status ───────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE payment_status AS ENUM ('pending', 'deposit_paid', 'fully_paid', 'waived', 'refunded');
    """)
    payment_status_enum = sa.String(50)
    payment_status_check = sa.CheckConstraint(
        "payment_state IN ('pending', 'deposit_paid', 'fully_paid', 'waived', 'refunded')",
        name="ck_appointments_payment_state_valid",
    )

    # ── Table: doctor_availability ───────────────────────────────────────────
    op.create_table(
        "doctor_availability",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK → users.id (doctor)",
        ),
        sa.Column(
            "branch_id",
            sa.String(50),
            nullable=False,
            comment="Branch identifier",
        ),
        sa.Column(
            "start_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Shift start time (UTC)",
        ),
        sa.Column(
            "end_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Shift end time (UTC)",
        ),
        sa.Column(
            "is_cancelled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="Whether this shift is cancelled",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Record creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Record last update timestamp (UTC)",
        ),
        sa.CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_doctor_availability_time_order",
        ),
    )

    # Index on doctor_id + start_datetime for availability queries
    op.create_index(
        "ix_doctor_availability_doctor_start",
        "doctor_availability",
        ["doctor_id", "start_datetime"],
    )

    # Index on branch_id for branch-based queries
    op.create_index(
        "ix_doctor_availability_branch",
        "doctor_availability",
        ["branch_id"],
    )

    # ── Table: appointments ───────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key (UUID v4)",
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK → users.id (doctor)",
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK → users.id (patient)",
        ),
        sa.Column(
            "branch_id",
            sa.String(50),
            nullable=False,
            comment="Branch identifier",
        ),
        sa.Column(
            "start_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Appointment start time (UTC)",
        ),
        sa.Column(
            "end_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Appointment end time (UTC)",
        ),
        sa.Column(
            "status",
            appointment_status_enum,
            server_default=sa.text("'booked'"),
            nullable=False,
            comment="Appointment status",
        ),
        sa.Column(
            "payment_state",
            payment_status_enum,
            server_default=sa.text("'pending'"),
            nullable=False,
            comment="Payment status (INT-005 Phase 2 placeholder)",
        ),
        sa.Column(
            "booking_source",
            sa.String(50),
            nullable=False,
            comment="Source of booking: 'patient', 'receptionist', or 'admin_override'",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="Record creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
            comment="Record last update timestamp (UTC)",
        ),
        sa.CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_appointments_time_order",
        ),
        appointment_status_check,
        payment_status_check,
    )

    # Index on doctor_id + start_datetime for conflict detection (FR-019)
    op.create_index(
        "ix_appointments_doctor_start",
        "appointments",
        ["doctor_id", "start_datetime"],
    )

    # Index on patient_id for patient appointment history
    op.create_index(
        "ix_appointments_patient",
        "appointments",
        ["patient_id"],
    )

    # Index on branch_id for branch-based queries
    op.create_index(
        "ix_appointments_branch",
        "appointments",
        ["branch_id"],
    )

    # Index on status for filtering by status
    op.create_index(
        "ix_appointments_status",
        "appointments",
        ["status"],
    )


def downgrade() -> None:
    """Drop tables and enums (in reverse order)."""
    # Drop appointments table and indexes
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_branch", table_name="appointments")
    op.drop_index("ix_appointments_patient", table_name="appointments")
    op.drop_index("ix_appointments_doctor_start", table_name="appointments")
    op.drop_table("appointments")

    # Drop doctor_availability table and indexes
    op.drop_index("ix_doctor_availability_branch", table_name="doctor_availability")
    op.drop_index("ix_doctor_availability_doctor_start", table_name="doctor_availability")
    op.drop_table("doctor_availability")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS appointment_status")