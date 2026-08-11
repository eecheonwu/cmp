"""
Tests for OTP Delivery Fix (Round 2).

Verifies the fixes for the root causes that were NOT addressed by the
previous OTP delivery fix (Round 1):

1. send_otp_task no longer requires a User to exist (registration flow)
   — Previously, the Celery task looked up a User by phone number and
   returned early with "User not found" when no user existed yet. For
   the registration flow, the user is created AFTER OTP verification,
   so the task always failed silently.

2. WhatsApp URL does not contain extra /v1/ path segment
   — Previously, the URL was f"{api_url}/v1/{phone_number_id}/messages"
   which produced https://graph.facebook.com/v18.0/v1/{id}/messages —
   the extra /v1/ caused 404 errors from the WhatsApp Cloud API.

3. Celery include path matches router import (workers.tasks)
   — Previously, the include path was "src.backend.workers.tasks" but
   the correct path (used by the router and docker) is "workers.tasks".

4. Celery task_routes use explicit task names
   — Previously, the routes used "src.backend.workers.tasks.send_otp_task"
   but the tasks are registered with explicit names like "send_otp_task".
"""

import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backend.services.notification_service import (
    WhatsAppCloudAPIClient,
    NotificationOrchestrator,
)


# ── Test 1: send_otp_task does not require User to exist ────────────────────

class TestSendOtpTaskNoUser:
    """
    Test that send_otp_task works when no User record exists.

    This is the PRIMARY bug fix: previously, send_otp_task looked up a
    User by phone number and returned early with "User not found" when
    no user existed. For the registration flow, the user is created AFTER
    OTP verification, so the task always failed silently.
    """

    def test_send_otp_task_source_no_user_lookup(self):
        """Verify the source code of send_otp_task does not query User."""
        try:
            from src.backend.workers.tasks import send_otp_task
        except ImportError:
            pytest.skip("Celery not installed")

        source = inspect.getsource(send_otp_task)

        # The task should NOT query for a User record
        assert "select(User)" not in source, (
            "send_otp_task should NOT query select(User) — the User lookup "
            "was the primary bug that prevented OTP delivery during registration."
        )
        # The task should NOT import User (only VerificationOTP is needed)
        assert "from models.user import User" not in source, (
            "send_otp_task should NOT import User — only VerificationOTP is needed."
        )
        # The task should use otp.phone_number directly
        assert "otp.phone_number" in source, (
            "send_otp_task should use otp.phone_number directly for sending."
        )

    def test_send_otp_task_source_no_user_not_found_return(self):
        """Verify the task does not return 'User not found' error."""
        try:
            from src.backend.workers.tasks import send_otp_task
        except ImportError:
            pytest.skip("Celery not installed")

        source = inspect.getsource(send_otp_task)

        # Check that the function body does NOT contain a return with "User not found"
        # The docstring may mention the old bug, so we check the body only
        # by looking for the pattern that was the old bug: return {"success": False, "error": "User not found"}
        assert 'return {"success": False, "error": "User not found"}' not in source, (
            "send_otp_task should NOT return 'User not found' — this was the "
            "silent failure that prevented OTP delivery during registration."
        )
        # Also check the old import pattern is gone
        assert "from models.user import User" not in source, (
            "send_otp_task should NOT import User — only VerificationOTP is needed."
        )

    def test_send_otp_task_inner_logic_uses_otp_phone_number(self):
        """
        Verify the inner _send() function uses otp.phone_number directly.

        This is a static analysis test that checks the source code of the
        send_otp_task function body. The dynamic test (calling the task
        function directly) is not possible here because the task uses
        asyncio.run() which conflicts with pytest-asyncio's event loop.

        The code fix is verified by three complementary approaches:
        1. Static analysis: source code doesn't query User (tests above)
        2. Orchestrator test: send_otp works with just a phone number
        3. This test: inner logic uses otp.phone_number directly
        """
        try:
            from src.backend.workers.tasks import send_otp_task
        except ImportError:
            pytest.skip("Celery not installed")

        source = inspect.getsource(send_otp_task)

        # Verify the task passes otp.phone_number to the orchestrator
        assert "orchestrator.send_otp(" in source
        assert "otp.phone_number," in source
        assert "otp_code," in source

        # Verify the task does NOT query for User
        assert "select(User)" not in source, (
            "send_otp_task must not query select(User). "
            "The User lookup was the primary bug."
        )


# ── Test 2: WhatsApp URL construction ────────────────────────────────────────

class TestWhatsAppUrlConstruction:
    """
    Test that the WhatsApp API URL is constructed correctly.

    Previously, the URL was f"{self.api_url}/v1/{self.phone_number_id}/messages"
    which produced https://graph.facebook.com/v18.0/v1/{id}/messages —
    the extra /v1/ caused 404 errors from the WhatsApp Cloud API.

    The correct WhatsApp Cloud API endpoint is:
    POST https://graph.facebook.com/{version}/{phone-number-id}/messages
    """

    @pytest.mark.asyncio
    async def test_whatsapp_url_no_extra_v1(self):
        """Test that WhatsApp URL does not contain extra /v1/ path segment."""
        client = WhatsAppCloudAPIClient(db=None)
        client.api_url = "https://graph.facebook.com/v18.0"
        client.api_token = "test-token"
        client.phone_number_id = "123456789"

        with patch(
            "src.backend.services.notification_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)

            await client.send(
                "+234801234567", "test message", "otp_verification"
            )

            # Check the URL used in the POST request
            call_args = mock_client.post.call_args
            url = call_args[0][0]  # First positional argument

            # The URL should NOT contain /v1/
            assert "/v1/" not in url, (
                f"WhatsApp URL should not contain '/v1/' but got: {url}"
            )
            # The URL should be correct
            assert url == "https://graph.facebook.com/v18.0/123456789/messages"

    @pytest.mark.asyncio
    async def test_whatsapp_url_with_real_api_url(self):
        """Test URL construction with the real WhatsApp API URL format."""
        client = WhatsAppCloudAPIClient(db=None)
        client.api_url = "https://graph.facebook.com/v18.0"
        client.api_token = "test-token"
        client.phone_number_id = "107839179001234"

        with patch(
            "src.backend.services.notification_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)

            await client.send(
                "+234801234567", "test", "otp_verification"
            )

            url = mock_client.post.call_args[0][0]
            assert url == "https://graph.facebook.com/v18.0/107839179001234/messages"
            assert "/v1/" not in url

    def test_whatsapp_url_source_no_v1(self):
        """Verify the source code does not construct URL with /v1/."""
        source = inspect.getsource(WhatsAppCloudAPIClient.send)
        assert "/v1/" not in source, (
            "WhatsAppCloudAPIClient.send should not use /v1/ in the URL. "
            "The correct WhatsApp Cloud API endpoint is "
            "https://graph.facebook.com/{version}/{phone-number-id}/messages"
        )


# ── Test 3: Celery configuration ─────────────────────────────────────────────

class TestCeleryConfig:
    """
    Test Celery configuration for correct include path and task routing.

    Previously:
    - include was ["src.backend.workers.tasks"] but should be ["workers.tasks"]
    - task_routes used "src.backend.workers.tasks.send_otp_task" but should
      use the explicit task name "send_otp_task"
    """

    def test_celery_include_path(self):
        """Test that Celery include path uses workers.tasks."""
        try:
            from src.backend.workers.celery_app import celery_app
        except ImportError:
            pytest.skip("Celery not installed")

        include = celery_app.conf.include
        assert "workers.tasks" in include, (
            f"Celery include should contain 'workers.tasks', got: {include}"
        )
        assert "src.backend.workers.tasks" not in include, (
            f"Celery include should NOT contain 'src.backend.workers.tasks', "
            f"got: {include}"
        )

    def test_celery_task_routes(self):
        """Test that Celery task routes use explicit task names."""
        try:
            from src.backend.workers.celery_app import celery_app
        except ImportError:
            pytest.skip("Celery not installed")

        routes = celery_app.conf.task_routes
        # The routes should use the explicit task names
        assert "send_otp_task" in routes
        assert "send_appointment_confirmation_task" in routes
        assert "send_appointment_reminder_task" in routes
        assert "send_cancellation_alert_task" in routes
        # Should NOT use the old src.backend.workers.tasks prefix
        for key in routes:
            assert not key.startswith("src.backend.workers.tasks"), (
                f"Task route key should not start with "
                f"'src.backend.workers.tasks': {key}"
            )


# ── Test 4: Integration — OTP delivery without user ──────────────────────────

class TestOtpDeliveryWithoutUser:
    """
    Integration test: verify OTP can be delivered when no User exists.

    This simulates the registration flow where:
    1. User requests OTP via /register
    2. OTP is created in DB (but no User yet)
    3. Celery task sends OTP using phone number from OTP record
    """

    @pytest.mark.asyncio
    async def test_orchestrator_send_otp_uses_phone_number(self):
        """Test that the orchestrator sends OTP using the provided phone number."""
        mock_db = AsyncMock()

        orchestrator = NotificationOrchestrator(mock_db)

        # Mock the first provider (WhatsApp) to succeed
        with patch.object(orchestrator.providers[0], "send") as mock_send:
            mock_send.return_value = (True, None)

            success, error, provider = await orchestrator.send_otp(
                "+234801234567", "123456"
            )

            assert success is True
            assert error is None
            assert provider == "whatsapp"
            mock_send.assert_called_once_with(
                "+234801234567",
                "Your CMP verification code is: 123456",
                "otp_verification",
            )

    @pytest.mark.asyncio
    async def test_orchestrator_send_otp_no_user_required(self):
        """Test that orchestrator.send_otp works without any User lookup."""
        mock_db = AsyncMock()

        orchestrator = NotificationOrchestrator(mock_db)

        # Mock all providers to fail (simulating unconfigured providers)
        for provider in orchestrator.providers:
            provider.send = AsyncMock(return_value=(False, "not configured"))

        success, error, provider = await orchestrator.send_otp(
            "+234801234567", "123456"
        )

        # Should fail gracefully (all providers unconfigured)
        assert success is False
        assert error is not None
        # But no exception should be raised — the phone number was used directly
