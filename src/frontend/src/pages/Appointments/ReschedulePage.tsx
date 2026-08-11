import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { getAppointments, getAvailableSlots, rescheduleAppointment } from '../../services/appointment'
import { cacheAppointments } from '../../services/db'
import type { Appointment, AvailableSlot } from '../../types/appointment'

export function ReschedulePage() {
    const [appointment, setAppointment] = useState<Appointment | null>(null)
    const [slots, setSlots] = useState<AvailableSlot[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isRescheduling, setIsRescheduling] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null)
    const { appointmentId } = useParams<{ appointmentId: string }>()
    const navigate = useNavigate()

    // Get today's date in YYYY-MM-DD format
    const today = new Date().toISOString().split('T')[0]

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
                // Load available slots for the doctor
                const availableSlots = await getAvailableSlots(found.doctorId, today)
                setSlots(availableSlots)
            } else {
                navigate('/appointments')
            }
        } catch (err) {
            setError('Failed to load appointment')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSelectSlot = (slot: AvailableSlot) => {
        if (!slot.isAvailable) return
        setSelectedSlot(slot)
    }

    const handleReschedule = async () => {
        if (!selectedSlot || !appointmentId) return

        setIsRescheduling(true)
        setError(null)

        try {
            const updated = await rescheduleAppointment(appointmentId, {
                startDatetime: selectedSlot.start,
                endDatetime: selectedSlot.end,
            })

            // Update cache
            const appointments = await getAppointments()
            await cacheAppointments(appointments)

            navigate('/appointments')
        } catch (err: any) {
            if (err.response?.status === 409) {
                setError('This slot is no longer available. Please select another time.')
                setSelectedSlot(null)
            } else {
                setError('Failed to reschedule appointment. Please try again.')
            }
        } finally {
            setIsRescheduling(false)
        }
    }

    const formatTime = (isoString: string): string => {
        const date = new Date(isoString)
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
        })
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading appointment...</div>
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
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow">
                <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <h1 className="text-2xl font-bold text-gray-900">
                            Reschedule Appointment
                        </h1>
                        <Link
                            to="/appointments"
                            className="text-sm font-medium text-primary-600 hover:text-primary-500"
                        >
                            Back to Appointments
                        </Link>
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

                {/* Current appointment info */}
                <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
                    <h2 className="text-sm font-medium text-gray-500">
                        Current Appointment
                    </h2>
                    <p className="mt-1 text-sm text-gray-900">
                        {new Date(appointment.startDatetime).toLocaleString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                        })}
                    </p>
                </div>

                {/* Available slots */}
                {slots.length === 0 ? (
                    <div className="rounded-lg bg-white p-6 text-center">
                        <p className="text-gray-500">No available slots for today</p>
                    </div>
                ) : (
                    <>
                        <div className="mb-4">
                            <h2 className="text-lg font-medium text-gray-900">
                                Select New Time
                            </h2>
                            <p className="text-sm text-gray-500">
                                {new Date().toLocaleDateString('en-US', {
                                    weekday: 'long',
                                    month: 'long',
                                    day: 'numeric',
                                })}
                            </p>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
                            {slots.map((slot, index) => (
                                <button
                                    key={index}
                                    onClick={() => handleSelectSlot(slot)}
                                    disabled={!slot.isAvailable}
                                    className={`rounded-lg border p-4 text-center transition-colors ${slot.isAvailable
                                            ? selectedSlot?.start === slot.start
                                                ? 'border-primary-500 bg-primary-50 text-primary-700'
                                                : 'border-gray-200 bg-white text-gray-900 hover:bg-gray-50'
                                            : 'cursor-not-allowed border-gray-100 bg-gray-50 text-gray-400'
                                        }`}
                                >
                                    <span className="text-sm font-medium">
                                        {formatTime(slot.start)} - {formatTime(slot.end)}
                                    </span>
                                    {!slot.isAvailable && (
                                        <span className="mt-1 block text-xs">Booked</span>
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* Reschedule button */}
                        {selectedSlot && (
                            <div className="mt-8">
                                <div className="rounded-lg border border-primary-200 bg-primary-50 p-4">
                                    <h3 className="font-medium text-primary-900">
                                        New Time Selected
                                    </h3>
                                    <p className="mt-1 text-sm text-primary-700">
                                        {formatTime(selectedSlot.start)} -{' '}
                                        {formatTime(selectedSlot.end)}
                                    </p>
                                </div>
                                <button
                                    onClick={handleReschedule}
                                    disabled={isRescheduling}
                                    className="mt-4 w-full rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 sm:w-auto"
                                >
                                    {isRescheduling ? 'Rescheduling...' : 'Confirm Reschedule'}
                                </button>
                            </div>
                        )}
                    </>
                )}
            </main>
        </div>
    )
}