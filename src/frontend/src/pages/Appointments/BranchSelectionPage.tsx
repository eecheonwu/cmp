import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { getBranches } from '../../services/appointment'
import type { Branch } from '../../types/appointment'

export function BranchSelectionPage() {
    const [branches, setBranches] = useState<Branch[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const navigate = useNavigate()

    useEffect(() => {
        loadBranches()
    }, [])

    const loadBranches = async () => {
        setIsLoading(true)
        setError(null)

        try {
            const data = await getBranches()
            setBranches(data)
        } catch (err) {
            setError('Failed to load branches')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSelectBranch = (branchId: string) => {
        navigate(`/appointments/new/doctor?branch=${branchId}`)
    }

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading branches...</div>
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
                            Select Branch
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

                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {branches.map((branch) => (
                        <button
                            key={branch.id}
                            onClick={() => handleSelectBranch(branch.id)}
                            className="rounded-lg border border-gray-200 bg-white p-6 text-left shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                            <h3 className="text-lg font-medium text-gray-900">
                                {branch.name}
                            </h3>
                            <p className="mt-2 text-sm text-gray-600">
                                {branch.address}
                            </p>
                            <p className="mt-1 text-sm text-gray-500">
                                {branch.phone}
                            </p>
                        </button>
                    ))}
                </div>
            </main>
        </div>
    )
}