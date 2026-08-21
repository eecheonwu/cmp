import { useState, useMemo, type FormEvent } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import apiClient from '../../services/api'
import { setToken, setRefreshToken, setUser } from '../../utils/storage'

export function PatientCreatePasswordPage() {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const token = searchParams.get('token')

    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [pageState, setPageState] = useState<'form' | 'expired' | 'used' | 'no-token'>(
        token ? 'form' : 'no-token'
    )

    // Real-time password strength checklist
    const checks = useMemo(() => ({
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        digit: /[0-9]/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password),
    }), [password])

    const allChecksPassed = Object.values(checks).every(Boolean)
    const passwordsMatch = password.length > 0 && password === confirmPassword
    const canSubmit = allChecksPassed && passwordsMatch && !isLoading

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        if (!canSubmit || !token) return
        setError(null)
        setIsLoading(true)

        try {
            const response = await apiClient.post('/auth/patient/verify-email', {
                token,
                password,
                confirm_password: confirmPassword,
            })

            // Store JWT tokens using storage utility
            const { access_token, refresh_token } = response.data
            if (access_token) setToken(access_token)
            if (refresh_token) setRefreshToken(refresh_token)

            // Redirect to patient sign-in page
            navigate('/patient/login', { replace: true })
        } catch (err: any) {
            const status = err?.response?.status
            const detail = err?.response?.data?.detail

            if (status === 409) {
                setPageState('used')
            } else if (status === 400 && typeof detail === 'string' && detail.toLowerCase().includes('expired')) {
                setPageState('expired')
            } else if (status === 422) {
                // Pydantic validation errors
                const errors = err?.response?.data?.detail
                if (Array.isArray(errors)) {
                    setError(errors.map((item: any) => item.msg || JSON.stringify(item)).join(', '))
                } else {
                    setError(typeof detail === 'string' ? detail : 'Validation error. Please check your input.')
                }
            } else {
                setError(typeof detail === 'string' ? detail : 'An error occurred. Please try again.')
            }
        } finally {
            setIsLoading(false)
        }
    }

    // ── Styles ──────────────────────────────────────────────────────────

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
            maxWidth: 480,
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
            position: 'relative' as const,
            marginBottom: 16,
        } as React.CSSProperties,
        input: {
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
        checklist: {
            background: '#f9fafb',
            borderRadius: 12,
            padding: '14px 18px',
            marginBottom: 20,
        } as React.CSSProperties,
        checklistTitle: {
            fontSize: 13,
            fontWeight: 600,
            color: '#6b7280',
            marginBottom: 10,
            textTransform: 'uppercase' as const,
            letterSpacing: '0.5px',
        } as React.CSSProperties,
        checkItem: (met: boolean) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            color: met ? '#059669' : '#9ca3af',
            marginBottom: 5,
            fontWeight: met ? 500 : 400,
            transition: 'color 0.2s ease',
        }) as React.CSSProperties,
        matchIndicator: (match: boolean, hasInput: boolean) => ({
            fontSize: 13,
            fontWeight: 500,
            color: !hasInput ? '#9ca3af' : match ? '#059669' : '#dc2626',
            marginTop: 6,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'color 0.2s ease',
        }) as React.CSSProperties,
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
            opacity: 0.5,
            cursor: 'not-allowed',
            boxShadow: 'none',
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
            marginTop: 24,
            fontSize: 14,
            color: '#6b7280',
        } as React.CSSProperties,
        link: {
            color: '#667eea',
            fontWeight: 600,
            textDecoration: 'none',
        } as React.CSSProperties,
        stateIcon: {
            width: 72,
            height: 72,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            fontSize: 32,
        } as React.CSSProperties,
    }

    // ── No Token State ──────────────────────────────────────────────────

    if (pageState === 'no-token') {
        return (
            <div style={styles.page}>
                <div style={styles.card}>
                    <div style={styles.cardAccent} />
                    <div style={{ ...styles.stateIcon, background: '#fef3c7', color: '#d97706' }}>⚠️</div>
                    <h1 style={styles.title}>No Verification Token</h1>
                    <p style={styles.subtitle}>
                        No verification token was found in the URL. Please use the link from your
                        verification email to create your password.
                    </p>
                    <div style={styles.linkRow}>
                        <Link to="/patient/register" style={styles.link}>Register for an account</Link>
                        {' · '}
                        <Link to="/login" style={styles.link}>Sign in</Link>
                    </div>
                </div>
            </div>
        )
    }

    // ── Expired Token State ─────────────────────────────────────────────

    if (pageState === 'expired') {
        return (
            <div style={styles.page}>
                <div style={styles.card}>
                    <div style={styles.cardAccent} />
                    <div style={{ ...styles.stateIcon, background: '#fee2e2', color: '#dc2626' }}>⏰</div>
                    <h1 style={styles.title}>Link Expired</h1>
                    <p style={styles.subtitle}>
                        This verification link has expired. Verification links are valid for 60 minutes.
                        Please request a new one to create your password.
                    </p>
                    <Link to="/patient/register" style={{ textDecoration: 'none' }}>
                        <button style={styles.button}>
                            Request New Link
                        </button>
                    </Link>
                    <div style={styles.linkRow}>
                        Already have an account? <Link to="/login" style={styles.link}>Sign in</Link>
                    </div>
                </div>
            </div>
        )
    }

    // ── Used Token State ────────────────────────────────────────────────

    if (pageState === 'used') {
        return (
            <div style={styles.page}>
                <div style={styles.card}>
                    <div style={styles.cardAccent} />
                    <div style={{ ...styles.stateIcon, background: '#dbeafe', color: '#2563eb' }}>✓</div>
                    <h1 style={styles.title}>Link Already Used</h1>
                    <p style={styles.subtitle}>
                        This verification link has already been used to create a password.
                        Please log in with your email and password.
                    </p>
                    <Link to="/login" style={{ textDecoration: 'none' }}>
                        <button style={styles.button}>
                            Go to Login
                        </button>
                    </Link>
                    <div style={styles.linkRow}>
                        Need a new account? <Link to="/patient/register" style={styles.link}>Register</Link>
                    </div>
                </div>
            </div>
        )
    }

    // ── Password Creation Form ──────────────────────────────────────────

    return (
        <div style={styles.page}>
            <div style={styles.card}>
                <div style={styles.cardAccent} />

                {/* Header Icon */}
                <div style={styles.iconContainer}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                </div>

                <h1 style={styles.title}>Create Your Password</h1>
                <p style={styles.subtitle}>
                    Set a strong password to secure your account and complete your registration.
                </p>

                {/* Error Banner */}
                {error && (
                    <div style={styles.errorBanner}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
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
                                style={styles.input}
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

                    {/* Password Strength Checklist */}
                    <div style={styles.checklist}>
                        <div style={styles.checklistTitle}>Password Requirements</div>
                        <div style={styles.checkItem(checks.length)}>
                            <span>{checks.length ? '✅' : '○'}</span>
                            At least 8 characters
                        </div>
                        <div style={styles.checkItem(checks.uppercase)}>
                            <span>{checks.uppercase ? '✅' : '○'}</span>
                            At least one uppercase letter (A-Z)
                        </div>
                        <div style={styles.checkItem(checks.lowercase)}>
                            <span>{checks.lowercase ? '✅' : '○'}</span>
                            At least one lowercase letter (a-z)
                        </div>
                        <div style={styles.checkItem(checks.digit)}>
                            <span>{checks.digit ? '✅' : '○'}</span>
                            At least one digit (0-9)
                        </div>
                        <div style={styles.checkItem(checks.special)}>
                            <span>{checks.special ? '✅' : '○'}</span>
                            At least one special character (!@#$%...)
                        </div>
                    </div>

                    {/* Confirm Password Field */}
                    <div style={styles.inputWrapper}>
                        <label style={styles.label}>Confirm Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showConfirmPassword ? 'text' : 'password'}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Re-enter your password"
                                required
                                style={styles.input}
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
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                tabIndex={-1}
                                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                            >
                                {showConfirmPassword ? '🙈' : '👁️'}
                            </button>
                        </div>
                        <div style={styles.matchIndicator(passwordsMatch, confirmPassword.length > 0)}>
                            <span>
                                {confirmPassword.length === 0
                                    ? '○'
                                    : passwordsMatch
                                        ? '✅'
                                        : '❌'}
                            </span>
                            {confirmPassword.length === 0
                                ? 'Passwords must match'
                                : passwordsMatch
                                    ? 'Passwords match'
                                    : 'Passwords do not match'}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={!canSubmit}
                        style={{
                            ...styles.button,
                            ...(!canSubmit ? styles.buttonDisabled : {}),
                        }}
                    >
                        {isLoading ? (
                            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                                <svg width="20" height="20" viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
                                    <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="3" fill="none" opacity="0.3" />
                                    <path d="M12 2a10 10 0 0 1 10 10" stroke="white" strokeWidth="3" fill="none" strokeLinecap="round" />
                                </svg>
                                Creating Password...
                            </span>
                        ) : (
                            'Create Password & Sign In'
                        )}
                    </button>
                </form>

                <div style={styles.linkRow}>
                    Already have an account? <Link to="/login" style={styles.link}>Sign in</Link>
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
