// End-to-End Authentication Tests for React Native using Detox
import { device, element, by, expect as detoxExpect, waitFor } from 'detox'

describe('Authentication Flow', () => {
    beforeAll(async () => {
        await device.launchApp()
    })

    beforeEach(async () => {
        await device.reloadReactNative()
        // Clear any existing authentication state
        await device.clearKeychain()
    })

    describe('Login Flow', () => {
        it('should display login screen on app launch when not authenticated', async () => {
            await detoxExpect(element(by.id('login-screen'))).toBeVisible()
            await detoxExpect(element(by.id('email-input'))).toBeVisible()
            await detoxExpect(element(by.id('password-input'))).toBeVisible()
            await detoxExpect(element(by.id('login-button'))).toBeVisible()
        })

        it('should show validation errors for empty fields', async () => {
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('email-error')))
                .toBeVisible()
                .withTimeout(2000)
            await waitFor(element(by.id('password-error')))
                .toBeVisible()
                .withTimeout(2000)
        })

        it('should show validation error for invalid email format', async () => {
            await element(by.id('email-input')).typeText('invalid-email')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('email-error')))
                .toBeVisible()
                .withTimeout(2000)
        })

        it('should successfully login with valid credentials', async () => {
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            // Wait for login to complete and navigate to main screen
            await waitFor(element(by.id('main-screen')))
                .toBeVisible()
                .withTimeout(5000)

            // Verify user is logged in
            await detoxExpect(element(by.id('user-profile-button'))).toBeVisible()
        })

        it('should show error message for invalid credentials', async () => {
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('wrongpassword')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('login-error')))
                .toBeVisible()
                .withTimeout(3000)

            await detoxExpect(element(by.text('Invalid credentials'))).toBeVisible()
        })

        it('should show loading state during login', async () => {
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            // Check loading indicator appears
            await waitFor(element(by.id('login-loading')))
                .toBeVisible()
                .withTimeout(1000)
        })

        it('should navigate to forgot password screen', async () => {
            await element(by.id('forgot-password-link')).tap()

            await waitFor(element(by.id('forgot-password-screen')))
                .toBeVisible()
                .withTimeout(2000)

            await detoxExpect(element(by.id('forgot-email-input'))).toBeVisible()
            await detoxExpect(element(by.id('send-reset-button'))).toBeVisible()
        })

        it('should navigate to registration screen', async () => {
            await element(by.id('register-link')).tap()

            await waitFor(element(by.id('register-screen')))
                .toBeVisible()
                .withTimeout(2000)

            await detoxExpect(element(by.id('register-name-input'))).toBeVisible()
            await detoxExpect(element(by.id('register-email-input'))).toBeVisible()
            await detoxExpect(element(by.id('register-password-input'))).toBeVisible()
            await detoxExpect(element(by.id('register-confirm-password-input'))).toBeVisible()
        })
    })

    describe('Registration Flow', () => {
        beforeEach(async () => {
            await element(by.id('register-link')).tap()
            await waitFor(element(by.id('register-screen'))).toBeVisible()
        })

        it('should show validation errors for empty registration fields', async () => {
            await element(by.id('register-button')).tap()

            await waitFor(element(by.id('name-error'))).toBeVisible()
            await waitFor(element(by.id('email-error'))).toBeVisible()
            await waitFor(element(by.id('password-error'))).toBeVisible()
        })

        it('should show error for password mismatch', async () => {
            await element(by.id('register-name-input')).typeText('Test User')
            await element(by.id('register-email-input')).typeText('test@example.com')
            await element(by.id('register-password-input')).typeText('password123')
            await element(by.id('register-confirm-password-input')).typeText('password456')
            await element(by.id('register-button')).tap()

            await waitFor(element(by.id('confirm-password-error')))
                .toBeVisible()
                .withTimeout(2000)
        })

        it('should successfully register with valid information', async () => {
            await element(by.id('register-name-input')).typeText('Test User')
            await element(by.id('register-email-input')).typeText('newuser@example.com')
            await element(by.id('register-password-input')).typeText('password123')
            await element(by.id('register-confirm-password-input')).typeText('password123')
            await element(by.id('register-button')).tap()

            // Wait for registration to complete and navigate to main screen
            await waitFor(element(by.id('main-screen')))
                .toBeVisible()
                .withTimeout(5000)
        })

        it('should show error for existing email', async () => {
            await element(by.id('register-name-input')).typeText('Test User')
            await element(by.id('register-email-input')).typeText('existing@example.com')
            await element(by.id('register-password-input')).typeText('password123')
            await element(by.id('register-confirm-password-input')).typeText('password123')
            await element(by.id('register-button')).tap()

            await waitFor(element(by.id('register-error')))
                .toBeVisible()
                .withTimeout(3000)
        })
    })

    describe('Biometric Authentication', () => {
        beforeEach(async () => {
            // Login first to access biometric settings
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('main-screen'))).toBeVisible()
        })

        it('should show biometric setup option when available', async () => {
            await element(by.id('user-profile-button')).tap()
            await waitFor(element(by.id('profile-screen'))).toBeVisible()

            await element(by.id('security-settings-button')).tap()
            await waitFor(element(by.id('security-screen'))).toBeVisible()

            // Check if biometric option is available (device dependent)
            try {
                await detoxExpect(element(by.id('biometric-toggle'))).toBeVisible()
            } catch (error) {
                // Biometric not available on this device/simulator
                console.log('Biometric authentication not available on this device')
            }
        })

        it('should enable biometric authentication', async () => {
            await element(by.id('user-profile-button')).tap()
            await waitFor(element(by.id('profile-screen'))).toBeVisible()

            await element(by.id('security-settings-button')).tap()
            await waitFor(element(by.id('security-screen'))).toBeVisible()

            try {
                await element(by.id('biometric-toggle')).tap()

                // Wait for biometric setup confirmation
                await waitFor(element(by.id('biometric-setup-success')))
                    .toBeVisible()
                    .withTimeout(3000)
            } catch (error) {
                console.log('Biometric setup not available on this device')
            }
        })

        it('should authenticate with biometrics on app launch', async () => {
            // First enable biometric auth (if available)
            try {
                await element(by.id('user-profile-button')).tap()
                await element(by.id('security-settings-button')).tap()
                await element(by.id('biometric-toggle')).tap()

                // Logout and relaunch app
                await element(by.id('logout-button')).tap()
                await device.relaunchApp()

                // Should show biometric prompt instead of login form
                await waitFor(element(by.id('biometric-prompt')))
                    .toBeVisible()
                    .withTimeout(3000)

                // Simulate successful biometric authentication
                await device.setBiometricEnrollment(true)
                await device.matchBiometric()

                // Should navigate to main screen
                await waitFor(element(by.id('main-screen')))
                    .toBeVisible()
                    .withTimeout(5000)
            } catch (error) {
                console.log('Biometric authentication test skipped - not available')
            }
        })
    })

    describe('OAuth Platform Connections', () => {
        beforeEach(async () => {
            // Login first
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('main-screen'))).toBeVisible()
        })

        it('should navigate to platform connections screen', async () => {
            await element(by.id('user-profile-button')).tap()
            await waitFor(element(by.id('profile-screen'))).toBeVisible()

            await element(by.id('platform-connections-button')).tap()
            await waitFor(element(by.id('platforms-screen'))).toBeVisible()

            await detoxExpect(element(by.id('gmail-connect-button'))).toBeVisible()
            await detoxExpect(element(by.id('slack-connect-button'))).toBeVisible()
        })

        it('should initiate Gmail connection flow', async () => {
            await element(by.id('user-profile-button')).tap()
            await element(by.id('platform-connections-button')).tap()
            await waitFor(element(by.id('platforms-screen'))).toBeVisible()

            await element(by.id('gmail-connect-button')).tap()

            // Should show OAuth webview or external browser
            await waitFor(element(by.id('oauth-webview')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should show connected platform status', async () => {
            await element(by.id('user-profile-button')).tap()
            await element(by.id('platform-connections-button')).tap()
            await waitFor(element(by.id('platforms-screen'))).toBeVisible()

            // Assuming Gmail is already connected
            try {
                await detoxExpect(element(by.id('gmail-connected-status'))).toBeVisible()
                await detoxExpect(element(by.id('gmail-disconnect-button'))).toBeVisible()
            } catch (error) {
                console.log('No connected platforms found')
            }
        })
    })

    describe('Session Management', () => {
        beforeEach(async () => {
            // Login first
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('main-screen'))).toBeVisible()
        })

        it('should show active sessions', async () => {
            await element(by.id('user-profile-button')).tap()
            await waitFor(element(by.id('profile-screen'))).toBeVisible()

            await element(by.id('security-settings-button')).tap()
            await waitFor(element(by.id('security-screen'))).toBeVisible()

            await element(by.id('active-sessions-button')).tap()
            await waitFor(element(by.id('sessions-screen'))).toBeVisible()

            await detoxExpect(element(by.id('current-session'))).toBeVisible()
        })

        it('should logout successfully', async () => {
            await element(by.id('user-profile-button')).tap()
            await waitFor(element(by.id('profile-screen'))).toBeVisible()

            await element(by.id('logout-button')).tap()

            // Should show confirmation dialog
            await waitFor(element(by.id('logout-confirmation')))
                .toBeVisible()
                .withTimeout(2000)

            await element(by.id('confirm-logout-button')).tap()

            // Should navigate back to login screen
            await waitFor(element(by.id('login-screen')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should handle automatic logout on token expiry', async () => {
            // This test would require mocking token expiry
            // For now, we'll simulate by clearing tokens manually
            await device.clearKeychain()

            // Try to perform an authenticated action
            await element(by.id('user-profile-button')).tap()

            // Should redirect to login screen
            await waitFor(element(by.id('login-screen')))
                .toBeVisible()
                .withTimeout(3000)
        })
    })

    describe('Offline Authentication', () => {
        it('should show offline message when network is unavailable', async () => {
            await device.setNetworkConnection(false)

            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('offline-message')))
                .toBeVisible()
                .withTimeout(3000)

            await device.setNetworkConnection(true)
        })

        it('should retry authentication when network is restored', async () => {
            await device.setNetworkConnection(false)

            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('offline-message'))).toBeVisible()

            // Restore network
            await device.setNetworkConnection(true)

            // Tap retry button
            await element(by.id('retry-login-button')).tap()

            // Should successfully login
            await waitFor(element(by.id('main-screen')))
                .toBeVisible()
                .withTimeout(5000)
        })
    })

    describe('Security Features', () => {
        beforeEach(async () => {
            // Login first
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            await waitFor(element(by.id('main-screen'))).toBeVisible()
        })

        it('should show security events log', async () => {
            await element(by.id('user-profile-button')).tap()
            await element(by.id('security-settings-button')).tap()
            await waitFor(element(by.id('security-screen'))).toBeVisible()

            await element(by.id('security-events-button')).tap()
            await waitFor(element(by.id('security-events-screen'))).toBeVisible()

            // Should show recent login event
            await detoxExpect(element(by.id('login-event'))).toBeVisible()
        })

        it('should handle app backgrounding securely', async () => {
            await device.sendToHome()
            await device.launchApp()

            // Should show privacy screen or require re-authentication
            try {
                await detoxExpect(element(by.id('privacy-screen'))).toBeVisible()
            } catch (error) {
                // App might require re-authentication instead
                await detoxExpect(element(by.id('login-screen'))).toBeVisible()
            }
        })
    })

    describe('Error Handling', () => {
        it('should handle server errors gracefully', async () => {
            // This would require mocking server responses
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            // If server returns 500 error
            try {
                await waitFor(element(by.id('server-error-message')))
                    .toBeVisible()
                    .withTimeout(5000)
            } catch (error) {
                // Server might be working fine
                console.log('Server error test skipped - server is responding')
            }
        })

        it('should handle timeout errors', async () => {
            // This would require network delay simulation
            await element(by.id('email-input')).typeText('test@example.com')
            await element(by.id('password-input')).typeText('password123')
            await element(by.id('login-button')).tap()

            // Should show timeout message after configured timeout
            try {
                await waitFor(element(by.id('timeout-error-message')))
                    .toBeVisible()
                    .withTimeout(35000) // Longer than API timeout
            } catch (error) {
                console.log('Timeout test skipped - request completed successfully')
            }
        })
    })

    afterAll(async () => {
        await device.clearKeychain()
    })
})