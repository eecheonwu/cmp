import { test, expect } from '@playwright/test'
import {
    setupPatientJourneyMocks,
    setLoggedInState,
    MOCK_PATIENT,
} from './test-utils'

test.describe('Patient Journey - E2E', () => {
    test.beforeEach(async ({ page }) => {
        await setupPatientJourneyMocks(page)
    })

    test('TC-PJ-01: Full patient registration flow', async ({ page }) => {
        // Override the register mock to return an unverified user (no redirect to dashboard)
        await page.route('**/api/v1/auth/register', async (route) => {
            await route.fulfill({
                status: 201,
                contentType: 'application/json',
                body: JSON.stringify({
                    access_token: 'mock-token-unverified',
                    refresh_token: 'mock-refresh',
                    user: { ...MOCK_PATIENT, isVerified: false },
                }),
            })
        })

        // Navigate to register page
        await page.goto('/register')
        await page.waitForLoadState('networkidle')

        // Verify we're on the registration page
        await expect(page.locator('text=Patient Registration')).toBeVisible()

        // Fill in registration form
        await page.fill('#phoneNumber', '+2348012345678')
        await page.fill('#email', 'patient@test.com')
        await page.fill('#password', 'SecurePass123!')
        await page.fill('#fullName', 'John Doe')
        await page.fill('#dateOfBirth', '1990-01-15')
        await page.selectOption('#gender', 'male')
        await page.fill('#emergencyContact', 'Jane Doe - +2348012345679')

        // Submit registration
        await page.click('button[type="submit"]')

        // Should navigate to verify-otp page
        await page.waitForURL('**/verify-otp')
        await expect(page.locator('h1')).toContainText('Verify Your Phone')
    })

    test('TC-PJ-02: OTP verification flow', async ({ page }) => {
        // Set phone number in session storage (as done during registration)
        await page.goto('/verify-otp')
        await page.evaluate(() => {
            sessionStorage.setItem('verify_phone', '+2348012345678')
        })
        await page.reload()
        await page.waitForLoadState('networkidle')

        // Verify the phone number is displayed
        await expect(page.locator('text=+2348012345678')).toBeVisible()

        // Fill in OTP digits one by one
        const otpInputs = page.locator('input[inputmode="numeric"]')
        const digits = ['1', '2', '3', '4', '5', '6']
        for (let i = 0; i < digits.length; i++) {
            await otpInputs.nth(i).fill(digits[i])
        }

        // Click verify button
        await page.click('button[type="submit"]')

        // Should navigate to dashboard after successful verification
        await page.waitForURL('**/dashboard')
        await expect(page.locator('h1')).toContainText('Dashboard')
    })

    test('TC-PJ-03: Staff login flow', async ({ page }) => {
        // Navigate to login page
        await page.goto('/login')
        await page.waitForLoadState('networkidle')

        // Verify we're on the login page
        await expect(page.locator('h1')).toContainText('Clinic Modernization Platform')
        await expect(page.locator('text=Staff Login')).toBeVisible()

        // Fill in login form
        await page.fill('#email', 'staff@clinic.com')
        await page.fill('#password', 'StaffPass123!')

        // Submit login
        await page.click('button[type="submit"]')

        // Should navigate to dashboard after successful login
        await page.waitForURL('**/dashboard')
        await expect(page.locator('h1')).toContainText('Dashboard')
    })

    test('TC-PJ-04: View appointments list', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to appointments page
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Verify appointments are displayed
        await expect(page.locator('h1')).toContainText('My Appointments')

        // Verify status badges
        const bookedBadges = page.locator('text=Booked')
        await expect(bookedBadges.first()).toBeVisible()

        // Verify "Book New Appointment" button is present
        await expect(page.locator('text=Book New Appointment')).toBeVisible()
    })

    test('TC-PJ-05: Book new appointment flow', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to branch selection
        await page.goto('/appointments/new')
        await page.waitForLoadState('networkidle')

        // Verify branch selection page
        await expect(page.locator('h1')).toContainText('Select Branch')

        // Select first branch
        await page.click('text=Main Clinic')
        await page.waitForURL('**/appointments/new/doctor**')

        // Verify doctor selection page
        await expect(page.locator('h1')).toContainText('Select Doctor')

        // Select first doctor
        await page.click('text=Dr. John Smith')
        await page.waitForURL('**/appointments/new/slot**')

        // Verify slot selection page
        await expect(page.locator('h1')).toContainText('Select Time Slot')

        // Select first available slot
        const availableSlots = page.locator('button:not([disabled])')
        await availableSlots.first().click()

        // Verify selected slot is highlighted and confirm button appears
        await expect(page.locator('text=Confirm Booking')).toBeVisible()

        // Click confirm booking
        await page.click('text=Confirm Booking')

        // Should navigate to confirmation page
        await page.waitForURL('**/appointments/**/confirm')
        await expect(page.locator('text=Appointment Booked!')).toBeVisible()

        // Verify appointment details on confirmation
        await expect(page.locator('text=View My Appointments')).toBeVisible()
        await expect(page.locator('text=Book Another')).toBeVisible()
    })

    test('TC-PJ-06: Cancel appointment with penalty warning', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to appointments page
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Click cancel button on first appointment
        await page.click('button:has-text("Cancel"):first-of-type')

        // Verify cancel confirmation dialog appears
        await expect(page.locator('text=Confirm Cancellation')).toBeVisible()

        // Verify cancel button in dialog
        await expect(page.locator('text=Yes, Cancel')).toBeVisible()
        await expect(page.locator('text=No, Keep')).toBeVisible()

        // Click "Yes, Cancel" to confirm
        await page.click('text=Yes, Cancel')

        // Wait for the cancellation to process
        await page.waitForTimeout(1000)

        // Verify the appointment status changed to cancelled
        await expect(page.locator('text=Cancelled')).toBeVisible()
    })

    test('TC-PJ-07: Cancel appointment - dismiss confirmation', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to appointments page
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Click cancel button on first appointment
        await page.click('button:has-text("Cancel"):first-of-type')

        // Verify cancel confirmation dialog appears
        await expect(page.locator('text=Confirm Cancellation')).toBeVisible()

        // Click "No, Keep" to dismiss
        await page.click('text=No, Keep')

        // Verify dialog is dismissed
        await expect(page.locator('text=Confirm Cancellation')).not.toBeVisible()
    })

    test('TC-PJ-08: Login form validation - empty fields', async ({ page }) => {
        await page.goto('/login')
        await page.waitForLoadState('networkidle')

        // Try submitting empty form
        await page.click('button[type="submit"]')

        // HTML5 validation should prevent submission
        // Verify we're still on the login page
        await expect(page.locator('h1')).toContainText('Clinic Modernization Platform')
    })

    test('TC-PJ-09: Login form validation - invalid credentials', async ({ page }) => {
        await page.goto('/login')
        await page.waitForLoadState('networkidle')

        // Fill in invalid credentials
        await page.fill('#email', 'wrong@email.com')
        await page.fill('#password', 'wrongpassword')

        // Override the login mock to return 401
        await page.route('**/api/v1/auth/login', async (route) => {
            await route.fulfill({
                status: 401,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Invalid credentials' }),
            })
        })

        // Submit login
        await page.click('button[type="submit"]')

        // Verify error message is displayed
        await expect(page.locator('text=Invalid email or password')).toBeVisible()
    })

    test('TC-PJ-10: Unauthenticated user redirected to login', async ({ page }) => {
        // Try to access protected route without auth
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Should be redirected to login
        await expect(page).toHaveURL(/\/login/)
    })

    test('TC-PJ-11: Logout clears session and redirects', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to appointments page
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Click logout button
        await page.click('text=Logout')

        // Should redirect to login
        await expect(page).toHaveURL(/\/login/)

        // Verify localStorage is cleared
        const token = await page.evaluate(() => localStorage.getItem('cmp_access_token'))
        expect(token).toBeNull()
    })

    test('TC-PJ-12: Navigate between booking flow steps', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Start booking flow
        await page.goto('/appointments/new')
        await page.waitForLoadState('networkidle')

        // Verify branch selection
        await expect(page.locator('h1')).toContainText('Select Branch')

        // Navigate back to appointments
        await page.click('text=Back to Appointments')
        await expect(page).toHaveURL(/\/appointments$/)
    })
})