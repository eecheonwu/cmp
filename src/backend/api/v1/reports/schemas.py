"""
CMP Reports Pydantic Schemas.

Request and response models for report endpoints.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Branch Daily Report Schemas ───────────────────────────────────────────────

class BranchDailyReportResponse(BaseModel):
    """Response schema for branch daily report."""

    branch_id: str = Field(..., description="Branch identifier")
    report_date: date = Field(..., description="Date of the report")
    total_appointments: int = Field(..., description="Total appointments for the day")
    completed_appointments: int = Field(..., description="Number of completed appointments")
    cancelled_appointments: int = Field(..., description="Number of cancelled appointments")
    no_show_appointments: int = Field(..., description="Number of no-show appointments")
    pending_appointments: int = Field(..., description="Number of pending appointments")
    utilization_rate: float = Field(..., description="Doctor utilization rate (0-100)")
    total_revenue: float = Field(default=0.0, description="Total revenue for the day (placeholder)")
    generated_at: datetime = Field(..., description="Report generation timestamp")

    class Config:
        from_attributes = True


# ── Organization Summary Report Schemas ─────────────────────────────────────

class BranchSummary(BaseModel):
    """Summary for a single branch in organization report."""

    branch_id: str = Field(..., description="Branch identifier")
    total_appointments: int = Field(..., description="Total appointments in period")
    completed_appointments: int = Field(..., description="Number of completed appointments")
    cancelled_appointments: int = Field(..., description="Number of cancelled appointments")
    no_show_appointments: int = Field(..., description="Number of no-show appointments")
    utilization_rate: float = Field(..., description="Doctor utilization rate (0-100)")


class OrganizationSummaryReportResponse(BaseModel):
    """Response schema for organization summary report."""

    start_date: date = Field(..., description="Start date of the report period")
    end_date: date = Field(..., description="End date of the report period")
    total_appointments: int = Field(..., description="Total appointments across all branches")
    completed_appointments: int = Field(..., description="Total completed appointments")
    cancelled_appointments: int = Field(..., description="Total cancelled appointments")
    no_show_appointments: int = Field(..., description="Total no-show appointments")
    overall_utilization_rate: float = Field(..., description="Overall utilization rate (0-100)")
    branch_summaries: list[BranchSummary] = Field(..., description="Per-branch summaries")
    generated_at: datetime = Field(..., description="Report generation timestamp")

    class Config:
        from_attributes = True


# ── Notification Delivery Report Schemas ─────────────────────────────────────

class NotificationDeliveryStatsResponse(BaseModel):
    """Response schema for notification delivery statistics."""

    start_date: date = Field(..., description="Start date of the report period")
    end_date: date = Field(..., description="End date of the report period")
    total_notifications: int = Field(..., description="Total notifications sent")
    successful_deliveries: int = Field(..., description="Number of successful deliveries")
    failed_deliveries: int = Field(..., description="Number of failed deliveries")
    success_rate: float = Field(..., description="Success rate percentage (0-100)")
    provider_stats: dict = Field(..., description="Per-provider delivery statistics")
    generated_at: datetime = Field(..., description="Report generation timestamp")

    class Config:
        from_attributes = True
