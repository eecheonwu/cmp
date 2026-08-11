import { test, expect } from '@playwright/test'
import {
    setupOfflineModeMocks,
    setLoggedInState,
} from './test-utils'

test.describe('Offline Mode - E2E', () => {
    test.beforeEach(async ({ page }) => {
        await setupOfflineModeMocks(page)
    })

    test('TC-OM-01: Dashboard loads with cached appointments online', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Navigate to appointments page while online
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Verify appointments are loaded from API
        await expect(page.locator('h1')).toContainText('My Appointments')
        await expect(page.locator('text=Appointment #appt').first()).toBeVisible()

        // Verify IndexedDB cache was populated
        const cachedCount = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const request = indexedDB.open('CMPDatabase')
                request.onsuccess = () => {
                    const db = request.result
                    const tx = db.transaction('appointments', 'readonly')
                    const store = tx.objectStore('appointments')
                    const count = store.count()
                    count.onsuccess = () => resolve(count.result)
                }
                request.onerror = () => resolve(0)
            })
        })
        expect(cachedCount).toBe(2)
    })

    test('TC-OM-02: Offline banner appears when network is disconnected', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Load the appointments page first while online
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Verify data is visible
        await expect(page.locator('h1')).toContainText('My Appointments')

        // Simulate going offline
        await page.context().setOffline(true)

        // Trigger the offline event
        await page.evaluate(() => window.dispatchEvent(new Event('offline')))

        // Verify offline banner is displayed
        await expect(page.locator('.offline-banner')).toBeVisible()
        await expect(page.locator('.offline-banner')).toContainText('Offline Mode — Read Only')

        // Restore online state
        await page.context().setOffline(false)
    })

    test('TC-OM-03: Cached appointments viewable in offline mode', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Load the page first while online to populate cache
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Force an error when API is called (simulate offline API failure)
        await page.route('**/api/v1/appointments', async (route) => {
            await route.abort('internetdisconnected')
        })

        // Now simulate going offline
        await page.context().setOffline(true)
        await page.evaluate(() => window.dispatchEvent(new Event('offline')))

        // Use reload instead of goto since browser is offline
        await page.reload()

        // Wait for the page to try to load and fall back to cache
        await page.waitForTimeout(2000)

        // Verify offline banner is shown
        await expect(page.locator('.offline-banner')).toBeVisible()

        // Verify cached appointment data is still displayed
        await expect(page.locator('text=Appointment #appt').first()).toBeVisible()

        // Restore online state
        await page.context().setOffline(false)
        await page.evaluate(() => window.dispatchEvent(new Event('online')))
    })

    test('TC-OM-04: Offline banner disappears when back online', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Load the appointments page
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Simulate going offline
        await page.context().setOffline(true)
        await page.evaluate(() => window.dispatchEvent(new Event('offline')))

        // Verify offline banner is displayed
        await expect(page.locator('.offline-banner')).toBeVisible()

        // Simulate coming back online
        await page.context().setOffline(false)
        await page.evaluate(() => window.dispatchEvent(new Event('online')))

        // Verify banner disappears
        await expect(page.locator('.offline-banner')).not.toBeVisible()
    })

    test('TC-OM-05: IndexedDB cache is cleared on logout', async ({ page }) => {
        // Navigate to a page on the app domain first, then set localStorage
        await page.goto('/login')
        await page.waitForLoadState('networkidle')
        await setLoggedInState(page)

        // Load the appointments page to populate cache
        await page.goto('/appointments')
        await page.waitForLoadState('networkidle')

        // Verify data is cached
        let cachedCount = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const request = indexedDB.open('CMPDatabase')
                request.onsuccess = () => {
                    const db = request.result
                    const tx = db.transaction('appointments', 'readonly')
                    const store = tx.objectStore('appointments')
                    const count = store.count()
                    count.onsuccess = () => resolve(count.result)
                }
                request.onerror = () => resolve(0)
            })
        })
        expect(cachedCount).toBe(2)

        // Click logout button
        await page.click('text=Logout')

        // Wait for redirect to login
        await page.waitForURL('**/login')

        // Verify IndexedDB was cleared
        cachedCount = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const request = indexedDB.open('CMPDatabase')
                request.onsuccess = () => {
                    const db = request.result
                    try {
                        const tx = db.transaction('appointments', 'readonly')
                        const store = tx.objectStore('appointments')
                        const count = store.count()
                        count.onsuccess = () => resolve(count.result)
                    } catch {
                        // Table no longer exists, meaning it was cleared
                        resolve(0)
                    }
                }
                request.onerror = () => resolve(0)
            })
        })
        expect(cachedCount).toBe(0)
    })

    test('TC-OM-06: Login page accessible when offline', async ({ page }) => {
        // Navigate to login page first while online
        await page.goto('/login')
        await page.waitForLoadState('networkidle')

        // Verify login page loaded
        await expect(page.locator('h1')).toContainText('Clinic Modernization Platform')

        // Now go offline
        await page.context().setOffline(true)
        await page.evaluate(() => window.dispatchEvent(new Event('offline')))

        // Verify offline banner is shown
        await expect(page.locator('.offline-banner')).toBeVisible()

        // Verify login page content is still visible
        await expect(page.locator('text=Staff Login')).toBeVisible()

        // Restore online state
        await page.context().setOffline(false)
        await page.evaluate(() => window.dispatchEvent(new Event('online')))
    })
})