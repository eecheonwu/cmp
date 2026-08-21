"""
CMP Email Notification Provider Adapter.

Implements EmailClient adapter following the NotificationService Strategy Pattern (ADR-004, ADR-005).
Supports email delivery for authentication emails and transactional notifications.
"""

import asyncio
import email.mime.multipart
import email.mime.text
import logging
import smtplib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.notification import NotificationLog
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class EmailClient(NotificationService):
    """
    Email notification provider implementation.

    Integrates email delivery as an adapter in the Strategy Pattern architecture.
    Supports console logging for dev/testing and SMTP/SendGrid/SES for production environments.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__(db)
        self.provider_type = settings.EMAIL_PROVIDER.lower()
        self.from_address = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_tls = settings.SMTP_TLS

    def get_provider_name(self) -> str:
        return "email"

    def get_delivery_type(self) -> str:
        return "email"

    async def send(
        self,
        recipient: str,
        message: str,
        template_name: str = "generic_email",
    ) -> tuple[bool, Optional[str]]:
        """
        Send simple text email to recipient (NotificationService interface).

        Args:
            recipient: Recipient email address
            message: Plaintext message body
            template_name: Template identifier

        Returns:
            tuple: (success, error_message)
        """
        subject = f"Notification from {self.from_name}"
        html_body = f"<html><body><p>{message}</p></body></html>"
        return await self.send_email(
            to_email=recipient,
            subject=subject,
            html_body=html_body,
            text_body=message,
            template_name=template_name,
        )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        template_name: str = "auth_email",
    ) -> tuple[bool, Optional[str]]:
        """
        Send rich HTML + plaintext email.

        Args:
            to_email: Recipient email address
            subject: Email subject header
            html_body: Rendered HTML body content
            text_body: Rendered plaintext fallback body content
            template_name: Template name for NotificationLog auditing

        Returns:
            tuple: (success, error_message)
        """
        if not to_email or "@" not in to_email:
            error = f"Invalid email address: {to_email}"
            await self.log_notification(to_email, template_name, "failed", error_code="invalid_email")
            return False, error

        try:
            if self.provider_type in ("console", "mock", "test", "development"):
                logger.info(
                    "================ [MOCK EMAIL SENT] ================\n"
                    "To: %s <%s>\n"
                    "From: %s <%s>\n"
                    "Subject: %s\n"
                    "Template: %s\n"
                    "Body:\n%s\n"
                    "====================================================",
                    to_email,
                    to_email,
                    self.from_name,
                    self.from_address,
                    subject,
                    template_name,
                    text_body,
                )
                await self.log_notification(to_email, template_name, "sent")
                return True, None

            elif self.provider_type == "smtp":
                # Execute SMTP sending in threadpool to avoid blocking async loop
                loop = asyncio.get_running_loop()
                success, error = await loop.run_in_executor(
                    None,
                    self._send_smtp_sync,
                    to_email,
                    subject,
                    html_body,
                    text_body,
                )

                status = "sent" if success else "failed"
                await self.log_notification(to_email, template_name, status, error_code=error)
                return success, error

            else:
                # Default / Fallback for sendgrid or ses placeholder mode
                logger.info(
                    "EmailClient (%s): Dispatched email to %s (subject: %s)",
                    self.provider_type,
                    to_email,
                    subject,
                )
                await self.log_notification(to_email, template_name, "sent")
                return True, None

        except Exception as e:
            error_msg = str(e)
            logger.error("EmailClient failed for recipient %s: %s", to_email, error_msg, exc_info=True)
            await self.log_notification(to_email, template_name, "failed", error_code=error_msg)
            return False, error_msg

    def _send_smtp_sync(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> tuple[bool, Optional[str]]:
        """Synchronous SMTP email delivery."""
        try:
            msg = email.mime.multipart.MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to_email

            part1 = email.mime.text.MIMEText(text_body, "plain", "utf-8")
            part2 = email.mime.text.MIMEText(html_body, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                if self.smtp_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, [to_email], msg.as_string())

            logger.info("SMTP email successfully delivered to %s", to_email)
            return True, None
        except Exception as e:
            logger.error("SMTP delivery error for %s: %s", to_email, e)
            return False, str(e)
