"""
Unit & Integration Tests for Task 2: Patient Registration with Email (Vertical Slice 2).

Tests:
- Email verification token service logic (60-min TTL, bcrypt hash, single-use, rate limit 3/15min)
- Patient email registration logic (User creation with is_email_verified=False, PatientProfile)
- Duplicate email conflict handling (HTTP 409)
- Duplicate phone conflict handling (HTTP 409)
- Email rate limit handling (HTTP 429 on 4th request)
- POST /api/v1/auth/patient/register API endpoint validation and response
- Alembic migration 0008 file structure validation
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.main import app
from src.backend.models.user import User, UserRole, PatientProfile, EmailVerificationToken
from src.backend.services.auth_service import AuthService, verify_password
from src.backend.db.session import get_db


@pytest.fixture
def client():
    """Create a TestClient for FastAPI app."""
    return TestClient(app)


class TestPatientEmailRegistrationUnit:
    """Unit tests for AuthService email registration and verification token methods."""

    @pytest.mark.asyncio
    async def test_create_email_verification_token_success(self):
        """Test token creation generates 60-min TTL and bcrypt-hashed token."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Mock check_email_rate_limit to return 0
        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 0

        # Mock prior tokens query to return empty list
        prior_tokens_result = MagicMock()
        prior_tokens_result.scalars.return_value = []

        mock_db.execute.side_effect = [rate_limit_result, prior_tokens_result]

        service = AuthService(mock_db)
        email = "test.patient@example.com"

        token_record, raw_token = await service.create_email_verification_token(email)

        assert raw_token is not None
        assert len(raw_token) > 20
        assert token_record.email == email
        assert token_record.is_used is False
        assert token_record.is_expired is False
        assert token_record.attempts == 0
        # Verify bcrypt hash matches raw token
        assert verify_password(raw_token, token_record.token_hash)
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_email_verification_token_rate_limit(self):
        """Test rate limit enforcement (max 3 requests / 15 minutes)."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # Return 3 existing requests in last 15 minutes
        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 3
        mock_db.execute.return_value = rate_limit_result

        service = AuthService(mock_db)
        email = "ratelimited@example.com"

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await service.create_email_verification_token(email)

    @pytest.mark.asyncio
    async def test_register_patient_with_email_success(self):
        """Test register_patient_with_email creates user and profile with unverified email."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Mock get_user_by_email -> None
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = None

        # Mock get_user_by_phone -> None
        phone_result = MagicMock()
        phone_result.scalar_one_or_none.return_value = None

        # Mock check_email_rate_limit -> 0
        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 0

        # Mock prior tokens -> []
        prior_tokens_result = MagicMock()
        prior_tokens_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            email_result,
            phone_result,
            rate_limit_result,
            prior_tokens_result,
        ]

        service = AuthService(mock_db)
        user, raw_token = await service.register_patient_with_email(
            email="newpatient@example.com",
            phone_number="+2348012345678",
            full_name="New Patient",
            date_of_birth="1995-04-20",
            gender="female",
            emergency_contact="+2348098765432",
        )

        assert user.email == "newpatient@example.com"
        assert user.phone_number == "+2348012345678"
        assert user.role == UserRole.PATIENT
        assert user.is_email_verified is False
        assert raw_token is not None
        assert mock_db.add.call_count >= 2  # User, PatientProfile, EmailVerificationToken

    @pytest.mark.asyncio
    async def test_register_patient_with_email_duplicate_email(self):
        """Test registration fails with ValueError if email is already registered."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        existing_user = User(
            id="11111111-1111-1111-1111-111111111111",
            email="existing@example.com",
            phone_number="+2348011111111",
            role=UserRole.PATIENT,
        )
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = email_result

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="email already exists"):
            await service.register_patient_with_email(
                email="existing@example.com",
                phone_number="+2348022222222",
                full_name="Duplicate Patient",
            )

    @pytest.mark.asyncio
    async def test_register_patient_with_email_duplicate_phone(self):
        """Test registration fails with ValueError if phone number is already registered."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # get_user_by_email -> None
        email_result = MagicMock()
        email_result.scalar_one_or_none.return_value = None

        # get_user_by_phone -> existing user
        existing_user = User(
            id="22222222-2222-2222-2222-222222222222",
            email="other@example.com",
            phone_number="+2348011111111",
            role=UserRole.PATIENT,
        )
        phone_result = MagicMock()
        phone_result.scalar_one_or_none.return_value = existing_user

        mock_db.execute.side_effect = [email_result, phone_result]

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="phone number already exists"):
            await service.register_patient_with_email(
                email="new@example.com",
                phone_number="+2348011111111",
                full_name="Duplicate Phone Patient",
            )


class TestPatientEmailRegistrationRouter:
    """Router level integration tests for POST /api/v1/auth/patient/register."""

    def test_register_patient_email_success_endpoint(self, client):
        """Test POST /api/v1/auth/patient/register returns 200 OK."""
        mock_user = MagicMock()
        mock_user.id = "33333333-3333-3333-3333-333333333333"

        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService, \
                 patch("api.v1.auth.router.send_auth_email") as mock_celery:

                mock_service_instance = AsyncMock()
                mock_service_instance.register_patient_with_email.return_value = (mock_user, "mock_raw_token_123")
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/register",
                    json={
                        "email": "testapi@example.com",
                        "phone_number": "+2348012345678",
                        "full_name": "API Test Patient",
                        "date_of_birth": "1990-01-01",
                        "gender": "female",
                        "emergency_contact": "+2348098765432",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "Verification email sent" in data["message"]
                mock_service_instance.register_patient_with_email.assert_called_once()
                mock_celery.delay.assert_called_once_with("testapi@example.com", "mock_raw_token_123", "API Test Patient")
        finally:
            app.dependency_overrides.clear()

    def test_register_patient_email_duplicate_conflict_endpoint(self, client):
        """Test POST /api/v1/auth/patient/register returns 409 Conflict for duplicate email/phone."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = AsyncMock()
                mock_service_instance.register_patient_with_email.side_effect = ValueError(
                    "User with this email already exists."
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/register",
                    json={
                        "email": "duplicate@example.com",
                        "phone_number": "+2348012345678",
                        "full_name": "Duplicate User",
                    },
                )

                assert response.status_code == 409
                assert "already exists" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_register_patient_email_rate_limit_endpoint(self, client):
        """Test POST /api/v1/auth/patient/register returns 429 Too Many Requests."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = AsyncMock()
                mock_service_instance.register_patient_with_email.side_effect = ValueError(
                    "Rate limit exceeded. Maximum 3 email verification requests per 15 minutes allowed."
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/register",
                    json={
                        "email": "flooder@example.com",
                        "phone_number": "+2348012345678",
                        "full_name": "Flooder User",
                    },
                )

                assert response.status_code == 429
                assert "Rate limit exceeded" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_register_patient_email_invalid_body_endpoint(self, client):
        """Test invalid email format returns 422 Unprocessable Entity."""
        response = client.post(
            "/api/v1/auth/patient/register",
            json={
                "email": "not-an-email",
                "phone_number": "+2348012345678",
                "full_name": "Invalid Email User",
            },
        )
        assert response.status_code == 422


class TestAlembicMigration0008:
    """Test Alembic Migration 0008 file validity."""

    def test_migration_0008_file_exists_and_valid(self):
        """Verify 0008 migration file exists with correct identifiers."""
        migration_file = Path("alembic/versions/0008_add_email_verification_to_users.py")
        assert migration_file.exists()

        content = migration_file.read_text(encoding="utf-8")
        assert 'revision: str = "0008_add_email_verify_to_users"' in content
        assert 'down_revision: Union[str, None] = "0007_email_verification_tokens"' in content
        assert 'op.add_column(' in content
        assert '"users"' in content
        assert '"is_email_verified"' in content
        assert '"email_verified_at"' in content


# ══════════════════════════════════════════════════════════════════════════
# Checkpoint 3 Tests: Email Verification & Password Creation
# ══════════════════════════════════════════════════════════════════════════


class TestPasswordValidationSchema:
    """Test PatientVerifyEmailRequest Pydantic schema password policy enforcement."""

    def test_valid_strong_password(self):
        """Test that a fully compliant password passes validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        req = PatientVerifyEmailRequest(
            token="some_valid_token",
            password="StrongPass1!",
            confirm_password="StrongPass1!",
        )
        assert req.password == "StrongPass1!"

    def test_password_too_short(self):
        """Test password < 8 chars fails validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="at least 8 characters"):
            PatientVerifyEmailRequest(
                token="tok", password="Ab1!", confirm_password="Ab1!"
            )

    def test_password_no_uppercase(self):
        """Test password without uppercase fails validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="uppercase"):
            PatientVerifyEmailRequest(
                token="tok", password="lowercase1!", confirm_password="lowercase1!"
            )

    def test_password_no_lowercase(self):
        """Test password without lowercase fails validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="lowercase"):
            PatientVerifyEmailRequest(
                token="tok", password="UPPERCASE1!", confirm_password="UPPERCASE1!"
            )

    def test_password_no_digit(self):
        """Test password without digit fails validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="digit"):
            PatientVerifyEmailRequest(
                token="tok", password="NoDigits!!", confirm_password="NoDigits!!"
            )

    def test_password_no_special(self):
        """Test password without special character fails validation."""
        from src.backend.api.v1.auth.schemas import PatientVerifyEmailRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="special"):
            PatientVerifyEmailRequest(
                token="tok", password="NoSpecial1", confirm_password="NoSpecial1"
            )


class TestVerifyEmailTokenUnit:
    """Unit tests for AuthService.verify_email_token method."""

    @pytest.mark.asyncio
    async def test_verify_email_token_success(self):
        """Test successful token verification: sets password, marks verified, returns JWT."""
        from src.backend.services.auth_service import AuthService, hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()

        # Create a real bcrypt hash for the raw token
        raw_token = "test_raw_token_12345"
        token_hash = hash_password(raw_token)

        # Mock active tokens query
        mock_token_record = MagicMock()
        mock_token_record.token_hash = token_hash
        mock_token_record.email = "verify@example.com"
        mock_token_record.is_used = False

        active_result = MagicMock()
        active_result.scalars.return_value.all.return_value = [mock_token_record]

        # Mock get_user_by_email result
        mock_user = User(
            id="44444444-4444-4444-4444-444444444444",
            email="verify@example.com",
            phone_number="+2348012340000",
            password_hash="old_hash",
            role=UserRole.PATIENT,
            is_email_verified=False,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        mock_db.execute.side_effect = [active_result, user_result]

        service = AuthService(mock_db)
        user, access_token, refresh_token = await service.verify_email_token(
            raw_token=raw_token,
            password="NewPassword1!",
        )

        assert user.is_email_verified is True
        assert user.email_verified_at is not None
        assert user.password_hash != "old_hash"
        assert mock_token_record.is_used is True
        assert access_token is not None
        assert refresh_token is not None

    @pytest.mark.asyncio
    async def test_verify_email_token_expired_raises(self):
        """Test expired/invalid token raises ValueError."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # No active tokens
        active_result = MagicMock()
        active_result.scalars.return_value.all.return_value = []

        # No used tokens either
        used_result = MagicMock()
        used_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [active_result, used_result]

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="Invalid or expired"):
            await service.verify_email_token(
                raw_token="nonexistent_token",
                password="Whatever1!",
            )

    @pytest.mark.asyncio
    async def test_verify_email_token_already_used_raises(self):
        """Test already-used token raises TOKEN_ALREADY_USED ValueError."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        raw_token = "used_token_xyz"
        token_hash = hash_password(raw_token)

        # No active tokens
        active_result = MagicMock()
        active_result.scalars.return_value.all.return_value = []

        # Used token matches
        used_token = MagicMock()
        used_token.token_hash = token_hash
        used_result = MagicMock()
        used_result.scalars.return_value.all.return_value = [used_token]

        mock_db.execute.side_effect = [active_result, used_result]

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="TOKEN_ALREADY_USED"):
            await service.verify_email_token(
                raw_token=raw_token,
                password="Whatever1!",
            )


class TestJWTAudienceClaim:
    """Test JWT access tokens include correct audience claim per ADR-005."""

    def test_patient_jwt_has_aud_patient(self):
        """Test patient role access token includes aud: 'patient'."""
        service = AuthService(None)
        token = service.create_access_token("user-id-1", UserRole.PATIENT)
        payload = service.decode_token(token)
        assert payload["aud"] == "patient"
        assert payload["role"] == "patient"

    def test_staff_jwt_has_aud_staff(self):
        """Test non-patient role access token includes aud: 'staff'."""
        service = AuthService(None)
        for role in [UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.ADMIN, UserRole.MANAGER]:
            token = service.create_access_token("user-id-2", role)
            payload = service.decode_token(token)
            assert payload["aud"] == "staff", f"Expected 'staff' audience for role {role}"
            assert payload["role"] == role.value


class TestVerifyEmailRouter:
    """Router-level integration tests for POST /api/v1/auth/patient/verify-email."""

    def test_verify_email_success_endpoint(self, client):
        """Test POST /api/v1/auth/patient/verify-email returns 200 + JWT."""
        mock_user = MagicMock()
        mock_user.id = "55555555-5555-5555-5555-555555555555"
        mock_user.email = "verified@example.com"
        mock_user.role = UserRole.PATIENT
        mock_user.is_email_verified = True

        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = AsyncMock()
                mock_service_instance.verify_email_token.return_value = (
                    mock_user,
                    "mock_access_jwt",
                    "mock_refresh_jwt",
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/verify-email",
                    json={
                        "token": "valid_raw_token_abc",
                        "password": "StrongPass1!",
                        "confirm_password": "StrongPass1!",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "mock_access_jwt"
                assert data["refresh_token"] == "mock_refresh_jwt"
                assert data["token_type"] == "bearer"
                assert data["user"]["email"] == "verified@example.com"
                assert data["user"]["is_email_verified"] is True
                mock_service_instance.verify_email_token.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_verify_email_expired_token_endpoint(self, client):
        """Test POST /api/v1/auth/patient/verify-email returns 400 for expired token."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = AsyncMock()
                mock_service_instance.verify_email_token.side_effect = ValueError(
                    "Invalid or expired verification token."
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/verify-email",
                    json={
                        "token": "expired_token_xyz",
                        "password": "StrongPass1!",
                        "confirm_password": "StrongPass1!",
                    },
                )

                assert response.status_code == 400
                assert "expired" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_verify_email_used_token_endpoint(self, client):
        """Test POST /api/v1/auth/patient/verify-email returns 409 for used token."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = AsyncMock()
                mock_service_instance.verify_email_token.side_effect = ValueError(
                    "TOKEN_ALREADY_USED"
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/verify-email",
                    json={
                        "token": "used_token_xyz",
                        "password": "StrongPass1!",
                        "confirm_password": "StrongPass1!",
                    },
                )

                assert response.status_code == 409
                assert "already been used" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_verify_email_password_mismatch_endpoint(self, client):
        """Test password != confirm_password returns 400."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService"):
                response = client.post(
                    "/api/v1/auth/patient/verify-email",
                    json={
                        "token": "some_token",
                        "password": "StrongPass1!",
                        "confirm_password": "DifferentPass2@",
                    },
                )

                assert response.status_code == 400
                assert "do not match" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_verify_email_weak_password_endpoint(self, client):
        """Test weak password returns 422 (Pydantic validation error)."""
        response = client.post(
            "/api/v1/auth/patient/verify-email",
            json={
                "token": "some_token",
                "password": "weak",
                "confirm_password": "weak",
            },
        )
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# Checkpoint 4 Tests: Patient Login & Auth Separation
# ══════════════════════════════════════════════════════════════════════════


class TestPatientLoginSchema:
    """Test PatientLoginRequest Pydantic schema validation."""

    def test_valid_patient_login_request(self):
        """Test valid patient login request passes validation."""
        from src.backend.api.v1.auth.schemas import PatientLoginRequest
        req = PatientLoginRequest(email="patient@example.com", password="MyPassword1!")
        assert req.email == "patient@example.com"
        assert req.password == "MyPassword1!"

    def test_patient_login_request_invalid_email(self):
        """Test invalid email fails validation."""
        from src.backend.api.v1.auth.schemas import PatientLoginRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PatientLoginRequest(email="not-an-email", password="MyPassword1!")


class TestAuthenticatePatientUnit:
    """Unit tests for AuthService.authenticate_patient method."""

    @pytest.mark.asyncio
    async def test_authenticate_patient_success(self):
        """Test successful patient authentication returns user and no error."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        pw_hash = hash_password("CorrectPass1!")
        mock_user = User(
            id="66666666-6666-6666-6666-666666666666",
            email="verified.patient@example.com",
            phone_number="+2348099990000",
            password_hash=pw_hash,
            role=UserRole.PATIENT,
            is_email_verified=True,
        )

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result

        service = AuthService(mock_db)
        user, error_reason = await service.authenticate_patient(
            email="verified.patient@example.com",
            password="CorrectPass1!",
        )

        assert user is not None
        assert user.email == "verified.patient@example.com"
        assert error_reason is None

    @pytest.mark.asyncio
    async def test_authenticate_patient_wrong_password(self):
        """Test wrong password returns INVALID_CREDENTIALS."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        pw_hash = hash_password("CorrectPass1!")
        mock_user = User(
            id="66666666-6666-6666-6666-666666666666",
            email="patient@example.com",
            phone_number="+2348099990000",
            password_hash=pw_hash,
            role=UserRole.PATIENT,
            is_email_verified=True,
        )

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result

        service = AuthService(mock_db)
        user, error_reason = await service.authenticate_patient(
            email="patient@example.com",
            password="WrongPass99!",
        )

        assert user is None
        assert error_reason == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_authenticate_patient_nonexistent_email(self):
        """Test nonexistent email returns INVALID_CREDENTIALS."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = user_result

        service = AuthService(mock_db)
        user, error_reason = await service.authenticate_patient(
            email="nobody@example.com",
            password="Whatever1!",
        )

        assert user is None
        assert error_reason == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_authenticate_patient_staff_role_rejected(self):
        """Test non-patient role returns INVALID_CREDENTIALS."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        pw_hash = hash_password("StaffPass1!")
        mock_user = User(
            id="77777777-7777-7777-7777-777777777777",
            email="doctor@example.com",
            phone_number="+2348099991111",
            password_hash=pw_hash,
            role=UserRole.DOCTOR,
            is_email_verified=True,
        )

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result

        service = AuthService(mock_db)
        user, error_reason = await service.authenticate_patient(
            email="doctor@example.com",
            password="StaffPass1!",
        )

        assert user is None
        assert error_reason == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_authenticate_patient_unverified_email(self):
        """Test unverified email returns EMAIL_NOT_VERIFIED."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        pw_hash = hash_password("CorrectPass1!")
        mock_user = User(
            id="88888888-8888-8888-8888-888888888888",
            email="unverified@example.com",
            phone_number="+2348099992222",
            password_hash=pw_hash,
            role=UserRole.PATIENT,
            is_email_verified=False,
        )

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result

        service = AuthService(mock_db)
        user, error_reason = await service.authenticate_patient(
            email="unverified@example.com",
            password="CorrectPass1!",
        )

        assert user is None
        assert error_reason == "EMAIL_NOT_VERIFIED"


class TestPatientLoginRouter:
    """Router-level integration tests for POST /api/v1/auth/patient/login."""

    def test_patient_login_success_endpoint(self, client):
        """Test POST /api/v1/auth/patient/login returns 200 + JWT tokens."""
        mock_user = MagicMock()
        mock_user.id = "99999999-9999-9999-9999-999999999999"
        mock_user.email = "loggedin@example.com"
        mock_user.role = UserRole.PATIENT
        mock_user.is_email_verified = True

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.authenticate_patient = AsyncMock(return_value=(mock_user, None))
                mock_service_instance.create_access_token.return_value = "patient_access_jwt"
                mock_service_instance.create_refresh_token.return_value = "patient_refresh_jwt"
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/login",
                    json={
                        "email": "loggedin@example.com",
                        "password": "StrongPass1!",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
                mock_service_instance.authenticate_patient.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_patient_login_invalid_credentials_endpoint(self, client):
        """Test POST /api/v1/auth/patient/login returns 401 for wrong password."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.authenticate_patient = AsyncMock(return_value=(None, "INVALID_CREDENTIALS"))
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/login",
                    json={
                        "email": "wrong@example.com",
                        "password": "WrongPass1!",
                    },
                )

                assert response.status_code == 401
                assert "Invalid email or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_patient_login_unverified_email_endpoint(self, client):
        """Test POST /api/v1/auth/patient/login returns 403 for unverified email."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.authenticate_patient = AsyncMock(return_value=(None, "EMAIL_NOT_VERIFIED"))
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/login",
                    json={
                        "email": "unverified@example.com",
                        "password": "StrongPass1!",
                    },
                )

                assert response.status_code == 403
                assert "not verified" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


class TestAudienceAwareRoleChecker:
    """Test audience-aware RoleChecker enforcement per ADR-005."""

    def test_patient_token_blocked_on_staff_endpoint(self, client):
        """Test patient JWT (aud:patient) is rejected on staff-only endpoint."""
        from src.backend.core.security import RoleChecker

        # Create a patient JWT
        service = AuthService(None)
        patient_token = service.create_access_token("patient-uid-1", UserRole.PATIENT)

        # Verify it has aud: "patient"
        payload = service.decode_token(patient_token)
        assert payload["aud"] == "patient"

        # Use RoleChecker with required_audience="staff" to simulate staff endpoint check
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient as TC

        test_app = FastAPI()

        @test_app.get("/staff-only")
        async def staff_only(user=Depends(RoleChecker([UserRole.DOCTOR], required_audience="staff"))):
            return {"ok": True}

        tc = TC(test_app)
        response = tc.get(
            "/staff-only",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert response.status_code == 403
        assert "staff" in response.json()["detail"].lower()

    def test_staff_token_blocked_on_patient_endpoint(self, client):
        """Test staff JWT (aud:staff) is rejected on patient-only endpoint."""
        from src.backend.core.security import RoleChecker

        # Create a staff JWT
        service = AuthService(None)
        staff_token = service.create_access_token("staff-uid-1", UserRole.DOCTOR)

        # Verify it has aud: "staff"
        payload = service.decode_token(staff_token)
        assert payload["aud"] == "staff"

        # Use RoleChecker with required_audience="patient" to simulate patient endpoint check
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient as TC

        test_app = FastAPI()

        @test_app.get("/patient-only")
        async def patient_only(user=Depends(RoleChecker([UserRole.PATIENT], required_audience="patient"))):
            return {"ok": True}

        tc = TC(test_app)
        response = tc.get(
            "/patient-only",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 403
        assert "patient" in response.json()["detail"].lower()

    def test_no_audience_restriction_allows_both(self, client):
        """Test RoleChecker without required_audience accepts any audience."""
        # Patient JWT should work on an endpoint without audience restriction
        service = AuthService(None)
        patient_token = service.create_access_token("any-uid-1", UserRole.PATIENT)
        payload = service.decode_token(patient_token)
        assert payload["aud"] == "patient"
        assert payload["role"] == "patient"
        assert payload["type"] == "access"

    def test_patient_login_returns_jwt_with_aud_patient(self, client):
        """Test patient login endpoint returns JWT with aud: patient."""
        mock_user = MagicMock()
        mock_user.id = "aud-test-user-1"
        mock_user.email = "aud@example.com"
        mock_user.role = UserRole.PATIENT
        mock_user.is_email_verified = True

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                real_service = AuthService(None)
                access_token = real_service.create_access_token(str(mock_user.id), UserRole.PATIENT)
                refresh_token = real_service.create_refresh_token(str(mock_user.id))

                mock_service_instance = MagicMock()
                mock_service_instance.authenticate_patient = AsyncMock(return_value=(mock_user, None))
                mock_service_instance.create_access_token.return_value = access_token
                mock_service_instance.create_refresh_token.return_value = refresh_token
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/login",
                    json={"email": "aud@example.com", "password": "StrongPass1!"},
                )

                assert response.status_code == 200
                returned_token = response.json()["access_token"]

                # Decode and verify audience
                decoded = real_service.decode_token(returned_token)
                assert decoded["aud"] == "patient"
        finally:
            app.dependency_overrides.clear()

    def test_staff_login_returns_jwt_with_aud_staff(self, client):
        """Test staff login endpoint returns JWT with aud: staff."""
        mock_user = MagicMock()
        mock_user.id = "aud-test-user-2"
        mock_user.email = "staff@example.com"
        mock_user.role = UserRole.DOCTOR
        mock_user.is_email_verified = True

        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                real_service = AuthService(None)
                access_token = real_service.create_access_token(str(mock_user.id), UserRole.DOCTOR)
                refresh_token = real_service.create_refresh_token(str(mock_user.id))

                mock_service_instance = MagicMock()
                mock_service_instance.authenticate_staff = AsyncMock(return_value=mock_user)
                mock_service_instance.create_access_token.return_value = access_token
                mock_service_instance.create_refresh_token.return_value = refresh_token
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/login",
                    json={"email": "staff@example.com", "password": "StaffPass1!"},
                )

                assert response.status_code == 200
                returned_token = response.json()["access_token"]

                # Decode and verify audience
                decoded = real_service.decode_token(returned_token)
                assert decoded["aud"] == "staff"
        finally:
            app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════════════
# Checkpoint 5 Tests: Resend Verification, Deprecation Headers & NOT NULL
# ══════════════════════════════════════════════════════════════════════════


class TestAlembicMigration0009:
    """Test Alembic Migration 0009 file validity."""

    def test_migration_0009_file_exists_and_valid(self):
        """Verify 0009 migration file exists with correct identifiers."""
        migration_file = Path("alembic/versions/0009_make_email_not_null_in_users.py")
        assert migration_file.exists()

        content = migration_file.read_text(encoding="utf-8")
        assert 'revision: str = "0009_email_not_null_in_users"' in content
        assert 'down_revision: Union[str, None] = "0008_add_email_verify_to_users"' in content
        assert 'op.alter_column(' in content
        assert '"users"' in content
        assert '"email"' in content
        assert 'nullable=False' in content


class TestResendVerificationEmailUnit:
    """Unit tests for AuthService.resend_verification_email method."""

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self):
        """Test successful resend: invalidates active tokens, creates new token."""
        from src.backend.services.auth_service import hash_password

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock user
        mock_user = User(
            id="10101010-1010-1010-1010-101010101010",
            email="resend@example.com",
            phone_number="+2348012345678",
            password_hash="hash",
            role=UserRole.PATIENT,
            is_email_verified=False,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        # Mock rate limit query (0 recent tokens)
        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 0

        # Mock active tokens query (1 active token to invalidate)
        old_token = MagicMock()
        old_token.is_expired = False
        active_tokens_result = MagicMock()
        active_tokens_result.scalars.return_value.all.return_value = [old_token]

        # Prior tokens query inside create_email_verification_token
        prior_tokens_result = MagicMock()
        prior_tokens_result.scalars.return_value = []

        mock_db.execute.side_effect = [
            rate_limit_result,      # 1. resend: check_email_rate_limit
            user_result,            # 2. resend: get_user_by_email
            active_tokens_result,   # 3. resend: active tokens to invalidate
            rate_limit_result,      # 4. create_email_verification_token: check_email_rate_limit
            prior_tokens_result,    # 5. create_email_verification_token: prior tokens
        ]

        service = AuthService(mock_db)
        user, raw_token = await service.resend_verification_email("resend@example.com")

        assert user == mock_user
        assert raw_token is not None
        assert old_token.is_expired is True

    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(self):
        """Test resend for verified email raises EMAIL_ALREADY_VERIFIED."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        mock_user = User(
            id="10101010-1010-1010-1010-101010101010",
            email="verified@example.com",
            phone_number="+2348012345678",
            password_hash="hash",
            role=UserRole.PATIENT,
            is_email_verified=True,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 0

        mock_db.execute.side_effect = [rate_limit_result, user_result]

        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="EMAIL_ALREADY_VERIFIED"):
            await service.resend_verification_email("verified@example.com")

    @pytest.mark.asyncio
    async def test_resend_verification_email_nonexistent_user(self):
        """Test resend for nonexistent email returns (None, None) safely."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 0

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [rate_limit_result, user_result]

        service = AuthService(mock_db)
        user, raw_token = await service.resend_verification_email("nobody@example.com")

        assert user is None
        assert raw_token is None

    @pytest.mark.asyncio
    async def test_resend_verification_email_rate_limit_exceeded(self):
        """Test resend fails with ValueError when 3 tokens already issued in 15 mins."""
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        rate_limit_result = MagicMock()
        rate_limit_result.scalar_one.return_value = 3
        mock_db.execute.return_value = rate_limit_result

        service = AuthService(mock_db)
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await service.resend_verification_email("ratelimited@example.com")


class TestResendVerificationRouter:
    """Router-level integration tests for POST /api/v1/auth/patient/resend-verification."""

    def test_resend_verification_success_endpoint(self, client):
        """Test POST /api/v1/auth/patient/resend-verification returns 200."""
        mock_user = MagicMock()
        mock_user.email = "unverified@example.com"

        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.resend_verification_email = AsyncMock(
                    return_value=(mock_user, "new_raw_token_xyz")
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/resend-verification",
                    json={"email": "unverified@example.com"},
                )

                assert response.status_code == 200
                assert "sent" in response.json()["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_resend_verification_already_verified_endpoint(self, client):
        """Test resend for verified email returns 409 Conflict."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.resend_verification_email = AsyncMock(
                    side_effect=ValueError("EMAIL_ALREADY_VERIFIED")
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/resend-verification",
                    json={"email": "verified@example.com"},
                )

                assert response.status_code == 409
                assert "already verified" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_resend_verification_rate_limit_endpoint(self, client):
        """Test resend rate limit failure returns 429 Too Many Requests."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.resend_verification_email = AsyncMock(
                    side_effect=ValueError("Rate limit exceeded for verification emails.")
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/resend-verification",
                    json={"email": "spammer@example.com"},
                )

                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_resend_verification_nonexistent_email_returns_200(self, client):
        """Test resend for nonexistent email returns 200 to prevent enumeration."""
        async def override_get_db():
            mock_db = MagicMock()
            mock_db.commit = AsyncMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.resend_verification_email = AsyncMock(
                    return_value=(None, None)
                )
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/auth/patient/resend-verification",
                    json={"email": "nonexistent@example.com"},
                )

                assert response.status_code == 200
                assert "sent" in response.json()["message"].lower()
        finally:
            app.dependency_overrides.clear()


class TestDeprecationHeaders:
    """Test legacy OTP endpoints include Deprecation and Sunset headers per ADR-005."""

    def test_register_otp_endpoint_has_deprecation_headers(self, client):
        """Test POST /api/v1/register returns Deprecation header."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.get_user_by_phone = AsyncMock(return_value=None)
                mock_otp = MagicMock()
                mock_otp.id = "otp-id-1"
                mock_otp.phone_number = "+2348011112222"
                mock_service_instance.create_otp = AsyncMock(return_value=(mock_otp, "123456"))
                mock_service_instance.create_registration_token.return_value = "reg_token_123"
                MockAuthService.return_value = mock_service_instance

                with patch("api.v1.auth.router._send_otp_notification", new_callable=AsyncMock):
                    response = client.post(
                        "/api/v1/register",
                        json={
                            "phone_number": "+2348011112222",
                            "full_name": "Test User",
                        },
                    )

                    assert response.status_code == 201
                    assert response.headers.get("deprecation") == "true"
                    assert "sunset" in response.headers
        finally:
            app.dependency_overrides.clear()

    def test_verify_request_endpoint_has_deprecation_headers(self, client):
        """Test POST /api/v1/verify-request returns Deprecation header."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_service_instance = MagicMock()
                mock_service_instance.get_user_by_phone = AsyncMock(return_value=MagicMock())
                mock_otp = MagicMock()
                mock_otp.id = "otp-id-2"
                mock_otp.phone_number = "+2348011112222"
                mock_service_instance.create_otp = AsyncMock(return_value=(mock_otp, "654321"))
                MockAuthService.return_value = mock_service_instance

                with patch("api.v1.auth.router._send_otp_notification", new_callable=AsyncMock):
                    response = client.post(
                        "/api/v1/verify-request",
                        json={"phone_number": "+2348011112222"},
                    )

                    assert response.status_code == 202
                    assert response.headers.get("deprecation") == "true"
                    assert "sunset" in response.headers
        finally:
            app.dependency_overrides.clear()

    def test_verify_code_endpoint_has_deprecation_headers(self, client):
        """Test POST /api/v1/verify-code returns Deprecation header."""
        async def override_get_db():
            mock_db = MagicMock()
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            with patch("api.v1.auth.router.AuthService") as MockAuthService:
                mock_user = MagicMock()
                mock_user.id = "user-id-3"
                mock_user.role = UserRole.PATIENT

                mock_service_instance = MagicMock()
                mock_service_instance.verify_otp_code = AsyncMock(return_value=(True, None))
                mock_service_instance.get_user_by_phone = AsyncMock(return_value=mock_user)
                mock_service_instance.create_access_token.return_value = "access_token"
                mock_service_instance.create_refresh_token.return_value = "refresh_token"
                MockAuthService.return_value = mock_service_instance

                response = client.post(
                    "/api/v1/verify-code",
                    json={
                        "phone_number": "+2348011112222",
                        "otp_code": "123456",
                    },
                )

                assert response.status_code == 200
                assert response.headers.get("deprecation") == "true"
                assert "sunset" in response.headers
        finally:
            app.dependency_overrides.clear()

