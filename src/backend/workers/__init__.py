"""
CMP Celery Workers Package.

Provides async task processing for notifications.
"""

from workers.celery_app import celery_app
from workers.tasks import (
    send_otp_task,
    send_appointment_confirmation_task,
    send_appointment_reminder_task,
    send_cancellation_alert_task,
)

__all__ = [
    "celery_app",
    "send_otp_task",
    "send_appointment_confirmation_task",
    "send_appointment_reminder_task",
    "send_cancellation_alert_task",
]
