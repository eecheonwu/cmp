"""
CMP Celery Tasks for Notification Processing.

Async tasks for:
- OTP delivery
- Appointment confirmations
- Appointment reminders (24h and 2h)
- Cancellation alerts
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from celery import shared_task

from core.config import settings
from db.session import AsyncSessionLocal
from models.user import VerificationOTP
from services.notification_service import NotificationOrchestrator

logger = logging.getLogger(__name__)


# ── Helper Functions ───────────────────────────────────────────────────────

async def _get_db_session():
    """Get async database session for task context."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.database_url_async, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()


# ── OTP Task ───────────────────────────────────────────────────────────────

@shared_task(
    name="send_otp_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_otp_task(
    self,
    verification_id: str,
    otp_code: str,
) -> dict:
    """
    Send OTP via notification orchestrator.

    Args:
        verification_id: UUID of the VerificationOTP record
        otp_code: Plain text OTP code to send

    Returns:
        dict with success status and provider used

    Note:
        This task does NOT require a User record to exist. The phone number
        is retrieved directly from the VerificationOTP record, which is
        created before the user account during the registration flow.
        Previously, this task looked up a User by phone number and returned
        early with "User not found" when no user existed yet — preventing
        OTP delivery for the registration flow.
    """
    import asyncio

    async def _send():
        async for db in _get_db_session():
            # Get OTP record
            from sqlalchemy import select
            result = await db.execute(
                select(VerificationOTP).where(VerificationOTP.id == verification_id)
            )
            otp = result.scalar_one_or_none()

            if not otp:
                logger.error(
                    "send_otp_task: OTP record not found (verification_id=%s)",
                    verification_id,
                )
                return {"success": False, "error": "OTP not found"}

            # Send via orchestrator with the actual OTP code.
            # The phone number comes directly from the OTP record — no User
            # lookup is needed. This is critical for the registration flow
            # where the user account is created AFTER OTP verification.
            orchestrator = NotificationOrchestrator(db)
            success, error, provider = await orchestrator.send_otp(
                otp.phone_number,
                otp_code,
            )

            if success:
                logger.info(
                    "send_otp_task: OTP delivered via %s to %s (verification_id=%s)",
                    provider,
                    otp.phone_number,
                    verification_id,
                )
            else:
                logger.error(
                    "send_otp_task: OTP delivery FAILED via %s to %s: %s "
                    "(verification_id=%s)",
                    provider,
                    otp.phone_number,
                    error,
                    verification_id,
                )

            return {
                "success": success,
                "error": error,
                "provider": provider,
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        logger.error(
            "send_otp_task: Exception during OTP delivery "
            "(verification_id=%s): %s",
            verification_id,
            e,
            exc_info=True,
        )
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}


# ── Appointment Confirmation Task ───────────────────────────────────────────

@shared_task(
    name="send_appointment_confirmation_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_appointment_confirmation_task(
    self,
    appointment_id: str,
) -> dict:
    """
    Send appointment confirmation via notification orchestrator.

    Args:
        appointment_id: UUID of the appointment

    Returns:
        dict with success status and provider used
    """
    import asyncio

    async def _send():
        async for db in _get_db_session():
            # Get appointment
            from sqlalchemy import select
            result = await db.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalar_one_or_none()

            if not appointment:
                return {"success": False, "error": "Appointment not found"}

            # Get patient phone
            result = await db.execute(
                select(User).where(User.id == appointment.patient_id)
            )
            patient = result.scalar_one_or_none()

            if not patient:
                return {"success": False, "error": "Patient not found"}

            # Send via orchestrator
            orchestrator = NotificationOrchestrator(db)
            success, error, provider = await orchestrator.send_appointment_confirmation(
                patient.phone_number,
                {
                    "doctor": "Doctor",
                    "date": str(appointment.start_datetime.date()) if appointment.start_datetime else "date",
                    "time": str(appointment.start_datetime.time()) if appointment.start_datetime else "time",
                },
            )

            return {
                "success": success,
                "error": error,
                "provider": provider,
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}


# ── Appointment Reminder Task ───────────────────────────────────────────────

@shared_task(
    name="send_appointment_reminder_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_appointment_reminder_task(
    self,
    appointment_id: str,
    reminder_type: str = "24h",
) -> dict:
    """
    Send appointment reminder via notification orchestrator.

    Args:
        appointment_id: UUID of the appointment
        reminder_type: "24h" or "2h"

    Returns:
        dict with success status and provider used
    """
    import asyncio

    async def _send():
        async for db in _get_db_session():
            # Get appointment
            from sqlalchemy import select
            result = await db.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalar_one_or_none()

            if not appointment:
                return {"success": False, "error": "Appointment not found"}

            # Get patient phone
            result = await db.execute(
                select(User).where(User.id == appointment.patient_id)
            )
            patient = result.scalar_one_or_none()

            if not patient:
                return {"success": False, "error": "Patient not found"}

            # Send via orchestrator
            orchestrator = NotificationOrchestrator(db)
            success, error, provider = await orchestrator.send_appointment_reminder(
                patient.phone_number,
                {
                    "doctor": "Doctor",
                    "time": str(appointment.start_datetime.time()) if appointment.start_datetime else "time",
                },
                reminder_type,
            )

            return {
                "success": success,
                "error": error,
                "provider": provider,
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}


# ── Cancellation Alert Task ───────────────────────────────────────────────────

@shared_task(
    name="send_cancellation_alert_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_cancellation_alert_task(
    self,
    appointment_id: str,
) -> dict:
    """
    Send cancellation alert via notification orchestrator.

    Args:
        appointment_id: UUID of the appointment

    Returns:
        dict with success status and provider used
    """
    import asyncio

    async def _send():
        async for db in _get_db_session():
            # Get appointment
            from sqlalchemy import select
            result = await db.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalar_one_or_none()

            if not appointment:
                return {"success": False, "error": "Appointment not found"}

            # Get patient phone
            result = await db.execute(
                select(User).where(User.id == appointment.patient_id)
            )
            patient = result.scalar_one_or_none()

            if not patient:
                return {"success": False, "error": "Patient not found"}

            # Send via orchestrator
            orchestrator = NotificationOrchestrator(db)
            success, error, provider = await orchestrator.send_cancellation_alert(
                patient.phone_number,
                {
                    "doctor": "Doctor",
                    "date": str(appointment.start_datetime.date()) if appointment.start_datetime else "date",
                },
            )

            return {
                "success": success,
                "error": error,
                "provider": provider,
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}


# ── Auth Email Delivery Task ───────────────────────────────────────────────

@shared_task(
    name="send_auth_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_auth_email(
    self,
    to_email: str,
    verification_token: str,
    full_name: Optional[str] = None,
) -> dict:
    """
    Send authentication verification email containing password creation link.

    Args:
        to_email: Recipient email address
        verification_token: Plaintext URL verification token
        full_name: Optional recipient name

    Returns:
        dict with success status and provider used
    """
    import asyncio
    from services.notification.providers.email_provider import EmailClient

    async def _send():
        async for db in _get_db_session():
            client = EmailClient(db)
            verification_url = f"{settings.EMAIL_VERIFICATION_BASE_URL}?token={verification_token}"
            recipient_name = full_name or "Patient"

            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Verify Email</title></head>
<body style="font-family: sans-serif; padding: 20px;">
    <h2>Clinic Modernization Platform</h2>
    <p>Hello {recipient_name},</p>
    <p>Please click the link below to verify your email and set your password:</p>
    <p><a href="{verification_url}" style="background: #0056b3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Create Password</a></p>
    <p>Or copy this URL: {verification_url}</p>
    <p>This link expires in 60 minutes.</p>
</body>
</html>"""

            text_body = (
                f"Hello {recipient_name},\n\n"
                f"Please verify your email and create your password by visiting:\n"
                f"{verification_url}\n\n"
                f"This link expires in 60 minutes.\n\n"
                f"Clinic Modernization Platform"
            )

            subject = "Verify Your Email - Clinic Modernization Platform"
            success, error = await client.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                template_name="auth_email",
            )

            if success:
                logger.info("send_auth_email: Auth email sent to %s", to_email)
            else:
                logger.error("send_auth_email: Failed to send to %s: %s", to_email, error)

            return {
                "success": success,
                "error": error,
                "provider": "email",
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        logger.error("send_auth_email exception for %s: %s", to_email, e, exc_info=True)
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}


@shared_task(
    name="send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notification(
    self,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    template_name: str = "generic_notification",
) -> dict:
    """
    Send general transactional email.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML body string
        text_body: Plaintext body string
        template_name: Audit log template tag

    Returns:
        dict with success status and provider used
    """
    import asyncio
    from services.notification.providers.email_provider import EmailClient

    async def _send():
        async for db in _get_db_session():
            client = EmailClient(db)
            success, error = await client.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                template_name=template_name,
            )

            return {
                "success": success,
                "error": error,
                "provider": "email",
            }

    try:
        return asyncio.run(_send())
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {"success": False, "error": str(e)}

