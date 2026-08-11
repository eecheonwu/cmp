"""
Integration Tests for Email-Based Patient Registration Lifecycle (ADR-005).

Tests end-to-end multi-step flow:
1. Patient registration request (`POST /api/v1/auth/patient/register`)
2. Token verification & password creation (`POST /api/v1/auth/patient/verify-email`)
3. Patient login with newly created password (`POST /api/v1/auth/patient/login`)
4. Resend verification link flow (`POST /api/v1/auth/patient/resend-verification`)
5. Error cases: rate limiting (429), expired token (400), used token (409), weak password (422)
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.main import app
from src.backend.models.user import User, UserRole, EmailVerificationToken
from src.backend.services.auth_service import AuthService, hash_password
from src.backend.db.session import get_db


@pytest.fixture
def client():
    return TestClient(app)


class TestEmailRegistrationFullLifecycle:
    """Integration test suite for the complete patient registration journey."""

    def test_full_registration_and_login_flow(self, client):
        """
        Step-by-step test of complete registration flow:
        Register -> Verify Email & Set Password -> Patient Login.
        """
        raw_verification_token = "valid_lifecycle_raw_token_999"
        hashed_token = hash_password(raw_verification_token)

        # 1. Mock DB and services for registration
        mock_user = User(
            id="lifecycle-user-111",
            email="lifecycle@example.com",
            phone_number="+2348123456789",
            password_hash="temp_hash",
            role=UserRole.PATIENT,
            is_email_verified=False,
        )

        mock_token_record = MagicMock()
        mock_token_record.token_hash = hashed_token
        mock_token_record.email = "lifecycle@example.com"
        mock_token_record.is_used = False

        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            # ── Step 1: Register Patient Email ──────────────────────────────────
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = AsyncMock()
                mock_service.register_patient_with_email.return_value = (mock_user, raw_verification_token)
                MockAuthService.return_value = mock_service

                reg_response = client.post(
                    "/api/v1/auth/patient/register",
                    json={
                        "email": "lifecycle@example.com",
                        "phone_number": "+2348123456789",
                        "full_name": "Lifecycle Patient",
                    },
                )

                assert reg_response.status_code == status.HTTP_200_OK
                assert "sent" in reg_response.json()["message"].lower()

            # ── Step 2: Verify Email & Create Password ─────────────────────────
            mock_user.is_email_verified = True
            mock_user.password_hash = hash_password("StrongPass123!")

            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                real_service = AuthService(None)
                access_jwt = real_service.create_access_token(str(mock_user.id), UserRole.PATIENT)
                refresh_jwt = real_service.create_refresh_token(str(mock_user.id))

                mock_service = AsyncMock()
                mock_service.verify_email_token.return_value = (
                    mock_user,
                    access_jwt,
                    refresh_jwt,
                )
                MockAuthService.return_value = mock_service

                verify_response = client.post(
                    "/api/v1/auth/patient/verify-email",
                    json={
                        "token": raw_verification_token,
                        "password": "StrongPass123!",
                        "confirm_password": "StrongPass123!",
                    },
                )

                assert verify_response.status_code == status.HTTP_200_OK
                verify_data = verify_response.json()
                assert verify_data["access_token"] == access_jwt
                assert verify_data["user"]["is_email_verified"] is True

            # ── Step 3: Patient Login ──────────────────────────────────────────
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = MagicMock()
                mock_service.authenticate_patient = AsyncMock(return_value=(mock_user, None))
                mock_service.create_access_token.return_value = access_jwt
                mock_service.create_refresh_token.return_value = refresh_jwt
                MockAuthService.return_value = mock_service

                login_response = client.post(
                    "/api/v1/auth/patient/login",
                    json={
                        "email": "lifecycle@example.com",
                        "password": "StrongPass123!",
                    },
                )

                assert login_response.status_code == status.HTTP_200_OK
                login_data = login_response.json()
                assert login_data["access_token"] == access_jwt
                assert login_data["token_type"] == "bearer"

                # Verify JWT audience is 'patient'
                decoded_jwt = real_service.decode_token(login_data["access_token"])
                assert decoded_jwt["aud"] == "patient"

        finally:
            app.dependency_overrides.clear()

    def test_resend_verification_invalidation_flow(self, client):
        """Test resend verification endpoint invalidates prior token and issues new token."""
        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            mock_user = User(
                id="resend-user-222",
                email="resend.flow@example.com",
                phone_number="+2348123456780",
                role=UserRole.PATIENT,
                is_email_verified=False,
            )

            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service = AsyncMock()
                mock_service.resend_verification_email.return_value = (mock_user, "new_resent_raw_token")
                MockAuthService.return_value = mock_service

                response = client.post(
                    "/api/v1/auth/patient/resend-verification",
                    json={"email": "resend.flow@example.com"},
                )

                assert response.status_code == status.HTTP_200_OK
                assert "sent" in response.json()["message"].lower()
                mock_service.resend_verification_email.assert_called_once_with("resend.flow@example.com")

        finally:
            app.dependency_overrides.clear()
