# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: offline-mode.spec.ts >> Offline Mode - E2E >> TC-OM-03: Cached appointments viewable in offline mode
- Location: src\frontend\tests\e2e\offline-mode.spec.ts:70:5

# Error details

```
Error: page.reload: net::ERR_INTERNET_DISCONNECTED
Call log:
  - waiting for navigation until "load"

```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | import {
  3   |     setupOfflineModeMocks,
  4   |     setLoggedInState,
  5   | } from './test-utils'
  6   | 
  7   | test.describe('Offline Mode - E2E', () => {
  8   |     test.beforeEach(async ({ page }) => {
  9   |         await setupOfflineModeMocks(page)
  10  |     })
  11  | 
  12  |     test('TC-OM-01: Dashboard loads with cached appointments online', async ({ page }) => {
  13  |         // Navigate to a page on the app domain first, then set localStorage
  14  |         await page.goto('/login')
  15  |         await page.waitForLoadState('networkidle')
  16  |         await setLoggedInState(page)
  17  | 
  18  |         // Navigate to appointments page while online
  19  |         await page.goto('/appointments')
  20  |         await page.waitForLoadState('networkidle')
  21  | 
  22  |         // Verify appointments are loaded from API
  23  |         await expect(page.locator('h1')).toContainText('My Appointments')
  24  |         await expect(page.locator('text=Appointment #appt').first()).toBeVisible()
  25  | 
  26  |         // Verify IndexedDB cache was populated
  27  |         const cachedCount = await page.evaluate(async () => {
  28  |             return new Promise((resolve) => {
  29  |                 const request = indexedDB.open('CMPDatabase')
  30  |                 request.onsuccess = () => {
  31  |                     const db = request.result
  32  |                     const tx = db.transaction('appointments', 'readonly')
  33  |                     const store = tx.objectStore('appointments')
  34  |                     const count = store.count()
  35  |                     count.onsuccess = () => resolve(count.result)
  36  |                 }
  37  |                 request.onerror = () => resolve(0)
  38  |             })
  39  |         })
  40  |         expect(cachedCount).toBe(2)
  41  |     })
  42  | 
  43  |     test('TC-OM-02: Offline banner appears when network is disconnected', async ({ page }) => {
  44  |         // Navigate to a page on the app domain first, then set localStorage
  45  |         await page.goto('/login')
  46  |         await page.waitForLoadState('networkidle')
  47  |         await setLoggedInState(page)
  48  | 
  49  |         // Load the appointments page first while online
  50  |         await page.goto('/appointments')
  51  |         await page.waitForLoadState('networkidle')
  52  | 
  53  |         // Verify data is visible
  54  |         await expect(page.locator('h1')).toContainText('My Appointments')
  55  | 
  56  |         // Simulate going offline
  57  |         await page.context().setOffline(true)
  58  | 
  59  |         // Trigger the offline event
  60  |         await page.evaluate(() => window.dispatchEvent(new Event('offline')))
  61  | 
  62  |         // Verify offline banner is displayed
  63  |         await expect(page.locator('.offline-banner')).toBeVisible()
  64  |         await expect(page.locator('.offline-banner')).toContainText('Offline Mode — Read Only')
  65  | 
  66  |         // Restore online state
  67  |         await page.context().setOffline(false)
  68  |     })
  69  | 
  70  |     test('TC-OM-03: Cached appointments viewable in offline mode', async ({ page }) => {
  71  |         // Navigate to a page on the app domain first, then set localStorage
  72  |         await page.goto('/login')
  73  |         await page.waitForLoadState('networkidle')
  74  |         await setLoggedInState(page)
  75  | 
  76  |         // Load the page first while online to populate cache
  77  |         await page.goto('/appointments')
  78  |         await page.waitForLoadState('networkidle')
  79  | 
  80  |         // Force an error when API is called (simulate offline API failure)
  81  |         await page.route('**/api/v1/appointments', async (route) => {
  82  |             await route.abort('internetdisconnected')
  83  |         })
  84  | 
  85  |         // Now simulate going offline
  86  |         await page.context().setOffline(true)
  87  |         await page.evaluate(() => window.dispatchEvent(new Event('offline')))
  88  | 
  89  |         // Use reload instead of goto since browser is offline
> 90  |         await page.reload()
      |                    ^ Error: page.reload: net::ERR_INTERNET_DISCONNECTED
  91  | 
  92  |         // Wait for the page to try to load and fall back to cache
  93  |         await page.waitForTimeout(2000)
  94  | 
  95  |         // Verify offline banner is shown
  96  |         await expect(page.locator('.offline-banner')).toBeVisible()
  97  | 
  98  |         // Verify cached appointment data is still displayed
  99  |         await expect(page.locator('text=Appointment #appt').first()).toBeVisible()
  100 | 
  101 |         // Restore online state
  102 |         await page.context().setOffline(false)
  103 |         await page.evaluate(() => window.dispatchEvent(new Event('online')))
  104 |     })
  105 | 
  106 |     test('TC-OM-04: Offline banner disappears when back online', async ({ page }) => {
  107 |         // Navigate to a page on the app domain first, then set localStorage
  108 |         await page.goto('/login')
  109 |         await page.waitForLoadState('networkidle')
  110 |         await setLoggedInState(page)
  111 | 
  112 |         // Load the appointments page
  113 |         await page.goto('/appointments')
  114 |         await page.waitForLoadState('networkidle')
  115 | 
  116 |         // Simulate going offline
  117 |         await page.context().setOffline(true)
  118 |         await page.evaluate(() => window.dispatchEvent(new Event('offline')))
  119 | 
  120 |         // Verify offline banner is displayed
  121 |         await expect(page.locator('.offline-banner')).toBeVisible()
  122 | 
  123 |         // Simulate coming back online
  124 |         await page.context().setOffline(false)
  125 |         await page.evaluate(() => window.dispatchEvent(new Event('online')))
  126 | 
  127 |         // Verify banner disappears
  128 |         await expect(page.locator('.offline-banner')).not.toBeVisible()
  129 |     })
  130 | 
  131 |     test('TC-OM-05: IndexedDB cache is cleared on logout', async ({ page }) => {
  132 |         // Navigate to a page on the app domain first, then set localStorage
  133 |         await page.goto('/login')
  134 |         await page.waitForLoadState('networkidle')
  135 |         await setLoggedInState(page)
  136 | 
  137 |         // Load the appointments page to populate cache
  138 |         await page.goto('/appointments')
  139 |         await page.waitForLoadState('networkidle')
  140 | 
  141 |         // Verify data is cached
  142 |         let cachedCount = await page.evaluate(async () => {
  143 |             return new Promise((resolve) => {
  144 |                 const request = indexedDB.open('CMPDatabase')
  145 |                 request.onsuccess = () => {
  146 |                     const db = request.result
  147 |                     const tx = db.transaction('appointments', 'readonly')
  148 |                     const store = tx.objectStore('appointments')
  149 |                     const count = store.count()
  150 |                     count.onsuccess = () => resolve(count.result)
  151 |                 }
  152 |                 request.onerror = () => resolve(0)
  153 |             })
  154 |         })
  155 |         expect(cachedCount).toBe(2)
  156 | 
  157 |         // Click logout button
  158 |         await page.click('text=Logout')
  159 | 
  160 |         // Wait for redirect to login
  161 |         await page.waitForURL('**/login')
  162 | 
  163 |         // Verify IndexedDB was cleared
  164 |         cachedCount = await page.evaluate(async () => {
  165 |             return new Promise((resolve) => {
  166 |                 const request = indexedDB.open('CMPDatabase')
  167 |                 request.onsuccess = () => {
  168 |                     const db = request.result
  169 |                     try {
  170 |                         const tx = db.transaction('appointments', 'readonly')
  171 |                         const store = tx.objectStore('appointments')
  172 |                         const count = store.count()
  173 |                         count.onsuccess = () => resolve(count.result)
  174 |                     } catch {
  175 |                         // Table no longer exists, meaning it was cleared
  176 |                         resolve(0)
  177 |                     }
  178 |                 }
  179 |                 request.onerror = () => resolve(0)
  180 |             })
  181 |         })
  182 |         expect(cachedCount).toBe(0)
  183 |     })
  184 | 
  185 |     test('TC-OM-06: Login page accessible when offline', async ({ page }) => {
  186 |         // Navigate to login page first while online
  187 |         await page.goto('/login')
  188 |         await page.waitForLoadState('networkidle')
  189 | 
  190 |         // Verify login page loaded
```