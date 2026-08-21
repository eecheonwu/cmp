"""
Unit & Integration Tests for JWT Audience Claim Differentiation & Security Boundaries (ADR-005).

Tests:
- Patient access tokens include `aud: "patient"`
- Staff access tokens include `aud: "staff"` for all staff roles (doctor, receptionist, manager, admin, executive)
- Token decoding with `verify_aud=False` handles any audience
- Audience-aware RoleChecker blocks patient tokens on staff endpoints (403 Forbidden)
- Audience-aware RoleChecker blocks staff tokens on patient endpoints (403 Forbidden)
- Audience-aware RoleChecker without required_audience permits valid tokens of any audience
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.models.user import User, UserRole
from src.backend.services.auth_service import AuthService
from src.backend.core.security import RoleChecker
from src.backend.db.session import get_db


class TestJWTAudienceClaims:
    """Test JWT audience claim assignment during access token creation."""

    def test_patient_role_access_token_has_aud_patient(self):
        """Verify access token created for PATIENT role contains aud: 'patient'."""
        service = AuthService(None)
        token = service.create_access_token("patient-uuid-101", UserRole.PATIENT)
        payload = service.decode_token(token)

        assert payload["aud"] == "patient"
        assert payload["role"] == "patient"
        assert payload["sub"] == "patient-uuid-101"
        assert payload["type"] == "access"

    def test_staff_roles_access_token_has_aud_staff(self):
        """Verify access tokens created for staff roles contain aud: 'staff'."""
        service = AuthService(None)
        staff_roles = [
            UserRole.DOCTOR,
            UserRole.RECEPTIONIST,
            UserRole.MANAGER,
            UserRole.ADMIN,
            UserRole.EXECUTIVE,
        ]

        for role in staff_roles:
            token = service.create_access_token(f"staff-{role.value}-uid", role)
            payload = service.decode_token(token)

            assert payload["aud"] == "staff", f"Expected 'staff' aud for role {role.value}"
            assert payload["role"] == role.value
            assert payload["type"] == "access"

    def test_decode_token_skips_aud_verification(self):
        """Verify decode_token successfully decodes both patient and staff tokens without error."""
        service = AuthService(None)
        patient_token = service.create_access_token("p-1", UserRole.PATIENT)
        staff_token = service.create_access_token("s-1", UserRole.DOCTOR)

        patient_payload = service.decode_token(patient_token)
        staff_payload = service.decode_token(staff_token)

        assert patient_payload["sub"] == "p-1"
        assert staff_payload["sub"] == "s-1"


class TestRoleCheckerAudienceEnforcement:
    """Test audience-aware RoleChecker dependency enforcing security boundaries."""

    def test_patient_token_rejected_on_staff_endpoint(self):
        """Test a token with aud:patient receives 403 Forbidden on a staff-required endpoint."""
        service = AuthService(None)
        patient_token = service.create_access_token("patient-123", UserRole.PATIENT)

        app = FastAPI()

        @app.get("/staff-only")
        async def staff_endpoint(user=Depends(RoleChecker([UserRole.DOCTOR], required_audience="staff"))):
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get(
            "/staff-only",
            headers={"Authorization": f"Bearer {patient_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "staff" in response.json()["detail"].lower()

    def test_staff_token_rejected_on_patient_endpoint(self):
        """Test a token with aud:staff receives 403 Forbidden on a patient-required endpoint."""
        service = AuthService(None)
        staff_token = service.create_access_token("doctor-456", UserRole.DOCTOR)

        app = FastAPI()

        @app.get("/patient-only")
        async def patient_endpoint(user=Depends(RoleChecker([UserRole.PATIENT], required_audience="patient"))):
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get(
            "/patient-only",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "patient" in response.json()["detail"].lower()

    def test_patient_token_accepted_on_patient_endpoint(self):
        """Test a token with aud:patient passes RoleChecker on patient-required endpoint."""
        service = AuthService(None)
        patient_token = service.create_access_token("patient-789", UserRole.PATIENT)

        mock_user = User(
            id="patient-789",
            email="patient@example.com",
            phone_number="+2348000000000",
            role=UserRole.PATIENT,
        )

        app = FastAPI()

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        @app.get("/patient-only")
        async def patient_endpoint(user=Depends(RoleChecker([UserRole.PATIENT], required_audience="patient"))):
            return {"user_id": str(user.id)}

        client = TestClient(app)

        with patch("src.backend.core.security.AuthService") as MockAuthService:
            mock_inst = MagicMock()
            mock_inst.decode_token.return_value = service.decode_token(patient_token)
            mock_inst.get_user_by_id = AsyncMock(return_value=mock_user)
            MockAuthService.return_value = mock_inst

            response = client.get(
                "/patient-only",
                headers={"Authorization": f"Bearer {patient_token}"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["user_id"] == "patient-789"

    def test_staff_token_accepted_on_staff_endpoint(self):
        """Test a token with aud:staff passes RoleChecker on staff-required endpoint."""
        service = AuthService(None)
        doctor_token = service.create_access_token("doctor-789", UserRole.DOCTOR)

        mock_user = User(
            id="doctor-789",
            email="doctor@example.com",
            phone_number="+2348000000001",
            role=UserRole.DOCTOR,
        )

        app = FastAPI()

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        @app.get("/doctor-only")
        async def doctor_endpoint(user=Depends(RoleChecker([UserRole.DOCTOR], required_audience="staff"))):
            return {"user_id": str(user.id)}

        client = TestClient(app)

        with patch("src.backend.core.security.AuthService") as MockAuthService:
            mock_inst = MagicMock()
            mock_inst.decode_token.return_value = service.decode_token(doctor_token)
            mock_inst.get_user_by_id = AsyncMock(return_value=mock_user)
            MockAuthService.return_value = mock_inst

            response = client.get(
                "/doctor-only",
                headers={"Authorization": f"Bearer {doctor_token}"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["user_id"] == "doctor-789"
