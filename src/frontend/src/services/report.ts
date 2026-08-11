/**
 * CMP Report Service for Manager Dashboard.
 *
 * Implements Task 5.3 — Management Dashboard:
 * - getBranchDailyReport: Fetch daily operational metrics for a branch
 * - getOrganizationSummary: Fetch organization-wide summary
 * - getNotificationDeliveryStats: Fetch notification delivery statistics
 */

import apiClient from './api'
import type {
    BranchDailyReport,
    OrganizationSummaryReport,
    NotificationDeliveryStats,
} from '../types/report'

// Get daily operational report for a branch
export const getBranchDailyReport = async (
    branchId: string,
    reportDate: string
): Promise<BranchDailyReport> => {
    const response = await apiClient.get<any>(
        `/reports/branch/daily?branch_id=${branchId}&report_date=${reportDate}`
    )
    return {
        branchId: response.data.branch_id,
        reportDate: response.data.report_date,
        totalAppointments: response.data.total_appointments,
        completedAppointments: response.data.completed_appointments,
        cancelledAppointments: response.data.cancelled_appointments,
        noShowAppointments: response.data.no_show_appointments,
        pendingAppointments: response.data.pending_appointments,
        utilizationRate: response.data.utilization_rate,
        totalRevenue: response.data.total_revenue,
        generatedAt: response.data.generated_at,
    }
}

// Get organization-wide summary report
export const getOrganizationSummary = async (
    startDate: string,
    endDate: string
): Promise<OrganizationSummaryReport> => {
    const response = await apiClient.get<any>(
        `/reports/organization/summary?start_date=${startDate}&end_date=${endDate}`
    )
    return {
        startDate: response.data.start_date,
        endDate: response.data.end_date,
        totalAppointments: response.data.total_appointments,
        completedAppointments: response.data.completed_appointments,
        cancelledAppointments: response.data.cancelled_appointments,
        noShowAppointments: response.data.no_show_appointments,
        overallUtilizationRate: response.data.overall_utilization_rate,
        branchSummaries: response.data.branch_summaries?.map((b: any) => ({
            branchId: b.branch_id,
            totalAppointments: b.total_appointments,
            completedAppointments: b.completed_appointments,
            cancelledAppointments: b.cancelled_appointments,
            noShowAppointments: b.no_show_appointments,
            utilizationRate: b.utilization_rate,
        })) || [],
        generatedAt: response.data.generated_at,
    }
}

// Get notification delivery statistics
export const getNotificationDeliveryStats = async (
    startDate: string,
    endDate: string
): Promise<NotificationDeliveryStats> => {
    const response = await apiClient.get<any>(
        `/reports/notification-delivery?start_date=${startDate}&end_date=${endDate}`
    )
    return {
        startDate: response.data.start_date,
        endDate: response.data.end_date,
        totalNotifications: response.data.total_notifications,
        successfulDeliveries: response.data.successful_deliveries,
        failedDeliveries: response.data.failed_deliveries,
        successRate: response.data.success_rate,
        providerStats: response.data.provider_stats,
        generatedAt: response.data.generated_at,
    }
}

// Get branches (mock implementation - would call real API)
export const getBranches = async (): Promise<Array<{ id: string; name: string }>> => {
    // In production, this would call the actual API
    // For now, return mock data
    return [
        { id: 'branch-1', name: 'Main Clinic' },
        { id: 'branch-2', name: 'Branch Clinic A' },
        { id: 'branch-3', name: 'Branch Clinic B' },
    ]
}