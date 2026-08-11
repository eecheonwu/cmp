/**
 * CMP Report Types for Manager Dashboard.
 *
 * Implements Task 5.3 — Management Dashboard:
 * - Branch daily report types
 * - Organization summary report types
 * - Notification delivery statistics types
 */

// ── Branch Daily Report Types ───────────────────────────────────────────────

export interface BranchDailyReport {
    branchId: string
    reportDate: string
    totalAppointments: number
    completedAppointments: number
    cancelledAppointments: number
    noShowAppointments: number
    pendingAppointments: number
    utilizationRate: number
    totalRevenue: number
    generatedAt: string
}

// ── Organization Summary Report Types ─────────────────────────────────────

export interface BranchSummary {
    branchId: string
    totalAppointments: number
    completedAppointments: number
    cancelledAppointments: number
    noShowAppointments: number
    utilizationRate: number
}

export interface OrganizationSummaryReport {
    startDate: string
    endDate: string
    totalAppointments: number
    completedAppointments: number
    cancelledAppointments: number
    noShowAppointments: number
    overallUtilizationRate: number
    branchSummaries: BranchSummary[]
    generatedAt: string
}

// ── Notification Delivery Statistics Types ─────────────────────────────────

export interface ProviderStats {
    total: number
    sent: number
    failed: number
    successRate: number
}

export interface NotificationDeliveryStats {
    startDate: string
    endDate: string
    totalNotifications: number
    successfulDeliveries: number
    failedDeliveries: number
    successRate: number
    providerStats: Record<string, ProviderStats>
    generatedAt: string
}

// ── Manager Dashboard State Types ───────────────────────────────────────

export interface ManagerDashboardState {
    branchDailyReport: BranchDailyReport | null
    organizationSummary: OrganizationSummaryReport | null
    notificationStats: NotificationDeliveryStats | null
    selectedBranch: string
    selectedDate: string
    dateRange: {
        startDate: string
        endDate: string
    }
    isLoading: boolean
    error: string | null
}