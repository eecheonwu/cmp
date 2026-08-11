import { Page } from '@playwright/test'

// Mock user data
export const MOCK_PATIENT = {
    id: 'patient-uuid-1',
    phoneNumber: '+2348012345678',
    email: 'patient@test.com',
    role: 'patient' as const,
    isVerified: true,
}

export const MOCK_DOCTOR = {
    id: 'doctor-uuid-1',
    fullName: 'Dr. John Smith',
    specialization: 'General Practitioner',
    branchId: 'branch-1',
}

export const MOCK_BRANCHES = [
    {
        id: 'branch-1',
        name: 'Main Clinic',
        address: '123 Main Street, Lagos',
        phone: '+234-1-234-5678',
        email: 'main@clinic.com',
    },
    {
        id: 'branch-2',
        name: 'Branch Clinic A',
        address: '456 Branch Avenue, Lagos',
        phone: '+234-1-345-6789',
        email: 'branch-a@clinic.com',
    },
]

export const MOCK_DOCTORS = [
    {
        id: 'doctor-uuid-1',
        fullName: 'Dr. John Smith',
        specialization: 'General Practitioner',
        branchId: 'branch-1',
    },
    {
        id: 'doctor-uuid-2',
        fullName: 'Dr. Sarah Johnson',
        specialization: 'Pediatrician',
        branchId: 'branch-1',
    },
]

export const MOCK_AVAILABLE_SLOTS = [
    { start: '2026-07-15T09:00:00Z', end: '2026-07-15T09:30:00Z', isAvailable: true },
    { start: '2026-07-15T09:30:00Z', end: '2026-07-15T10:00:00Z', isAvailable: true },
    { start: '2026-07-15T10:00:00Z', end: '2026-07-15T10:30:00Z', isAvailable: true },
    { start: '2026-07-15T10:30:00Z', end: '2026-07-15T11:00:00Z', isAvailable: true },
    { start: '2026-07-15T11:00:00Z', end: '2026-07-15T11:30:00Z', isAvailable: true },
]

export const MOCK_APPOINTMENTS = [
    {
        id: 'appt-uuid-1',
        doctorId: 'doctor-uuid-1',
        patientId: 'patient-uuid-1',
        branchId: 'branch-1',
        startDatetime: '2026-07-15T09:00:00Z',
        endDatetime: '2026-07-15T09:30:00Z',
        status: 'booked' as const,
        paymentState: 'pending' as const,
        bookingSource: 'patient' as const,
        createdAt: '2026-07-10T08:00:00Z',
        updatedAt: '2026-07-10T08:00:00Z',
    },
    {
        id: 'appt-uuid-2',
        doctorId: 'doctor-uuid-2',
        patientId: 'patient-uuid-1',
        branchId: 'branch-1',
        startDatetime: '2026-07-16T14:00:00Z',
        endDatetime: '2026-07-16T14:30:00Z',
        status: 'booked' as const,
        paymentState: 'pending' as const,
        bookingSource: 'patient' as const,
        createdAt: '2026-07-10T09:00:00Z',
        updatedAt: '2026-07-10T09:00:00Z',
    },
]

export const MOCK_CANCEL_RESPONSE = {
    id: 'appt-uuid-1',
    status: 'cancelled',
    message: 'Appointment cancelled successfully',
}

// Auth tokens
export const MOCK_ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwYXRpZW50LXV1aWQtMSIsInJvbGUiOiJwYXRpZW50IiwiZXhwIjo0ODUxMzg3MjAwfQ.mock-token'
export const MOCK_REFRESH_TOKEN = 'mock-refresh-token'

// Login response
export const MOCK_LOGIN_RESPONSE = {
    access_token: MOCK_ACCESS_TOKEN,
    refresh_token: MOCK_REFRESH_TOKEN,
    user: MOCK_PATIENT,
}

// Register response
export const MOCK_REGISTER_RESPONSE = {
    access_token: MOCK_ACCESS_TOKEN,
    refresh_token: MOCK_REFRESH_TOKEN,
    user: MOCK_PATIENT,
}

// Verify OTP response
export const MOCK_VERIFY_OTP_RESPONSE = {
    access_token: MOCK_ACCESS_TOKEN,
    refresh_token: MOCK_REFRESH_TOKEN,
    user: MOCK_PATIENT,
}

// Book appointment response
export const MOCK_BOOK_RESPONSE = {
    id: 'appt-uuid-3',
    doctorId: 'doctor-uuid-1',
    patientId: 'patient-uuid-1',
    branchId: 'branch-1',
    startDatetime: '2026-07-15T09:00:00Z',
    endDatetime: '2026-07-15T09:30:00Z',
    status: 'booked',
    paymentState: 'pending',
    bookingSource: 'patient',
    createdAt: '2026-07-10T10:00:00Z',
    updatedAt: '2026-07-10T10:00:00Z',
}

/**
 * Set up API route mocking for the patient journey
 */
export async function setupPatientJourneyMocks(page: Page) {
    // Mock auth endpoints
    await page.route('**/api/v1/auth/login', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_LOGIN_RESPONSE),
        })
    })

    await page.route('**/api/v1/auth/register', async (route) => {
        await route.fulfill({
            status: 201,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_REGISTER_RESPONSE),
        })
    })

    await page.route('**/api/v1/auth/verify-code', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_VERIFY_OTP_RESPONSE),
        })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_PATIENT),
        })
    })

    // Mock appointment endpoints
    await page.route('**/api/v1/appointments', async (route, request) => {
        if (request.method() === 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_APPOINTMENTS),
            })
        } else if (request.method() === 'POST') {
            await route.fulfill({
                status: 201,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_BOOK_RESPONSE),
            })
        } else {
            await route.continue()
        }
    })

    await page.route('**/api/v1/appointments/available-slots*', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_AVAILABLE_SLOTS),
        })
    })

    await page.route('**/api/v1/appointments/*', async (route, request) => {
        if (request.method() === 'DELETE') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_CANCEL_RESPONSE),
            })
        } else {
            await route.continue()
        }
    })
}

/**
 * Set up API route mocking for offline mode test
 */
export async function setupOfflineModeMocks(page: Page) {
    // Mock auth to auto-login
    await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_PATIENT),
        })
    })

    // Mock appointments endpoint
    await page.route('**/api/v1/appointments', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_APPOINTMENTS),
        })
    })
}

/**
 * Set localStorage with auth data to simulate logged-in state.
 * Must be called AFTER page.goto() to ensure the origin is accessible.
 */
export async function setLoggedInState(page: Page) {
    await page.evaluate(({ token, user }) => {
        localStorage.setItem('cmp_access_token', token)
        localStorage.setItem('cmp_refresh_token', 'mock-refresh-token')
        localStorage.setItem('cmp_user', JSON.stringify(user))
    }, { token: MOCK_ACCESS_TOKEN, user: MOCK_PATIENT })
}