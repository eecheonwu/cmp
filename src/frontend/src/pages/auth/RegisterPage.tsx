import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export function RegisterPage() {
    const [phoneNumber, setPhoneNumber] = useState('')
    const [fullName, setFullName] = useState('')
    const [dateOfBirth, setDateOfBirth] = useState<string | undefined>(undefined)
    const [gender, setGender] = useState<string | undefined>(undefined)
    const [emergencyContact, setEmergencyContact] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()
    const { register } = useAuth()

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            const cleanPhone = phoneNumber.replace(/[\s\-\(\)]/g, '')
            // Store phone number for OTP verification page
            sessionStorage.setItem('verify_phone', cleanPhone)

            await register({
                phone_number: cleanPhone,
                full_name: fullName.trim(),
                date_of_birth: dateOfBirth || undefined,
                gender: gender || undefined,
                emergency_contact: emergencyContact?.trim() || undefined,
            })
            navigate('/verify-otp')
        } catch (err: any) {
            console.error('Registration error:', err)
            console.error('Error response:', err?.response?.data)
            console.error('Error status:', err?.response?.status)
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
        <div className="min-h-screen flex items-center justify-center px-4 py-12">
            {/* Decorative background elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-200/30 rounded-full blur-3xl" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent-200/20 rounded-full blur-3xl" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-100/20 rounded-full blur-3xl" />
            </div>

            <div className="w-full max-w-md animate-fade-in">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/30 mb-4">
                        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-bold gradient-text">
                        Clinic Modernization Platform
                    </h1>
                    <p className="mt-2 text-secondary-500">
                        Create your patient account
                    </p>
                </div>

                {/* Form Card */}
                <div className="glass-card p-8">
                    <form className="space-y-5" onSubmit={handleSubmit}>
                        {error && (
                            <div className="error-message">
                                <div className="flex items-center gap-2">
                                    <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                    </svg>
                                    {error}
                                </div>
                            </div>
                        )}

                        <div>
                            <label htmlFor="phoneNumber" className="form-label">
                                Phone Number
                            </label>
                            <input
                                id="phoneNumber"
                                type="tel"
                                required
                                value={phoneNumber}
                                onChange={(e) => setPhoneNumber(e.target.value)}
                                className="input-field"
                                placeholder="+234 800 000 0000"
                                disabled={isLoading}
                            />
                        </div>

                        <div>
                            <label htmlFor="fullName" className="form-label">
                                Full Name
                            </label>
                            <input
                                id="fullName"
                                type="text"
                                required
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                className="input-field"
                                placeholder="Enter your full name"
                                disabled={isLoading}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="dateOfBirth" className="form-label">
                                    Date of Birth
                                </label>
                                <input
                                    id="dateOfBirth"
                                    type="date"
                                    value={dateOfBirth}
                                    onChange={(e) => setDateOfBirth(e.target.value)}
                                    className="input-field"
                                    disabled={isLoading}
                                />
                            </div>

                            <div>
                                <label htmlFor="gender" className="form-label">
                                    Gender
                                </label>
                                <select
                                    id="gender"
                                    value={gender}
                                    onChange={(e) => setGender(e.target.value)}
                                    className="select-field"
                                    disabled={isLoading}
                                >
                                    <option value="">Select</option>
                                    <option value="male">Male</option>
                                    <option value="female">Female</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label htmlFor="emergencyContact" className="form-label">
                                Emergency Contact <span className="text-secondary-400 font-normal">(Optional)</span>
                            </label>
                            <input
                                id="emergencyContact"
                                type="text"
                                value={emergencyContact}
                                onChange={(e) => setEmergencyContact(e.target.value)}
                                className="input-field"
                                placeholder="Emergency contact name and phone"
                                disabled={isLoading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="btn-primary w-full"
                        >
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Creating account...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                                    </svg>
                                    Create Account
                                </span>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <p className="mt-6 text-center text-sm text-secondary-500">
                    Already have an account?{' '}
                    <Link to="/login" className="font-semibold text-primary-600 hover:text-primary-500 transition-colors">
                        Sign in here
                    </Link>
                </p>
            </div>
        </div>
    )
}