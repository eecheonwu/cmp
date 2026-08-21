"""
CMP Appointment & DoctorAvailability models.

Implements Task 3.1 — Scheduling Schema:

- Appointment model with status, payment_state, booking_source
- DoctorAvailability model for time-bound shifts (FR-018)
- appointment_status enum: booked, cancelled, completed, no-show
- payment_status enum: pending, deposit_paid, fully_paid, waived, refunded
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class AppointmentStatus(str, enum.Enum):
    """Appointment status enum for tracking appointment lifecycle."""

    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no-show"


class PaymentStatus(str, enum.Enum):
    """Payment status enum (INT-005 Phase 2 placeholder)."""

    PENDING = "pending"
    DEPOSIT_PAID = "deposit_paid"
    FULLY_PAID = "fully_paid"
    WAIVED = "waived"
    REFUNDED = "refunded"


class BookingSource(str, enum.Enum):
    """Source of appointment booking."""

    PATIENT = "patient"
    RECEPTIONIST = "receptionist"
    ADMIN_OVERRIDE = "admin_override"


class Appointment(BaseModel):
    """
    Appointment entity for scheduling.

    Supports pessimistic locking for concurrent booking (FR-019).
    Foreign keys use RESTRICT to preserve audit trail.
    """

    __tablename__ = "appointments"

    __table_args__ = (
        CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_appointments_time_order",
        ),
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK → users.id (doctor)",
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK → users.id (patient)",
    )
    branch_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Branch identifier",
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Appointment start time (UTC)",
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Appointment end time (UTC)",
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status", create_type=True),
        server_default="booked",
        nullable=False,
        comment="Appointment status",
    )
    payment_state: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", create_type=True),
        server_default="pending",
        nullable=False,
        comment="Payment status (INT-005 Phase 2 placeholder)",
    )
    booking_source: Mapped[BookingSource] = mapped_column(
        Enum(BookingSource, name="booking_source", create_type=False),
        nullable=False,
        comment="Source of booking: 'patient', 'receptionist', or 'admin_override'",
    )

    # Relationships
    doctor: Mapped["User"] = relationship(
        "User",
        primaryjoin="Appointment.doctor_id == User.id",
        backref="appointments_as_doctor",
    )
    patient: Mapped["User"] = relationship(
        "User",
        primaryjoin="Appointment.patient_id == User.id",
        backref="appointments_as_patient",
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, doctor_id={self.doctor_id}, "
            f"patient_id={self.patient_id}, status={self.status.value})>"
        )


class DoctorAvailability(BaseModel):
    """
    Doctor availability slot for time-bound shifts (FR-018).

    Represents a doctor's working hours at a specific branch.
    Used for availability queries and conflict detection.
    """

    __tablename__ = "doctor_availability"

    __table_args__ = (
        CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_doctor_availability_time_order",
        ),
    )

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK → users.id (doctor)",
    )
    branch_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Branch identifier",
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Shift start time (UTC)",
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Shift end time (UTC)",
    )
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        server_default=func.text("false"),
        nullable=False,
        comment="Whether this shift is cancelled",
    )

    # Relationships
    doctor: Mapped["User"] = relationship(
        "User",
        primaryjoin="DoctorAvailability.doctor_id == User.id",
        backref="availability_slots",
    )

    def __repr__(self) -> str:
        return (
            f"<DoctorAvailability(id={self.id}, doctor_id={self.doctor_id}, "
            f"branch_id={self.branch_id}, start={self.start_datetime}, "
            f"end={self.end_datetime}, cancelled={self.is_cancelled})>"
        )
