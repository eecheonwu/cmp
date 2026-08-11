"""
CMP Notification Service.

Implements Strategy Pattern for multi-channel notification delivery:
- WhatsApp Cloud API (primary)
- Termii SMS (Nigerian DND-bypass fallback)
- Infobip SMS (international fallback)

With failover orchestrator and idempotency tracking.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.notification import NotificationLog

logger = logging.getLogger(__name__)


# ── Abstract Base Class ───────────────────────────────────────────────────────

class NotificationService(ABC):
    """
    Abstract base class for notification providers.

    Implements Strategy Pattern for pluggable notification channels.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.timeout = settings.NOTIFICATION_TIMEOUT_SECONDS

    @abstractmethod
    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Send a notification to a recipient.

        Args:
            recipient: Phone number or identifier
            message: Message content to send
            template_name: Template identifier for tracking

        Returns:
            tuple: (success, error_message)
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name for logging."""
        pass

    @abstractmethod
    def get_delivery_type(self) -> str:
        """Return the delivery type (whatsapp/sms)."""
        pass

    async def log_notification(
        self,
        recipient: str,
        template_name: str,
        status: str,
        error_code: Optional[str] = None,
    ) -> None:
        """Log notification attempt to database."""
        if self.db is None:
            return

        log = NotificationLog(
            recipient=recipient,
            delivery_type=self.get_delivery_type(),
            provider=self.get_provider_name(),
            template_name=template_name,
            status=status,
            error_code=error_code,
            sent_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()

    async def check_idempotency(
        self,
        recipient: str,
        template_name: str,
        within_seconds: int = 300,
    ) -> bool:
        """
        Check if a notification was already sent recently.

        Prevents duplicate sends on retry.

        Args:
            recipient: Recipient identifier
            template_name: Template name
            within_seconds: Time window to check (default 5 minutes)

        Returns:
            True if should skip (already sent), False to proceed
        """
        if self.db is None:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
        result = await self.db.execute(
            select(NotificationLog)
            .where(NotificationLog.recipient == recipient)
            .where(NotificationLog.template_name == template_name)
            .where(NotificationLog.status == "sent")
            .where(NotificationLog.sent_at >= cutoff)
        )
        return result.scalar_one_or_none() is not None


# ── WhatsApp Cloud API Client ───────────────────────────────────────────────

class WhatsAppCloudAPIClient(NotificationService):
    """
    WhatsApp Business Cloud API client.

    Primary notification channel for OTP and appointment confirmations.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)
        self.api_url = settings.WHATSAPP_API_URL
        self.api_token = settings.WHATSAPP_API_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

    def get_provider_name(self) -> str:
        return "whatsapp"

    def get_delivery_type(self) -> str:
        return "whatsapp"

    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str,
    ) -> tuple[bool, Optional[str]]:
        """Send message via WhatsApp Cloud API."""
        if not self.api_url or not self.api_token:
            logger.warning(
                "WhatsApp API not configured (api_url=%s, api_token=%s). "
                "Cannot send OTP via WhatsApp.",
                bool(self.api_url),
                bool(self.api_token),
            )
            return False, "WhatsApp API not configured"

        # Check idempotency
        if await self.check_idempotency(recipient, template_name):
            logger.info("WhatsApp idempotency check passed — skipping duplicate send to %s", recipient)
            return True, None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": recipient,
                        "type": "text",
                        "text": {"body": message},
                    },
                )

                if response.status_code == 200:
                    await self.log_notification(recipient, template_name, "sent")
                    logger.info("WhatsApp message sent successfully to %s", recipient)
                    return True, None
                else:
                    error = response.json().get("error", {}).get("message", "Unknown error")
                    await self.log_notification(
                        recipient, template_name, "failed", error_code=error
                    )
                    logger.error(
                        "WhatsApp API error for %s: status=%s, error=%s",
                        recipient,
                        response.status_code,
                        error,
                    )
                    return False, error

        except asyncio.TimeoutError:
            await self.log_notification(
                recipient, template_name, "failed", error_code="timeout"
            )
            logger.error("WhatsApp API timeout for %s after %ss", recipient, self.timeout)
            return False, "Timeout"
        except Exception as e:
            await self.log_notification(
                recipient, template_name, "failed", error_code=str(e)
            )
            logger.error("WhatsApp API exception for %s: %s", recipient, e, exc_info=True)
            return False, str(e)


# ── Termii SMS Client ─────────────────────────────────────────────────────────

class TermiiSMSClient(NotificationService):
    """
    Termii SMS gateway client.

    Nigerian SMS provider with DND-bypass capability.
    Used as primary SMS fallback.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)
        self.api_url = settings.TERMII_API_URL
        self.api_key = settings.TERMII_API_KEY
        self.sender_id = settings.TERMII_SENDER_ID

    def get_provider_name(self) -> str:
        return "termii"

    def get_delivery_type(self) -> str:
        return "sms"

    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str,
    ) -> tuple[bool, Optional[str]]:
        """Send message via Termii SMS API."""
        if not self.api_key:
            logger.warning(
                "Termii API not configured (api_key missing). Cannot send OTP via Termii."
            )
            return False, "Termii API not configured"

        # Check idempotency
        if await self.check_idempotency(recipient, template_name):
            logger.info("Termii idempotency check passed — skipping duplicate send to %s", recipient)
            return True, None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/sms/send",
                    headers={
                        "Content-Type": "application/json",
                    },
                    json={
                        "api_key": self.api_key,
                        "to": recipient,
                        "from": self.sender_id or "CMP",
                        "sms": message,
                        "type": "plain",
                        "channel": "dnd",  # DND-bypass
                    },
                )

                if response.status_code == 200:
                    await self.log_notification(recipient, template_name, "sent")
                    logger.info("Termii SMS sent successfully to %s", recipient)
                    return True, None
                else:
                    error = response.json().get("message", "Unknown error")
                    await self.log_notification(
                        recipient, template_name, "failed", error_code=error
                    )
                    logger.error(
                        "Termii API error for %s: status=%s, error=%s",
                        recipient,
                        response.status_code,
                        error,
                    )
                    return False, error

        except asyncio.TimeoutError:
            await self.log_notification(
                recipient, template_name, "failed", error_code="timeout"
            )
            logger.error("Termii API timeout for %s after %ss", recipient, self.timeout)
            return False, "Timeout"
        except Exception as e:
            await self.log_notification(
                recipient, template_name, "failed", error_code=str(e)
            )
            logger.error("Termii API exception for %s: %s", recipient, e, exc_info=True)
            return False, str(e)


# ── Infobip SMS Client ──────────────────────────────────────────────────────

class InfobipSMSClient(NotificationService):
    """
    Infobip SMS gateway client.

    International SMS provider. Used as secondary fallback.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)
        self.api_url = settings.INFOBIP_API_URL
        self.api_key = settings.INFOBIP_API_KEY
        self.base_url = settings.INFOBIP_BASE_URL

    def get_provider_name(self) -> str:
        return "infobip"

    def get_delivery_type(self) -> str:
        return "sms"

    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str,
    ) -> tuple[bool, Optional[str]]:
        """Send message via Infobip SMS API."""
        if not self.api_key:
            logger.warning(
                "Infobip API not configured (api_key missing). Cannot send OTP via Infobip."
            )
            return False, "Infobip API not configured"

        # Check idempotency
        if await self.check_idempotency(recipient, template_name):
            logger.info("Infobip idempotency check passed — skipping duplicate send to %s", recipient)
            return True, None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/sms/2/text/advanced",
                    headers={
                        "Authorization": f"App {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "messages": [
                            {
                                "from": "CMP",
                                "destinations": [{"to": recipient}],
                                "text": message,
                            }
                        ]
                    },
                )

                if response.status_code == 200:
                    await self.log_notification(recipient, template_name, "sent")
                    logger.info("Infobip SMS sent successfully to %s", recipient)
                    return True, None
                else:
                    error = response.json().get("requestError", {}).get("serviceException", {}).get("messageId", "Unknown error")
                    await self.log_notification(
                        recipient, template_name, "failed", error_code=error
                    )
                    logger.error(
                        "Infobip API error for %s: status=%s, error=%s",
                        recipient,
                        response.status_code,
                        error,
                    )
                    return False, error

        except asyncio.TimeoutError:
            await self.log_notification(
                recipient, template_name, "failed", error_code="timeout"
            )
            logger.error("Infobip API timeout for %s after %ss", recipient, self.timeout)
            return False, "Timeout"
        except Exception as e:
            await self.log_notification(
                recipient, template_name, "failed", error_code=str(e)
            )
            logger.error("Infobip API exception for %s: %s", recipient, e, exc_info=True)
            return False, str(e)


# ── Failover Orchestrator ───────────────────────────────────────────────────

class NotificationOrchestrator:
    """
    Orchestrates notification delivery with failover chain.

    Tries providers in order: WhatsApp → Termii → Infobip
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.providers: list[NotificationService] = [
            WhatsAppCloudAPIClient(db),
            TermiiSMSClient(db),
            InfobipSMSClient(db),
        ]

    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send notification with automatic failover.

        Args:
            recipient: Phone number or identifier
            message: Message content
            template_name: Template identifier

        Returns:
            tuple: (success, error_message, provider_used)
        """
        last_error = None
        provider_used = "none"

        for provider in self.providers:
            success, error = await provider.send(recipient, message, template_name)
            provider_used = provider.get_provider_name()

            if success:
                logger.info(
                    "Notification delivered via %s to %s", provider_used, recipient
                )
                return True, None, provider_used

            last_error = error
            logger.warning(
                "Provider %s failed for %s: %s — trying next provider",
                provider_used,
                recipient,
                error,
            )

        logger.error(
            "All notification providers failed for %s. Last error: %s",
            recipient,
            last_error,
        )
        return False, last_error, provider_used

    async def send_otp(
        self,
        phone_number: str,
        otp_code: str,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send OTP code to phone number.

        Args:
            phone_number: Recipient phone number
            otp_code: 6-digit OTP code

        Returns:
            tuple: (success, error_message, provider_used)
        """
        message = f"Your CMP verification code is: {otp_code}"
        return await self.send(phone_number, message, "otp_verification")

    async def send_appointment_confirmation(
        self,
        phone_number: str,
        appointment_details: dict,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send appointment confirmation to phone number.

        Args:
            phone_number: Recipient phone number
            appointment_details: Dict with appointment info

        Returns:
            tuple: (success, error_message, provider_used)
        """
        message = (
            f"Appointment confirmed: {appointment_details.get('doctor', 'Doctor')} "
            f"on {appointment_details.get('date', 'date')} "
            f"at {appointment_details.get('time', 'time')}"
        )
        return await self.send(phone_number, message, "appointment_confirmation")

    async def send_appointment_reminder(
        self,
        phone_number: str,
        appointment_details: dict,
        reminder_type: str,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send appointment reminder to phone number.

        Args:
            phone_number: Recipient phone number
            appointment_details: Dict with appointment info
            reminder_type: "24h" or "2h"

        Returns:
            tuple: (success, error_message, provider_used)
        """
        when = "tomorrow" if reminder_type == "24h" else "in 2 hours"
        message = (
            f"Appointment reminder: {appointment_details.get('doctor', 'Doctor')} "
            f"at {appointment_details.get('time', 'time')} {when}"
        )
        return await self.send(phone_number, message, f"appointment_reminder_{reminder_type}")

    async def send_cancellation_alert(
        self,
        phone_number: str,
        appointment_details: dict,
    ) -> tuple[bool, Optional[str], str]:
        """
        Send cancellation alert to phone number.

        Args:
            phone_number: Recipient phone number
            appointment_details: Dict with appointment info

        Returns:
            tuple: (success, error_message, provider_used)
        """
        message = (
            f"Appointment cancelled: {appointment_details.get('doctor', 'Doctor')} "
            f"on {appointment_details.get('date', 'date')}"
        )
        return await self.send(phone_number, message, "appointment_cancellation")
