"""
CMP Test Configuration and Shared Fixtures.

This conftest.py provides shared pytest fixtures for all backend tests.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backend.core.config import settings
from src.backend.main import app
from src.backend.models.user import User, UserRole, PatientProfile, VerificationOTP
from src.backend.models.appointment import (
    Appointment,
    AppointmentStatus,
    BookingSource,
    DoctorAvailability,
)
from src.backend.models.clinical_record import ClinicalRecord
from src.backend.models.notification import NotificationLog


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = "12345678-1234-5678-1234-567812345678"
    user.phone_number = "+2348012345678"
    user.email = "test@example.com"
    user.password_hash = "$2b$12$test_hash"
    user.role = UserRole.PATIENT
    return user


@pytest.fixture
def mock_doctor_user():
    """Create a mock doctor user for testing."""
    user = MagicMock(spec=User)
    user.id = "11111111-1111-1111-1111-111111111111"
    user.phone_number = "+2348011111111"
    user.email = "doctor@example.com"
    user.password_hash = "$2b$12$test_hash"
    user.role = UserRole.DOCTOR
    return user


@pytest.fixture
def mock_manager_user():
    """Create a mock manager user for testing."""
    user = MagicMock(spec=User)
    user.id = "22222222-2222-2222-2222-222222222222"
    user.phone_number = "+2348022222222"
    user.email = "manager@example.com"
    user.password_hash = "$2b$12$test_hash"
    user.role = UserRole.MANAGER
    return user


@pytest.fixture
def mock_appointment():
    """Create a mock appointment for testing."""
    appointment = MagicMock(spec=Appointment)
    appointment.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    appointment.doctor_id = "11111111-1111-1111-1111-111111111111"
    appointment.patient_id = "12345678-1234-5678-1234-567812345678"
    appointment.branch_id = "branch_001"
    appointment.start_datetime = datetime.now(timezone.utc) + timedelta(days=1)
    appointment.end_datetime = datetime.now(timezone.utc) + timedelta(days=1, hours=1)
    appointment.status = AppointmentStatus.BOOKED
    appointment.payment_state = "pending"
    appointment.booking_source = BookingSource.PATIENT
    return appointment


@pytest.fixture
def mock_otp():
    """Create a mock OTP for testing."""
    otp = MagicMock(spec=VerificationOTP)
    otp.id = "87654321-4321-4321-4324-876543218765"
    otp.phone_number = "+2348012345678"
    otp.hashed_otp = "$2b$12$test_otp_hash"
    otp.attempts = 0
    otp.is_used = False
    otp.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    otp.delivery_channel = "whatsapp"
    return otp


@pytest.fixture
def mock_doctor_availability():
    """Create a mock doctor availability for testing."""
    availability = MagicMock(spec=DoctorAvailability)
    availability.id = "99999999-9999-9999-9999-999999999999"
    availability.doctor_id = "11111111-1111-1111-1111-111111111111"
    availability.branch_id = "branch_001"
    availability.start_datetime = datetime.now(timezone.utc).replace(hour=9, minute=0)
    availability.end_datetime = datetime.now(timezone.utc).replace(hour=17, minute=0)
    availability.is_cancelled = False
    return availability


@pytest.fixture
def mock_notification_log():
    """Create a mock notification log for testing."""
    log = MagicMock(spec=NotificationLog)
    log.id = "notification-123"
    log.recipient = "+2348012345678"
    log.delivery_type = "whatsapp"
    log.provider = "whatsapp"
    log.template_name = "appointment_confirmation"
    log.status = "sent"
    log.error_code = None
    log.delivery_attempts = 1
    return log


@pytest.fixture
def mock_async_session():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    loop.close()
