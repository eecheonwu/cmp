"""
CMP Report Service.

Implements Task 3.4 — Reports & Dashboards:
- Branch daily report aggregation
- Organization summary report aggregation
- Notification delivery statistics
"""

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment, AppointmentStatus
from models.notification import NotificationLog


class ReportService:
    """
    Report generation service for operational metrics.

    Provides aggregated data for:
    - Branch daily operations (manager access)
    - Organization-wide summaries (executive access)
    - Notification delivery statistics (admin access)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Branch Daily Report ───────────────────────────────────────────────────

    async def get_branch_daily_report(
        self,
        branch_id: str,
        report_date: date,
    ) -> dict:
        """
        Get daily operational report for a branch.

        Args:
            branch_id: Branch identifier
            report_date: Date for the report

        Returns:
            Dictionary with daily metrics:
            - total_appointments: Count of all appointments
            - completed_appointments: Count of completed
            - cancelled_appointments: Count of cancelled
            - no_show_appointments: Count of no-shows
            - pending_appointments: Count of booked (pending)
            - utilization_rate: Doctor time utilization percentage
        """
        # Calculate date range for the day
        start_of_day = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)

        # Query for appointment counts by status
        query = (
            select(
                Appointment.status,
                func.count(Appointment.id).label("count"),
            )
            .where(
                and_(
                    Appointment.branch_id == branch_id,
                    Appointment.start_datetime >= start_of_day,
                    Appointment.start_datetime < end_of_day,
                )
            )
            .group_by(Appointment.status)
        )

        result = await self.db.execute(query)
        status_counts = {row.status: row.count for row in result.all()}

        # Calculate total and utilization
        total_appointments = sum(status_counts.values())
        booked_count = status_counts.get(AppointmentStatus.BOOKED, 0)

        # Get total available slots for the day to calculate utilization
        # This would require doctor_availability table - simplified for now
        # Utilization = (booked time / available time) * 100
        utilization_rate = 0.0
        if total_appointments > 0:
            # Simplified: assume 8 hours per doctor per day, 100% if all slots filled
            utilization_rate = min(100.0, (booked_count / max(total_appointments, 1)) * 100)

        return {
            "branch_id": branch_id,
            "report_date": report_date,
            "total_appointments": total_appointments,
            "completed_appointments": status_counts.get(AppointmentStatus.COMPLETED, 0),
            "cancelled_appointments": status_counts.get(AppointmentStatus.CANCELLED, 0),
            "no_show_appointments": status_counts.get(AppointmentStatus.NO_SHOW, 0),
            "pending_appointments": status_counts.get(AppointmentStatus.BOOKED, 0),
            "utilization_rate": round(utilization_rate, 2),
            "total_revenue": 0.0,  # Placeholder for Phase 2 payment integration
            "generated_at": datetime.now(timezone.utc),
        }

    # ── Organization Summary Report ───────────────────────────────────────────

    async def get_organization_summary_report(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Get organization-wide summary report.

        Args:
            start_date: Start date of the report period
            end_date: End date of the report period

        Returns:
            Dictionary with organization metrics and per-branch breakdowns
        """
        # Calculate date range
        start_of_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc) + timedelta(days=1)

        # Query for total counts
        total_query = (
            select(
                Appointment.status,
                func.count(Appointment.id).label("count"),
            )
            .where(
                and_(
                    Appointment.start_datetime >= start_of_start,
                    Appointment.start_datetime < end_of_end,
                )
            )
            .group_by(Appointment.status)
        )

        result = await self.db.execute(total_query)
        total_status_counts = {row.status: row.count for row in result.all()}

        # Query for per-branch counts
        branch_query = (
            select(
                Appointment.branch_id,
                Appointment.status,
                func.count(Appointment.id).label("count"),
            )
            .where(
                and_(
                    Appointment.start_datetime >= start_of_start,
                    Appointment.start_datetime < end_of_end,
                )
            )
            .group_by(Appointment.branch_id, Appointment.status)
        )

        result = await self.db.execute(branch_query)
        branch_data = {}
        for row in result.all():
            if row.branch_id not in branch_data:
                branch_data[row.branch_id] = {}
            branch_data[row.branch_id][row.status] = row.count

        # Build branch summaries
        branch_summaries = []
        for branch_id, status_counts in branch_data.items():
            branch_total = sum(status_counts.values())
            branch_summaries.append({
                "branch_id": branch_id,
                "total_appointments": branch_total,
                "completed_appointments": status_counts.get(AppointmentStatus.COMPLETED, 0),
                "cancelled_appointments": status_counts.get(AppointmentStatus.CANCELLED, 0),
                "no_show_appointments": status_counts.get(AppointmentStatus.NO_SHOW, 0),
                "utilization_rate": round(
                    (status_counts.get(AppointmentStatus.BOOKED, 0) / max(branch_total, 1)) * 100,
                    2
                ),
            })

        # Calculate overall utilization
        total_appointments = sum(total_status_counts.values())
        overall_utilization = 0.0
        if total_appointments > 0:
            overall_utilization = round(
                (total_status_counts.get(AppointmentStatus.BOOKED, 0) / total_appointments) * 100,
                2
            )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_appointments": total_appointments,
            "completed_appointments": total_status_counts.get(AppointmentStatus.COMPLETED, 0),
            "cancelled_appointments": total_status_counts.get(AppointmentStatus.CANCELLED, 0),
            "no_show_appointments": total_status_counts.get(AppointmentStatus.NO_SHOW, 0),
            "overall_utilization_rate": overall_utilization,
            "branch_summaries": branch_summaries,
            "generated_at": datetime.now(timezone.utc),
        }

    # ── Notification Delivery Statistics ─────────────────────────────────────

    async def get_notification_delivery_stats(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Get notification delivery statistics.

        Args:
            start_date: Start date of the report period
            end_date: End date of the report period

        Returns:
            Dictionary with delivery metrics and per-provider breakdowns
        """
        # Calculate date range
        start_of_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc) + timedelta(days=1)

        # Query for total counts
        total_query = (
            select(
                NotificationLog.status,
                func.count(NotificationLog.id).label("count"),
            )
            .where(
                and_(
                    NotificationLog.created_at >= start_of_start,
                    NotificationLog.created_at < end_of_end,
                )
            )
            .group_by(NotificationLog.status)
        )

        result = await self.db.execute(total_query)
        status_counts = {row.status: row.count for row in result.all()}

        # Query for per-provider counts
        provider_query = (
            select(
                NotificationLog.provider,
                NotificationLog.status,
                func.count(NotificationLog.id).label("count"),
            )
            .where(
                and_(
                    NotificationLog.created_at >= start_of_start,
                    NotificationLog.created_at < end_of_end,
                )
            )
            .group_by(NotificationLog.provider, NotificationLog.status)
        )

        result = await self.db.execute(provider_query)
        provider_data = {}
        for row in result.all():
            if row.provider not in provider_data:
                provider_data[row.provider] = {}
            provider_data[row.provider][row.status] = row.count

        # Build provider stats
        provider_stats = {}
        for provider, status_counts in provider_data.items():
            provider_total = sum(status_counts.values())
            provider_stats[provider] = {
                "total": provider_total,
                "sent": status_counts.get("sent", 0),
                "failed": status_counts.get("failed", 0),
                "success_rate": round(
                    (status_counts.get("sent", 0) / max(provider_total, 1)) * 100,
                    2
                ),
            }

        # Calculate overall success rate
        total_notifications = sum(status_counts.values())
        successful = status_counts.get("sent", 0)
        success_rate = 0.0
        if total_notifications > 0:
            success_rate = round((successful / total_notifications) * 100, 2)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_notifications": total_notifications,
            "successful_deliveries": successful,
            "failed_deliveries": status_counts.get("failed", 0),
            "success_rate": success_rate,
            "provider_stats": provider_stats,
            "generated_at": datetime.now(timezone.utc),
        }
