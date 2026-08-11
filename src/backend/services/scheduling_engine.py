"""
CMP Scheduling Engine Service.

Implements Task 3.2 — Booking Engine with Pessimistic Locking:

- POST /appointments: lock sequence → insert or HTTP 409
- DELETE /appointments/{id}: tiered penalty logic (Tier 1/2/3)
- PATCH /appointments/{id}: reschedule with re-lock
- Staff override for Tier 3 logs to audit
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.appointment import (
    Appointment,
    AppointmentStatus,
    BookingSource,
)
from models.user import User, UserRole
from models.audit import AuditLog
from services.notification_service import NotificationOrchestrator


# ── Penalty Tier Logic ─────────────────────────────────────────────────────────

class PenaltyTier:
    """
    Penalty tier for appointment cancellation.

    Tier 1: Cancellation < 2 hours before appointment (strict penalty)
    Tier 2: Cancellation >= 2 hours before appointment (warning)
    Tier 3: Staff override (admin/manager can cancel any appointment)
    """

    TIER_1_THRESHOLD_HOURS = 2
    TIER_1_PENALTY_MESSAGE = "Cancellation within 2 hours incurs a penalty"
    TIER_2_WARNING_MESSAGE = "Cancellation confirmed with warning"
    TIER_3_OVERRIDE_MESSAGE = "Staff override - cancellation logged to audit"


# ── Scheduling Engine ─────────────────────────────────────────────────────────

class SchedulingEngine:
    """
    Appointment booking engine with pessimistic locking.

    Implements FR-019: High-concurrency doctor scheduling with database-level
    pessimistic locking (SELECT ... FOR UPDATE) to prevent double-booking.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeout = settings.DB_TRANSACTION_TIMEOUT_SECONDS

    # ── Conflict Detection ───────────────────────────────────────────────────

    async def check_slot_conflict(
        self,
        doctor_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_appointment_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Check if a time slot conflicts with existing appointments.

        Uses SELECT FOR UPDATE to lock the range and prevent race conditions.

        Args:
            doctor_id: The doctor's UUID
            start_datetime: Proposed appointment start time
            end_datetime: Proposed appointment end time
            exclude_appointment_id: UUID to exclude from check (for updates)

        Returns:
            True if conflict exists, False if slot is available
        """
        # Build query to find overlapping appointments
        # Two time ranges overlap if: start1 < end2 AND start2 < end1
        query = (
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.status == AppointmentStatus.BOOKED,
                    Appointment.start_datetime < end_datetime,
                    Appointment.end_datetime > start_datetime,
                )
            )
            .with_for_update()  # Pessimistic lock
        )

        if exclude_appointment_id:
            query = query.where(Appointment.id != exclude_appointment_id)

        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        return existing is not None

    # ── Booking Operations ─────────────────────────────────────────────────

    async def book_appointment(
        self,
        doctor_id: uuid.UUID,
        patient_id: uuid.UUID,
        branch_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        booking_source: BookingSource = BookingSource.PATIENT,
    ) -> Appointment:
        """
        Book an appointment with pessimistic locking.

        Lock sequence:
        1. Lock the time range for the doctor
        2. Check for conflicts
        3. If no conflict, insert the appointment
        4. If conflict, raise HTTP 409 Conflict

        Args:
            doctor_id: The doctor's UUID
            patient_id: The patient's UUID
            branch_id: Branch identifier
            start_datetime: Appointment start time
            end_datetime: Appointment end time
            booking_source: Source of booking (patient, receptionist, admin_override)

        Returns:
            The created Appointment

        Raises:
            HTTPException: 409 if slot is already booked
        """
        # Check for conflicts with lock
        has_conflict = await self.check_slot_conflict(
            doctor_id, start_datetime, end_datetime
        )

        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This time slot is already booked. Please select another time.",
            )

        # Create appointment
        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=patient_id,
            branch_id=branch_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status=AppointmentStatus.BOOKED,
            booking_source=booking_source,
        )
        self.db.add(appointment)
        await self.db.flush()

        return appointment

    # ── Cancellation Operations ───────────────────────────────────────────

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        user: User,
        is_staff_override: bool = False,
    ) -> tuple[Appointment, str]:
        """
        Cancel an appointment with tiered penalty logic.

        Tier 1: Cancellation < 2 hours before appointment (strict penalty)
        Tier 2: Cancellation >= 2 hours before appointment (warning)
        Tier 3: Staff override (admin/manager can cancel any appointment)

        Args:
            appointment_id: The appointment's UUID
            user: The user requesting cancellation
            is_staff_override: Whether this is a staff override

        Returns:
            tuple: (cancelled appointment, penalty tier message)

        Raises:
            HTTPException: 404 if appointment not found
            HTTPException: 403 if patient not authorized
        """
        # Get appointment with lock
        result = await self.db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # Check authorization
        is_patient = appointment.patient_id == user.id
        is_staff = user.role in [
            UserRole.RECEPTIONIST,
            UserRole.DOCTOR,
            UserRole.MANAGER,
            UserRole.ADMIN,
        ]

        if not is_patient and not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this appointment",
            )

        # Check if already cancelled
        if appointment.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Appointment is already cancelled",
            )

        # Determine penalty tier
        now = datetime.now(timezone.utc)
        hours_before = (appointment.start_datetime - now).total_seconds() / 3600

        if is_staff_override or user.role in [UserRole.MANAGER, UserRole.ADMIN]:
            # Tier 3: Staff override
            message = PenaltyTier.TIER_3_OVERRIDE_MESSAGE

            # Log to audit
            audit_log = AuditLog(
                user_id=user.id,
                action="cancel_appointment_override",
                resource_type="appointment",
                resource_id=str(appointment_id),
                details={
                    "doctor_id": str(appointment.doctor_id),
                    "patient_id": str(appointment.patient_id),
                    "start_datetime": str(appointment.start_datetime),
                    "override_role": user.role.value,
                },
            )
            self.db.add(audit_log)

        elif hours_before < PenaltyTier.TIER_1_THRESHOLD_HOURS:
            # Tier 1: Cancellation within 2 hours
            message = PenaltyTier.TIER_1_PENALTY_MESSAGE
        else:
            # Tier 2: Cancellation with warning
            message = PenaltyTier.TIER_2_WARNING_MESSAGE

        # Update appointment status
        appointment.status = AppointmentStatus.CANCELLED
        await self.db.flush()

        return appointment, message

    # ── Reschedule Operations ───────────────────────────────────────────────

    async def reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        new_start_datetime: datetime,
        new_end_datetime: datetime,
        user: User,
    ) -> tuple[Appointment, str]:
        """
        Reschedule an appointment with re-locking.

        Lock sequence:
        1. Lock the existing appointment
        2. Check for conflicts on the new time slot
        3. If no conflict, update the appointment
        4. If conflict, raise HTTP 409 Conflict

        Args:
            appointment_id: The appointment's UUID
            new_start_datetime: New appointment start time
            new_end_datetime: New appointment end time
            user: The user requesting reschedule

        Returns:
            tuple: (rescheduled appointment, message)

        Raises:
            HTTPException: 404 if appointment not found
            HTTPException: 403 if not authorized
            HTTPException: 409 if new slot conflicts
        """
        # Get appointment with lock
        result = await self.db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        # Check authorization
        is_patient = appointment.patient_id == user.id
        is_staff = user.role in [
            UserRole.RECEPTIONIST,
            UserRole.DOCTOR,
            UserRole.MANAGER,
            UserRole.ADMIN,
        ]

        if not is_patient and not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reschedule this appointment",
            )

        # Check if already cancelled/completed
        if appointment.status in [
            AppointmentStatus.CANCELLED,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.NO_SHOW,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reschedule a {appointment.status.value} appointment",
            )

        # Check for conflicts on new slot
        has_conflict = await self.check_slot_conflict(
            appointment.doctor_id,
            new_start_datetime,
            new_end_datetime,
            exclude_appointment_id=appointment_id,
        )

        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The new time slot is already booked. Please select another time.",
            )

        # Update appointment
        appointment.start_datetime = new_start_datetime
        appointment.end_datetime = new_end_datetime
        await self.db.flush()

        return appointment, "Appointment rescheduled successfully"

    # ── Query Operations ─────────────────────────────────────────────────────

    async def get_appointment(
        self,
        appointment_id: uuid.UUID,
    ) -> Optional[Appointment]:
        """Get an appointment by ID."""
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_appointments_by_patient(
        self,
        patient_id: uuid.UUID,
        status: Optional[AppointmentStatus] = None,
    ) -> list[Appointment]:
        """Get all appointments for a patient, optionally filtered by status."""
        query = select(Appointment).where(Appointment.patient_id == patient_id)

        if status:
            query = query.where(Appointment.status == status)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_appointments_by_doctor(
        self,
        doctor_id: uuid.UUID,
        date: Optional[datetime] = None,
    ) -> list[Appointment]:
        """Get all appointments for a doctor, optionally filtered by date."""
        query = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
        )

        if date:
            # Filter for appointments on the given date
            query = query.where(
                Appointment.start_datetime >= date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
                Appointment.start_datetime < date.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                ) + timedelta(days=1),
            )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_available_slots(
        self,
        doctor_id: uuid.UUID,
        date: datetime,
    ) -> list[dict]:
        """
        Get available time slots for a doctor on a given date.

        Returns slots that are within doctor's availability and not booked.
        """
        from models.appointment import DoctorAvailability

        # Get doctor's availability for the date
        availability_query = select(DoctorAvailability).where(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.is_cancelled == False,
        )

        result = await self.db.execute(availability_query)
        availabilities = result.scalars().all()

        # Get booked appointments for the date
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        booked_query = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_datetime >= start_of_day,
            Appointment.start_datetime < end_of_day,
        )

        result = await self.db.execute(booked_query)
        booked = result.scalars().all()

        # Calculate available slots (simplified - returns availability ranges)
        available_slots = []
        for avail in availabilities:
            # Check if this availability overlaps with the date
            if avail.start_datetime.date() == date.date():
                available_slots.append({
                    "start": avail.start_datetime.isoformat(),
                    "end": avail.end_datetime.isoformat(),
                    "is_available": not any(
                        a.start_datetime < avail.end_datetime
                        and a.end_datetime > avail.start_datetime
                        for a in booked
                    ),
                })

        return available_slots

    # ── Notification Integration ───────────────────────────────────────────

    async def send_appointment_confirmation(
        self,
        appointment: Appointment,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send appointment confirmation notification.

        Uses the notification orchestrator to send via WhatsApp/SMS.

        Args:
            appointment: The appointment to confirm

        Returns:
            tuple: (success, error, provider_used)
        """
        # Get patient phone
        result = await self.db.execute(
            select(User).where(User.id == appointment.patient_id)
        )
        patient = result.scalar_one_or_none()

        if not patient:
            return False, "Patient not found", "none"

        # Send via orchestrator
        orchestrator = NotificationOrchestrator(self.db)
        return await orchestrator.send_appointment_confirmation(
            patient.phone_number,
            {
                "doctor": "Doctor",
                "date": str(appointment.start_datetime.date()) if appointment.start_datetime else "date",
                "time": str(appointment.start_datetime.time()) if appointment.start_datetime else "time",
            },
        )

    async def send_cancellation_alert(
        self,
        appointment: Appointment,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send cancellation alert notification.

        Args:
            appointment: The cancelled appointment

        Returns:
            tuple: (success, error, provider_used)
        """
        # Get patient phone
        result = await self.db.execute(
            select(User).where(User.id == appointment.patient_id)
        )
        patient = result.scalar_one_or_none()

        if not patient:
            return False, "Patient not found", "none"

        # Send via orchestrator
        orchestrator = NotificationOrchestrator(self.db)
        return await orchestrator.send_cancellation_alert(
            patient.phone_number,
            {
                "doctor": "Doctor",
                "date": str(appointment.start_datetime.date()) if appointment.start_datetime else "date",
            },
        )
