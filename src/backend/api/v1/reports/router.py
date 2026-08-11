"""
CMP Reports API Router.

Implements Task 3.4 — Reports & Dashboards:
- GET /reports/branch/daily (manager)
- GET /reports/organization/summary (executive)
- GET /reports/notification-delivery (admin)
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import RoleChecker
from db.session import get_db
from models.user import UserRole
from services.report_service import ReportService
from api.v1.reports.schemas import (
    BranchDailyReportResponse,
    OrganizationSummaryReportResponse,
    NotificationDeliveryStatsResponse,
)

# Create router
router = APIRouter()


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Get report service instance."""
    return ReportService(db)


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get(
    "/reports/branch/daily",
    response_model=BranchDailyReportResponse,
    tags=["reports"],
)
async def get_branch_daily_report(
    branch_id: str = Query(..., description="Branch identifier"),
    report_date: date = Query(default=date.today(), description="Report date (defaults to today)"),
    current_user: UserRole = Depends(RoleChecker([UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily operational report for a branch.

    Access: manager only

    Returns:
        - Total appointments for the day
        - Completed, cancelled, no-show counts
        - Utilization rate
    """
    service = ReportService(db)
    report = await service.get_branch_daily_report(branch_id, report_date)
    return BranchDailyReportResponse(**report)


@router.get(
    "/reports/organization/summary",
    response_model=OrganizationSummaryReportResponse,
    tags=["reports"],
)
async def get_organization_summary(
    start_date: date = Query(..., description="Start date of report period"),
    end_date: date = Query(..., description="End date of report period"),
    current_user: UserRole = Depends(RoleChecker([UserRole.EXECUTIVE])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get organization-wide summary report.

    Access: executive only

    Returns:
        - Total appointments across all branches
        - Per-branch breakdowns
        - Overall utilization rate
    """
    service = ReportService(db)
    report = await service.get_organization_summary_report(start_date, end_date)
    return OrganizationSummaryReportResponse(**report)


@router.get(
    "/reports/notification-delivery",
    response_model=NotificationDeliveryStatsResponse,
    tags=["reports"],
)
async def get_notification_delivery_stats(
    start_date: date = Query(..., description="Start date of report period"),
    end_date: date = Query(..., description="End date of report period"),
    current_user: UserRole = Depends(RoleChecker([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification delivery statistics.

    Access: admin only

    Returns:
        - Total notifications sent
        - Success/failure counts
        - Per-provider delivery rates
    """
    service = ReportService(db)
    stats = await service.get_notification_delivery_stats(start_date, end_date)
    return NotificationDeliveryStatsResponse(**stats)
