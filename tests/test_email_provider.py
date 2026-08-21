"""
Unit tests for Task 1: Email Verification Tokens Schema + Email Notification Provider.

Tests:
- EmailClient initialization and provider interface implementation
- Email delivery via mock/console provider with NotificationLog auditing
- Invalid recipient email handling
- Celery worker tasks: send_auth_email, send_email_notification
- EmailVerificationToken model creation and attributes
- Migration 0007 schema structure check
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backend.services.notification.providers.email_provider import EmailClient
from src.backend.models.user import EmailVerificationToken
from src.backend.models.notification import NotificationLog
from src.backend.workers.tasks import send_auth_email, send_email_notification


class TestEmailClientProvider:
    """Tests for EmailClient notification provider adapter."""

    def test_email_client_initialization(self):
        """Test EmailClient initialization and provider properties."""
        client = EmailClient()
        assert client.get_provider_name() == "email"
        assert client.get_delivery_type() == "email"
        assert hasattr(client, "send_email")
        assert hasattr(client, "send")

    @pytest.mark.asyncio
    async def test_send_email_mock_provider_success(self):
        """Test sending email via mock/console provider creates audit log."""
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        client = EmailClient(db=mock_db)
        client.provider_type = "console"

        to_email = "patient@example.com"
        subject = "Verify Your Email"
        html_body = "<h1>Click link to verify</h1>"
        text_body = "Click link to verify"

        success, error = await client.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            template_name="auth_email",
        )

        assert success is True
        assert error is None
        assert mock_db.add.called

        # Verify NotificationLog instance passed to db.add
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.recipient == to_email
        assert added_obj.provider == "email"
        assert added_obj.delivery_type == "email"
        assert added_obj.status == "sent"
        assert added_obj.template_name == "auth_email"

    @pytest.mark.asyncio
    async def test_send_email_invalid_recipient(self):
        """Test sending email with invalid recipient format fails."""
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        client = EmailClient(db=mock_db)

        success, error = await client.send_email(
            to_email="invalid-email-no-at-sign",
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            template_name="auth_email",
        )

        assert success is False
        assert "Invalid email address" in error
        assert mock_db.add.called
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.status == "failed"
        assert added_obj.error_code == "invalid_email"

    @pytest.mark.asyncio
    async def test_notification_service_interface_send(self):
        """Test send method satisfying NotificationService base interface."""
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        client = EmailClient(db=mock_db)
        client.provider_type = "mock"

        success, error = await client.send(
            recipient="test@example.com",
            message="Hello, this is a test notification message.",
            template_name="generic_test",
        )

        assert success is True
        assert error is None
        assert mock_db.add.called


class TestEmailVerificationTokenModel:
    """Tests for EmailVerificationToken model."""

    def test_email_verification_token_model_attributes(self):
        """Test EmailVerificationToken model instantiation and fields."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=60)

        token = EmailVerificationToken(
            email="patient@example.com",
            token_hash="$2b$12$sample_hashed_token_string",
            attempts=0,
            is_used=False,
            is_expired=False,
            expires_at=expires,
        )

        assert token.email == "patient@example.com"
        assert token.token_hash == "$2b$12$sample_hashed_token_string"
        assert token.attempts == 0
        assert token.is_used is False
        assert token.is_expired is False
        assert token.expires_at == expires
        assert "EmailVerificationToken" in repr(token)


class TestCeleryEmailTasks:
    """Tests for Celery email worker tasks."""

    def test_send_auth_email_task_execution(self):
        """Test send_auth_email Celery task enqueues and invokes EmailClient."""
        from contextlib import asynccontextmanager

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        mock_session_local = MagicMock(return_value=mock_session_ctx())

        # tasks.py imports AsyncSessionLocal from db.session (bare module path)
        # and imports EmailClient locally inside the function from services.notification...
        with patch("workers.tasks.AsyncSessionLocal", mock_session_local), \
             patch("services.notification.providers.email_provider.EmailClient.send_email",
                   new_callable=AsyncMock, return_value=(True, None)):
            result = send_auth_email.run(
                to_email="newpatient@example.com",
                verification_token="sample-token-12345",
                full_name="Jane Doe",
            )

            assert result["success"] is True
            assert result["provider"] == "email"

    def test_send_email_notification_task_execution(self):
        """Test send_email_notification Celery task enqueues and invokes EmailClient."""
        from contextlib import asynccontextmanager

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.close = AsyncMock()

        @asynccontextmanager
        async def mock_session_ctx():
            yield mock_session

        mock_session_local = MagicMock(return_value=mock_session_ctx())

        with patch("workers.tasks.AsyncSessionLocal", mock_session_local), \
             patch("services.notification.providers.email_provider.EmailClient.send_email",
                   new_callable=AsyncMock, return_value=(True, None)):
            result = send_email_notification.run(
                to_email="user@example.com",
                subject="Appointment Notice",
                html_body="<p>Your appointment is scheduled.</p>",
                text_body="Your appointment is scheduled.",
                template_name="appointment_notice",
            )

            assert result["success"] is True
            assert result["provider"] == "email"


class TestAlembicMigration0007:
    """Tests for Alembic migration file 0007."""

    def test_migration_0007_file_exists_and_valid(self):
        """Verify migration 0007 revision file exists and defines upgrade/downgrade."""
        migration_file = project_root / "alembic" / "versions" / "0007_email_verification_tokens.py"
        assert migration_file.exists()

        content = migration_file.read_text(encoding="utf-8")
        assert 'revision: str = "0007_email_verification_tokens"' in content
        assert 'down_revision: Union[str, None] = "0006_security_audit_logs"' in content
        assert "def upgrade() -> None:" in content
        assert "def downgrade() -> None:" in content
        assert "op.create_table" in content
        assert "email_verification_tokens" in content
        assert "ix_email_verification_tokens_email" in content
        assert "ix_email_verification_tokens_expires_at" in content
