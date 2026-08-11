"""
CMP Clinical Record Service — Encrypted Medical Records.

Implements Task 3.3 — Clinical Records with KMS Encryption:

- POST /clinical-records: encrypt before DB write
- GET /clinical-records/{id}: decrypt in memory for doctors only
- Audit log written in same transaction
- Role-based access: doctors can create/read, patients can read own records
"""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.clinical_record import ClinicalRecord
from models.user import User, UserRole
from models.audit import AuditLog
from utils.encryption import (
    encrypt_clinical_field,
    decrypt_clinical_field,
)


class ClinicalRecordService:
    """
    Service for managing encrypted clinical records.

    All clinical data is encrypted at the application layer using AES-256-GCM
    with AWS KMS envelope encryption before being written to the database.
    Decryption occurs only in application memory for authorized doctor role users.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Create ───────────────────────────────────────────────────────────────

    async def create_clinical_record(
        self,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        doctor_id: uuid.UUID,
        notes: str,
        diagnosis: str,
        prescriptions: str,
        user: User,
    ) -> ClinicalRecord:
        """
        Create a new clinical record with encrypted fields.

        Encrypts all clinical fields before writing to the database.
        Writes an audit log entry in the same transaction.

        Args:
            appointment_id: FK to appointments.id
            patient_id: FK to users.id (patient)
            doctor_id: FK to users.id (doctor)
            notes: Plaintext clinical notes (encrypted before storage)
            diagnosis: Plaintext diagnosis (encrypted before storage)
            prescriptions: Plaintext prescriptions (encrypted before storage)
            user: The authenticated user creating the record

        Returns:
            ClinicalRecord: The created record (with encrypted fields)

        Raises:
            HTTPException: 403 if user is not a doctor
            HTTPException: 409 if record already exists for this appointment
        """
        # Only doctors can create clinical records
        if user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only doctors can create clinical records",
            )

        # Check if record already exists for this appointment
        existing = await self._get_by_appointment(appointment_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A clinical record already exists for this appointment",
            )

        # Encrypt clinical fields using envelope encryption
        encrypted_notes, kms_key_notes = encrypt_clinical_field(notes)
        encrypted_diagnosis, kms_key_diag = encrypt_clinical_field(diagnosis)
        encrypted_prescriptions, kms_key_rx = encrypt_clinical_field(prescriptions)

        # Use the first key version (all encrypted with same DEK per record)
        # In practice, all fields share the same data key for this record
        kms_key_version = kms_key_notes

        # Create the record
        record = ClinicalRecord(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            encrypted_notes=encrypted_notes,
            encrypted_diagnosis=encrypted_diagnosis,
            encrypted_prescriptions=encrypted_prescriptions,
            kms_key_version=kms_key_version,
        )
        self.db.add(record)
        await self.db.flush()

        # Write audit log
        audit_log = AuditLog(
            user_id=user.id,
            action="CREATE_CLINICAL_RECORD",
            resource_type="clinical_record",
            resource_id=str(record.id),
            details={
                "appointment_id": str(appointment_id),
                "patient_id": str(patient_id),
                "doctor_id": str(doctor_id),
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        return record

    # ── Read (with decryption) ──────────────────────────────────────────────

    async def get_clinical_record(
        self,
        record_id: uuid.UUID,
        user: User,
    ) -> dict:
        """
        Get a clinical record with decrypted fields.

        Decrypts clinical fields in application memory only.
        Access control:
        - Doctors: can read any record
        - Patients: can read only their own records
        - Others: denied

        Args:
            record_id: The clinical record UUID
            user: The authenticated user requesting access

        Returns:
            dict: Clinical record with decrypted fields

        Raises:
            HTTPException: 404 if record not found
            HTTPException: 403 if not authorized
        """
        # Get the record
        result = await self.db.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinical record not found",
            )

        # Check authorization
        is_doctor = user.role == UserRole.DOCTOR
        is_own_record = user.role == UserRole.PATIENT and record.patient_id == user.id
        is_staff = user.role in [
            UserRole.MANAGER,
            UserRole.ADMIN,
            UserRole.EXECUTIVE,
        ]

        if not is_doctor and not is_own_record and not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this clinical record",
            )

        # Decrypt fields in memory (only doctors get full decryption)
        if is_doctor:
            decrypted_notes = decrypt_clinical_field(
                record.encrypted_notes, record.kms_key_version
            )
            decrypted_diagnosis = decrypt_clinical_field(
                record.encrypted_diagnosis, record.kms_key_version
            )
            decrypted_prescriptions = decrypt_clinical_field(
                record.encrypted_prescriptions, record.kms_key_version
            )

            # Write audit log for doctor access
            audit_log = AuditLog(
                user_id=user.id,
                action="READ_CLINICAL_RECORD",
                resource_type="clinical_record",
                resource_id=str(record.id),
                details={
                    "appointment_id": str(record.appointment_id),
                    "patient_id": str(record.patient_id),
                    "decrypted_fields": ["notes", "diagnosis", "prescriptions"],
                },
            )
            self.db.add(audit_log)
            await self.db.flush()
        else:
            # Non-doctors see masked/redacted fields
            decrypted_notes = "[REDACTED - Doctor access only]"
            decrypted_diagnosis = "[REDACTED - Doctor access only]"
            decrypted_prescriptions = "[REDACTED - Doctor access only]"

        return {
            "id": str(record.id),
            "appointment_id": str(record.appointment_id),
            "patient_id": str(record.patient_id),
            "doctor_id": str(record.doctor_id),
            "notes": decrypted_notes,
            "diagnosis": decrypted_diagnosis,
            "prescriptions": decrypted_prescriptions,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    # ── Update ───────────────────────────────────────────────────────────────

    async def update_clinical_record(
        self,
        record_id: uuid.UUID,
        user: User,
        notes: Optional[str] = None,
        diagnosis: Optional[str] = None,
        prescriptions: Optional[str] = None,
    ) -> dict:
        """
        Update a clinical record with re-encryption.

        Only doctors can update clinical records. Fields are re-encrypted
        with a new data key before storage.

        Args:
            record_id: The clinical record UUID
            user: The authenticated user (must be doctor)
            notes: Updated notes (optional)
            diagnosis: Updated diagnosis (optional)
            prescriptions: Updated prescriptions (optional)

        Returns:
            dict: Updated clinical record with decrypted fields

        Raises:
            HTTPException: 403 if user is not a doctor
            HTTPException: 404 if record not found
        """
        # Only doctors can update
        if user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only doctors can update clinical records",
            )

        # Get the record
        result = await self.db.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinical record not found",
            )

        # Re-encrypt and update only provided fields
        if notes is not None:
            encrypted_notes, kms_key = encrypt_clinical_field(notes)
            record.encrypted_notes = encrypted_notes
            record.kms_key_version = kms_key

        if diagnosis is not None:
            encrypted_diagnosis, kms_key = encrypt_clinical_field(diagnosis)
            record.encrypted_diagnosis = encrypted_diagnosis
            record.kms_key_version = kms_key

        if prescriptions is not None:
            encrypted_prescriptions, kms_key = encrypt_clinical_field(prescriptions)
            record.encrypted_prescriptions = encrypted_prescriptions
            record.kms_key_version = kms_key

        await self.db.flush()

        # Write audit log
        audit_log = AuditLog(
            user_id=user.id,
            action="UPDATE_CLINICAL_RECORD",
            resource_type="clinical_record",
            resource_id=str(record.id),
            details={
                "appointment_id": str(record.appointment_id),
                "updated_fields": [
                    field for field, val in
                    [("notes", notes), ("diagnosis", diagnosis), ("prescriptions", prescriptions)]
                    if val is not None
                ],
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        # Return decrypted record
        return await self.get_clinical_record(record_id, user)

    # ── List by Patient ─────────────────────────────────────────────────────

    async def get_records_by_patient(
        self,
        patient_id: uuid.UUID,
        user: User,
    ) -> list[dict]:
        """
        Get all clinical records for a patient.

        Access control:
        - Doctors: can view any patient's records
        - Patients: can view only their own records (redacted)
        - Staff: can view any patient's records (redacted)

        Args:
            patient_id: The patient's UUID
            user: The authenticated user

        Returns:
            list[dict]: List of clinical records (decrypted for doctors)
        """
        # Check authorization
        is_doctor = user.role == UserRole.DOCTOR
        is_own_records = user.role == UserRole.PATIENT and user.id == patient_id
        is_staff = user.role in [
            UserRole.MANAGER,
            UserRole.ADMIN,
            UserRole.EXECUTIVE,
        ]

        if not is_doctor and not is_own_records and not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these records",
            )

        # Get records
        result = await self.db.execute(
            select(ClinicalRecord)
            .where(ClinicalRecord.patient_id == patient_id)
            .order_by(ClinicalRecord.created_at.desc())
        )
        records = result.scalars().all()

        # Decrypt or redact based on role
        result_list = []
        for record in records:
            if is_doctor:
                decrypted_notes = decrypt_clinical_field(
                    record.encrypted_notes, record.kms_key_version
                )
                decrypted_diagnosis = decrypt_clinical_field(
                    record.encrypted_diagnosis, record.kms_key_version
                )
                decrypted_prescriptions = decrypt_clinical_field(
                    record.encrypted_prescriptions, record.kms_key_version
                )
            else:
                decrypted_notes = "[REDACTED - Doctor access only]"
                decrypted_diagnosis = "[REDACTED - Doctor access only]"
                decrypted_prescriptions = "[REDACTED - Doctor access only]"

            result_list.append({
                "id": str(record.id),
                "appointment_id": str(record.appointment_id),
                "patient_id": str(record.patient_id),
                "doctor_id": str(record.doctor_id),
                "notes": decrypted_notes,
                "diagnosis": decrypted_diagnosis,
                "prescriptions": decrypted_prescriptions,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })

        # Write audit log for doctor access
        if is_doctor and records:
            audit_log = AuditLog(
                user_id=user.id,
                action="LIST_CLINICAL_RECORDS",
                resource_type="clinical_record",
                resource_id=f"patient:{patient_id}",
                details={
                    "patient_id": str(patient_id),
                    "record_count": len(records),
                },
            )
            self.db.add(audit_log)
            await self.db.flush()

        return result_list

    # ── Release Lab Results (FR-008) ───────────────────────────────────────────

    async def release_lab_results(
        self,
        record_id: uuid.UUID,
        user: User,
        lab_results: str,
        released: bool,
    ) -> dict:
        """
        Release lab results to patient (FR-008).

        Only doctors can release lab results. The lab results are encrypted
        before being written to the database. Audit log written on release.

        Args:
            record_id: The clinical record UUID
            user: The authenticated user (must be doctor)
            lab_results: Plaintext lab results (encrypted before storage)
            released: Whether to release the lab results

        Returns:
            dict: Updated clinical record with decrypted fields

        Raises:
            HTTPException: 403 if user is not a doctor
            HTTPException: 404 if record not found
        """
        # Only doctors can release lab results
        if user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only doctors can release lab results",
            )

        # Get the record
        result = await self.db.execute(
            select(ClinicalRecord).where(ClinicalRecord.id == record_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinical record not found",
            )

        # Encrypt and store lab results
        encrypted_lab_results, kms_key = encrypt_clinical_field(lab_results)
        record.encrypted_prescriptions = encrypted_lab_results
        record.kms_key_version = kms_key

        await self.db.flush()

        # Write audit log
        audit_log = AuditLog(
            user_id=user.id,
            action="RELEASE_LAB_RESULTS",
            resource_type="clinical_record",
            resource_id=str(record.id),
            details={
                "appointment_id": str(record.appointment_id),
                "patient_id": str(record.patient_id),
                "released": released,
            },
        )
        self.db.add(audit_log)
        await self.db.flush()

        # Return decrypted record
        return await self.get_clinical_record(record_id, user)

    # ── Internal Helpers ─────────────────────────────────────────────────────

    async def _get_by_appointment(
        self,
        appointment_id: uuid.UUID,
    ) -> Optional[ClinicalRecord]:
        """Check if a clinical record exists for an appointment."""
        result = await self.db.execute(
            select(ClinicalRecord).where(
                ClinicalRecord.appointment_id == appointment_id
            )
        )
        return result.scalar_one_or_none()
