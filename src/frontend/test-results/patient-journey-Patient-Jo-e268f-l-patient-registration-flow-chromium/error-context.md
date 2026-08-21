# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: patient-journey.spec.ts >> Patient Journey - E2E >> TC-PJ-01: Full patient registration flow
- Location: src\frontend\tests\e2e\patient-journey.spec.ts:13:5

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('h1')
Expected substring: "Verify Your Phone"
Received string:    "Dashboard"
Timeout: 10000ms

Call log:
  - Expect "toContainText" with timeout 10000ms
  - waiting for locator('h1')
    23 × locator resolved to <h1 class="text-2xl font-bold">Dashboard</h1>
       - unexpected value "Dashboard"

```

```yaml
- heading "Dashboard" [level=1]
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | import {
  3   |     setupPatientJourneyMocks,
  4   |     setLoggedInState,
  5   |     MOCK_PATIENT,
  6   | } from './test-utils'
  7   | 
  8   | test.describe('Patient Journey - E2E', () => {
  9   |     test.beforeEach(async ({ page }) => {
  10  |         await setupPatientJourneyMocks(page)
  11  |     })
  12  | 
  13  |     test('TC-PJ-01: Full patient registration flow', async ({ page }) => {
  14  |         // Override the register mock to return an unverified user (no redirect to dashboard)
  15  |         await page.route('**/api/v1/auth/register', async (route) => {
  16  |             await route.fulfill({
  17  |                 status: 201,
  18  |                 contentType: 'application/json',
  19  |                 body: JSON.stringify({
  20  |                     access_token: 'mock-token-unverified',
  21  |                     refresh_token: 'mock-refresh',
  22  |                     user: { ...MOCK_PATIENT, isVerified: false },
  23  |                 }),
  24  |             })
  25  |         })
  26  | 
  27  |         // Navigate to register page
  28  |         await page.goto('/register')
  29  |         await page.waitForLoadState('networkidle')
  30  | 
  31  |         // Verify we're on the registration page
  32  |         await expect(page.locator('text=Patient Registration')).toBeVisible()
  33  | 
  34  |         // Fill in registration form
  35  |         await page.fill('#phoneNumber', '+2348012345678')
  36  |         await page.fill('#email', 'patient@test.com')
  37  |         await page.fill('#password', 'SecurePass123!')
  38  |         await page.fill('#fullName', 'John Doe')
  39  |         await page.fill('#dateOfBirth', '1990-01-15')
  40  |         await page.selectOption('#gender', 'male')
  41  |         await page.fill('#emergencyContact', 'Jane Doe - +2348012345679')
  42  | 
  43  |         // Submit registration
  44  |         await page.click('button[type="submit"]')
  45  | 
  46  |         // Should navigate to verify-otp page
  47  |         await page.waitForURL('**/verify-otp')
> 48  |         await expect(page.locator('h1')).toContainText('Verify Your Phone')
      |                                          ^ Error: expect(locator).toContainText(expected) failed
  49  |     })
  50  | 
  51  |     test('TC-PJ-02: OTP verification flow', async ({ page }) => {
  52  |         // Set phone number in session storage (as done during registration)
  53  |         await page.goto('/verify-otp')
  54  |         await page.evaluate(() => {
  55  |             sessionStorage.setItem('verify_phone', '+2348012345678')
  56  |         })
  57  |         await page.reload()
  58  |         await page.waitForLoadState('networkidle')
  59  | 
  60  |         // Verify the phone number is displayed
  61  |         await expect(page.locator('text=+2348012345678')).toBeVisible()
  62  | 
  63  |         // Fill in OTP digits one by one
  64  |         const otpInputs = page.locator('input[inputmode="numeric"]')
  65  |         const digits = ['1', '2', '3', '4', '5', '6']
  66  |         for (let i = 0; i < digits.length; i++) {
  67  |             await otpInputs.nth(i).fill(digits[i])
  68  |         }
  69  | 
  70  |         // Click verify button
  71  |         await page.click('button[type="submit"]')
  72  | 
  73  |         // Should navigate to dashboard after successful verification
  74  |         await page.waitForURL('**/dashboard')
  75  |         await expect(page.locator('h1')).toContainText('Dashboard')
  76  |     })
  77  | 
  78  |     test('TC-PJ-03: Staff login flow', async ({ page }) => {
  79  |         // Navigate to login page
  80  |         await page.goto('/login')
  81  |         await page.waitForLoadState('networkidle')
  82  | 
  83  |         // Verify we're on the login page
  84  |         await expect(page.locator('h1')).toContainText('Clinic Modernization Platform')
  85  |         await expect(page.locator('text=Staff Login')).toBeVisible()
  86  | 
  87  |         // Fill in login form
  88  |         await page.fill('#email', 'staff@clinic.com')
  89  |         await page.fill('#password', 'StaffPass123!')
  90  | 
  91  |         // Submit login
  92  |         await page.click('button[type="submit"]')
  93  | 
  94  |         // Should navigate to dashboard after successful login
  95  |         await page.waitForURL('**/dashboard')
  96  |         await expect(page.locator('h1')).toContainText('Dashboard')
  97  |     })
  98  | 
  99  |     test('TC-PJ-04: View appointments list', async ({ page }) => {
  100 |         // Navigate to a page on the app domain first, then set localStorage
  101 |         await page.goto('/login')
  102 |         await page.waitForLoadState('networkidle')
  103 |         await setLoggedInState(page)
  104 | 
  105 |         // Navigate to appointments page
  106 |         await page.goto('/appointments')
  107 |         await page.waitForLoadState('networkidle')
  108 | 
  109 |         // Verify appointments are displayed
  110 |         await expect(page.locator('h1')).toContainText('My Appointments')
  111 | 
  112 |         // Verify status badges
  113 |         const bookedBadges = page.locator('text=Booked')
  114 |         await expect(bookedBadges.first()).toBeVisible()
  115 | 
  116 |         // Verify "Book New Appointment" button is present
  117 |         await expect(page.locator('text=Book New Appointment')).toBeVisible()
  118 |     })
  119 | 
  120 |     test('TC-PJ-05: Book new appointment flow', async ({ page }) => {
  121 |         // Navigate to a page on the app domain first, then set localStorage
  122 |         await page.goto('/login')
  123 |         await page.waitForLoadState('networkidle')
  124 |         await setLoggedInState(page)
  125 | 
  126 |         // Navigate to branch selection
  127 |         await page.goto('/appointments/new')
  128 |         await page.waitForLoadState('networkidle')
  129 | 
  130 |         // Verify branch selection page
  131 |         await expect(page.locator('h1')).toContainText('Select Branch')
  132 | 
  133 |         // Select first branch
  134 |         await page.click('text=Main Clinic')
  135 |         await page.waitForURL('**/appointments/new/doctor**')
  136 | 
  137 |         // Verify doctor selection page
  138 |         await expect(page.locator('h1')).toContainText('Select Doctor')
  139 | 
  140 |         // Select first doctor
  141 |         await page.click('text=Dr. John Smith')
  142 |         await page.waitForURL('**/appointments/new/slot**')
  143 | 
  144 |         // Verify slot selection page
  145 |         await expect(page.locator('h1')).toContainText('Select Time Slot')
  146 | 
  147 |         // Select first available slot
  148 |         const availableSlots = page.locator('button:not([disabled])')
```