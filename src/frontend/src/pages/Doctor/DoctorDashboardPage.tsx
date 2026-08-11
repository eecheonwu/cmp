import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getAppointments, getBranches, getDoctorsByBranch } from '../../services/appointment'
import {
    getClinicalRecordsByPatient,
    createClinicalRecord,
    updateClinicalRecord,
    releaseLabResults,
} from '../../services/clinical'
import { cacheAppointments, getCachedAppointments, clearOfflineCache } from '../../services/db'
import type { Appointment, AppointmentStatus, Branch, Doctor } from '../../types/appointment'
import type { ClinicalRecord, PatientInfo } from '../../types/clinical'

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

// Mock patient info (in production, this would come from the API)
function getMockPatientInfo(patientId: string): PatientInfo {
    return {
        id: patientId,
        fullName: `Patient ${patientId.slice(0, 8)}`,
        dateOfBirth: '1990-01-01',
        gender: 'Male',
        phoneNumber: '+234-XXX-XXX-XXXX',
        email: 'patient@example.com',
    }
}

export function DoctorDashboardPage() {
    const [appointments, setAppointments] = useState<Appointment[]>([])
    const [branches, setBranches] = useState<Branch[]>([])
    const [doctors, setDoctors] = useState<Doctor[]>([])
    const [selectedBranch, setSelectedBranch] = useState<string>('')
    const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
    const [selectedDoctor, setSelectedDoctor] = useState<string>('')
    const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null)
    const [clinicalRecord, setClinicalRecord] = useState<ClinicalRecord | null>(null)
    const [patientHistory, setPatientHistory] = useState<ClinicalRecord[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showClinicalModal, setShowClinicalModal] = useState(false)
    const [showHistoryModal, setShowHistoryModal] = useState(false)
    const [clinicalForm, setClinicalForm] = useState({
        notes: '',
        diagnosis: '',
        prescriptions: '',
        labResults: '',
    })
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
            const cached = await getCachedAppointments()
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

    const handleLogout = () => {
        clearOfflineCache()
        logout()
        navigate('/login')
    }

    const handleClinicalEntry = async (appointment: Appointment) => {
        setSelectedAppointment(appointment)
        setClinicalForm({
            notes: '',
            diagnosis: '',
            prescriptions: '',
            labResults: '',
        })

        // Check if clinical record already exists
        try {
            const records = await getClinicalRecordsByPatient(appointment.patientId)
            const existingRecord = records.find((r) => r.appointmentId === appointment.id)
            if (existingRecord) {
                setClinicalRecord(existingRecord)
                setClinicalForm({
                    notes: existingRecord.notes,
                    diagnosis: existingRecord.diagnosis,
                    prescriptions: existingRecord.prescriptions,
                    labResults: existingRecord.labResults || '',
                })
            } else {
                setClinicalRecord(null)
            }
        } catch (err) {
            setClinicalRecord(null)
        }

        setShowClinicalModal(true)
    }

    const handleViewHistory = async (appointment: Appointment) => {
        try {
            const records = await getClinicalRecordsByPatient(appointment.patientId)
            setPatientHistory(records)
            setSelectedAppointment(appointment)
            setShowHistoryModal(true)
        } catch (err) {
            setError('Failed to load patient history')
        }
    }

    const handleSaveClinicalRecord = async () => {
        if (!selectedAppointment) return

        setIsSaving(true)
        try {
            if (clinicalRecord) {
                // Update existing record
                await updateClinicalRecord(clinicalRecord.id, {
                    notes: clinicalForm.notes,
                    diagnosis: clinicalForm.diagnosis,
                    prescriptions: clinicalForm.prescriptions,
                })
            } else {
                // Create new record
                await createClinicalRecord({
                    appointment_id: selectedAppointment.id,
                    patient_id: selectedAppointment.patientId,
                    notes: clinicalForm.notes,
                    diagnosis: clinicalForm.diagnosis,
                    prescriptions: clinicalForm.prescriptions,
                })
            }

            // Update appointment status to completed
            setAppointments((prev) =>
                prev.map((a) =>
                    a.id === selectedAppointment.id
                        ? { ...a, status: 'completed' as AppointmentStatus }
                        : a
                )
            )

            setShowClinicalModal(false)
            setSelectedAppointment(null)
            setClinicalRecord(null)
        } catch (err) {
            setError('Failed to save clinical record')
        } finally {
            setIsSaving(false)
        }
    }

    const handleReleaseLabResults = async () => {
        if (!clinicalRecord) return

        try {
            await releaseLabResults(clinicalRecord.id, clinicalForm.labResults)
            setClinicalForm((prev) => ({ ...prev, labResults: '' }))
        } catch (err) {
            setError('Failed to release lab results')
        }
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
                            Doctor Clinical Portal
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
                                                            Patient
                                                        </p>
                                                        <p className="text-sm font-medium text-gray-900">
                                                            {getMockPatientInfo(appointment.patientId).fullName}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm text-gray-500">
                                                            Status
                                                        </p>
                                                        <p className="text-sm font-medium text-gray-900">
                                                            {appointment.status}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Action buttons */}
                                            <div className="ml-4 flex space-x-2">
                                                {appointment.status === 'booked' && (
                                                    <>
                                                        <button
                                                            onClick={() => handleClinicalEntry(appointment)}
                                                            className="rounded-md border border-transparent bg-primary-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                                                        >
                                                            Clinical Notes
                                                        </button>
                                                        <button
                                                            onClick={() => handleViewHistory(appointment)}
                                                            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                                                        >
                                                            History
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </main>

            {/* Clinical Notes Modal */}
            {showClinicalModal && selectedAppointment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-2xl rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Clinical Notes - {getMockPatientInfo(selectedAppointment.patientId).fullName}
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Notes
                                </label>
                                <textarea
                                    value={clinicalForm.notes}
                                    onChange={(e) =>
                                        setClinicalForm((prev) => ({
                                            ...prev,
                                            notes: e.target.value,
                                        }))
                                    }
                                    rows={4}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Enter clinical notes..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Diagnosis
                                </label>
                                <textarea
                                    value={clinicalForm.diagnosis}
                                    onChange={(e) =>
                                        setClinicalForm((prev) => ({
                                            ...prev,
                                            diagnosis: e.target.value,
                                        }))
                                    }
                                    rows={3}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Enter diagnosis..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Prescriptions
                                </label>
                                <textarea
                                    value={clinicalForm.prescriptions}
                                    onChange={(e) =>
                                        setClinicalForm((prev) => ({
                                            ...prev,
                                            prescriptions: e.target.value,
                                        }))
                                    }
                                    rows={3}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Enter prescriptions..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Lab Results
                                </label>
                                <textarea
                                    value={clinicalForm.labResults}
                                    onChange={(e) =>
                                        setClinicalForm((prev) => ({
                                            ...prev,
                                            labResults: e.target.value,
                                        }))
                                    }
                                    rows={3}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Enter lab results (optional)..."
                                />
                            </div>

                            {/* Lab Results Release Toggle (FR-008) */}
                            {clinicalForm.labResults && (
                                <div className="flex items-center">
                                    <input
                                        type="checkbox"
                                        id="release-lab-results"
                                        checked={clinicalRecord?.labResultsReleased || false}
                                        onChange={async (e) => {
                                            if (e.target.checked && clinicalRecord) {
                                                await handleReleaseLabResults()
                                            }
                                        }}
                                        className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                    />
                                    <label
                                        htmlFor="release-lab-results"
                                        className="ml-2 text-sm text-gray-700"
                                    >
                                        Release lab results to patient
                                    </label>
                                </div>
                            )}
                        </div>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => {
                                    setShowClinicalModal(false)
                                    setSelectedAppointment(null)
                                    setClinicalRecord(null)
                                }}
                                disabled={isSaving}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveClinicalRecord}
                                disabled={isSaving}
                                className="flex-1 rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                {isSaving ? 'Saving...' : 'Save Clinical Record'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Patient History Modal */}
            {showHistoryModal && selectedAppointment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-2xl rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Patient History - {getMockPatientInfo(selectedAppointment.patientId).fullName}
                        </h3>
                        <div className="max-h-96 overflow-y-auto">
                            {patientHistory.length === 0 ? (
                                <p className="text-gray-500">No previous clinical records found</p>
                            ) : (
                                <ul className="space-y-4">
                                    {patientHistory.map((record) => (
                                        <li key={record.id} className="border-b border-gray-200 pb-4">
                                            <p className="text-sm text-gray-500">
                                                {new Date(record.createdAt).toLocaleDateString()}
                                            </p>
                                            <div className="mt-2">
                                                <p className="text-sm font-medium text-gray-700">Notes:</p>
                                                <p className="text-sm text-gray-900">{record.notes}</p>
                                            </div>
                                            <div className="mt-2">
                                                <p className="text-sm font-medium text-gray-700">Diagnosis:</p>
                                                <p className="text-sm text-gray-900">{record.diagnosis}</p>
                                            </div>
                                            <div className="mt-2">
                                                <p className="text-sm font-medium text-gray-700">Prescriptions:</p>
                                                <p className="text-sm text-gray-900">{record.prescriptions}</p>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                        <div className="mt-6">
                            <button
                                onClick={() => {
                                    setShowHistoryModal(false)
                                    setSelectedAppointment(null)
                                    setPatientHistory([])
                                }}
                                className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}