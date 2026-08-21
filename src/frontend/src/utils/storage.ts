// Token storage utilities
const TOKEN_KEY = 'cmp_access_token'
const REFRESH_TOKEN_KEY = 'cmp_refresh_token'

export const setToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token)
}

export const getToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY)
}

export const setRefreshToken = (token: string): void => {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export const getRefreshToken = (): string | null => {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export const clearToken = (): void => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
}

// User storage
const USER_KEY = 'cmp_user'

export const setUser = (user: unknown): void => {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export const getUser = (): unknown | null => {
    const userStr = localStorage.getItem(USER_KEY)
    if (userStr) {
        try {
            return JSON.parse(userStr)
        } catch {
            return null
        }
    }
    return null
}

export const clearUser = (): void => {
    localStorage.removeItem(USER_KEY)
}

// Clear all auth data
export const clearAuth = (): void => {
    clearToken()
    clearUser()
}