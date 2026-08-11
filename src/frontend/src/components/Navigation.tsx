/**
 * CMP Navigation Component.
 *
 * Provides role-based navigation links for all user types.
 */

import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface NavigationItem {
    path: string
    label: string
    icon?: string
}

export function Navigation() {
    const { user } = useAuth()
    const location = useLocation()

    const isActive = (path: string) => {
        return location.pathname === path || location.pathname.startsWith(path)
    }

    // Role-based navigation items
    const getNavItems = (): NavigationItem[] => {
        const items: NavigationItem[] = []

        // Patient navigation
        if (user?.role === 'patient') {
            items.push(
                { path: '/dashboard', label: 'Dashboard' },
                { path: '/appointments', label: 'My Appointments' },
                { path: '/appointments/new', label: 'Book Appointment' }
            )
        }

        // Receptionist navigation
        if (user?.role === 'receptionist') {
            items.push(
                { path: '/staff/dashboard', label: 'Dashboard' },
                { path: '/appointments', label: 'Appointments' }
            )
        }

        // Doctor navigation
        if (user?.role === 'doctor') {
            items.push(
                { path: '/doctor/dashboard', label: 'Dashboard' },
                { path: '/appointments', label: 'Appointments' }
            )
        }

        // Manager navigation
        if (user?.role === 'manager') {
            items.push(
                { path: '/manager/dashboard', label: 'Dashboard' }
            )
        }

        // Admin navigation
        if (user?.role === 'admin') {
            items.push(
                { path: '/admin/dashboard', label: 'Dashboard' }
            )
        }

        return items
    }

    const navItems = getNavItems()

    if (navItems.length === 0) {
        return null
    }

    return (
        <nav className="bg-white/80 backdrop-blur-lg border-b border-secondary-200/60 sticky top-0 z-50">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-16 items-center justify-between">
                    {/* Logo */}
                    <Link to="/dashboard" className="flex items-center gap-2.5">
                        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 shadow-sm">
                            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <span className="text-sm font-bold gradient-text">CMP</span>
                    </Link>

                    {/* Navigation Links */}
                    <div className="flex items-center gap-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={isActive(item.path) ? 'nav-link-active' : 'nav-link-inactive'}
                            >
                                {item.label}
                            </Link>
                        ))}
                    </div>
                </div>
            </div>
        </nav>
    )
}