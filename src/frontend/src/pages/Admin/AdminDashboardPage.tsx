/**
 * CMP Admin Dashboard Page.
 *
 * Implements Task 5.4 — Admin Console:
 * - Create/edit branches
 * - Assign roles to staff users
 * - Manage doctor availability
 * - System settings
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import {
    getBranches,
    createBranch,
    updateBranch,
    deleteBranch,
    getUsers,
    updateUserRole,
    getDoctorAvailability,
    createAvailability,
    updateAvailability,
    deleteAvailability,
} from '../../services/admin'
import type {
    Branch,
    CreateBranchRequest,
    User,
    DoctorAvailability,
    CreateAvailabilityRequest,
} from '../../types/admin'

// Tab types
type TabType = 'branches' | 'users' | 'availability' | 'settings'

// Role options for user management
const ROLE_OPTIONS = [
    { value: 'patient', label: 'Patient' },
    { value: 'receptionist', label: 'Receptionist' },
    { value: 'doctor', label: 'Doctor' },
    { value: 'manager', label: 'Manager' },
    { value: 'admin', label: 'Admin' },
    { value: 'executive', label: 'Executive' },
]

// Role badge component
function RoleBadge({ role }: { role: string }) {
    const roleColors: Record<string, string> = {
        patient: 'bg-blue-100 text-blue-800',
        receptionist: 'bg-purple-100 text-purple-800',
        doctor: 'bg-green-100 text-green-800',
        manager: 'bg-yellow-100 text-yellow-800',
        admin: 'bg-red-100 text-red-800',
        executive: 'bg-indigo-100 text-indigo-800',
    }

    return (
        <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${roleColors[role] || 'bg-gray-100 text-gray-800'}`}
        >
            {role.charAt(0).toUpperCase() + role.slice(1)}
        </span>
    )
}

// Status badge for availability
function AvailabilityStatusBadge({ isCancelled }: { isCancelled: boolean }) {
    return (
        <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${isCancelled ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}
        >
            {isCancelled ? 'Cancelled' : 'Active'}
        </span>
    )
}

export function AdminDashboardPage() {
    const [activeTab, setActiveTab] = useState<TabType>('branches')
    const [branches, setBranches] = useState<Branch[]>([])
    const [users, setUsers] = useState<User[]>([])
    const [availability, setAvailability] = useState<DoctorAvailability[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)

    // Branch form state
    const [showBranchForm, setShowBranchForm] = useState(false)
    const [editingBranch, setEditingBranch] = useState<Branch | null>(null)
    const [branchForm, setBranchForm] = useState<CreateBranchRequest>({
        name: '',
        address: '',
        phone: '',
        email: '',
    })

    // User role form state
    const [showRoleForm, setShowRoleForm] = useState(false)
    const [selectedUser, setSelectedUser] = useState<User | null>(null)
    const [selectedRole, setSelectedRole] = useState<string>('receptionist')

    // Availability form state
    const [showAvailabilityForm, setShowAvailabilityForm] = useState(false)
    const [availabilityForm, setAvailabilityForm] = useState<CreateAvailabilityRequest>({
        doctorId: '',
        branchId: '',
        startDatetime: '',
        endDatetime: '',
    })

    const { user, logout } = useAuth()
    const navigate = useNavigate()

    // Load initial data
    useEffect(() => {
        loadAllData()
    }, [])

    const loadAllData = async () => {
        setIsLoading(true)
        setError(null)

        try {
            const [branchesData, usersData, availabilityData] = await Promise.all([
                getBranches(),
                getUsers(),
                getDoctorAvailability(),
            ])
            setBranches(branchesData)
            setUsers(usersData)
            setAvailability(availabilityData)
        } catch (err) {
            setError('Failed to load admin data')
        } finally {
            setIsLoading(false)
        }
    }

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    // ── Branch Management Handlers ───────────────────────────────────────────

    const handleCreateBranch = async () => {
        if (!branchForm.name || !branchForm.address || !branchForm.phone) {
            setError('Name, address, and phone are required')
            return
        }

        try {
            await createBranch(branchForm)
            setSuccess('Branch created successfully')
            setShowBranchForm(false)
            setBranchForm({ name: '', address: '', phone: '', email: '' })
            loadAllData()
        } catch (err) {
            setError('Failed to create branch')
        }
    }

    const handleUpdateBranch = async () => {
        if (!editingBranch) return

        try {
            await updateBranch(editingBranch.id, branchForm)
            setSuccess('Branch updated successfully')
            setEditingBranch(null)
            setShowBranchForm(false)
            setBranchForm({ name: '', address: '', phone: '', email: '' })
            loadAllData()
        } catch (err) {
            setError('Failed to update branch')
        }
    }

    const handleDeleteBranch = async (branchId: string) => {
        if (!confirm('Are you sure you want to delete this branch?')) return

        try {
            await deleteBranch(branchId)
            setSuccess('Branch deleted successfully')
            loadAllData()
        } catch (err) {
            setError('Failed to delete branch')
        }
    }

    const startEditBranch = (branch: Branch) => {
        setEditingBranch(branch)
        setBranchForm({
            name: branch.name,
            address: branch.address,
            phone: branch.phone,
            email: branch.email,
        })
        setShowBranchForm(true)
    }

    // ── User Role Management Handlers ───────────────────────────────────────

    const handleUpdateUserRole = async () => {
        if (!selectedUser) return

        try {
            await updateUserRole(selectedUser.id, { role: selectedRole as any })
            setSuccess(`User role updated to ${selectedRole}`)
            setShowRoleForm(false)
            setSelectedUser(null)
            loadAllData()
        } catch (err) {
            setError('Failed to update user role')
        }
    }

    const startEditRole = (user: User) => {
        setSelectedUser(user)
        setSelectedRole(user.role)
        setShowRoleForm(true)
    }

    // ── Availability Management Handlers ─────────────────────────────────────

    const handleCreateAvailability = async () => {
        if (!availabilityForm.doctorId || !availabilityForm.branchId || !availabilityForm.startDatetime || !availabilityForm.endDatetime) {
            setError('All fields are required')
            return
        }

        try {
            await createAvailability(availabilityForm)
            setSuccess('Availability created successfully')
            setShowAvailabilityForm(false)
            setAvailabilityForm({ doctorId: '', branchId: '', startDatetime: '', endDatetime: '' })
            loadAllData()
        } catch (err) {
            setError('Failed to create availability')
        }
    }

    const handleDeleteAvailability = async (availabilityId: string) => {
        if (!confirm('Are you sure you want to delete this availability slot?')) return

        try {
            await deleteAvailability(availabilityId)
            setSuccess('Availability deleted successfully')
            loadAllData()
        } catch (err) {
            setError('Failed to delete availability')
        }
    }

    // Clear messages after timeout
    useEffect(() => {
        if (error || success) {
            const timer = setTimeout(() => {
                setError(null)
                setSuccess(null)
            }, 5000)
            return () => clearTimeout(timer)
        }
    }, [error, success])

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="text-lg">Loading admin dashboard...</div>
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
                            Admin Console
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
                {/* Messages */}
                {error && (
                    <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="mb-4 rounded-md bg-green-50 p-4 text-sm text-green-700">
                        {success}
                    </div>
                )}

                {/* Tabs */}
                <div className="mb-6 border-b border-gray-200">
                    <nav className="-mb-px flex space-x-8">
                        {(['branches', 'users', 'availability', 'settings'] as TabType[]).map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`border-b-2 py-2 px-1 text-sm font-medium ${activeTab === tab
                                        ? 'border-primary-500 text-primary-600'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    }`}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Tab Content */}
                {activeTab === 'branches' && (
                    <div>
                        <div className="mb-4 flex items-center justify-between">
                            <h2 className="text-lg font-medium text-gray-900">
                                Branch Management
                            </h2>
                            <button
                                onClick={() => {
                                    setEditingBranch(null)
                                    setBranchForm({ name: '', address: '', phone: '', email: '' })
                                    setShowBranchForm(true)
                                }}
                                className="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Add Branch
                            </button>
                        </div>

                        <div className="overflow-hidden rounded-lg bg-white shadow">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Name
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Address
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Phone
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Email
                                        </th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {branches.map((branch) => (
                                        <tr key={branch.id}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                {branch.name}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {branch.address}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {branch.phone}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {branch.email}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => startEditBranch(branch)}
                                                    className="text-primary-600 hover:text-primary-900 mr-4"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteBranch(branch.id)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === 'users' && (
                    <div>
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            User Management
                        </h2>

                        <div className="overflow-hidden rounded-lg bg-white shadow">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Phone Number
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Email
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Role
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Verified
                                        </th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {users.map((u) => (
                                        <tr key={u.id}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                {u.phoneNumber}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {u.email || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                <RoleBadge role={u.role} />
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {u.isVerified ? 'Yes' : 'No'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => startEditRole(u)}
                                                    className="text-primary-600 hover:text-primary-900"
                                                >
                                                    Change Role
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === 'availability' && (
                    <div>
                        <div className="mb-4 flex items-center justify-between">
                            <h2 className="text-lg font-medium text-gray-900">
                                Doctor Availability
                            </h2>
                            <button
                                onClick={() => {
                                    setAvailabilityForm({ doctorId: '', branchId: '', startDatetime: '', endDatetime: '' })
                                    setShowAvailabilityForm(true)
                                }}
                                className="inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Add Availability
                            </button>
                        </div>

                        <div className="overflow-hidden rounded-lg bg-white shadow">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Doctor
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Branch
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Start
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            End
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {availability.map((a) => (
                                        <tr key={a.id}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                {a.doctorId.slice(0, 8)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {branches.find((b) => b.id === a.branchId)?.name || a.branchId}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {new Date(a.startDatetime).toLocaleString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {new Date(a.endDatetime).toLocaleString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                <AvailabilityStatusBadge isCancelled={a.isCancelled} />
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => handleDeleteAvailability(a.id)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === 'settings' && (
                    <div>
                        <h2 className="mb-4 text-lg font-medium text-gray-900">
                            System Settings
                        </h2>
                        <div className="rounded-lg bg-white p-6 shadow">
                            <p className="text-gray-500">
                                System settings management will be available in Phase 2.
                            </p>
                        </div>
                    </div>
                )}
            </main>

            {/* Branch Form Modal */}
            {showBranchForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            {editingBranch ? 'Edit Branch' : 'Add Branch'}
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Name
                                </label>
                                <input
                                    type="text"
                                    value={branchForm.name}
                                    onChange={(e) =>
                                        setBranchForm((prev) => ({ ...prev, name: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Branch name"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Address
                                </label>
                                <input
                                    type="text"
                                    value={branchForm.address}
                                    onChange={(e) =>
                                        setBranchForm((prev) => ({ ...prev, address: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Branch address"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Phone
                                </label>
                                <input
                                    type="tel"
                                    value={branchForm.phone}
                                    onChange={(e) =>
                                        setBranchForm((prev) => ({ ...prev, phone: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="+234-1-234-5678"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={branchForm.email}
                                    onChange={(e) =>
                                        setBranchForm((prev) => ({ ...prev, email: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="branch@clinic.com"
                                />
                            </div>
                        </div>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => {
                                    setShowBranchForm(false)
                                    setEditingBranch(null)
                                }}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={editingBranch ? handleUpdateBranch : handleCreateBranch}
                                className="flex-1 rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                {editingBranch ? 'Update' : 'Create'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Role Change Modal */}
            {showRoleForm && selectedUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Change User Role
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <p className="text-sm text-gray-600">
                                    User: {selectedUser.phoneNumber}
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    New Role
                                </label>
                                <select
                                    value={selectedRole}
                                    onChange={(e) => setSelectedRole(e.target.value)}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                >
                                    {ROLE_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => {
                                    setShowRoleForm(false)
                                    setSelectedUser(null)
                                }}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleUpdateUserRole}
                                className="flex-1 rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Update Role
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Availability Form Modal */}
            {showAvailabilityForm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="w-full max-w-md rounded-lg bg-white p-6">
                        <h3 className="mb-4 text-lg font-medium text-gray-900">
                            Add Availability
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Doctor ID
                                </label>
                                <input
                                    type="text"
                                    value={availabilityForm.doctorId}
                                    onChange={(e) =>
                                        setAvailabilityForm((prev) => ({ ...prev, doctorId: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                    placeholder="Doctor UUID"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Branch
                                </label>
                                <select
                                    value={availabilityForm.branchId}
                                    onChange={(e) =>
                                        setAvailabilityForm((prev) => ({ ...prev, branchId: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                >
                                    <option value="">Select branch</option>
                                    {branches.map((branch) => (
                                        <option key={branch.id} value={branch.id}>
                                            {branch.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    Start Date & Time
                                </label>
                                <input
                                    type="datetime-local"
                                    value={availabilityForm.startDatetime}
                                    onChange={(e) =>
                                        setAvailabilityForm((prev) => ({ ...prev, startDatetime: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">
                                    End Date & Time
                                </label>
                                <input
                                    type="datetime-local"
                                    value={availabilityForm.endDatetime}
                                    onChange={(e) =>
                                        setAvailabilityForm((prev) => ({ ...prev, endDatetime: e.target.value }))
                                    }
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                                />
                            </div>
                        </div>
                        <div className="mt-6 flex space-x-3">
                            <button
                                onClick={() => setShowAvailabilityForm(false)}
                                className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateAvailability}
                                className="flex-1 rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                            >
                                Create
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}