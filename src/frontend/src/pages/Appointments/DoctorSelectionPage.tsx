import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { getDoctorsByBranch } from '../../services/appointment'
import type { Doctor } from '../../types/appointment'

export function DoctorSelectionPage() {
    const [doctors, setDoctors] = useState<Doctor[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const branchId = searchParams.get('branch')

    useEffect(() => {
        if (branchId) {
            loadDoctors()
        }
    }, [branchId])

    const loadDoctors = async () => {
        if (!branchId) return

        setIsLoading(true)
        setError(null)

        try {
            const data = await getDoctorsByBranch(branchId)
            setDoctors(data)
        } catch (err) {
            setError('Failed to load doctors')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSelectDoctor = (doctorId: string) => {
        navigate(
            `/appointments/new/slot?branch=${branchId}&doctor=${doctorId}`
        )
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading doctors...</div>
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
                            Select Doctor
                        </h1>
                        <Link
                            to="/appointments/new"
                            className="text-sm font-medium text-primary-600 hover:text-primary-500"
                        >
                            Change Branch
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

                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {doctors.map((doctor) => (
                        <button
                            key={doctor.id}
                            onClick={() => handleSelectDoctor(doctor.id)}
                            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                            <h3 className="text-lg font-medium text-gray-900">
                                {doctor.fullName}
                            </h3>
                            <p className="mt-2 text-sm text-gray-600">
                                {doctor.specialization || 'General Practitioner'}
                            </p>
                        </button>
                    ))}
                </div>
            </main>
        </div>
    )
}