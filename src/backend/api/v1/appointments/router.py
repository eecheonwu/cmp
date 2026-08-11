"""
CMP Appointments API Router.

Implements Task 3.2 — Booking Engine with Pessimistic Locking:

- POST /appointments: book appointment with lock sequence
- DELETE /appointments/{id}: cancel with tiered penalty logic
- PATCH /appointments/{id}: reschedule with re-lock
- GET /appointments: list appointments for current user
- GET /appointments/available-slots: get available slots for a doctor
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import RoleChecker
from db.session import get_db
from models.user import User, UserRole
from models.appointment import AppointmentStatus, BookingSource
from services.scheduling_engine import SchedulingEngine
from api.v1.appointments.schemas import (
    BookAppointmentRequest,
    RescheduleAppointmentRequest,
    AppointmentResponse,
    CancelAppointmentResponse,
    AvailableSlotResponse,
)

# Create router
router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_scheduling_engine(db: AsyncSession = Depends(get_db)) -> SchedulingEngine:
    """Get scheduling engine instance."""
    return SchedulingEngine(db)


def create_appointment_response(appointment) -> AppointmentResponse:
    """Create appointment response from model."""
    return AppointmentResponse(
        id=str(appointment.id),
        doctor_id=str(appointment.doctor_id),
        patient_id=str(appointment.patient_id),
        branch_id=appointment.branch_id,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        status=appointment.status,
        booking_source=appointment.booking_source,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["appointments"],
)
async def book_appointment(
    request: BookAppointmentRequest,
    current_user: User = Depends(RoleChecker([UserRole.PATIENT, UserRole.RECEPTIONIST])),
    db: AsyncSession = Depends(get_db),
):
    """
    Book an appointment with pessimistic locking.

    Lock sequence:
    1. Lock the time range for the doctor
    2. Check for conflicts
    3. If no conflict, insert the appointment
    4. If conflict, return HTTP 409 Conflict

    For patients: booking_source = 'patient'
    For receptionists: booking_source = 'receptionist'
    """
    engine = SchedulingEngine(db)

    # Determine booking source
    booking_source = (
        BookingSource.RECEPTIONIST
        if current_user.role != UserRole.PATIENT
        else BookingSource.PATIENT
    )

    # Book appointment
    try:
        appointment = await engine.book_appointment(
            doctor_id=uuid.UUID(request.doctor_id),
            patient_id=current_user.id,
            branch_id=request.branch_id,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
            booking_source=booking_source,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to book appointment: {str(e)}",
        )

    # Send confirmation notification (async, don't wait)
    # In production, this would be a Celery task
    # await engine.send_appointment_confirmation(appointment)

    return create_appointment_response(appointment)


@router.get(
    "/appointments",
    response_model=list[AppointmentResponse],
    tags=["appointments"],
)
async def list_appointments(
    status_filter: Optional[AppointmentStatus] = None,
    current_user: User = Depends(
        RoleChecker([UserRole.PATIENT, UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    List appointments for the current user.

    - Patients: see their own appointments
    - Doctors: see their appointments (query param for date)
    - Staff: see all appointments (with optional status filter)
    """
    engine = SchedulingEngine(db)

    if current_user.role == UserRole.PATIENT:
        appointments = await engine.get_appointments_by_patient(
            current_user.id, status_filter
        )
    elif current_user.role == UserRole.DOCTOR:
        appointments = await engine.get_appointments_by_doctor(current_user.id)
    else:
        # For staff, return all appointments (would need branch filter in production)
        from sqlalchemy import select
        from models.appointment import Appointment
        query = select(Appointment)
        if status_filter:
            query = query.where(Appointment.status == status_filter)
        result = await db.execute(query)
        appointments = result.scalars().all()

    return [create_appointment_response(a) for a in appointments]


@router.delete(
    "/appointments/{appointment_id}",
    response_model=CancelAppointmentResponse,
    tags=["appointments"],
)
async def cancel_appointment(
    appointment_id: str,
    current_user: User = Depends(
        RoleChecker([UserRole.PATIENT, UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.MANAGER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an appointment with tiered penalty logic.

    Tier 1: Cancellation < 2 hours before appointment (strict penalty)
    Tier 2: Cancellation >= 2 hours before appointment (warning)
    Tier 3: Staff override (admin/manager can cancel any appointment)
    """
    engine = SchedulingEngine(db)

    try:
        appointment, message = await engine.cancel_appointment(
            appointment_id=uuid.UUID(appointment_id),
            user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel appointment: {str(e)}",
        )

    # Send cancellation alert (async, don't wait)
    # In production, this would be a Celery task
    # await engine.send_cancellation_alert(appointment)

    return CancelAppointmentResponse(
        id=str(appointment.id),
        status=appointment.status,
        message=message,
    )


@router.patch(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    tags=["appointments"],
)
async def reschedule_appointment(
    appointment_id: str,
    request: RescheduleAppointmentRequest,
    current_user: User = Depends(
        RoleChecker([UserRole.PATIENT, UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.MANAGER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Reschedule an appointment with re-locking.

    Lock sequence:
    1. Lock the existing appointment
    2. Check for conflicts on the new time slot
    3. If no conflict, update the appointment
    4. If conflict, return HTTP 409 Conflict
    """
    engine = SchedulingEngine(db)

    try:
        appointment, message = await engine.reschedule_appointment(
            appointment_id=uuid.UUID(appointment_id),
            new_start_datetime=request.start_datetime,
            new_end_datetime=request.end_datetime,
            user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reschedule appointment: {str(e)}",
        )

    return create_appointment_response(appointment)


@router.get(
    "/appointments/available-slots",
    response_model=list[AvailableSlotResponse],
    tags=["appointments"],
)
async def get_available_slots(
    doctor_id: str,
    date: datetime,
    current_user: User = Depends(
        RoleChecker([UserRole.PATIENT, UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.MANAGER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get available time slots for a doctor on a given date.

    Returns slots that are within doctor's availability and not booked.
    """
    engine = SchedulingEngine(db)

    try:
        slots = await engine.get_available_slots(
            doctor_id=uuid.UUID(doctor_id),
            date=date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available slots: {str(e)}",
        )

    return [AvailableSlotResponse(**slot) for slot in slots]
