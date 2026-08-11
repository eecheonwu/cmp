import { useState, type FormEvent, useRef, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export function VerifyOTPPage() {
    const [otp, setOtp] = useState(['', '', '', '', '', ''])
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [phoneNumber, setPhoneNumber] = useState('')
    const inputRefs = useRef<HTMLInputElement[]>([])
    const navigate = useNavigate()
    const { verifyOTP } = useAuth()

    // Get phone number from session storage (set during registration)
    useEffect(() => {
        const storedPhone = sessionStorage.getItem('verify_phone')
        if (storedPhone) {
            setPhoneNumber(storedPhone)
        }
    }, [])

    const handleChange = (index: number, value: string) => {
        if (value.length > 1) return

        const newOtp = [...otp]
        newOtp[index] = value
        setOtp(newOtp)

        // Auto-focus next input
        if (value && index < 5) {
            inputRefs.current[index + 1]?.focus()
        }
    }

    const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            inputRefs.current[index - 1]?.focus()
        }
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        const otpCode = otp.join('')
        if (otpCode.length !== 6) {
            setError('Please enter the complete 6-digit code')
            setIsLoading(false)
            return
        }

        try {
            await verifyOTP(phoneNumber, otpCode)
            navigate('/dashboard')
        } catch (err) {
            setError('Invalid OTP code. Please try again.')
            setOtp(['', '', '', '', '', ''])
            inputRefs.current[0]?.focus()
        } finally {
            setIsLoading(false)
        }
    }

    const handleResendOTP = async () => {
        if (!phoneNumber) return
        setError(null)
        try {
            const apiClient = (await import('../../services/api')).default
            const response = await apiClient.post('/verify-request', { phone_number: phoneNumber })
            // In development mode, update the stored OTP
            if (response.data.otp) {
                sessionStorage.setItem('dev_otp', response.data.otp)
            }
            alert('A new OTP code has been sent to your phone number.')
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to resend OTP. Please try again.')
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
                        Verify Your Phone
                    </h1>
                    <p className="mt-2 text-secondary-500">
                        Enter the 6-digit code sent to{' '}
                        <span className="font-semibold text-secondary-700">{phoneNumber}</span>
                    </p>
                </div>

                {/* Form Card */}
                <div className="glass-card p-8">
                    <form className="space-y-6" onSubmit={handleSubmit}>
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

                        {/* OTP Inputs */}
                        <div>
                            <label className="form-label text-center block mb-4">
                                Verification Code
                            </label>
                            <div className="flex justify-center gap-3">
                                {otp.map((digit, index) => (
                                    <input
                                        key={index}
                                        ref={(el: HTMLInputElement | null) => { if (el) inputRefs.current[index] = el }}
                                        type="text"
                                        inputMode="numeric"
                                        pattern="[0-9]*"
                                        maxLength={1}
                                        value={digit}
                                        onChange={(e) => handleChange(index, e.target.value)}
                                        onKeyDown={(e) => handleKeyDown(index, e)}
                                        className={`w-12 h-14 text-center text-2xl font-bold rounded-xl border-2 transition-all duration-200 outline-none
                                            ${digit ? 'border-primary-400 bg-primary-50 shadow-sm shadow-primary-200' : 'border-secondary-200 bg-white/70'}
                                            focus:border-primary-400 focus:ring-4 focus:ring-primary-100
                                            disabled:opacity-50`}
                                        disabled={isLoading}
                                    />
                                ))}
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading || otp.join('').length !== 6}
                            className="btn-primary w-full"
                        >
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Verifying...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Verify Code
                                </span>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <p className="mt-6 text-center text-sm text-secondary-500">
                    Didn't receive the code?{' '}
                    <button
                        type="button"
                        onClick={handleResendOTP}
                        className="font-semibold text-primary-600 hover:text-primary-500 transition-colors bg-transparent border-none cursor-pointer"
                    >
                        Resend Code
                    </button>
                </p>
            </div>
        </div>
    )
}