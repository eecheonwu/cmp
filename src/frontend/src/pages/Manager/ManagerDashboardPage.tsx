/**
 * CMP Manager Dashboard Page.
 *
 * Implements Task 5.3 — Management Dashboard:
 * - Daily ops metrics load
 * - 30-second auto-refresh
 * - KPIs and charts for manager/executive roles
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import {
    getBranchDailyReport,
    getOrganizationSummary,
    getNotificationDeliveryStats,
    getBranches,
} from '../../services/report'
import type {
    BranchDailyReport,
    OrganizationSummaryReport,
    NotificationDeliveryStats,
} from '../../types/report'

// Format date for display
function formatDate(dateString: string): string {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
    })
}

// Simple bar chart component for utilization rates
function UtilizationBar({ rate }: { rate: number }) {
    const getColor = (rate: number) => {
        if (rate >= 80) return 'bg-green-500'
        if (rate >= 50) return 'bg-yellow-500'
        return 'bg-red-500'
    }

    return (
        <div className="w-full bg-gray-200 rounded-full h-4">
            <div
                className={`h-4 rounded-full ${getColor(rate)} transition-all duration-300`}
                style={{ width: `${Math.min(rate, 100)}%` }}
            />
        </div>
    )
}

// KPI Card component
function KPICard({
    title,
    value,
    subtitle,
    trend,
}: {
    title: string
    value: string | number
    subtitle?: string
    trend?: 'up' | 'down' | 'neutral'
}) {
    const trendColor = {
        up: 'text-green-600',
        down: 'text-red-600',
        neutral: 'text-gray-600',
    } as const

    return (
        <div className="rounded-lg bg-white p-6 shadow">
            <h3 className="text-sm font-medium text-gray-500">{title}</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
            {subtitle && (
                <p className={`mt-1 text-sm ${trendColor[trend || "neutral"]}`}>
                    {subtitle}
                </p>
            )}
        </div>
    )
}

export function ManagerDashboardPage() {
    const [branchDailyReport, setBranchDailyReport] = useState<BranchDailyReport | null>(null)
    const [organizationSummary, setOrganizationSummary] = useState<OrganizationSummaryReport | null>(null)
    const [notificationStats, setNotificationStats] = useState<NotificationDeliveryStats | null>(null)
    const [branches, setBranches] = useState<Array<{ id: string; name: string }>>([])
    const [selectedBranch, setSelectedBranch] = useState<string>('')
    const [selectedDate, setSelectedDate] = useState<string>(
        new Date().toISOString().split('T')[0]
    )
    const [dateRange, setDateRange] = useState({
        startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
    })
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true)

    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

    // Load initial data
    useEffect(() => {
        loadInitialData()
    }, [])

    // Set up auto-refresh (30 seconds)
    useEffect(() => {
        if (autoRefreshEnabled) {
            refreshIntervalRef.current = setInterval(() => {
                loadAllReports()
            }, 30000)
        }

        return () => {
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current)
            }
        }
    }, [autoRefreshEnabled, selectedBranch, selectedDate, dateRange])

    const loadInitialData = async () => {
        setIsLoading(true)
        setError(null)

        try {
            // Load branches
            const branchesData = await getBranches()
            setBranches(branchesData)
            if (branchesData.length > 0 && !selectedBranch) {
                setSelectedBranch(branchesData[0].id)
            }

            // Load all reports
            await loadAllReports()
        } catch (err) {
            setError('Failed to load dashboard data')
        } finally {
            setIsLoading(false)
        }
    }

    const loadAllReports = useCallback(async () => {
        if (!selectedBranch) return

        setError(null)
        try {
            // Load branch daily report
            const dailyReport = await getBranchDailyReport(selectedBranch, selectedDate)
            setBranchDailyReport(dailyReport)

            // Load organization summary
            const orgSummary = await getOrganizationSummary(dateRange.startDate, dateRange.endDate)
            setOrganizationSummary(orgSummary)

            // Load notification stats
            const notifStats = await getNotificationDeliveryStats(
                dateRange.startDate,
                dateRange.endDate
            )
            setNotificationStats(notifStats)

            setLastRefresh(new Date())
        } catch (err) {
            setError('Failed to load reports')
        }
    }, [selectedBranch, selectedDate, dateRange])

    // Load reports when branch or date changes
    useEffect(() => {
        if (selectedBranch) {
            loadAllReports()
        }
    }, [selectedBranch, selectedDate, dateRange, loadAllReports])

    const handleLogout = () => {
        if (refreshIntervalRef.current) {
            clearInterval(refreshIntervalRef.current)
        }
        logout()
        navigate('/login')
    }

    const handleManualRefresh = () => {
        loadAllReports()
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading dashboard...</div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow">
                <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <h1 className="text-2xl font-bold text-gray-900">
                            Management Dashboard
                        </h1>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-600">
                                {user?.phoneNumber}
                            </span>
                            <span className="text-xs text-gray-500">
                                Last refresh: {lastRefresh.toLocaleTimeString()}
                            </span>
                            <button
                                onClick={handleManualRefresh}
                                className="text-sm font-medium text-primary-600 hover:text-primary-500"
                            >
                                Refresh
                            </button>
                            <button
                                onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                                className={`text-sm font-medium ${autoRefreshEnabled
                                    ? 'text-green-600 hover:text-green-500'
                                    : 'text-gray-600 hover:text-gray-500'
                                    }`}
                            >
                                {autoRefreshEnabled ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
                            </button>
                            <button
                                onClick={handleLogout}
                                className="text-sm font-medium text-primary-600 hover:text-primary-500"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                {error && (
                    <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {/* Filters */}
                <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Branch
                        </label>
                        <select
                            value={selectedBranch}
                            onChange={(e) => setSelectedBranch(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {branches.map((branch) => (
                                <option key={branch.id} value={branch.id}>
                                    {branch.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Report Date
                        </label>
                        <input
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        />
                    </div>
                </div>

                {/* Branch Daily Report Section */}
                {branchDailyReport && (
                    <div className="mb-8">
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            Daily Operations - {formatDate(branchDailyReport.reportDate)}
                        </h2>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            <KPICard
                                title="Total Appointments"
                                value={branchDailyReport.totalAppointments}
                                subtitle="All appointments today"
                            />
                            <KPICard
                                title="Completed"
                                value={branchDailyReport.completedAppointments}
                                subtitle="Finished consultations"
                            />
                            <KPICard
                                title="Cancelled"
                                value={branchDailyReport.cancelledAppointments}
                                subtitle="Cancelled appointments"
                            />
                            <KPICard
                                title="No-show"
                                value={branchDailyReport.noShowAppointments}
                                subtitle="Missed appointments"
                            />
                        </div>
                        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="rounded-lg bg-white p-6 shadow">
                                <h3 className="text-sm font-medium text-gray-500">
                                    Utilization Rate
                                </h3>
                                <p className="mt-2 text-2xl font-bold text-gray-900">
                                    {branchDailyReport.utilizationRate}%
                                </p>
                                <div className="mt-4">
                                    <UtilizationBar rate={branchDailyReport.utilizationRate} />
                                </div>
                            </div>
                            <div className="rounded-lg bg-white p-6 shadow">
                                <h3 className="text-sm font-medium text-gray-500">
                                    Pending Appointments
                                </h3>
                                <p className="mt-2 text-2xl font-bold text-gray-900">
                                    {branchDailyReport.pendingAppointments}
                                </p>
                                <p className="mt-1 text-sm text-gray-600">
                                    Awaiting completion
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Organization Summary Section */}
                {organizationSummary && (
                    <div className="mb-8">
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            Organization Summary ({formatDate(organizationSummary.startDate)} - {formatDate(organizationSummary.endDate)})
                        </h2>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            <KPICard
                                title="Total Appointments"
                                value={organizationSummary.totalAppointments}
                                subtitle="Across all branches"
                            />
                            <KPICard
                                title="Completed"
                                value={organizationSummary.completedAppointments}
                                subtitle="All completed"
                            />
                            <KPICard
                                title="Cancelled"
                                value={organizationSummary.cancelledAppointments}
                                subtitle="All cancelled"
                            />
                            <KPICard
                                title="No-show"
                                value={organizationSummary.noShowAppointments}
                                subtitle="All missed"
                            />
                        </div>

                        {/* Branch breakdown */}
                        <div className="mt-6">
                            <h3 className="mb-3 text-md font-medium text-gray-700">
                                Per-Branch Utilization
                            </h3>
                            <div className="space-y-3">
                                {organizationSummary.branchSummaries.map((branch) => (
                                    <div
                                        key={branch.branchId}
                                        className="flex items-center justify-between rounded-lg bg-white p-4 shadow"
                                    >
                                        <div className="flex-1">
                                            <p className="font-medium text-gray-900">
                                                {branches.find((b) => b.id === branch.branchId)?.name || branch.branchId}
                                            </p>
                                            <p className="text-sm text-gray-500">
                                                {branch.totalAppointments} appointments
                                            </p>
                                        </div>
                                        <div className="w-32">
                                            <UtilizationBar rate={branch.utilizationRate} />
                                        </div>
                                        <p className="ml-4 w-16 text-right text-sm font-medium text-gray-900">
                                            {branch.utilizationRate}%
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Notification Delivery Section */}
                {notificationStats && (
                    <div className="mb-8">
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            Notification Delivery Metrics
                        </h2>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            <KPICard
                                title="Total Sent"
                                value={notificationStats.totalNotifications}
                                subtitle="All notifications"
                            />
                            <KPICard
                                title="Successful"
                                value={notificationStats.successfulDeliveries}
                                subtitle="Delivered successfully"
                            />
                            <KPICard
                                title="Failed"
                                value={notificationStats.failedDeliveries}
                                subtitle="Delivery failures"
                            />
                            <KPICard
                                title="Success Rate"
                                value={`${notificationStats.successRate}%`}
                                subtitle="Overall delivery rate"
                            />
                        </div>

                        {/* Provider breakdown */}
                        <div className="mt-6">
                            <h3 className="mb-3 text-md font-medium text-gray-700">
                                Per-Provider Statistics
                            </h3>
                            <div className="overflow-hidden rounded-lg bg-white shadow">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Provider
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Total
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Sent
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Failed
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Success Rate
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {Object.entries(notificationStats.providerStats).map(([provider, stats]) => (
                                            <tr key={provider}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                    {provider}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {stats.total}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">
                                                    {stats.sent}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">
                                                    {stats.failed}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {stats.successRate}%
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}