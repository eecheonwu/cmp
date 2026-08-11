
"""
CMP Celery Application Configuration.

Configures Celery with Redis as broker for async task processing.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from celery import Celery

from core.config import settings


# Create Celery application
celery_app = Celery(
    "cmp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time for reliability
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
)

# Task routing — uses the explicit task names defined via @shared_task(name=...)
celery_app.conf.task_routes = {
    "send_otp_task": {"queue": "notifications"},
    "send_appointment_confirmation_task": {"queue": "notifications"},
    "send_appointment_reminder_task": {"queue": "notifications"},
    "send_cancellation_alert_task": {"queue": "notifications"},
}


if __name__ == "__main__":
    # Start worker
    celery_app.start()
