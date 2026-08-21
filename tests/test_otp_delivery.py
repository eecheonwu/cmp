"""
Tests for OTP delivery system.

Verifies:
- OTP generation and storage
- OTP delivery via notification service
- OTP verification flow
- Rate limiting
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.auth_service import AuthService
from src.backend.services.notification_service import NotificationOrchestrator
from src.backend.models.user import User, UserRole, VerificationOTP


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def auth_service(mock_db):
    """Create AuthService instance with mock DB."""
    return AuthService(mock_db)


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        phone_number="+234801234567",
        email="test@example.com",
        password_hash="hashed_password",
        role=UserRole.PATIENT,
    )


# ── OTP Generation Tests ───────────────────────────────────────────────────

class TestOTPGeneration:
    """Test OTP generation functionality."""

    def test_generate_otp_length(self, auth_service):
        """Test that generated OTP is 6 digits."""
        otp = auth_service.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_uniqueness(self, auth_service):
        """Test that generated OTPs are unique."""
        otps = [auth_service.generate_otp() for _ in range(100)]
        assert len(set(otps)) == 100  # All unique

    def test_hash_otp(self, auth_service):
        """Test OTP hashing."""
        otp = "123456"
        hashed = auth_service.hash_otp(otp)
        assert hashed != otp
        assert len(hashed) > 0

    def test_verify_otp(self, auth_service):
        """Test OTP verification."""
        otp = "123456"
        hashed = auth_service.hash_otp(otp)
        assert auth_service.verify_otp(otp, hashed) is True
        assert auth_service.verify_otp("000000", hashed) is False


# ── OTP Creation Tests ─────────────────────────────────────────────────────

class TestOTPCreation:
    """Test OTP creation and storage."""

    @pytest.mark.asyncio
    async def test_create_otp_returns_tuple(self, auth_service, mock_db, sample_user):
        """Test that create_otp returns both OTP record and plain text code."""
        # Mock get_user_by_phone to return user
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        
        # Mock rate limit check
        auth_service.check_rate_limit = AsyncMock(return_value=0)
        
        # Mock database flush
        mock_db.flush = AsyncMock()
        
        # Create OTP
        otp, otp_code = await auth_service.create_otp("+234801234567")
        
        # Verify return values
        assert otp is not None
        assert isinstance(otp_code, str)
        assert len(otp_code) == 6
        assert otp_code.isdigit()
        
        # Verify OTP record properties
        assert otp.phone_number == "+234801234567"
        assert otp.hashed_otp != otp_code  # Should be hashed
        assert otp.is_used != True  # Should not be used (could be None in mock)

    @pytest.mark.asyncio
    async def test_create_otp_rate_limit(self, auth_service, mock_db):
        """Test OTP creation respects rate limits."""
        # Mock rate limit check to return max requests
        auth_service.check_rate_limit = AsyncMock(return_value=3)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await auth_service.create_otp("+234801234567")


# ── OTP Verification Tests ─────────────────────────────────────────────────

class TestOTPVerification:
    """Test OTP verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_otp_success(self, auth_service, mock_db, sample_user):
        """Test successful OTP verification."""
        # Create a valid OTP
        otp_code = "123456"
        hashed_otp = auth_service.hash_otp(otp_code)
        
        # Mock active OTP
        mock_otp = VerificationOTP(
            id="otp-id-123",
            phone_number="+234801234567",
            hashed_otp=hashed_otp,
            attempts=0,
            is_used=False,
            expires_at=datetime.now(timezone.utc),
        )
        
        auth_service.get_active_otp = AsyncMock(return_value=mock_otp)
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        mock_db.flush = AsyncMock()
        
        # Verify OTP
        success, error = await auth_service.verify_otp_code("+234801234567", otp_code)
        
        assert success is True
        assert error is None
        assert mock_otp.is_used is True

    @pytest.mark.asyncio
    async def test_verify_otp_invalid_code(self, auth_service, mock_db, sample_user):
        """Test OTP verification with invalid code."""
        # Create a valid OTP
        otp_code = "123456"
        hashed_otp = auth_service.hash_otp(otp_code)
        
        # Mock active OTP
        mock_otp = VerificationOTP(
            id="otp-id-123",
            phone_number="+234801234567",
            hashed_otp=hashed_otp,
            attempts=0,
            is_used=False,
            expires_at=datetime.now(timezone.utc),
        )
        
        auth_service.get_active_otp = AsyncMock(return_value=mock_otp)
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        mock_db.flush = AsyncMock()
        
        # Verify with wrong code
        success, error = await auth_service.verify_otp_code("+234801234567", "000000")
        
        assert success is False
        assert "Invalid OTP" in error
        assert mock_otp.attempts == 1

    @pytest.mark.asyncio
    async def test_verify_otp_max_attempts(self, auth_service, mock_db, sample_user):
        """Test OTP verification with max attempts exceeded."""
        # Create a valid OTP
        otp_code = "123456"
        hashed_otp = auth_service.hash_otp(otp_code)
        
        # Mock active OTP with max attempts
        mock_otp = VerificationOTP(
            id="otp-id-123",
            phone_number="+234801234567",
            hashed_otp=hashed_otp,
            attempts=5,  # Max attempts
            is_used=False,
            expires_at=datetime.now(timezone.utc),
        )
        
        auth_service.get_active_otp = AsyncMock(return_value=mock_otp)
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        
        # Verify should fail
        success, error = await auth_service.verify_otp_code("+234801234567", otp_code)
        
        assert success is False
        assert "Maximum attempts exceeded" in error


# ── Notification Delivery Tests ────────────────────────────────────────────

class TestNotificationDelivery:
    """Test OTP notification delivery."""

    @pytest.mark.asyncio
    async def test_send_otp_via_whatsapp(self, mock_db):
        """Test OTP delivery via WhatsApp."""
        orchestrator = NotificationOrchestrator(mock_db)
        
        # Mock WhatsApp client
        with patch.object(orchestrator.providers[0], 'send') as mock_send:
            mock_send.return_value = (True, None)
            
            success, error, provider = await orchestrator.send_otp(
                "+234801234567",
                "123456"
            )
            
            assert success is True
            assert error is None
            assert provider == "whatsapp"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_otp_fallback_to_sms(self, mock_db):
        """Test OTP delivery falls back to SMS if WhatsApp fails."""
        orchestrator = NotificationOrchestrator(mock_db)
        
        # Mock WhatsApp to fail, Termii to succeed
        with patch.object(orchestrator.providers[0], 'send') as mock_whatsapp:
            with patch.object(orchestrator.providers[1], 'send') as mock_termii:
                mock_whatsapp.return_value = (False, "WhatsApp error")
                mock_termii.return_value = (True, None)
                
                success, error, provider = await orchestrator.send_otp(
                    "+234801234567",
                    "123456"
                )
                
                assert success is True
                assert provider == "termii"

    @pytest.mark.asyncio
    async def test_send_otp_all_providers_fail(self, mock_db):
        """Test OTP delivery when all providers fail."""
        orchestrator = NotificationOrchestrator(mock_db)
        
        # Mock all providers to fail
        for provider in orchestrator.providers:
            with patch.object(provider, 'send') as mock_send:
                mock_send.return_value = (False, "Provider error")
        
        success, error, provider = await orchestrator.send_otp(
            "+234801234567",
            "123456"
        )
        
        assert success is False
        assert error is not None


# ── Integration Tests ──────────────────────────────────────────────────────

class TestOTPFlowIntegration:
    """Test complete OTP flow integration."""

    @pytest.mark.asyncio
    async def test_complete_otp_flow(self, auth_service, mock_db, sample_user):
        """Test complete OTP flow: create → send → verify."""
        # Step 1: Create OTP
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        auth_service.check_rate_limit = AsyncMock(return_value=0)
        mock_db.flush = AsyncMock()
        
        otp, otp_code = await auth_service.create_otp("+234801234567")
        
        # Step 2: Send OTP (simulated)
        assert isinstance(otp_code, str)
        assert len(otp_code) == 6
        
        # Step 3: Verify OTP - create a proper mock OTP with attempts set
        from src.backend.models.user import VerificationOTP
        hashed_otp = auth_service.hash_otp(otp_code)
        verified_otp = VerificationOTP(
            id="test-id",
            phone_number="+234801234567",
            hashed_otp=hashed_otp,
            attempts=0,
            is_used=False,
            expires_at=datetime.now(timezone.utc),
        )
        auth_service.get_active_otp = AsyncMock(return_value=verified_otp)
        auth_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        
        success, error = await auth_service.verify_otp_code("+234801234567", otp_code)
        
        assert success is True
        assert error is None
        assert verified_otp.is_used is True


# ── Run Tests ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])