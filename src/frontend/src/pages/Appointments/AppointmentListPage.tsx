import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getAppointments, cancelAppointment } from '../../services/appointment'
import { cacheAppointments, getCachedAppointments, clearOfflineCache } from '../../services/db'
import type { Appointment, AppointmentStatus } from '../../types/appointment'

// Status badge component
function StatusBadge({ status }: { status: AppointmentStatus }) {
    const statusConfig = {
        booked: { label: 'Booked', className: 'bg-blue-100 text-blue-800' },
        cancelled: { label: 'Cancelled', className: 'bg-gray-100 text-gray-800' },
        completed: { label: 'Completed', className: 'bg-green-100 text-green-800' },
        'no-show': { label: 'No Show', className: 'bg-red-100 text-red-800' },
    }

    const config = statusConfig[status]

    return (
        <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
        >
            {config.label}
        </span>
    )
}

// Format date for display
function formatDateTime(dateString: string): string {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    })
}

// Check if cancellation is within 2 hours (Tier 1 penalty)
function isWithinTwoHours(dateString: string): boolean {
    const appointmentTime = new Date(dateString)
    const now = new Date()
    const diffHours = (appointmentTime.getTime() - now.getTime()) / (1000 * 60 * 60)
    return diffHours < 2
}

export function AppointmentListPage() {
    const [appointments, setAppointments] = useState<Appointment[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [cancellingId, setCancellingId] = useState<string | null>(null)
    const [showCancelConfirm, setShowCancelConfirm] = useState<string | null>(null)
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        loadAppointments()
    }, [])

    const loadAppointments = async () => {
        setIsLoading(true)
        setError(null)

        try {
            const data = await getAppointments()
            setAppointments(data)
            // Cache for offline access
            await cacheAppointments(data)
        } catch (err) {
            // Try to load from cache
            const cached = await getCachedAppointments()
            if (cached.length > 0) {
                setAppointments(cached)
            } else {
                setError('Failed to load appointments')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const handleCancel = async (appointmentId: string) => {
        setCancellingId(appointmentId)

        try {
            await cancelAppointment(appointmentId)
            // Update local state
            setAppointments(
                appointments.map((a) =>
                    a.id === appointmentId
                        ? { ...a, status: 'cancelled' as AppointmentStatus }
                        : a
                )
            )
            setShowCancelConfirm(null)
        } catch (err) {
            setError('Failed to cancel appointment')
        } finally {
            setCancellingId(null)
        }
    }

    const handleLogout = () => {
        clearOfflineCache()
        logout()
        navigate('/login')
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading appointments...</div>
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
                            My Appointments
                        </h1>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-600">
                                {user?.phoneNumber}
                            </span>
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

                {/* New Appointment Button */}
                <div className="mb-6">
                    <Link
                        to="/appointments/new"
                        className="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                    >
                        Book New Appointment
                    </Link>
                </div>

                {/* Appointments List */}
                {appointments.length === 0 ? (
                    <div className="rounded-lg bg-white p-6 text-center">
                        <p className="text-gray-500">No appointments found</p>
                        <Link
                            to="/appointments/new"
                            className="mt-4 inline-block text-sm font-medium text-primary-600 hover:text-primary-500"
                        >
                            Book your first appointment
                        </Link>
                    </div>
                ) : (
                    <div className="overflow-hidden rounded-lg bg-white shadow">
                        <ul className="divide-y divide-gray-200">
                            {appointments.map((appointment) => (
                                <li key={appointment.id} className="p-6">
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center justify-between">
                                                <h3 className="text-lg font-medium text-gray-900">
                                                    Appointment #{appointment.id.slice(0, 8)}
                                                </h3>
                                                <StatusBadge status={appointment.status} />
                                            </div>
                                            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                                <div>
                                                    <p className="text-sm text-gray-500">
                                                        Date & Time
                                                    </p>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {formatDateTime(appointment.startDatetime)}
                                                    </p>
                                                </div>
                                                <div>
                                                    <p className="text-sm text-gray-500">
                                                        Branch
                                                    </p>
                                                    <p className="text-sm font-medium text-gray-900">
                                                        {appointment.branchId}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Action buttons */}
                                        {appointment.status === 'booked' && (
                                            <div className="ml-4 flex space-x-2">
                                                <Link
                                                    to={`/appointments/${appointment.id}/reschedule`}
                                                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                                                >
                                                    Reschedule
                                                </Link>
                                                <button
                                                    onClick={() =>
                                                        setShowCancelConfirm(appointment.id)
                                                    }
                                                    className="rounded-md border border-transparent bg-red-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Cancel confirmation dialog */}
                                    {showCancelConfirm === appointment.id && (
                                        <div className="mt-4 rounded-md border border-yellow-200 bg-yellow-50 p-4">
                                            <div className="flex">
                                                <div className="flex-shrink-0">
                                                    <svg
                                                        className="h-5 w-5 text-yellow-400"
                                                        viewBox="0 0 20 20"
                                                        fill="currentColor"
                                                    >
                                                        <path
                                                            fillRule="evenodd"
                                                            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.82-1.742 2.82H4.42c-1.53 0-2.493-1.486-1.743-2.82l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 112 0 012 0z"
                                                            clipRule="evenodd"
                                                        />
                                                        <path
                                                            fillRule="evenodd"
                                                            d="M10 11V7m0 4h.01v.01H10V11z"
                                                            clipRule="evenodd"
                                                        />
                                                    </svg>
                                                </div>
                                                <div className="ml-3 flex-1">
                                                    <h3 className="text-sm font-medium text-yellow-800">
                                                        Confirm Cancellation
                                                    </h3>
                                                    <div className="mt-2 text-sm text-yellow-700">
                                                        {isWithinTwoHours(
                                                            appointment.startDatetime
                                                        ) ? (
                                                            <p>
                                                                Warning: This appointment is
                                                                within 2 hours of the scheduled
                                                                time. Cancellation will incur a
                                                                penalty.
                                                            </p>
                                                        ) : (
                                                            <p>
                                                                Are you sure you want to cancel
                                                                this appointment?
                                                            </p>
                                                        )}
                                                    </div>
                                                    <div className="mt-4 flex space-x-3">
                                                        <button
                                                            onClick={() =>
                                                                handleCancel(appointment.id)
                                                            }
                                                            disabled={
                                                                cancellingId === appointment.id
                                                            }
                                                            className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50"
                                                        >
                                                            {cancellingId === appointment.id
                                                                ? 'Cancelling...'
                                                                : 'Yes, Cancel'}
                                                        </button>
                                                        <button
                                                            onClick={() =>
                                                                setShowCancelConfirm(null)
                                                            }
                                                            disabled={
                                                                cancellingId === appointment.id
                                                            }
                                                            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                                                        >
                                                            No, Keep
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </main>
        </div>
    )
}