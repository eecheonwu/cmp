/**
 * CMP Patient Dashboard Page.
 *
 * Implements patient portal navigation:
 * - My Appointments (view, cancel, reschedule)
 * - Book New Appointment
 * - Profile information
 */

import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { clearOfflineCache } from '../../services/db'

export function PatientDashboardPage() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        clearOfflineCache()
        logout()
        navigate('/login')
    }

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="bg-white/80 backdrop-blur-lg border-b border-secondary-200/60">
                <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold gradient-text">
                                Patient Portal
                            </h1>
                            <p className="mt-1 text-sm text-secondary-500">
                                Welcome back, manage your healthcare journey
                            </p>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-50 border border-primary-100">
                                <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse-slow" />
                                <span className="text-sm font-medium text-primary-700">
                                    {user?.phoneNumber}
                                </span>
                            </div>
                            <button
                                onClick={handleLogout}
                                className="btn-secondary py-2 px-4 text-sm"
                            >
                                <span className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                    </svg>
                                    Logout
                                </span>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
                {/* Welcome Section */}
                <div className="glass-card p-8 mb-8 animate-fade-in">
                    <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/30 flex items-center justify-center">
                            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-secondary-900">
                                Welcome to CMP!
                            </h2>
                            <p className="mt-1 text-secondary-500 leading-relaxed">
                                Manage your appointments and bookings from this portal.
                                You can view upcoming appointments, book new ones, or reschedule existing ones.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Navigation Cards */}
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 animate-slide-up">
                    {/* My Appointments Card */}
                    <Link
                        to="/appointments"
                        className="dash-card group"
                    >
                        <div className="flex flex-col h-full">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-100 to-primary-50 text-primary-600 group-hover:scale-110 transition-transform duration-300">
                                    <svg
                                        className="h-6 w-6"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z"
                                        />
                                    </svg>
                                </div>
                                <svg className="w-5 h-5 text-secondary-300 group-hover:text-primary-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-semibold text-secondary-900 group-hover:text-primary-700 transition-colors">
                                My Appointments
                            </h3>
                            <p className="mt-1.5 text-sm text-secondary-500 flex-grow">
                                View, cancel, or reschedule your appointments
                            </p>
                            <div className="mt-4 flex items-center gap-2 text-xs font-medium text-primary-600">
                                <span>View appointments</span>
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                            </div>
                        </div>
                    </Link>

                    {/* Book New Appointment Card */}
                    <Link
                        to="/appointments/new"
                        className="dash-card group"
                    >
                        <div className="flex flex-col h-full">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-100 to-emerald-50 text-emerald-600 group-hover:scale-110 transition-transform duration-300">
                                    <svg
                                        className="h-6 w-6"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                                        />
                                    </svg>
                                </div>
                                <svg className="w-5 h-5 text-secondary-300 group-hover:text-emerald-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-semibold text-secondary-900 group-hover:text-emerald-700 transition-colors">
                                Book New Appointment
                            </h3>
                            <p className="mt-1.5 text-sm text-secondary-500 flex-grow">
                                Schedule a new appointment with a doctor
                            </p>
                            <div className="mt-4 flex items-center gap-2 text-xs font-medium text-emerald-600">
                                <span>Book now</span>
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                            </div>
                        </div>
                    </Link>

                    {/* Profile Card (placeholder for future) */}
                    <div className="glass-card p-6 opacity-70 hover:opacity-100 transition-opacity duration-300">
                        <div className="flex flex-col h-full">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-secondary-100 to-secondary-50 text-secondary-600">
                                    <svg
                                        className="h-6 w-6"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                                        />
                                    </svg>
                                </div>
                            </div>
                            <h3 className="text-lg font-semibold text-secondary-900">
                                Profile
                            </h3>
                            <p className="mt-1.5 text-sm text-secondary-500 flex-grow">
                                View and edit your profile
                            </p>
                            <div className="mt-4">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary-100 text-secondary-600">
                                    Coming Soon
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="mt-10 animate-fade-in">
                    <h3 className="text-lg font-semibold text-secondary-900 mb-4">
                        Quick Actions
                    </h3>
                    <div className="flex flex-wrap gap-3">
                        <Link
                            to="/appointments"
                            className="btn-primary"
                        >
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                </svg>
                                View My Appointments
                            </span>
                        </Link>
                        <Link
                            to="/appointments/new"
                            className="btn-secondary"
                        >
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                                </svg>
                                Book New Appointment
                            </span>
                        </Link>
                    </div>
                </div>
            </main>
        </div>
    )
}