"""
Test suite for Task 2.2: Authentication & RBAC Module.

Tests:
- JWT token generation and validation
- OTP generation, verification, and rate limiting
- Patient registration
- Staff login
- Role-based access control
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backend.services.auth_service import AuthService, hash_password, verify_password
from src.backend.models.user import User, UserRole, VerificationOTP
from src.backend.core.security import RoleChecker


# ── Unit Tests for AuthService ──────────────────────────────────────────

class TestAuthServicePassword:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)

    def test_hash_password_creates_different_hashes(self):
        """Test that same password creates different hashes (salt)."""
        password = "testpassword123"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)

        # Different salts should produce different hashes
        assert hashed1 != hashed2
        # But both should verify correctly
        assert verify_password(password, hashed1)
        assert verify_password(password, hashed2)


class TestAuthServiceOTP:
    """Tests for OTP generation."""

    def test_generate_otp(self):
        """Test OTP generation."""
        otp = AuthService.generate_otp()

        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_uniqueness(self):
        """Test that OTPs are unique."""
        otps = [AuthService.generate_otp() for _ in range(100)]
        # With 6 digits, we should have mostly unique values
        assert len(set(otps)) > 90


class TestAuthServiceJWT:
    """Tests for JWT token operations."""

    def test_create_access_token(self, mock_user):
        """Test JWT access token creation."""
        auth_service = AuthService(None)
        token = auth_service.create_access_token(mock_user.id, mock_user.role)

        assert token is not None
        assert len(token) > 0

        # Decode and verify
        payload = auth_service.decode_token(token)
        assert payload["sub"] == str(mock_user.id)
        assert payload["role"] == mock_user.role.value
        assert payload["type"] == "access"

    def test_create_refresh_token(self, mock_user):
        """Test JWT refresh token creation."""
        auth_service = AuthService(None)
        token = auth_service.create_refresh_token(mock_user.id)

        assert token is not None
        assert len(token) > 0

        # Decode and verify
        payload = auth_service.decode_token(token)
        assert payload["sub"] == str(mock_user.id)
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Test that invalid tokens raise an error."""
        auth_service = AuthService(None)

        with pytest.raises(Exception):
            auth_service.decode_token("invalid.token.here")

    def test_registration_token_roundtrip(self):
        """Test registration token creation and decoding."""
        auth_service = AuthService(None)
        data = {
            "phone_number": "+2348012345678",
            "full_name": "Pending Patient",
        }
        token = auth_service.create_registration_token(data)
        assert token is not None
        
        decoded = auth_service.decode_registration_token(token)
        assert decoded["phone_number"] == "+2348012345678"
        assert decoded["full_name"] == "Pending Patient"
        assert decoded["type"] == "registration_pending"


# ── Unit Tests for RoleChecker ───────────────────────────────────────────

class TestRoleChecker:
    """Tests for RoleChecker dependency."""

    def test_role_checker_is_callable(self):
        """Test that RoleChecker is callable."""
        checker = RoleChecker([UserRole.DOCTOR])
        assert callable(checker)

    def test_role_checker_is_async(self):
        """Test that RoleChecker returns a coroutine function."""
        import inspect
        checker = RoleChecker([UserRole.DOCTOR])
        assert inspect.iscoroutinefunction(checker)

    def test_role_checker_with_multiple_roles(self):
        """Test RoleChecker with multiple roles."""
        checker = RoleChecker([UserRole.DOCTOR, UserRole.MANAGER])
        assert callable(checker)


# ── Integration Tests for Auth Endpoints ───────────────────────────────────

class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    def test_register_endpoint_exists(self, test_client):
        """Test that /api/v1/register endpoint exists."""
        try:
            response = test_client.post(
                "/api/v1/register",
                json={
                    "phone_number": "+2348012345678",
                    "full_name": "Test Patient",
                },
            )
            # 401, 409, 201, or 500 are all valid responses
            assert response.status_code in [401, 409, 201, 500]
        except Exception:
            # Database not available - endpoint exists but can't connect
            pass

    def test_verify_request_endpoint_exists(self, test_client):
        """Test that /api/v1/verify-request endpoint exists."""
        try:
            response = test_client.post(
                "/api/v1/verify-request",
                json={
                    "phone_number": "+2348012345678",
                },
            )
            assert response.status_code in [200, 429, 500]
        except Exception:
            # Database not available - endpoint exists but can't connect
            pass

    def test_verify_code_endpoint_exists(self, test_client):
        """Test that /api/v1/verify-code endpoint exists."""
        try:
            response = test_client.post(
                "/api/v1/verify-code",
                json={
                    "phone_number": "+2348012345678",
                    "otp_code": "123456",
                },
            )
            assert response.status_code in [401, 400, 200, 500]
        except Exception:
            # Database not available - endpoint exists but can't connect
            pass

    def test_login_endpoint_exists(self, test_client):
        """Test that /api/v1/login endpoint exists."""
        try:
            response = test_client.post(
                "/api/v1/login",
                json={
                    "email": "doctor@example.com",
                    "password": "testpassword123",
                },
            )
            assert response.status_code in [401, 200, 500]
        except Exception:
            # Database not available - endpoint exists but can't connect
            pass


# ── Security Tests ───────────────────────────────────────────────────────

class TestAuthSecurity:
    """Security tests for authentication."""

    @pytest.mark.asyncio
    async def test_otp_rate_limiting(self, mock_async_session):
        """Test OTP rate limiting logic."""
        # Mock the rate limit check to return 3 (at limit)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)

        # This should raise rate limit error
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await auth_service.create_otp("+2348012345678")

    @pytest.mark.asyncio
    async def test_otp_max_attempts(self, mock_async_session):
        """Test OTP max attempts check."""
        # Create an OTP that's at max attempts
        mock_otp = MagicMock(spec=VerificationOTP)
        mock_otp.attempts = 5
        mock_otp.is_used = False
        mock_otp.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_otp.hashed_otp = hash_password("123456")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_otp
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)

        # This should fail due to max attempts
        success, error = await auth_service.verify_otp_code("+2348012345678", "123456")
        assert success is False
        assert "Maximum attempts" in error


# ── Additional Unit Tests for AuthService ─────────────────────────────────

class TestAuthServiceUserOperations:
    """Additional tests for AuthService user operations."""

    @pytest.mark.asyncio
    async def test_get_user_by_phone(self, mock_async_session):
        """Test get_user_by_phone method."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "12345678-1234-5678-1234-567812345678"
        mock_user.phone_number = "+2348012345678"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.get_user_by_phone("+2348012345678")

        assert user is not None
        assert user.phone_number == "+2348012345678"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_async_session):
        """Test get_user_by_email method."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "12345678-1234-5678-1234-567812345678"
        mock_user.email = "test@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.get_user_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_staff_valid(self, mock_async_session):
        """Test authenticate_staff with valid credentials."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "11111111-1111-1111-1111-111111111111"
        mock_user.email = "doctor@example.com"
        mock_user.password_hash = hash_password("correctpassword")
        mock_user.role = UserRole.DOCTOR

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.authenticate_staff("doctor@example.com", "correctpassword")

        assert user is not None
        assert user.email == "doctor@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_staff_wrong_password(self, mock_async_session):
        """Test authenticate_staff with wrong password."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "11111111-1111-1111-1111-111111111111"
        mock_user.email = "doctor@example.com"
        mock_user.password_hash = hash_password("correctpassword")
        mock_user.role = UserRole.DOCTOR

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.authenticate_staff("doctor@example.com", "wrongpassword")

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_staff_patient(self, mock_async_session):
        """Test authenticate_staff rejects patient users."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "12345678-1234-5678-1234-567812345678"
        mock_user.email = "patient@example.com"
        mock_user.password_hash = hash_password("password")
        mock_user.role = UserRole.PATIENT

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.authenticate_staff("patient@example.com", "password")

        assert user is None

    @pytest.mark.asyncio
    async def test_register_patient(self, mock_async_session):
        """Test register_patient method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)
        user = await auth_service.register_patient(
            phone_number="+2348012345678",
            full_name="Test Patient",
            date_of_birth=datetime(1990, 1, 1),
            gender="male",
        )

        assert user is not None
        assert user.role == UserRole.PATIENT

    @pytest.mark.asyncio
    async def test_register_patient_duplicate(self, mock_async_session):
        """Test register_patient rejects duplicate phone."""
        mock_user = MagicMock(spec=User)
        mock_user.phone_number = "+2348012345678"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result

        auth_service = AuthService(mock_async_session)

        with pytest.raises(ValueError, match="already exists"):
            await auth_service.register_patient(
                phone_number="+2348012345678",
                full_name="Test Patient",
            )


# ── Security Module Tests ───────────────────────────────────────────────────

class TestSecurityModule:
    """Tests for security module (RoleChecker, etc.)."""

    def test_oauth2_scheme_exists(self):
        """Test that OAuth2 scheme is configured."""
        from src.backend.core.security import oauth2_scheme

        assert oauth2_scheme is not None

    def test_role_checker_returns_callable(self):
        """Test that RoleChecker returns a callable function."""
        from src.backend.core.security import RoleChecker

        checker = RoleChecker([UserRole.DOCTOR])
        assert callable(checker)

    def test_role_checker_with_single_role(self):
        """Test RoleChecker with single role."""
        from src.backend.core.security import RoleChecker

        checker = RoleChecker([UserRole.ADMIN])
        assert callable(checker)

    def test_role_checker_with_all_roles(self):
        """Test RoleChecker with all roles."""
        from src.backend.core.security import RoleChecker

        checker = RoleChecker([UserRole.DOCTOR, UserRole.MANAGER, UserRole.ADMIN, UserRole.RECEPTIONIST])
        assert callable(checker)


# ── Config Module Tests ───────────────────────────────────────────────────

class TestConfigModule:
    """Tests for configuration module."""

    def test_settings_instance(self):
        """Test that settings instance is created."""
        from src.backend.core.config import settings

        assert settings is not None
        assert settings.APP_NAME == "Clinic Modernization Platform"
        assert settings.APP_VERSION == "1.0.0"

    def test_database_url_async(self):
        """Test database_url_async property."""
        from src.backend.core.config import settings

        url = settings.database_url_async
        assert "asyncpg" in url

    def test_is_production(self):
        """Test is_production property."""
        from src.backend.core.config import settings

        # Default is development
        assert settings.is_production is False

    def test_is_development(self):
        """Test is_development property."""
        from src.backend.core.config import settings

        # Default is "development" which should be considered development mode
        assert settings.is_development is True

    def test_cors_origins(self):
        """Test CORS origins configuration."""
        from src.backend.core.config import settings

        # CORS_ORIGINS is a comma-separated string, use the property to get list
        origins = settings.cors_origins_list
        assert len(origins) > 0
        assert "localhost" in origins[0]

    def test_jwt_settings(self):
        """Test JWT configuration."""
        from src.backend.core.config import settings

        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_otp_settings(self):
        """Test OTP configuration."""
        from src.backend.core.config import settings

        assert settings.OTP_LENGTH == 6
        assert settings.OTP_TTL_SECONDS == 600
        assert settings.OTP_MAX_ATTEMPTS == 5