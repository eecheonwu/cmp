import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getAppointments } from '../../services/appointment'
import type { Appointment } from '../../types/appointment'

export function BookingConfirmationPage() {
    const [appointment, setAppointment] = useState<Appointment | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const { appointmentId } = useParams<{ appointmentId: string }>()
    const navigate = useNavigate()

    useEffect(() => {
        if (appointmentId) {
            loadAppointment()
        }
    }, [appointmentId])

    const loadAppointment = async () => {
        try {
            const appointments = await getAppointments()
            const found = appointments.find((a) => a.id === appointmentId)
            if (found) {
                setAppointment(found)
            } else {
                // If not found, redirect to appointments list
                navigate('/appointments')
            }
        } catch (err) {
            navigate('/appointments')
        } finally {
            setIsLoading(false)
        }
    }

    const formatDateTime = (dateString: string): string => {
        const date = new Date(dateString)
        return date.toLocaleString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        })
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading confirmation...</div>
            </div>
        )
    }

    if (!appointment) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Appointment not found</div>
            </div>
        )
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
            <div className="w-full max-w-md">
                <div className="rounded-lg bg-white p-6 shadow">
                    {/* Success icon */}
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                        <svg
                            className="h-6 w-6 text-green-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M5 13l4 4L19 7"
                            />
                        </svg>
                    </div>

                    <h2 className="mt-4 text-center text-xl font-bold text-gray-900">
                        Appointment Booked!
                    </h2>

                    <div className="mt-6 space-y-4">
                        <div>
                            <p className="text-sm text-gray-500">Date & Time</p>
                            <p className="font-medium text-gray-900">
                                {formatDateTime(appointment.startDatetime)}
                            </p>
                        </div>

                        <div>
                            <p className="text-sm text-gray-500">Branch</p>
                            <p className="font-medium text-gray-900">
                                {appointment.branchId}
                            </p>
                        </div>

                        <div>
                            <p className="text-sm text-gray-500">Appointment ID</p>
                            <p className="font-mono text-sm text-gray-900">
                                {appointment.id}
                            </p>
                        </div>
                    </div>

                    <div className="mt-6 space-y-3">
                        <Link
                            to="/appointments"
                            className="block w-full rounded-md border border-transparent bg-primary-600 px-4 py-2 text-center text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                        >
                            View My Appointments
                        </Link>

                        <Link
                            to="/appointments/new"
                            className="block w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-center text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                        >
                            Book Another
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}