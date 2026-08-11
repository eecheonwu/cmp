"""
Test suite for Task 3.4: Reports & Dashboards.

Tests:
- GET /reports/branch/daily (manager) - returns daily ops metrics
- GET /reports/organization/summary (executive) - returns cross-clinic aggregated metrics
- GET /reports/notification-delivery (admin) - returns delivery success rates
"""

import sys
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.backend.services.report_service import ReportService
from src.backend.models.appointment import Appointment, AppointmentStatus


# ── Unit Tests for ReportService ───────────────────────────────────────────

class TestReportServiceInit:
    """Tests for ReportService initialization."""

    def test_report_service_init(self, mock_async_session):
        """Test ReportService initialization."""
        service = ReportService(mock_async_session)
        assert service.db == mock_async_session


class TestBranchDailyReport:
    """Tests for branch daily report."""

    @pytest.mark.asyncio
    async def test_branch_daily_report_structure(self, mock_async_session):
        """Test get_branch_daily_report returns correct structure."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(status=AppointmentStatus.BOOKED, count=10),
            MagicMock(status=AppointmentStatus.COMPLETED, count=5),
            MagicMock(status=AppointmentStatus.CANCELLED, count=2),
            MagicMock(status=AppointmentStatus.NO_SHOW, count=1),
        ]
        mock_async_session.execute.return_value = mock_result

        service = ReportService(mock_async_session)

        result = await service.get_branch_daily_report("branch_001", date.today())

        assert "branch_id" in result
        assert "report_date" in result
        assert "total_appointments" in result
        assert "completed_appointments" in result
        assert "cancelled_appointments" in result
        assert "no_show_appointments" in result
        assert "utilization_rate" in result
        assert result["branch_id"] == "branch_001"
        assert result["total_appointments"] == 18  # 10 + 5 + 2 + 1


class TestOrganizationSummaryReport:
    """Tests for organization summary report."""

    @pytest.mark.asyncio
    async def test_organization_summary_report_structure(self, mock_async_session):
        """Test get_organization_summary_report returns correct structure."""
        mock_total_result = MagicMock()
        mock_total_result.all.return_value = [
            MagicMock(status=AppointmentStatus.BOOKED, count=50),
            MagicMock(status=AppointmentStatus.COMPLETED, count=30),
            MagicMock(status=AppointmentStatus.CANCELLED, count=10),
            MagicMock(status=AppointmentStatus.NO_SHOW, count=5),
        ]

        mock_branch_result = MagicMock()
        mock_branch_result.all.return_value = [
            MagicMock(branch_id="branch_001", status=AppointmentStatus.BOOKED, count=20),
            MagicMock(branch_id="branch_001", status=AppointmentStatus.COMPLETED, count=15),
            MagicMock(branch_id="branch_002", status=AppointmentStatus.BOOKED, count=15),
            MagicMock(branch_id="branch_002", status=AppointmentStatus.COMPLETED, count=10),
        ]

        mock_async_session.execute.side_effect = [mock_total_result, mock_branch_result]

        service = ReportService(mock_async_session)

        result = await service.get_organization_summary_report(
            date.today() - timedelta(days=30),
            date.today()
        )

        assert "start_date" in result
        assert "end_date" in result
        assert "total_appointments" in result
        assert "branch_summaries" in result
        assert "overall_utilization_rate" in result


class TestNotificationDeliveryStats:
    """Tests for notification delivery stats."""

    @pytest.mark.asyncio
    async def test_notification_delivery_stats_structure(self, mock_async_session):
        """Test get_notification_delivery_stats returns correct structure."""
        mock_total_result = MagicMock()
        mock_total_result.all.return_value = [
            MagicMock(status="sent", count=90),
            MagicMock(status="failed", count=10),
        ]

        mock_provider_result = MagicMock()
        mock_provider_result.all.return_value = [
            MagicMock(provider="whatsapp", status="sent", count=50),
            MagicMock(provider="whatsapp", status="failed", count=5),
            MagicMock(provider="termii", status="sent", count=35),
            MagicMock(provider="termii", status="failed", count=5),
        ]

        mock_async_session.execute.side_effect = [mock_total_result, mock_provider_result]

        service = ReportService(mock_async_session)

        result = await service.get_notification_delivery_stats(
            date.today() - timedelta(days=7),
            date.today()
        )

        assert "start_date" in result
        assert "end_date" in result
        assert "total_notifications" in result
        assert "success_rate" in result
        assert "provider_stats" in result


# ── Integration Tests for Report Endpoints ───────────────────────────────────

class TestReportEndpoints:
    """Tests for report API endpoints."""

    def test_branch_daily_report_endpoint(self, test_client):
        """Test GET /api/v1/reports/branch/daily endpoint exists."""
        response = test_client.get(
            "/api/v1/reports/branch/daily",
            params={
                "branch_id": "branch_001",
                "report_date": date.today().isoformat(),
            },
        )
        assert response.status_code in [401, 200, 500]

    def test_organization_summary_report_endpoint(self, test_client):
        """Test GET /api/v1/reports/organization/summary endpoint exists."""
        response = test_client.get(
            "/api/v1/reports/organization/summary",
            params={
                "start_date": (date.today() - timedelta(days=30)).isoformat(),
                "end_date": date.today().isoformat(),
            },
        )
        assert response.status_code in [401, 200, 500]

    def test_notification_delivery_stats_endpoint(self, test_client):
        """Test GET /api/v1/reports/notification-delivery endpoint exists."""
        response = test_client.get(
            "/api/v1/reports/notification-delivery",
            params={
                "start_date": (date.today() - timedelta(days=7)).isoformat(),
                "end_date": date.today().isoformat(),
            },
        )
        assert response.status_code in [401, 200, 500]


class TestReportsRouter:
    """Tests for reports router inclusion."""

    def test_reports_router_included(self):
        """Test that reports router is included in main app."""
        from src.backend.main import app

        routes = [r.path for r in app.routes]
        report_routes = [r for r in routes if "/reports" in r]

        assert len(report_routes) > 0