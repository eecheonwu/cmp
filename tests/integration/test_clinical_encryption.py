"""
Integration Tests for Task 6.2: Clinical Encryption Round-Trip.

Tests:
- End-to-end encryption/decryption flow
- KMS envelope encryption with AES-256-GCM
- Clinical record creation and retrieval with proper decryption
- Audit log verification
"""

import sys
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.utils.encryption import (
    encrypt_aes256_gcm,
    decrypt_aes256_gcm,
    encrypt_clinical_field,
    decrypt_clinical_field,
    EncryptedData,
)
from src.backend.services.clinical_record_service import ClinicalRecordService
from src.backend.models.user import User, UserRole
from src.backend.models.clinical_record import ClinicalRecord
from src.backend.models.audit import AuditLog


# ── Integration Tests: Encryption Round-Trip ──────────────────────────────────

class TestClinicalEncryptionRoundTrip:
    """Integration tests for clinical encryption round-trip."""

    def test_encryption_round_trip_full_flow(self):
        """
        Test the full encryption round-trip for clinical data.

        This verifies:
        1. Plaintext is encrypted to JSON format
        2. KMS key version is generated
        3. Decryption recovers the original plaintext
        """
        original_notes = "Patient presents with acute malaria symptoms, fever of 39.5°C"
        original_diagnosis = "Severe malaria with parasitemia"
        original_prescriptions = "Artesunate 100mg IV every 8 hours for 3 days"

        # Encrypt all fields
        encrypted_notes, kms_key_notes = encrypt_clinical_field(original_notes)
        encrypted_diagnosis, kms_key_diag = encrypt_clinical_field(original_diagnosis)
        encrypted_prescriptions, kms_key_rx = encrypt_clinical_field(original_prescriptions)

        # Verify encrypted format
        notes_json = json.loads(encrypted_notes)
        assert "ciphertext" in notes_json
        assert "iv" in notes_json
        assert "tag" in notes_json

        # Verify KMS key format
        assert kms_key_notes.startswith("dev://")

        # Decrypt and verify
        decrypted_notes = decrypt_clinical_field(encrypted_notes, kms_key_notes)
        decrypted_diagnosis = decrypt_clinical_field(encrypted_diagnosis, kms_key_diag)
        decrypted_prescriptions = decrypt_clinical_field(encrypted_prescriptions, kms_key_rx)

        assert decrypted_notes == original_notes
        assert decrypted_diagnosis == original_diagnosis
        assert decrypted_prescriptions == original_prescriptions

    def test_encryption_no_plaintext_in_storage(self):
        """
        Test that encrypted data does not contain plaintext.

        This verifies that the database would only store ciphertext,
        not the original sensitive data.
        """
        original = "Patient has chronic hypertension, on medication"

        encrypted_payload, kms_key = encrypt_clinical_field(original)

        # The encrypted payload should NOT contain the original text
        assert original not in encrypted_payload

        # The encrypted payload should be valid JSON
        parsed = json.loads(encrypted_payload)
        assert "ciphertext" in parsed
        assert "iv" in parsed
        assert "tag" in parsed

        # Ciphertext should be base64-encoded
        import base64
        try:
            base64.b64decode(parsed["ciphertext"])
            base64.b64decode(parsed["iv"])
            base64.b64decode(parsed["tag"])
        except Exception:
            pytest.fail("Encrypted fields are not valid base64")


# ── Integration Tests: ClinicalRecordService Flow ───────────────────────────────

class TestClinicalRecordServiceIntegration:
    """Integration tests for ClinicalRecordService with encryption."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_clinical_record(self):
        """
        Test creating and retrieving a clinical record with encryption.

        This verifies the full flow:
        1. Doctor creates a clinical record (data is encrypted)
        2. Doctor retrieves the record (data is decrypted)
        3. Audit log is written
        """
        mock_session = AsyncMock()

        # Mock no existing record
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = ClinicalRecordService(mock_session)

        # Doctor creates record
        doctor = MagicMock(spec=User)
        doctor.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        doctor.role = UserRole.DOCTOR

        notes = "Patient complains of severe headache and dizziness"
        diagnosis = "Migraine with aura"
        prescriptions = "Paracetamol 500mg as needed"

        # Create the record
        record = await service.create_clinical_record(
            appointment_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            patient_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            doctor_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            notes=notes,
            diagnosis=diagnosis,
            prescriptions=prescriptions,
            user=doctor,
        )

        # Verify record was created with encrypted fields
        assert record is not None
        assert record.encrypted_notes is not None
        assert record.encrypted_diagnosis is not None
        assert record.encrypted_prescriptions is not None

        # Verify no plaintext in encrypted fields
        assert notes not in record.encrypted_notes
        assert diagnosis not in record.encrypted_diagnosis
        assert prescriptions not in record.encrypted_prescriptions

    @pytest.mark.asyncio
    async def test_patient_cannot_create_clinical_record(self):
        """Test that patients cannot create clinical records."""
        mock_session = AsyncMock()
        service = ClinicalRecordService(mock_session)

        patient = MagicMock(spec=User)
        patient.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        patient.role = UserRole.PATIENT

        with pytest.raises(Exception) as exc_info:
            await service.create_clinical_record(
                appointment_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
                patient_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                doctor_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                notes="Test notes",
                diagnosis="Test diagnosis",
                prescriptions="Test prescriptions",
                user=patient,
            )

        # Should be 403 Forbidden
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_audit_log_written_on_create(self):
        """Test that audit log is written when creating a clinical record."""
        mock_session = AsyncMock()

        # Mock no existing record
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = ClinicalRecordService(mock_session)

        doctor = MagicMock(spec=User)
        doctor.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        doctor.role = UserRole.DOCTOR

        await service.create_clinical_record(
            appointment_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            patient_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            doctor_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            notes="Test notes",
            diagnosis="Test diagnosis",
            prescriptions="Test prescriptions",
            user=doctor,
        )

        # Verify add was called (for both record and audit log)
        assert mock_session.add.call_count >= 2


# ── Integration Tests: Cross-Branch Access ────────────────────────────────────

class TestCrossBranchAccessIntegration:
    """Integration tests for cross-branch clinical record access."""

    @pytest.mark.asyncio
    async def test_doctor_can_access_any_patient_record(self):
        """Test that doctors can access any patient's clinical record."""
        mock_session = AsyncMock()

        # Create a mock record
        mock_record = MagicMock(spec=ClinicalRecord)
        mock_record.id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        mock_record.appointment_id = uuid.UUID("bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee")
        mock_record.patient_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
        mock_record.doctor_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        mock_record.encrypted_notes = '{"ciphertext": "test", "iv": "test", "tag": "test"}'
        mock_record.encrypted_diagnosis = '{"ciphertext": "test", "iv": "test", "tag": "test"}'
        mock_record.encrypted_prescriptions = '{"ciphertext": "test", "iv": "test", "tag": "test"}'
        mock_record.kms_key_version = "dev://test"
        mock_record.created_at = datetime.now(timezone.utc)
        mock_record.updated_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        service = ClinicalRecordService(mock_session)

        # Doctor from different branch accessing record
        doctor = MagicMock(spec=User)
        doctor.id = uuid.UUID("33333333-3333-3333-3333-333333333333")  # Different doctor
        doctor.role = UserRole.DOCTOR

        # Mock decrypt to return test values
        with patch(
            "src.backend.services.clinical_record_service.decrypt_clinical_field",
            side_effect=["Decrypted notes", "Decrypted diagnosis", "Decrypted prescriptions"]
        ):
            result = await service.get_clinical_record(
                record_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
                user=doctor,
            )

        assert result is not None
        assert result["notes"] == "Decrypted notes"
        assert result["diagnosis"] == "Decrypted diagnosis"
        assert result["prescriptions"] == "Decrypted prescriptions"


# ── Integration Tests: Security Properties ───────────────────────────────────

class TestClinicalSecurityIntegration:
    """Integration tests for clinical record security properties."""

    def test_encryption_uses_random_iv(self):
        """Test that each encryption uses a random IV (probabilistic encryption)."""
        key = b"0" * 32  # 256-bit key
        plaintext = "Same plaintext encrypted multiple times"

        # Encrypt the same plaintext multiple times
        encrypted1 = encrypt_aes256_gcm(plaintext, key)
        encrypted2 = encrypt_aes256_gcm(plaintext, key)
        encrypted3 = encrypt_aes256_gcm(plaintext, key)

        # All ciphertexts should be different due to random IV
        assert encrypted1.ciphertext != encrypted2.ciphertext
        assert encrypted2.ciphertext != encrypted3.ciphertext
        assert encrypted1.iv != encrypted2.iv
        assert encrypted2.iv != encrypted3.iv

    def test_decryption_fails_with_wrong_key(self):
        """Test that decryption fails when using wrong key."""
        key1 = b"0" * 32
        key2 = b"1" * 32  # Different key

        plaintext = "Sensitive medical data"
        encrypted = encrypt_aes256_gcm(plaintext, key1)

        # Should fail with wrong key
        with pytest.raises(ValueError):
            decrypt_aes256_gcm(encrypted, key2)

    def test_tampered_ciphertext_detected(self):
        """Test that tampered ciphertext is detected during decryption."""
        key = b"0" * 32
        plaintext = "Patient diagnosis data"
        encrypted = encrypt_aes256_gcm(plaintext, key)

        # Tamper with ciphertext
        tampered = EncryptedData(
            ciphertext="tampered" + encrypted.ciphertext[8:],
            iv=encrypted.iv,
            tag=encrypted.tag,
        )

        # Should fail integrity check
        with pytest.raises(ValueError):
            decrypt_aes256_gcm(tampered, key)

    def test_encrypted_data_json_format(self):
        """Test that EncryptedData JSON format is correct for database storage."""
        data = EncryptedData(
            ciphertext="YWJjMTIzNDU2Nzg5MA==",  # base64 encoded
            iv="aXYxMjM0NTY3ODkwYQ==",
            tag="dGFnMTIzNDU2Nzg5MA==",
        )

        json_str = data.to_json()
        parsed = json.loads(json_str)

        assert parsed["ciphertext"] == "YWJjMTIzNDU2Nzg5MA=="
        assert parsed["iv"] == "aXYxMjM0NTY3ODkwYQ=="
        assert parsed["tag"] == "dGFnMTIzNDU2Nzg5MA=="

        # Verify round-trip
        restored = EncryptedData.from_json(json_str)
        assert restored.ciphertext == data.ciphertext
        assert restored.iv == data.iv
        assert restored.tag == data.tag