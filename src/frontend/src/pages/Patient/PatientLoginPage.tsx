import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export function PatientLoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()
    const { patientLogin } = useAuth()

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            await patientLogin(email.trim(), password)
            navigate('/dashboard', { replace: true })
        } catch (err: any) {
            const status = err?.response?.status
            const detail = err?.response?.data?.detail

            if (status === 403) {
                setError('Your email address has not been verified. Please check your inbox for the verification link.')
            } else if (status === 401) {
                setError('Invalid email or password. Please try again.')
            } else if (typeof detail === 'string') {
                setError(detail)
            } else {
                setError('An error occurred. Please try again.')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const styles = {
        page: {
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: '24px',
            fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        } as React.CSSProperties,
        card: {
            width: '100%',
            maxWidth: 440,
            background: '#ffffff',
            borderRadius: 16,
            boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
            padding: 40,
            position: 'relative' as const,
            overflow: 'hidden',
        } as React.CSSProperties,
        cardAccent: {
            position: 'absolute' as const,
            top: 0,
            left: 0,
            right: 0,
            height: 4,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        } as React.CSSProperties,
        iconContainer: {
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            boxShadow: '0 8px 24px rgba(102, 126, 234, 0.35)',
        } as React.CSSProperties,
        title: {
            fontSize: 24,
            fontWeight: 700,
            color: '#1f2937',
            textAlign: 'center' as const,
            marginBottom: 8,
        } as React.CSSProperties,
        subtitle: {
            fontSize: 14,
            color: '#6b7280',
            textAlign: 'center' as const,
            marginBottom: 28,
            lineHeight: 1.5,
        } as React.CSSProperties,
        label: {
            display: 'block',
            fontSize: 14,
            fontWeight: 600,
            color: '#374151',
            marginBottom: 6,
        } as React.CSSProperties,
        inputWrapper: {
            marginBottom: 20,
        } as React.CSSProperties,
        input: {
            width: '100%',
            padding: '12px 16px',
            border: '2px solid #e5e7eb',
            borderRadius: 12,
            fontSize: 15,
            color: '#1f2937',
            outline: 'none',
            transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
            boxSizing: 'border-box' as const,
            background: '#fafbfc',
        } as React.CSSProperties,
        passwordInput: {
            width: '100%',
            padding: '12px 44px 12px 16px',
            border: '2px solid #e5e7eb',
            borderRadius: 12,
            fontSize: 15,
            color: '#1f2937',
            outline: 'none',
            transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
            boxSizing: 'border-box' as const,
            background: '#fafbfc',
        } as React.CSSProperties,
        inputFocus: {
            borderColor: '#667eea',
            boxShadow: '0 0 0 3px rgba(102, 126, 234, 0.12)',
            background: '#fff',
        } as React.CSSProperties,
        toggleBtn: {
            position: 'absolute' as const,
            right: 12,
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 4,
            color: '#9ca3af',
            fontSize: 18,
        } as React.CSSProperties,
        button: {
            width: '100%',
            padding: '14px 24px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: '#ffffff',
            border: 'none',
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease',
            boxShadow: '0 4px 14px rgba(102, 126, 234, 0.4)',
        } as React.CSSProperties,
        buttonDisabled: {
            opacity: 0.6,
            cursor: 'not-allowed',
        } as React.CSSProperties,
        errorBanner: {
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 12,
            padding: '12px 16px',
            marginBottom: 20,
            fontSize: 14,
            color: '#dc2626',
            lineHeight: 1.5,
        } as React.CSSProperties,
        linkRow: {
            textAlign: 'center' as const,
            marginTop: 20,
            fontSize: 14,
            color: '#6b7280',
        } as React.CSSProperties,
        link: {
            color: '#667eea',
            fontWeight: 600,
            textDecoration: 'none',
        } as React.CSSProperties,
        divider: {
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            margin: '20px 0',
            color: '#9ca3af',
            fontSize: 13,
        } as React.CSSProperties,
        dividerLine: {
            flex: 1,
            height: 1,
            background: '#e5e7eb',
        } as React.CSSProperties,
    }

    return (
        <div style={styles.page}>
            <div style={styles.card}>
                <div style={styles.cardAccent} />

                {/* Header Icon */}
                <div style={styles.iconContainer}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                    </svg>
                </div>

                <h1 style={styles.title}>Patient Sign In</h1>
                <p style={styles.subtitle}>
                    Sign in with your email and password to access your patient portal.
                </p>

                {/* Error Banner */}
                {error && (
                    <div style={styles.errorBanner}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Email Field */}
                    <div style={styles.inputWrapper}>
                        <label style={styles.label}>Email Address</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            required
                            disabled={isLoading}
                            style={styles.input}
                            onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#e5e7eb'
                                e.target.style.boxShadow = 'none'
                                e.target.style.background = '#fafbfc'
                            }}
                        />
                    </div>

                    {/* Password Field */}
                    <div style={styles.inputWrapper}>
                        <label style={styles.label}>Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                required
                                disabled={isLoading}
                                style={styles.passwordInput}
                                onFocus={(e) => Object.assign(e.target.style, styles.inputFocus)}
                                onBlur={(e) => {
                                    e.target.style.borderColor = '#e5e7eb'
                                    e.target.style.boxShadow = 'none'
                                    e.target.style.background = '#fafbfc'
                                }}
                            />
                            <button
                                type="button"
                                style={styles.toggleBtn}
                                onClick={() => setShowPassword(!showPassword)}
                                tabIndex={-1}
                                aria-label={showPassword ? 'Hide password' : 'Show password'}
                            >
                                {showPassword ? '🙈' : '👁️'}
                            </button>
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isLoading}
                        style={{
                            ...styles.button,
                            ...(isLoading ? styles.buttonDisabled : {}),
                        }}
                    >
                        {isLoading ? (
                            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                                <svg width="20" height="20" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                                    <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="3" fill="none" opacity="0.3" />
                                    <path d="M12 2a10 10 0 0 1 10 10" stroke="white" strokeWidth="3" fill="none" strokeLinecap="round" />
                                </svg>
                                Signing in...
                            </span>
                        ) : (
                            'Sign In'
                        )}
                    </button>
                </form>

                <div style={styles.linkRow}>
                    Don't have an account?{' '}
                    <Link to="/patient/register" style={styles.link}>Register</Link>
                </div>

                <div style={styles.divider}>
                    <div style={styles.dividerLine} />
                    <span>or</span>
                    <div style={styles.dividerLine} />
                </div>

                <div style={styles.linkRow}>
                    Are you a staff member?{' '}
                    <Link to="/login" style={styles.link}>Staff Sign In</Link>
                </div>

                {/* Inline keyframe for spinner */}
                <style>{`
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        </div>
    )
}
