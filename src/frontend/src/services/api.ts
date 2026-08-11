import axios from 'axios'
import { getToken, setToken, clearToken } from '../utils/storage'

// Create axios instance with base URL
const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
    (config) => {
        const token = getToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor to handle 401 errors
apiClient.interceptors.response.use(
    (response) => {
        return response
    },
    (error) => {
        if (error.response?.status === 401) {
            // Clear token and redirect to login
            clearToken()
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

export default apiClient