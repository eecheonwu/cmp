"""
CMP ClinicalRecord model — Restricted Medical (Encrypted).

Implements ADR-003: Application-Level AES-256-GCM Column Encryption + AWS KMS
envelope encryption for clinical data.

All clinical fields (notes, diagnosis, prescriptions) are stored as ciphertext.
Decryption only occurs in application memory for authenticated doctor role users.
System administrators and database administrators MUST NOT be able to read
clinical records or consultation notes.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class ClinicalRecord(BaseModel):
    """
    Clinical record entity — Restricted Medical (Encrypted).

    Stores encrypted clinical data for a patient's appointment. All medical
    fields are encrypted at the application layer using AES-256-GCM with
    AWS KMS envelope encryption.

    ⚠️ CRITICAL: encrypted_notes, encrypted_diagnosis, encrypted_prescriptions
    are stored as ciphertext. Decryption only occurs in application memory for
    authenticated doctor role users.
    """

    __tablename__ = "clinical_records"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        comment="FK → appointments.id (one-to-one with appointment)",
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK → users.id (patient)",
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK → users.id (doctor who created the record)",
    )
    encrypted_notes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256-GCM encrypted clinical notes (ciphertext + IV + tag as JSON)",
    )
    encrypted_diagnosis: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256-GCM encrypted diagnosis (ciphertext + IV + tag as JSON)",
    )
    encrypted_prescriptions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AES-256-GCM encrypted prescriptions (ciphertext + IV + tag as JSON)",
    )
    kms_key_version: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Encrypted KMS data key (Base64) used for envelope encryption",
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        backref="clinical_record",
        uselist=False,
    )
    patient: Mapped["User"] = relationship(
        "User",
        primaryjoin="ClinicalRecord.patient_id == User.id",
        backref="clinical_records_as_patient",
    )
    doctor: Mapped["User"] = relationship(
        "User",
        primaryjoin="ClinicalRecord.doctor_id == User.id",
        backref="clinical_records_as_doctor",
    )

    def __repr__(self) -> str:
        return (
            f"<ClinicalRecord(id={self.id}, appointment_id={self.appointment_id}, "
            f"patient_id={self.patient_id}, doctor_id={self.doctor_id})>"
        )
