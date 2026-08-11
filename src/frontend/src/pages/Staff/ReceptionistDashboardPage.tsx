import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getAppointments, getBranches, getDoctorsByBranch, bookAppointment } from '../../services/appointment'
import { cacheAppointments, getCachedAppointments, clearOfflineCache, cacheDoctorAvailability, getCachedDoctorAvailability } from '../../services/db'
import type { Appointment, AppointmentStatus, Branch, Doctor, AvailableSlot } from '../../types/appointment'

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

export function ReceptionistDashboardPage() {
    const [appointments, setAppointments] = useState<Appointment[]>([])
    const [branches, setBranches] = useState<Branch[]>([])
    const [doctors, setDoctors] = useState<Doctor[]>([])
    const [selectedBranch, setSelectedBranch] = useState<string>('')
    const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
    const [selectedDoctor, setSelectedDoctor] = useState<string>('')
    const [availableSlots, setAvailableSlots] = useState<Record<string, AvailableSlot[]>>({})
    const [isLoading, setIsLoading] = useState(true)
    const [isBooking, setIsBooking] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showWalkInModal, setShowWalkInModal] = useState(false)
    const [walkInPatient, setWalkInPatient] = useState({
        phoneNumber: '',
        email: '',
        fullName: '',
        dateOfBirth: '',
        gender: '',
    })
    const [showCheckInModal, setShowCheckInModal] = useState(false)
    const [checkInAppointment, setCheckInAppointment] = useState<Appointment | null>(null)
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    useEffect(() => {
        loadInitialData()
    }, [])

    useEffect(() => {
        if (selectedBranch) {
            loadDoctors(selectedBranch)
        }
    }, [selectedBranch])

    useEffect(() => {
        if (selectedDoctor && selectedDate) {
            loadAvailableSlots(selectedDoctor, selectedDate)
        }
    }, [selectedDoctor, selectedDate])

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

            // Load today's appointments for the selected branch
            await loadAppointments()
        } catch (err) {
            // Try to load from cache
            const cached = await getCachedAppointments()
            if (cached.length > 0) {
                setAppointments(cached)
            } else {
                setError('Failed to load dashboard data')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const loadAppointments = async () => {
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
            }
        }
    }

    const loadDoctors = async (branchId: string) => {
        try {
            const doctorsData = await getDoctorsByBranch(branchId)
            setDoctors(doctorsData)
            if (doctorsData.length > 0 && !selectedDoctor) {
                setSelectedDoctor(doctorsData[0].id)
            }
        } catch (err) {
            // Use cached data if available
            const cached = await getCachedDoctorAvailability()
            if (cached.length > 0) {
                const uniqueDoctors = cached
                    .filter((a) => a.branchId === branchId)
                    .map((a) => ({
                        id: a.doctorId,
                        fullName: `Dr. ${a.doctorId.slice(0, 8)}`,
                        branchId: a.branchId,
                    }))
                setDoctors(uniqueDoctors)
            }
        }
    }

    const loadAvailableSlots = async (doctorId: string, date: string) => {
        try {
            // In production, this would call the actual API
            // For now, generate mock slots
            const slots: AvailableSlot[] = []
            const startHour = 9
            const endHour = 17

            for (let hour = startHour; hour < endHour; hour++) {
                slots.push({
                    start: `${date}T${hour.toString().padStart(2, '0')}:00:00Z`,
                    end: `${date}T${(hour + 1).toString().padStart(2, '0')}:00:00Z`,
                    isAvailable: true,
                })
            }

            setAvailableSlots((prev) => ({ ...prev, [doctorId]: slots }))
        } catch (err) {
            // Use cached data
            const cached = await getCachedDoctorAvailability()
            const filtered = cached.filter(
                (a) => a.doctorId === doctorId && a.startDatetime.startsWith(date)
            )
            setAvailableSlots((prev) => ({ ...prev, [doctorId]: [] }))
        }
    }

    const handleLogout = () => {
        clearOfflineCache()
        logout()
        navigate('/login')
    }

    const handlePhoneBooking = async (slot: AvailableSlot) => {
        if (!selectedDoctor || !selectedBranch) return

        setIsBooking(true)
        try {
            const appointment = await bookAppointment({
                doctorId: selectedDoctor,
                branchId: selectedBranch,
                startDatetime: slot.start,
                endDatetime: slot.end,
            })

            // Add to local state
            setAppointments((prev) => [...prev, appointment])
            setShowWalkInModal(false)
            setWalkInPatient({
                phoneNumber: '',
                email: '',
                fullName: '',
                dateOfBirth: '',
                gender: '',
            })
        } catch (err) {
            setError('Failed to book appointment')
        } finally {
            setIsBooking(false)
        }
    }

    const handleCheckIn = (appointment: Appointment) => {
        setCheckInAppointment(appointment)
        setShowCheckInModal(true)
    }

    const confirmCheckIn = async () => {
        if (!checkInAppointment) return

        // In production, this would call the API to update appointment status
        // For now, just update local state
        setAppointments((prev) =>
            prev.map((a) =>
                a.id === checkInAppointment.id
                    ? { ...a, status: 'completed' as AppointmentStatus }
                    : a
            )
        )
        setShowCheckInModal(false)
        setCheckInAppointment(null)
    }

    const todayAppointments = appointments.filter((a) => {
        const appointmentDate = a.startDatetime.split('T')[0]
        return appointmentDate === selectedDate
    })

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
                            Receptionist Dashboard
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

                {/* Filters */}
                <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
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
                            Date
                        </label>
                        <input
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">
                            Doctor
                        </label>
                        <select
                            value={selectedDoctor}
                            onChange={(e) => setSelectedDoctor(e.target.value)}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {doctors.map((doctor) => (
                                <option key={doctor.id} value={doctor.id}>
                                    {doctor.fullName}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Action buttons */}
                <div className="mb-6 flex space-x-4">
                    <button
                        onClick={() => setShowWalkInModal(true)}
                        className="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                    >
                        Phone Booking (Walk-in)
                    </button>
                </div>

                {/* Today's Appointments */}
                <div className="mb-8">
                    <h2 className="mb-4 text-lg font-medium text-gray-900">
                        Appointments for {new Date(selectedDate).toLocaleDateString('en-US', {
                            weekday: 'long',
                            month: 'long',
                            day: 'numeric',
                        })}
                    </h2>

                    {todayAppointments.length === 0 ? (
                        <div className="rounded-lg bg-white p-6 text-center">
                            <p className="text-gray-500">No appointments scheduled for this date</p>
                        </div>
                    ) : (
                        <div className="overflow-hidden rounded-lg bg-white shadow">
                            <ul className="divide-y divide-gray-200">
                                {todayAppointments.map((appointment) => (
                                    <li key={appointment.id} className="p-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-lg font-medium text-gray-900">
                                                        Appointment #{appointment.id.slice(0, 8)}
                                                    </h3>
                                                    <StatusBadge status={appointment.status} />
                                                </div>
                                                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
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
                                                            Doctor
                                                        </p>
                                                        <p className="text-sm font-medium text-gray-900">
                                                            {doctors.find((d) => d.id === appointment.doctorId)?.fullName || 'Unknown'}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm text-gray-500">
                                                            Patient
                                                        </p>
                                                        <p className="text-sm font-medium text-gray-900">
                                                            {appointment.patientId.slice(0, 8)}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Action buttons */}
                                            {appointment.status === 'booked' && (
                                                <div className="ml-4 flex space-x-2">
                                                    <button
                                                        onClick={() => handleCheckIn(appointment)}
                                                        className="rounded-md border border-transparent bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                                                    >
                                                        Check-in
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                {/* Available Slots */}
                {selectedDoctor && availableSlots[selectedDoctor] && (
                    <div>
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            Available Slots
                        </h2>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            {availableSlots[selectedDoctor].map((slot, index) => (
                                <button
                                    key={index}
                                    onClick={() => handlePhoneBooking(slot)}
                                    disabled={isBooking}
                                    className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
                                >
                                    {new Date(slot.start).toLocaleTimeString('en-US', {
                                        hour: 'numeric',
                                        minute: '2-digit',
                                    })}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </main>

            {/* Walk-in Booking Modal */}
            {showWalkInModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Phone Booking (Walk-in)
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Phone Number
                                </label>
                                <input
                                    type="tel"
                                    value={walkInPatient.phoneNumber}
                                    onChange={(e) =>
                                        setWalkInPatient((prev) => ({
                                            ...prev,
                                            phoneNumber: e.target.value,
                                        }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="+234-XXX-XXX-XXXX"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={walkInPatient.email}
                                    onChange={(e) =>
                                        setWalkInPatient((prev) => ({
                                            ...prev,
                                            email: e.target.value,
                                        }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="patient@example.com"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Full Name
                                </label>
                                <input
                                    type="text"
                                    value={walkInPatient.fullName}
                                    onChange={(e) =>
                                        setWalkInPatient((prev) => ({
                                            ...prev,
                                            fullName: e.target.value,
                                        }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="John Doe"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Date of Birth
                                </label>
                                <input
                                    type="date"
                                    value={walkInPatient.dateOfBirth}
                                    onChange={(e) =>
                                        setWalkInPatient((prev) => ({
                                            ...prev,
                                            dateOfBirth: e.target.value,
                                        }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Gender
                                </label>
                                <select
                                    value={walkInPatient.gender}
                                    onChange={(e) =>
                                        setWalkInPatient((prev) => ({
                                            ...prev,
                                            gender: e.target.value,
                                        }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                >
                                    <option value="">Select gender</option>
                                    <option value="male">Male</option>
                                    <option value="female">Female</option>
                                </select>
                            </div>
                        </div>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => {
                                    // In production, this would create a patient and book appointment
                                    // For now, just close the modal
                                    setShowWalkInModal(false)
                                    setWalkInPatient({
                                        phoneNumber: '',
                                        email: '',
                                        fullName: '',
                                        dateOfBirth: '',
                                        gender: '',
                                    })
                                }}
                                disabled={isBooking}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    // In production, this would create a patient and book appointment
                                    // For now, just close the modal
                                    setShowWalkInModal(false)
                                    setWalkInPatient({
                                        phoneNumber: '',
                                        email: '',
                                        fullName: '',
                                        dateOfBirth: '',
                                        gender: '',
                                    })
                                }}
                                disabled={isBooking}
                                className="flex-1 rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                {isBooking ? 'Booking...' : 'Book Appointment'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Check-in Confirmation Modal */}
            {showCheckInModal && checkInAppointment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Confirm Check-in
                        </h3>
                        <p className="text-sm text-gray-600">
                            Are you sure you want to check in this patient?
                        </p>
                        <p className="mt-2 text-sm font-medium">
                            Appointment #{checkInAppointment.id.slice(0, 8)} at{' '}
                            {formatDateTime(checkInAppointment.startDatetime)}
                        </p>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => {
                                    setShowCheckInModal(false)
                                    setCheckInAppointment(null)
                                }}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmCheckIn}
                                className="flex-1 rounded-md border border-transparent bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                            >
                                Confirm Check-in
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}