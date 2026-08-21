import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import apiClient from '../services/api'
import { setToken, setRefreshToken, clearAuth, getUser, setUser } from '../utils/storage'

// User type
export interface User {
    id: string
    phoneNumber: string
    email: string
    role: 'patient' | 'receptionist' | 'doctor' | 'manager' | 'admin' | 'executive'
    isVerified: boolean
    audience?: 'patient' | 'staff'
}

// Auth context type
interface AuthContextType {
    user: User | null
    isLoading: boolean
    login: (email: string, password: string) => Promise<void>
    patientLogin: (email: string, password: string) => Promise<void>
    register: (data: RegisterData) => Promise<void>
    verifyOTP: (phoneNumber: string, otp: string) => Promise<void>
    logout: () => void
}

interface RegisterData {
    phone_number: string
    full_name: string
    date_of_birth?: string
    gender?: string
    emergency_contact?: string
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUserState] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    // Check for existing user on mount
    useEffect(() => {
        const storedUser = getUser()
        if (storedUser) {
            setUserState(storedUser as User)
        }
        setIsLoading(false)
    }, [])

    const login = async (email: string, password: string): Promise<void> => {
        try {
            const response = await apiClient.post('/login', { email, password })
            const { access_token, refresh_token } = response.data

            setToken(access_token)
            setRefreshToken(refresh_token)

            // Fetch user data via /me endpoint
            const meResponse = await apiClient.get('/me')
            const userData = { ...meResponse.data, audience: 'staff' }
            setUser(userData)
            setUserState(userData)
        } catch (error) {
            throw error
        }
    }

    const patientLogin = async (email: string, password: string): Promise<void> => {
        try {
            const response = await apiClient.post('/auth/patient/login', { email, password })
            const { access_token, refresh_token } = response.data

            setToken(access_token)
            setRefreshToken(refresh_token)

            // Fetch user data via /me endpoint
            const meResponse = await apiClient.get('/me')
            const userData = { ...meResponse.data, audience: 'patient' }
            setUser(userData)
            setUserState(userData)
        } catch (error) {
            throw error
        }
    }

    const register = async (data: RegisterData): Promise<void> => {
        try {
            const response = await apiClient.post('/register', data)
            const { registration_token, otp } = response.data

            if (registration_token) {
                sessionStorage.setItem('registration_token', registration_token)
            }
            sessionStorage.setItem('pending_registration_data', JSON.stringify(data))

            // In development mode, store the OTP for testing purposes
            if (otp) {
                sessionStorage.setItem('dev_otp', otp)
            }
        } catch (error) {
            throw error
        }
    }

    const verifyOTP = async (phoneNumber: string, otp: string): Promise<void> => {
        try {
            const registrationToken = sessionStorage.getItem('registration_token')
            const pendingDataStr = sessionStorage.getItem('pending_registration_data')
            const pendingData = pendingDataStr ? JSON.parse(pendingDataStr) : null

            const response = await apiClient.post('/verify-code', {
                phone_number: phoneNumber,
                otp_code: otp,
                registration_token: registrationToken || undefined,
                registration_data: pendingData || undefined,
            })
            const { access_token, refresh_token } = response.data

            setToken(access_token)
            setRefreshToken(refresh_token)

            // Clear temporary pending registration storage
            sessionStorage.removeItem('registration_token')
            sessionStorage.removeItem('pending_registration_data')

            // Fetch user data via /me endpoint
            const meResponse = await apiClient.get('/me')
            const userData = meResponse.data
            setUser(userData)
            setUserState(userData)
        } catch (error) {
            throw error
        }
    }

    const logout = (): void => {
        clearAuth()
        setUserState(null)
    }

    return (
        <AuthContext.Provider value={{ user, isLoading, login, patientLogin, register, verifyOTP, logout }}>
            {children}
        </AuthContext.Provider>
    )
}

// Hook to use auth context
export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}