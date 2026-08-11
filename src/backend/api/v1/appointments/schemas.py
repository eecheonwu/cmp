"""
CMP Appointment Pydantic Schemas.

Request and response models for appointment endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.appointment import AppointmentStatus, BookingSource


# ── Request Schemas ─────────────────────────────────────────────────────────

class BookAppointmentRequest(BaseModel):
    """Request schema for booking an appointment."""

    doctor_id: str = Field(..., description="Doctor's UUID")
    branch_id: str = Field(..., description="Branch identifier")
    start_datetime: datetime = Field(..., description="Appointment start time (UTC)")
    end_datetime: datetime = Field(..., description="Appointment end time (UTC)")


class RescheduleAppointmentRequest(BaseModel):
    """Request schema for rescheduling an appointment."""

    start_datetime: datetime = Field(..., description="New start time (UTC)")
    end_datetime: datetime = Field(..., description="New end time (UTC)")


# ── Response Schemas ───────────────────────────────────────────────────────

class AppointmentResponse(BaseModel):
    """Response schema for appointment data."""

    id: str = Field(..., description="Appointment UUID")
    doctor_id: str = Field(..., description="Doctor's UUID")
    patient_id: str = Field(..., description="Patient's UUID")
    branch_id: str = Field(..., description="Branch identifier")
    start_datetime: datetime = Field(..., description="Appointment start time (UTC)")
    end_datetime: datetime = Field(..., description="Appointment end time (UTC)")
    status: AppointmentStatus = Field(..., description="Appointment status")
    booking_source: BookingSource = Field(..., description="Source of booking")

    class Config:
        from_attributes = True


class CancelAppointmentResponse(BaseModel):
    """Response schema for appointment cancellation."""

    id: str = Field(..., description="Appointment UUID")
    status: AppointmentStatus = Field(..., description="Updated status (cancelled)")
    message: str = Field(..., description="Cancellation message with penalty info")


class AvailableSlotResponse(BaseModel):
    """Response schema for available time slot."""

    start: str = Field(..., description="Slot start time (ISO format)")
    end: str = Field(..., description="Slot end time (ISO format)")
    is_available: bool = Field(..., description="Whether slot is available")


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
