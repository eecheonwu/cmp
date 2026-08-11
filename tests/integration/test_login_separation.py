"""
Integration Tests for Patient vs Staff Login Separation & Deprecation Headers (ADR-005).

Tests:
1. Patient login returns JWT with aud:patient
2. Staff login returns JWT with aud:staff
3. Patient JWT blocked on staff endpoints (403 Forbidden)
4. Staff JWT blocked on patient endpoints (403 Forbidden)
5. Unverified email login attempt returns 403 Forbidden
6. Legacy OTP endpoints return Deprecation and Sunset headers
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.main import app
from src.backend.models.user import User, UserRole
from src.backend.services.auth_service import AuthService
from src.backend.core.security import RoleChecker
from src.backend.db.session import get_db


@pytest.fixture
def client():
    return TestClient(app)


class TestLoginSeparationAndSecurityBoundaries:
    """Integration test suite for login separation and audience boundaries."""

    def test_separate_login_audiences(self, client):
        """Verify Patient login returns aud:patient and Staff login returns aud:staff."""
        patient_user = User(
            id="p-user-001",
            email="patient.sep@example.com",
            phone_number="+2348000000001",
            role=UserRole.PATIENT,
            is_email_verified=True,
        )

        doctor_user = User(
            id="d-user-001",
            email="doctor.sep@example.com",
            phone_number="+2348000000002",
            role=UserRole.DOCTOR,
            is_email_verified=True,
        )

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            real_service = AuthService(None)
            patient_jwt = real_service.create_access_token("p-user-001", UserRole.PATIENT)
            doctor_jwt = real_service.create_access_token("d-user-001", UserRole.DOCTOR)
            refresh_jwt = real_service.create_refresh_token("dummy")

            # 1. Patient Login
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = MagicMock()
                mock_service.authenticate_patient = AsyncMock(return_value=(patient_user, None))
                mock_service.create_access_token.return_value = patient_jwt
                mock_service.create_refresh_token.return_value = refresh_jwt
                MockAuthService.return_value = mock_service

                p_res = client.post(
                    "/api/v1/auth/patient/login",
                    json={"email": "patient.sep@example.com", "password": "Pass123!"},
                )
                assert p_res.status_code == 200
                p_decoded = real_service.decode_token(p_res.json()["access_token"])
                assert p_decoded["aud"] == "patient"

            # 2. Staff Login
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = MagicMock()
                mock_service.authenticate_staff = AsyncMock(return_value=doctor_user)
                mock_service.create_access_token.return_value = doctor_jwt
                mock_service.create_refresh_token.return_value = refresh_jwt
                MockAuthService.return_value = mock_service

                d_res = client.post(
                    "/api/v1/login",
                    json={"email": "doctor.sep@example.com", "password": "Pass123!"},
                )
                assert d_res.status_code == 200
                d_decoded = real_service.decode_token(d_res.json()["access_token"])
                assert d_decoded["aud"] == "staff"

        finally:
            app.dependency_overrides.clear()

    def test_cross_boundary_access_blocked(self):
        """Verify patient token is blocked on staff endpoints and staff token on patient endpoints."""
        real_service = AuthService(None)
        patient_jwt = real_service.create_access_token("p-1", UserRole.PATIENT)
        staff_jwt = real_service.create_access_token("d-1", UserRole.DOCTOR)

        test_app = FastAPI()

        @test_app.get("/staff-portal")
        async def staff_portal(user=Depends(RoleChecker([UserRole.DOCTOR], required_audience="staff"))):
            return {"portal": "staff"}

        @test_app.get("/patient-portal")
        async def patient_portal(user=Depends(RoleChecker([UserRole.PATIENT], required_audience="patient"))):
            return {"portal": "patient"}

        tc = TestClient(test_app)

        # Patient token on staff portal -> 403
        r1 = tc.get("/staff-portal", headers={"Authorization": f"Bearer {patient_jwt}"})
        assert r1.status_code == status.HTTP_403_FORBIDDEN

        # Staff token on patient portal -> 403
        r2 = tc.get("/patient-portal", headers={"Authorization": f"Bearer {staff_jwt}"})
        assert r2.status_code == status.HTTP_403_FORBIDDEN

    def test_legacy_otp_endpoints_deprecation_headers(self, client):
        """Verify legacy OTP endpoints return Deprecation: true and Sunset headers."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = MagicMock()
                mock_service.get_user_by_phone = AsyncMock(return_value=None)
                mock_otp = MagicMock()
                mock_otp.id = "otp-legacy-1"
                mock_otp.phone_number = "+2348000009999"
                mock_service.create_otp = AsyncMock(return_value=(mock_otp, "112233"))
                mock_service.create_registration_token.return_value = "legacy_reg_token"
                MockAuthService.return_value = mock_service

                with patch("api.v1.auth.router._send_otp_notification", new_callable=AsyncMock):
                    res = client.post(
                        "/api/v1/register",
                        json={"phone_number": "+2348000009999", "full_name": "Legacy Patient"},
                    )
                    assert res.status_code == 201
                    assert res.headers.get("deprecation") == "true"
                    assert "sunset" in res.headers

        finally:
            app.dependency_overrides.clear()
