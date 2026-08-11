import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../../services/api'

export function PatientRegisterPage() {
    const [email, setEmail] = useState('')
    const [phoneNumber, setPhoneNumber] = useState('')
    const [fullName, setFullName] = useState('')
    const [dateOfBirth, setDateOfBirth] = useState('')
    const [gender, setGender] = useState('')
    const [emergencyContact, setEmergencyContact] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [isSuccess, setIsSuccess] = useState(false)
    const [successMessage, setSuccessMessage] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            const cleanPhone = phoneNumber.replace(/[\s\-\(\)]/g, '')
            const response = await apiClient.post('/auth/patient/register', {
                email: email.trim(),
                phone_number: cleanPhone,
                full_name: fullName.trim(),
                date_of_birth: dateOfBirth || undefined,
                gender: gender || undefined,
                emergency_contact: emergencyContact?.trim() || undefined,
            })

            setIsSuccess(true)
            setSuccessMessage(
                response.data?.message ||
                'Verification email sent. Please check your inbox to create your password.'
            )
        } catch (err: any) {
            console.error('Patient email registration error:', err)
            let message = 'Registration failed. Please try again.'
            const detail = err?.response?.data?.detail
            if (typeof detail === 'string') {
                message = detail
            } else if (Array.isArray(detail)) {
                message = detail.map((item: any) => item.msg || JSON.stringify(item)).join(', ')
            } else if (err?.message) {
                message = err.message
            }
            setError(message)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-secondary-50 via-white to-primary-50">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-200/30 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-200/20 rounded-full blur-3xl" />
            </div>

            <div className="w-full max-w-md animate-fade-in relative z-10">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/30 mb-4">
                        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900">
                        Patient Registration
                    </h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Register with your email to receive a password creation link
                    </p>
                </div>

                {/* Form Card or Success Screen */}
                <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-gray-100">
                    {isSuccess ? (
                        <div className="text-center py-6 space-y-4">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mb-2">
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-semibold text-gray-800">Check Your Email</h2>
                            <p className="text-gray-600 leading-relaxed">
                                {successMessage}
                            </p>
                            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-sm text-emerald-800">
                                Email sent to <strong className="font-semibold">{email}</strong>. The verification link expires in 60 minutes.
                            </div>
                            <div className="pt-4">
                                <Link
                                    to="/login"
                                    className="inline-block w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-md transition-all text-center"
                                >
                                    Return to Login
                                </Link>
                            </div>
                        </div>
                    ) : (
                        <form className="space-y-4" onSubmit={handleSubmit}>
                            {error && (
                                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-2">
                                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                    <span>{error}</span>
                                </div>
                            )}

                            <div>
                                <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1">
                                    Full Name <span className="text-rose-500">*</span>
                                </label>
                                <input
                                    id="fullName"
                                    type="text"
                                    required
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    placeholder="Jane Doe"
                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900"
                                />
                            </div>

                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                                    Email Address <span className="text-rose-500">*</span>
                                </label>
                                <input
                                    id="email"
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="patient@example.com"
                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900"
                                />
                            </div>

                            <div>
                                <label htmlFor="phoneNumber" className="block text-sm font-medium text-gray-700 mb-1">
                                    Phone Number <span className="text-rose-500">*</span>
                                </label>
                                <input
                                    id="phoneNumber"
                                    type="tel"
                                    required
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value)}
                                    placeholder="+234 801 234 5678"
                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="dateOfBirth" className="block text-sm font-medium text-gray-700 mb-1">
                                        Date of Birth
                                    </label>
                                    <input
                                        id="dateOfBirth"
                                        type="date"
                                        value={dateOfBirth}
                                        onChange={(e) => setDateOfBirth(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="gender" className="block text-sm font-medium text-gray-700 mb-1">
                                        Gender
                                    </label>
                                    <select
                                        id="gender"
                                        value={gender}
                                        onChange={(e) => setGender(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900 bg-white"
                                    >
                                        <option value="">Select...</option>
                                        <option value="male">Male</option>
                                        <option value="female">Female</option>
                                        <option value="other">Other</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label htmlFor="emergencyContact" className="block text-sm font-medium text-gray-700 mb-1">
                                    Emergency Contact (Optional)
                                </label>
                                <input
                                    id="emergencyContact"
                                    type="text"
                                    value={emergencyContact}
                                    onChange={(e) => setEmergencyContact(e.target.value)}
                                    placeholder="Name & phone number"
                                    className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all text-gray-900"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-medium rounded-xl shadow-lg shadow-primary-500/25 transition-all disabled:opacity-50 mt-4 flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                        Sending Verification Link...
                                    </>
                                ) : (
                                    'Register & Send Verification Link'
                                )}
                            </button>
                        </form>
                    )}
                </div>

                {/* Footer links */}
                <div className="text-center mt-6 space-y-2 text-sm text-gray-600">
                    <p>
                        Already have an account?{' '}
                        <Link to="/login" className="font-semibold text-primary-600 hover:text-primary-700 underline">
                            Log in
                        </Link>
                    </p>
                    <p>
                        Prefer phone verification?{' '}
                        <Link to="/register" className="font-medium text-gray-500 hover:text-gray-700 underline">
                            Register with OTP
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
