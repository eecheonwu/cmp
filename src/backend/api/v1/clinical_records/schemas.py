"""
CMP Clinical Record Pydantic Schemas.

Request and response models for clinical record endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ─────────────────────────────────────────────────────────

class CreateClinicalRecordRequest(BaseModel):
    """Request schema for creating a clinical record."""

    appointment_id: str = Field(..., description="Appointment UUID")
    patient_id: str = Field(..., description="Patient UUID")
    notes: str = Field(..., description="Clinical notes (plaintext, encrypted before storage)")
    diagnosis: str = Field(..., description="Diagnosis (plaintext, encrypted before storage)")
    prescriptions: str = Field(..., description="Prescriptions (plaintext, encrypted before storage)")


class UpdateClinicalRecordRequest(BaseModel):
    """Request schema for updating a clinical record."""

    notes: Optional[str] = Field(None, description="Updated clinical notes")
    diagnosis: Optional[str] = Field(None, description="Updated diagnosis")
    prescriptions: Optional[str] = Field(None, description="Updated prescriptions")


class ReleaseLabResultsRequest(BaseModel):
    """Request schema for releasing lab results to patient (FR-008)."""

    lab_results: str = Field(..., description="Lab results to release (plaintext, encrypted before storage)")
    released: bool = Field(..., description="Whether to release the lab results")


# ── Response Schemas ───────────────────────────────────────────────────────

class ClinicalRecordResponse(BaseModel):
    """Response schema for clinical record data."""

    id: str = Field(..., description="Clinical record UUID")
    appointment_id: str = Field(..., description="Appointment UUID")
    patient_id: str = Field(..., description="Patient UUID")
    doctor_id: str = Field(..., description="Doctor UUID")
    notes: str = Field(..., description="Clinical notes (decrypted for doctors, redacted for others)")
    diagnosis: str = Field(..., description="Diagnosis (decrypted for doctors, redacted for others)")
    prescriptions: str = Field(..., description="Prescriptions (decrypted for doctors, redacted for others)")
    created_at: Optional[str] = Field(None, description="Record creation timestamp (UTC)")
    updated_at: Optional[str] = Field(None, description="Record last update timestamp (UTC)")

    class Config:
        from_attributes = True
