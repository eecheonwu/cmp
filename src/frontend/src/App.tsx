import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { useAuth } from './contexts/AuthContext'
import { OfflineBanner } from './components/OfflineBanner'
import { Navigation } from './components/Navigation'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { VerifyOTPPage } from './pages/auth/VerifyOTPPage'
import { PatientDashboardPage } from './pages/Patient/PatientDashboardPage'
import { AppointmentListPage } from './pages/Appointments/AppointmentListPage'
import { BranchSelectionPage } from './pages/Appointments/BranchSelectionPage'
import { DoctorSelectionPage } from './pages/Appointments/DoctorSelectionPage'
import { SlotSelectionPage } from './pages/Appointments/SlotSelectionPage'
import { BookingConfirmationPage } from './pages/Appointments/BookingConfirmationPage'
import { ReschedulePage } from './pages/Appointments/ReschedulePage'
import { ReceptionistDashboardPage } from './pages/Staff/ReceptionistDashboardPage'
import { DoctorDashboardPage } from './pages/Doctor/DoctorDashboardPage'
import { ManagerDashboardPage } from './pages/Manager/ManagerDashboardPage'
import { AdminDashboardPage } from './pages/Admin/AdminDashboardPage'
import { PatientRegisterPage } from './pages/Patient/PatientRegisterPage'
import { PatientCreatePasswordPage } from './pages/Patient/PatientCreatePasswordPage'
import { PatientLoginPage } from './pages/Patient/PatientLoginPage'

// Loading spinner component
function LoadingSpinner() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-secondary-50 via-white to-primary-50">
            <div className="text-center animate-fade-in">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/30 mb-4">
                    <svg className="w-8 h-8 text-white animate-spin" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                </div>
                <p className="text-secondary-500 font-medium">Loading...</p>
            </div>
        </div>
    )
}

// Protected route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { user, isLoading } = useAuth()

    if (isLoading) {
        return <LoadingSpinner />
    }

    if (!user) {
        return <Navigate to="/login" replace />
    }

    return <>{children}</>
}

// Public route component (redirects to dashboard if already logged in)
function PublicRoute({ children }: { children: React.ReactNode }) {
    const { user, isLoading } = useAuth()

    if (isLoading) {
        return <LoadingSpinner />
    }

    if (user) {
        return <Navigate to="/dashboard" replace />
    }

    return <>{children}</>
}

function App() {
    return (
        <AuthProvider>
            <div className="min-h-screen">
                <OfflineBanner />
                <Navigation />
                <Routes>
                    {/* Public routes */}
                    <Route path="/login" element={
                        <PublicRoute>
                            <LoginPage />
                        </PublicRoute>
                    } />
                    <Route path="/register" element={
                        <PublicRoute>
                            <RegisterPage />
                        </PublicRoute>
                    } />
                    <Route path="/patient/register" element={
                        <PublicRoute>
                            <PatientRegisterPage />
                        </PublicRoute>
                    } />
                    <Route path="/patient/create-password" element={
                        <PublicRoute>
                            <PatientCreatePasswordPage />
                        </PublicRoute>
                    } />
                    <Route path="/patient/login" element={
                        <PublicRoute>
                            <PatientLoginPage />
                        </PublicRoute>
                    } />
                    <Route path="/verify-otp" element={<VerifyOTPPage />} />

                    {/* Protected routes */}
                    <Route path="/dashboard" element={
                        <ProtectedRoute>
                            <PatientDashboardPage />
                        </ProtectedRoute>
                    } />

                    {/* Appointment routes */}
                    <Route path="/appointments" element={
                        <ProtectedRoute>
                            <AppointmentListPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/appointments/new" element={
                        <ProtectedRoute>
                            <BranchSelectionPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/appointments/new/doctor" element={
                        <ProtectedRoute>
                            <DoctorSelectionPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/appointments/new/slot" element={
                        <ProtectedRoute>
                            <SlotSelectionPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/appointments/:appointmentId/confirm" element={
                        <ProtectedRoute>
                            <BookingConfirmationPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/appointments/:appointmentId/reschedule" element={
                        <ProtectedRoute>
                            <ReschedulePage />
                        </ProtectedRoute>
                    } />

                    {/* Staff routes */}
                    <Route path="/staff/dashboard" element={
                        <ProtectedRoute>
                            <ReceptionistDashboardPage />
                        </ProtectedRoute>
                    } />

                    {/* Doctor routes */}
                    <Route path="/doctor/dashboard" element={
                        <ProtectedRoute>
                            <DoctorDashboardPage />
                        </ProtectedRoute>
                    } />

                    {/* Manager routes */}
                    <Route path="/manager/dashboard" element={
                        <ProtectedRoute>
                            <ManagerDashboardPage />
                        </ProtectedRoute>
                    } />

                    {/* Admin routes */}
                    <Route path="/admin/dashboard" element={
                        <ProtectedRoute>
                            <AdminDashboardPage />
                        </ProtectedRoute>
                    } />

                    {/* Default redirect */}
                    <Route path="/" element={<Navigate to="/login" replace />} />
                </Routes>
            </div>
        </AuthProvider>
    )
}

export default App