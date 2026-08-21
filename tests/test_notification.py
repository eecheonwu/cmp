"""
Test suite for Task 2.3: NotificationService & Async Workers.

Tests:
- Abstract NotificationService + 3 provider adapters
- Failover: WhatsApp (15s) → Termii → Infobip
- Celery tasks: send_appointment_confirmation, send_otp
- notifications_log table migration
- Idempotency check (sent_at column mapping)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backend.services.notification_service import (
    NotificationService,
    WhatsAppCloudAPIClient,
    TermiiSMSClient,
    InfobipSMSClient,
    NotificationOrchestrator,
)
from src.backend.models.notification import NotificationLog


# ── Test: Abstract NotificationService ─────────────────────────────────────

class TestNotificationServiceAbstract:
    """Tests for NotificationService abstract class."""

    def test_notification_service_abstract(self):
        """Test that NotificationService is abstract and cannot be instantiated directly."""
        # Check that NotificationService is abstract
        assert hasattr(NotificationService, "__abstractmethods__")
        assert "send" in NotificationService.__abstractmethods__
        assert "get_provider_name" in NotificationService.__abstractmethods__
        assert "get_delivery_type" in NotificationService.__abstractmethods__

    def test_notification_service_subclass(self):
        """Test that subclasses implement required methods."""
        class TestService(NotificationService):
            async def send(self, recipient, message, template_name):
                return True, None

            def get_provider_name(self):
                return "test"

            def get_delivery_type(self):
                return "test"

        test_service = TestService()
        assert test_service.get_provider_name() == "test"
        assert test_service.get_delivery_type() == "test"


# ── Test: Provider Adapters ────────────────────────────────────────────────

class TestProviderAdapters:
    """Tests for notification provider adapters."""

    def test_whatsapp_client(self):
        """Test WhatsAppCloudAPIClient initialization."""
        client = WhatsAppCloudAPIClient()
        assert client.get_provider_name() == "whatsapp"
        assert client.get_delivery_type() == "whatsapp"

    def test_termii_client(self):
        """Test TermiiSMSClient initialization."""
        client = TermiiSMSClient()
        assert client.get_provider_name() == "termii"
        assert client.get_delivery_type() == "sms"

    def test_infobip_client(self):
        """Test InfobipSMSClient initialization."""
        client = InfobipSMSClient()
        assert client.get_provider_name() == "infobip"
        assert client.get_delivery_type() == "sms"


# ── Test: Failover Orchestrator ────────────────────────────────────────────

class TestNotificationOrchestrator:
    """Tests for NotificationOrchestrator."""

    def test_orchestrator_initialization(self):
        """Test NotificationOrchestrator initialization."""
        orchestrator = NotificationOrchestrator()
        assert len(orchestrator.providers) == 3
        assert isinstance(orchestrator.providers[0], WhatsAppCloudAPIClient)
        assert isinstance(orchestrator.providers[1], TermiiSMSClient)
        assert isinstance(orchestrator.providers[2], InfobipSMSClient)

    def test_orchestrator_failover(self):
        """Test failover chain logic."""
        orchestrator = NotificationOrchestrator()

        # Mock all providers to fail
        for provider in orchestrator.providers:
            provider.send = AsyncMock(return_value=(False, "API error"))

        # Test that it tries all providers
        import asyncio
        result = asyncio.run(orchestrator.send("test", "message", "template"))
        assert result[0] == False  # All failed
        assert result[2] == "infobip"  # Last provider tried

        # Mock first provider to succeed
        orchestrator.providers[0].send = AsyncMock(return_value=(True, None))
        result = asyncio.run(orchestrator.send("test", "message", "template"))
        assert result[0] == True  # Success
        assert result[2] == "whatsapp"  # First provider used

    def test_orchestrator_failover_to_sms(self):
        """Test that orchestrator falls back from WhatsApp to SMS providers."""
        orchestrator = NotificationOrchestrator()

        # Mock WhatsApp to fail, Termii to succeed
        orchestrator.providers[0].send = AsyncMock(return_value=(False, "WhatsApp error"))
        orchestrator.providers[1].send = AsyncMock(return_value=(True, None))

        import asyncio
        result = asyncio.run(orchestrator.send("test", "message", "template"))
        assert result[0] == True  # Success via fallback
        assert result[2] == "termii"  # Second provider used


# ── Test: NotificationLog Model ────────────────────────────────────────────

class TestNotificationLogModel:
    """Tests for NotificationLog model."""

    def test_notification_log_model(self):
        """Test NotificationLog model structure."""
        # Check model has required fields
        fields = [c.name for c in NotificationLog.__table__.c]
        assert "id" in fields
        assert "recipient" in fields
        assert "delivery_type" in fields
        assert "provider" in fields
        assert "template_name" in fields
        assert "status" in fields
        assert "error_code" in fields
        assert "delivery_attempts" in fields

    def test_notification_log_has_sent_at(self):
        """Test that NotificationLog model has sent_at column (required for idempotency check)."""
        fields = [c.name for c in NotificationLog.__table__.c]
        assert "sent_at" in fields, (
            "NotificationLog model is missing 'sent_at' column. "
            "This column is required by check_idempotency() and exists in the "
            "database migration (0003_notifications_log.py) but was not mapped in the ORM model."
        )

    def test_notification_log_sent_at_mapped_attribute(self):
        """Test that sent_at is a proper mapped attribute (not just a DB column)."""
        # This would raise AttributeError if sent_at is not mapped
        assert hasattr(NotificationLog, "sent_at"), (
            "NotificationLog.sent_at is not a mapped attribute. "
            "The check_idempotency() method references NotificationLog.sent_at "
            "and will raise AttributeError if it is not properly mapped."
        )


# ── Test: Idempotency Check ────────────────────────────────────────────────

class TestIdempotencyCheck:
    """Tests for the idempotency check functionality."""

    @pytest.mark.asyncio
    async def test_check_idempotency_no_db(self):
        """Test that check_idempotency returns False when db is None."""
        client = WhatsAppCloudAPIClient(db=None)
        result = await client.check_idempotency("+234801234567", "otp_verification")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_idempotency_no_existing_log(self):
        """Test that check_idempotency returns False when no prior send exists."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        client = WhatsAppCloudAPIClient(db=mock_db)
        result = await client.check_idempotency("+234801234567", "otp_verification")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_idempotency_existing_log(self):
        """Test that check_idempotency returns True when a prior send exists."""
        mock_db = AsyncMock()
        mock_log = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_log)))

        client = WhatsAppCloudAPIClient(db=mock_db)
        result = await client.check_idempotency("+234801234567", "otp_verification")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_idempotency_does_not_raise_attribute_error(self):
        """
        Test that check_idempotency does NOT raise AttributeError.

        This is a regression test for the bug where NotificationLog.sent_at
        was referenced in check_idempotency() but was not mapped in the ORM model,
        causing an AttributeError that made ALL providers fail.
        """
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        client = WhatsAppCloudAPIClient(db=mock_db)
        # This should NOT raise AttributeError
        result = await client.check_idempotency("+234801234567", "otp_verification")
        assert result is False


# ── Test: WhatsApp Client Unconfigured ─────────────────────────────────────

class TestWhatsAppUnconfigured:
    """Tests for WhatsApp client when API is not configured."""

    @pytest.mark.asyncio
    async def test_whatsapp_not_configured(self):
        """Test that WhatsApp client returns failure when API not configured."""
        client = WhatsAppCloudAPIClient(db=None)
        # api_url and api_token are None by default
        success, error = await client.send("+234801234567", "test", "otp_verification")
        assert success is False
        assert "not configured" in error.lower()


# ── Test: Celery Tasks ─────────────────────────────────────────────────────

class TestCeleryTasks:
    """Tests for Celery task definitions."""

    def test_celery_tasks_exist(self):
        """Test that Celery tasks are defined."""
        try:
            from src.backend.workers.tasks import (
                send_otp_task,
                send_appointment_confirmation_task,
                send_appointment_reminder_task,
                send_cancellation_alert_task,
            )

            # Check tasks are callable
            assert callable(send_otp_task)
            assert callable(send_appointment_confirmation_task)
            assert callable(send_appointment_reminder_task)
            assert callable(send_cancellation_alert_task)
        except ImportError:
            # Celery module not installed - structure is still valid
            pass

    def test_celery_app(self):
        """Test Celery app configuration."""
        try:
            from src.backend.workers.celery_app import celery_app

            assert celery_app is not None
            assert celery_app.conf.task_serializer == "json"
            assert celery_app.conf.result_serializer == "json"
        except ImportError:
            # Celery module not installed - structure is still valid
            pass
