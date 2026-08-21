"""
CMP Clinical Records API Router.

Implements Task 3.3 — Clinical Records with KMS Encryption:

- POST /clinical-records: encrypt before DB write (doctor only)
- GET /clinical-records/{id}: decrypt in memory for doctors only
- PATCH /clinical-records/{id}: update with re-encryption (doctor only)
- GET /clinical-records/by-patient/{patient_id}: list patient records
- PATCH /clinical-records/{id}/release-lab-results: release lab results (FR-008)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import RoleChecker
from db.session import get_db
from models.user import User, UserRole
from services.clinical_record_service import ClinicalRecordService
from api.v1.clinical_records.schemas import (
    CreateClinicalRecordRequest,
    UpdateClinicalRecordRequest,
    ReleaseLabResultsRequest,
    ClinicalRecordResponse,
)

# Create router
router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_clinical_record_service(
    db: AsyncSession = Depends(get_db),
) -> ClinicalRecordService:
    """Get clinical record service instance."""
    return ClinicalRecordService(db)


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/clinical-records",
    response_model=ClinicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["clinical-records"],
)
async def create_clinical_record(
    request: CreateClinicalRecordRequest,
    current_user: User = Depends(RoleChecker([UserRole.DOCTOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new clinical record with encrypted fields.

    Encrypts all clinical fields (notes, diagnosis, prescriptions) using
    AES-256-GCM with AWS KMS envelope encryption before writing to the database.
    Writes an audit log entry in the same transaction.

    Only doctors can create clinical records.
    """
    service = ClinicalRecordService(db)

    try:
        record = await service.create_clinical_record(
            appointment_id=uuid.UUID(request.appointment_id),
            patient_id=uuid.UUID(request.patient_id),
            doctor_id=current_user.id,
            notes=request.notes,
            diagnosis=request.diagnosis,
            prescriptions=request.prescriptions,
            user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clinical record: {str(e)}",
        )

    # Return the record (decrypted for the creating doctor)
    return await service.get_clinical_record(record.id, current_user)


@router.get(
    "/clinical-records/{record_id}",
    response_model=ClinicalRecordResponse,
    tags=["clinical-records"],
)
async def get_clinical_record(
    record_id: str,
    current_user: User = Depends(
        RoleChecker([UserRole.DOCTOR, UserRole.PATIENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.EXECUTIVE])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a clinical record with decrypted fields.

    Decrypts clinical fields in application memory only.
    - Doctors: full decryption of all fields
    - Patients: can view own records (redacted)
    - Staff (manager/admin/executive): can view records (redacted)
    - Audit log written for doctor access
    """
    service = ClinicalRecordService(db)

    try:
        result = await service.get_clinical_record(
            record_id=uuid.UUID(record_id),
            user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clinical record: {str(e)}",
        )

    return ClinicalRecordResponse(**result)


@router.patch(
    "/clinical-records/{record_id}",
    response_model=ClinicalRecordResponse,
    tags=["clinical-records"],
)
async def update_clinical_record(
    record_id: str,
    request: UpdateClinicalRecordRequest,
    current_user: User = Depends(RoleChecker([UserRole.DOCTOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a clinical record with re-encryption.

    Only doctors can update clinical records. Fields are re-encrypted
    with a new data key before storage. Audit log written on update.
    """
    service = ClinicalRecordService(db)

    try:
        result = await service.update_clinical_record(
            record_id=uuid.UUID(record_id),
            user=current_user,
            notes=request.notes,
            diagnosis=request.diagnosis,
            prescriptions=request.prescriptions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update clinical record: {str(e)}",
        )

    return ClinicalRecordResponse(**result)


@router.get(
    "/clinical-records/by-patient/{patient_id}",
    response_model=list[ClinicalRecordResponse],
    tags=["clinical-records"],
)
async def get_records_by_patient(
    patient_id: str,
    current_user: User = Depends(
        RoleChecker([UserRole.DOCTOR, UserRole.PATIENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.EXECUTIVE])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all clinical records for a patient.

    - Doctors: full decryption of all fields
    - Patients: can view own records (redacted)
    - Staff: can view records (redacted)
    - Audit log written for doctor access
    """
    service = ClinicalRecordService(db)

    try:
        results = await service.get_records_by_patient(
            patient_id=uuid.UUID(patient_id),
            user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve patient records: {str(e)}",
        )

    return [ClinicalRecordResponse(**r) for r in results]


@router.patch(
    "/clinical-records/{record_id}/release-lab-results",
    response_model=ClinicalRecordResponse,
    tags=["clinical-records"],
)
async def release_lab_results(
    record_id: str,
    request: ReleaseLabResultsRequest,
    current_user: User = Depends(RoleChecker([UserRole.DOCTOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Release lab results to patient (FR-008).

    Only doctors can release lab results. The lab results are encrypted
    before being written to the database. Audit log written on release.
    """
    service = ClinicalRecordService(db)

    try:
        result = await service.release_lab_results(
            record_id=uuid.UUID(record_id),
            user=current_user,
            lab_results=request.lab_results,
            released=request.released,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release lab results: {str(e)}",
        )

    return ClinicalRecordResponse(**result)
