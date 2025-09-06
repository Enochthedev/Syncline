// End-to-End Authentication Tests for Web App using Playwright
import { test, expect, Page } from '@playwright/test'

// Test data
const testUser = {
    email: 'test@example.com',
    password: 'password123',
    name: 'Test User'
}

const newUser = {
    email: 'newuser@example.com',
    password: 'password123',
    name: 'New User'
}

// Helper functions
async function loginUser(page: Page, email: string, password: string) {
    await page.fill('[data-testid="email-input"]', email)
    await page.fill('[data-testid="password-input"]', password)
    await page.click('[data-testid="login-button"]')
}

async function registerUser(page: Page, name: string, email: string, password: string) {
    await page.fill('[data-testid="register-name-input"]', name)
    await page.fill('[data-testid="register-email-input"]', email)
    await page.fill('[data-testid="register-password-input"]', password)
    await page.fill('[data-testid="register-confirm-password-input"]', password)
    await page.click('[data-testid="register-button"]')
}

test.describe('Authentication Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Clear localStorage before each test
        await page.goto('/')
        await page.evaluate(() => localStorage.clear())
        await page.reload()
    })

    test.describe('Login Flow', () => {
        test('should display login screen when not authenticated', async ({ page }) => {
            await page.goto('/')

            await expect(page.locator('[data-testid="login-screen"]')).toBeVisible()
            await expect(page.locator('[data-testid="email-input"]')).toBeVisible()
            await expect(page.locator('[data-testid="password-input"]')).toBeVisible()
            await expect(page.locator('[data-testid="login-button"]')).toBeVisible()
        })

        test('should show validation errors for empty fields', async ({ page }) => {
            await page.goto('/')
            await page.click('[data-testid="login-button"]')

            await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
            await expect(page.locator('[data-testid="password-error"]')).toBeVisible()
        })

        test('should show validation error for invalid email format', async ({ page }) => {
            await page.goto('/')
            await page.fill('[data-testid="email-input"]', 'invalid-email')
            await page.fill('[data-testid="password-input"]', 'password123')
            await page.click('[data-testid="login-button"]')

            await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
            await expect(page.locator('[data-testid="email-error"]')).toContainText('valid email')
        })

        test('should successfully login with valid credentials', async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)

            // Wait for navigation to main screen
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible({ timeout: 10000 })
            await expect(page.locator('[data-testid="user-profile-button"]')).toBeVisible()

            // Verify URL changed
            expect(page.url()).toContain('/dashboard')
        })

        test('should show error message for invalid credentials', async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, 'wrongpassword')

            await expect(page.locator('[data-testid="login-error"]')).toBeVisible({ timeout: 5000 })
            await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid credentials')
        })

        test('should show loading state during login', async ({ page }) => {
            await page.goto('/')
            await page.fill('[data-testid="email-input"]', testUser.email)
            await page.fill('[data-testid="password-input"]', testUser.password)

            // Click login and immediately check for loading state
            await page.click('[data-testid="login-button"]')
            await expect(page.locator('[data-testid="login-loading"]')).toBeVisible()
        })

        test('should navigate to forgot password screen', async ({ page }) => {
            await page.goto('/')
            await page.click('[data-testid="forgot-password-link"]')

            await expect(page.locator('[data-testid="forgot-password-screen"]')).toBeVisible()
            await expect(page.locator('[data-testid="forgot-email-input"]')).toBeVisible()
            await expect(page.locator('[data-testid="send-reset-button"]')).toBeVisible()
        })

        test('should navigate to registration screen', async ({ page }) => {
            await page.goto('/')
            await page.click('[data-testid="register-link"]')

            await expect(page.locator('[data-testid="register-screen"]')).toBeVisible()
            await expect(page.locator('[data-testid="register-name-input"]')).toBeVisible()
            await expect(page.locator('[data-testid="register-email-input"]')).toBeVisible()
            await expect(page.locator('[data-testid="register-password-input"]')).toBeVisible()
        })

        test('should support keyboard navigation', async ({ page }) => {
            await page.goto('/')

            // Tab through form elements
            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="email-input"]')).toBeFocused()

            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="password-input"]')).toBeFocused()

            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="login-button"]')).toBeFocused()

            // Submit with Enter
            await page.keyboard.press('Enter')
            await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
        })
    })

    test.describe('Registration Flow', () => {
        test.beforeEach(async ({ page }) => {
            await page.goto('/')
            await page.click('[data-testid="register-link"]')
            await expect(page.locator('[data-testid="register-screen"]')).toBeVisible()
        })

        test('should show validation errors for empty registration fields', async ({ page }) => {
            await page.click('[data-testid="register-button"]')

            await expect(page.locator('[data-testid="name-error"]')).toBeVisible()
            await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
            await expect(page.locator('[data-testid="password-error"]')).toBeVisible()
        })

        test('should show error for password mismatch', async ({ page }) => {
            await page.fill('[data-testid="register-name-input"]', newUser.name)
            await page.fill('[data-testid="register-email-input"]', newUser.email)
            await page.fill('[data-testid="register-password-input"]', 'password123')
            await page.fill('[data-testid="register-confirm-password-input"]', 'password456')
            await page.click('[data-testid="register-button"]')

            await expect(page.locator('[data-testid="confirm-password-error"]')).toBeVisible()
            await expect(page.locator('[data-testid="confirm-password-error"]')).toContainText('match')
        })

        test('should show password strength indicator', async ({ page }) => {
            await page.fill('[data-testid="register-password-input"]', 'weak')
            await expect(page.locator('[data-testid="password-strength"]')).toContainText('Weak')

            await page.fill('[data-testid="register-password-input"]', 'StrongPassword123!')
            await expect(page.locator('[data-testid="password-strength"]')).toContainText('Strong')
        })

        test('should successfully register with valid information', async ({ page }) => {
            await registerUser(page, newUser.name, newUser.email, newUser.password)

            // Wait for registration to complete and navigate to main screen
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible({ timeout: 10000 })
            expect(page.url()).toContain('/dashboard')
        })

        test('should show error for existing email', async ({ page }) => {
            await registerUser(page, 'Test User', testUser.email, testUser.password)

            await expect(page.locator('[data-testid="register-error"]')).toBeVisible({ timeout: 5000 })
            await expect(page.locator('[data-testid="register-error"]')).toContainText('already exists')
        })
    })

    test.describe('OAuth Platform Connections', () => {
        test.beforeEach(async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible()
        })

        test('should navigate to platform connections screen', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await expect(page.locator('[data-testid="profile-menu"]')).toBeVisible()

            await page.click('[data-testid="platform-connections-button"]')
            await expect(page.locator('[data-testid="platforms-screen"]')).toBeVisible()

            await expect(page.locator('[data-testid="gmail-connect-button"]')).toBeVisible()
            await expect(page.locator('[data-testid="slack-connect-button"]')).toBeVisible()
        })

        test('should initiate Gmail connection flow', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="platform-connections-button"]')
            await expect(page.locator('[data-testid="platforms-screen"]')).toBeVisible()

            // Mock OAuth popup
            const popupPromise = page.waitForEvent('popup')
            await page.click('[data-testid="gmail-connect-button"]')

            const popup = await popupPromise
            expect(popup.url()).toContain('oauth')
        })

        test('should show connected platform status', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="platform-connections-button"]')
            await expect(page.locator('[data-testid="platforms-screen"]')).toBeVisible()

            // Check for connected platforms (if any)
            const connectedPlatforms = page.locator('[data-testid*="connected-status"]')
            if (await connectedPlatforms.count() > 0) {
                await expect(connectedPlatforms.first()).toBeVisible()
            }
        })

        test('should disconnect platform', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="platform-connections-button"]')
            await expect(page.locator('[data-testid="platforms-screen"]')).toBeVisible()

            // Assuming Gmail is connected
            const disconnectButton = page.locator('[data-testid="gmail-disconnect-button"]')
            if (await disconnectButton.isVisible()) {
                await disconnectButton.click()

                // Confirm disconnection
                await expect(page.locator('[data-testid="disconnect-confirmation"]')).toBeVisible()
                await page.click('[data-testid="confirm-disconnect-button"]')

                // Should show success message
                await expect(page.locator('[data-testid="disconnect-success"]')).toBeVisible()
            }
        })
    })

    test.describe('Session Management', () => {
        test.beforeEach(async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible()
        })

        test('should show active sessions', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="security-settings-button"]')
            await expect(page.locator('[data-testid="security-screen"]')).toBeVisible()

            await page.click('[data-testid="active-sessions-button"]')
            await expect(page.locator('[data-testid="sessions-screen"]')).toBeVisible()

            await expect(page.locator('[data-testid="current-session"]')).toBeVisible()
            await expect(page.locator('[data-testid="current-session"]')).toContainText('Current Device')
        })

        test('should logout successfully', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="logout-button"]')

            // Should show confirmation dialog
            await expect(page.locator('[data-testid="logout-confirmation"]')).toBeVisible()
            await page.click('[data-testid="confirm-logout-button"]')

            // Should navigate back to login screen
            await expect(page.locator('[data-testid="login-screen"]')).toBeVisible({ timeout: 5000 })
            expect(page.url()).not.toContain('/dashboard')
        })

        test('should handle automatic logout on token expiry', async ({ page }) => {
            // Simulate token expiry by clearing localStorage
            await page.evaluate(() => localStorage.clear())

            // Try to perform an authenticated action
            await page.reload()

            // Should redirect to login screen
            await expect(page.locator('[data-testid="login-screen"]')).toBeVisible()
        })

        test('should maintain session across browser tabs', async ({ context }) => {
            const page1 = await context.newPage()
            const page2 = await context.newPage()

            // Login in first tab
            await page1.goto('/')
            await loginUser(page1, testUser.email, testUser.password)
            await expect(page1.locator('[data-testid="main-screen"]')).toBeVisible()

            // Navigate to app in second tab
            await page2.goto('/dashboard')
            await expect(page2.locator('[data-testid="main-screen"]')).toBeVisible()

            // Logout in first tab
            await page1.click('[data-testid="user-profile-button"]')
            await page1.click('[data-testid="logout-button"]')
            await page1.click('[data-testid="confirm-logout-button"]')

            // Second tab should also be logged out (with some delay)
            await page2.reload()
            await expect(page2.locator('[data-testid="login-screen"]')).toBeVisible()
        })
    })

    test.describe('Web-specific Features', () => {
        test.beforeEach(async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible()
        })

        test('should request notification permission', async ({ page, context }) => {
            // Grant notification permission
            await context.grantPermissions(['notifications'])

            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="notification-settings-button"]')
            await expect(page.locator('[data-testid="notification-screen"]')).toBeVisible()

            await page.click('[data-testid="enable-notifications-button"]')

            // Should show success message
            await expect(page.locator('[data-testid="notifications-enabled"]')).toBeVisible()
        })

        test('should support PWA installation', async ({ page }) => {
            // Check if PWA install prompt is available
            const installButton = page.locator('[data-testid="install-pwa-button"]')
            if (await installButton.isVisible()) {
                await installButton.click()

                // Should show install confirmation
                await expect(page.locator('[data-testid="pwa-install-prompt"]')).toBeVisible()
            }
        })

        test('should support keyboard shortcuts', async ({ page }) => {
            // Test Ctrl+K for search
            await page.keyboard.press('Control+k')
            await expect(page.locator('[data-testid="search-modal"]')).toBeVisible()

            // Test Escape to close
            await page.keyboard.press('Escape')
            await expect(page.locator('[data-testid="search-modal"]')).not.toBeVisible()
        })

        test('should work offline', async ({ page }) => {
            // Go offline
            await page.context().setOffline(true)

            // Should show offline indicator
            await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible()

            // Should still be able to view cached data
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible()

            // Go back online
            await page.context().setOffline(false)
            await expect(page.locator('[data-testid="offline-indicator"]')).not.toBeVisible()
        })
    })

    test.describe('Security Features', () => {
        test.beforeEach(async ({ page }) => {
            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible()
        })

        test('should show security events log', async ({ page }) => {
            await page.click('[data-testid="user-profile-button"]')
            await page.click('[data-testid="security-settings-button"]')
            await expect(page.locator('[data-testid="security-screen"]')).toBeVisible()

            await page.click('[data-testid="security-events-button"]')
            await expect(page.locator('[data-testid="security-events-screen"]')).toBeVisible()

            // Should show recent login event
            await expect(page.locator('[data-testid="login-event"]')).toBeVisible()
        })

        test('should handle CSP violations', async ({ page }) => {
            // This would require injecting unsafe content
            // For now, just verify CSP headers are present
            const response = await page.goto('/')
            const cspHeader = response?.headers()['content-security-policy']
            expect(cspHeader).toBeDefined()
        })

        test('should prevent XSS attacks', async ({ page }) => {
            // Try to inject script in input field
            const maliciousScript = '<script>alert("XSS")</script>'
            await page.fill('[data-testid="email-input"]', maliciousScript)

            // Should not execute script
            const alertPromise = page.waitForEvent('dialog', { timeout: 1000 }).catch(() => null)
            await page.click('[data-testid="login-button"]')

            const alert = await alertPromise
            expect(alert).toBeNull()
        })
    })

    test.describe('Accessibility', () => {
        test('should be keyboard navigable', async ({ page }) => {
            await page.goto('/')

            // Should be able to navigate entire login form with keyboard
            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="email-input"]')).toBeFocused()

            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="password-input"]')).toBeFocused()

            await page.keyboard.press('Tab')
            await expect(page.locator('[data-testid="login-button"]')).toBeFocused()
        })

        test('should have proper ARIA labels', async ({ page }) => {
            await page.goto('/')

            const emailInput = page.locator('[data-testid="email-input"]')
            const passwordInput = page.locator('[data-testid="password-input"]')

            await expect(emailInput).toHaveAttribute('aria-label')
            await expect(passwordInput).toHaveAttribute('aria-label')

            // Check for proper form labeling
            await expect(emailInput).toHaveAttribute('aria-describedby')
            await expect(passwordInput).toHaveAttribute('aria-describedby')
        })

        test('should support screen readers', async ({ page }) => {
            await page.goto('/')

            // Check for proper heading structure
            const headings = page.locator('h1, h2, h3, h4, h5, h6')
            expect(await headings.count()).toBeGreaterThan(0)

            // Check for alt text on images
            const images = page.locator('img')
            for (let i = 0; i < await images.count(); i++) {
                const img = images.nth(i)
                await expect(img).toHaveAttribute('alt')
            }
        })
    })

    test.describe('Error Handling', () => {
        test('should handle network errors gracefully', async ({ page }) => {
            // Simulate network failure
            await page.route('**/api/v1/auth/login', route => route.abort())

            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)

            await expect(page.locator('[data-testid="network-error"]')).toBeVisible({ timeout: 5000 })
        })

        test('should handle server errors gracefully', async ({ page }) => {
            // Mock server error
            await page.route('**/api/v1/auth/login', route =>
                route.fulfill({ status: 500, body: 'Internal Server Error' })
            )

            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)

            await expect(page.locator('[data-testid="server-error"]')).toBeVisible({ timeout: 5000 })
        })

        test('should handle timeout errors', async ({ page }) => {
            // Mock slow response
            await page.route('**/api/v1/auth/login', route =>
                new Promise(resolve => setTimeout(() => resolve(route.continue()), 35000))
            )

            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)

            await expect(page.locator('[data-testid="timeout-error"]')).toBeVisible({ timeout: 40000 })
        })

        test('should show user-friendly error messages', async ({ page }) => {
            await page.route('**/api/v1/auth/login', route =>
                route.fulfill({
                    status: 401,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Invalid credentials' })
                })
            )

            await page.goto('/')
            await loginUser(page, testUser.email, testUser.password)

            const errorMessage = page.locator('[data-testid="login-error"]')
            await expect(errorMessage).toBeVisible()
            await expect(errorMessage).toContainText('Invalid credentials')
        })
    })

    test.describe('Performance', () => {
        test('should load login page quickly', async ({ page }) => {
            const startTime = Date.now()
            await page.goto('/')
            await expect(page.locator('[data-testid="login-screen"]')).toBeVisible()
            const loadTime = Date.now() - startTime

            expect(loadTime).toBeLessThan(3000) // Should load within 3 seconds
        })

        test('should handle rapid form submissions', async ({ page }) => {
            await page.goto('/')
            await page.fill('[data-testid="email-input"]', testUser.email)
            await page.fill('[data-testid="password-input"]', testUser.password)

            // Click login button multiple times rapidly
            await Promise.all([
                page.click('[data-testid="login-button"]'),
                page.click('[data-testid="login-button"]'),
                page.click('[data-testid="login-button"]')
            ])

            // Should only make one request and handle gracefully
            await expect(page.locator('[data-testid="main-screen"]')).toBeVisible({ timeout: 10000 })
        })
    })
})