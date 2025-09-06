// Authentication Service Tests for Web App
import { webAuthService } from '@/services/authService'
import axios from 'axios'

// Mock dependencies
jest.mock('axios')

const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock localStorage
const localStorageMock = (() => {
    let store: Record<string, string> = {}
    return {
        getItem: jest.fn((key: string) => store[key] || null),
        setItem: jest.fn((key: string, value: string) => {
            store[key] = value
        }),
        removeItem: jest.fn((key: string) => {
            delete store[key]
        }),
        clear: jest.fn(() => {
            store = {}
        })
    }
})()

Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
})

// Mock Web Crypto API
const mockCrypto = {
    subtle: {
        generateKey: jest.fn(),
        encrypt: jest.fn(),
        decrypt: jest.fn(),
        exportKey: jest.fn(),
        importKey: jest.fn(),
    },
    getRandomValues: jest.fn((arr: Uint8Array) => {
        for (let i = 0; i < arr.length; i++) {
            arr[i] = Math.floor(Math.random() * 256)
        }
        return arr
    })
}

Object.defineProperty(window, 'crypto', {
    value: mockCrypto
})

// Mock navigator
Object.defineProperty(window, 'navigator', {
    value: {
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        platform: 'MacIntel'
    }
})

// Mock data
const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    isVerified: true,
    preferences: {
        notificationsEnabled: true,
        theme: 'light' as const,
        language: 'en'
    }
}

const mockTokens = {
    accessToken: 'access-token-123',
    refreshToken: 'refresh-token-123',
    expiresIn: Date.now() + 3600000, // 1 hour from now
    tokenType: 'Bearer' as const
}

const mockLoginResponse = {
    user: mockUser,
    ...mockTokens
}

describe('WebAuthService', () => {
    beforeEach(() => {
        jest.clearAllMocks()
        localStorageMock.clear()

        // Setup axios mock
        mockedAxios.create.mockReturnValue(mockedAxios)
        mockedAxios.interceptors = {
            request: { use: jest.fn() },
            response: { use: jest.fn() }
        } as any
    })

    describe('Device Management', () => {
        it('should generate and store device ID', async () => {
            // Create new service instance to trigger device ID generation
            const service = new (webAuthService.constructor as any)()

            expect(localStorageMock.setItem).toHaveBeenCalledWith(
                'remi_device_id',
                expect.stringMatching(/^web-/)
            )
        })

        it('should reuse existing device ID', async () => {
            localStorageMock.getItem.mockReturnValue('existing-device-id')

            const service = new (webAuthService.constructor as any)()

            expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
                'remi_device_id',
                expect.any(String)
            )
        })
    })

    describe('Token Management', () => {
        it('should store tokens in localStorage', async () => {
            await webAuthService.storeTokens(mockTokens)

            expect(localStorageMock.setItem).toHaveBeenCalledWith(
                'remi_auth_tokens',
                expect.stringContaining('accessToken')
            )
        })

        it('should retrieve tokens from localStorage', async () => {
            localStorageMock.getItem.mockReturnValue(JSON.stringify(mockTokens))

            const tokens = await webAuthService.getStoredTokens()

            expect(tokens).toEqual(expect.objectContaining({
                accessToken: mockTokens.accessToken,
                refreshToken: mockTokens.refreshToken,
                tokenType: mockTokens.tokenType
            }))
        })

        it('should return null when no tokens stored', async () => {
            localStorageMock.getItem.mockReturnValue(null)

            const tokens = await webAuthService.getStoredTokens()

            expect(tokens).toBeNull()
        })

        it('should clear all tokens and user data', async () => {
            await webAuthService.clearTokens()

            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_auth_tokens')
            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_user_data')
        })
    })

    describe('Authentication', () => {
        it('should login successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })

            const result = await webAuthService.login({
                email: 'test@example.com',
                password: 'password123'
            })

            expect(result).toEqual(mockLoginResponse)
            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/login',
                expect.objectContaining({
                    email: 'test@example.com',
                    password: 'password123',
                    deviceInfo: expect.objectContaining({
                        platform: 'web'
                    })
                })
            )
        })

        it('should handle login failure', async () => {
            const loginError = new Error('Invalid credentials')
            mockedAxios.post.mockRejectedValue(loginError)

            await expect(webAuthService.login({
                email: 'test@example.com',
                password: 'wrongpassword'
            })).rejects.toThrow('Invalid credentials')
        })

        it('should register successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })

            const result = await webAuthService.register({
                email: 'test@example.com',
                password: 'password123',
                name: 'Test User',
                confirmPassword: 'password123'
            })

            expect(result).toEqual(mockLoginResponse)
            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/register',
                expect.objectContaining({
                    email: 'test@example.com',
                    name: 'Test User'
                })
            )
        })

        it('should logout successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await webAuthService.logout()

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/logout',
                expect.objectContaining({
                    deviceInfo: expect.objectContaining({
                        platform: 'web'
                    })
                })
            )
            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_auth_tokens')
            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_user_data')
        })

        it('should continue logout even if server call fails', async () => {
            mockedAxios.post.mockRejectedValue(new Error('Network error'))

            await expect(webAuthService.logout()).resolves.not.toThrow()

            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_auth_tokens')
            expect(localStorageMock.removeItem).toHaveBeenCalledWith('remi_user_data')
        })
    })

    describe('Token Refresh', () => {
        it('should refresh tokens successfully', async () => {
            const currentTokens = { ...mockTokens, expiresIn: Date.now() - 1000 } // Expired
            localStorageMock.getItem.mockReturnValue(JSON.stringify(currentTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            const result = await webAuthService.refreshTokens()

            expect(result).toEqual(mockTokens)
            expect(mockedAxios.post).toHaveBeenCalledWith(
                'http://localhost:8000/api/v1/auth/refresh',
                expect.objectContaining({
                    refreshToken: currentTokens.refreshToken
                })
            )
        })

        it('should handle refresh token failure', async () => {
            localStorageMock.getItem.mockReturnValue(JSON.stringify(mockTokens))
            mockedAxios.post.mockRejectedValue(new Error('Invalid refresh token'))

            const result = await webAuthService.refreshTokens()

            expect(result).toBeNull()
        })

        it('should deduplicate concurrent refresh requests', async () => {
            localStorageMock.getItem.mockReturnValue(JSON.stringify(mockTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            // Make multiple concurrent refresh requests
            const promises = [
                webAuthService.refreshTokens(),
                webAuthService.refreshTokens(),
                webAuthService.refreshTokens()
            ]

            const results = await Promise.all(promises)

            // Should only make one API call
            expect(mockedAxios.post).toHaveBeenCalledTimes(1)
            // All promises should resolve to the same result
            results.forEach(result => {
                expect(result).toEqual(mockTokens)
            })
        })
    })

    describe('Authentication State', () => {
        it('should return true for valid tokens', async () => {
            const validTokens = { ...mockTokens, expiresIn: Date.now() + 3600000 }
            localStorageMock.getItem.mockReturnValue(JSON.stringify(validTokens))

            const isAuthenticated = await webAuthService.isAuthenticated()

            expect(isAuthenticated).toBe(true)
        })

        it('should attempt refresh for expired tokens', async () => {
            const expiredTokens = { ...mockTokens, expiresIn: Date.now() - 1000 }
            localStorageMock.getItem.mockReturnValue(JSON.stringify(expiredTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            const isAuthenticated = await webAuthService.isAuthenticated()

            expect(isAuthenticated).toBe(true)
            expect(mockedAxios.post).toHaveBeenCalledWith(
                'http://localhost:8000/api/v1/auth/refresh',
                expect.any(Object)
            )
        })

        it('should return false for no tokens', async () => {
            localStorageMock.getItem.mockReturnValue(null)

            const isAuthenticated = await webAuthService.isAuthenticated()

            expect(isAuthenticated).toBe(false)
        })
    })

    describe('User Data Management', () => {
        it('should store user data', async () => {
            await webAuthService.storeUser(mockUser)

            expect(localStorageMock.setItem).toHaveBeenCalledWith(
                'remi_user_data',
                JSON.stringify(mockUser)
            )
        })

        it('should retrieve user data', async () => {
            localStorageMock.getItem.mockReturnValue(JSON.stringify(mockUser))

            const user = await webAuthService.getStoredUser()

            expect(user).toEqual(mockUser)
        })

        it('should return null when no user data', async () => {
            localStorageMock.getItem.mockReturnValue(null)

            const user = await webAuthService.getStoredUser()

            expect(user).toBeNull()
        })
    })

    describe('Platform Connections', () => {
        it('should connect platform successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await webAuthService.connectPlatform('gmail', 'auth-code-123')

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/platforms/gmail/connect',
                expect.objectContaining({
                    authCode: 'auth-code-123',
                    deviceInfo: expect.objectContaining({
                        platform: 'web'
                    })
                })
            )
        })

        it('should disconnect platform successfully', async () => {
            mockedAxios.delete.mockResolvedValue({ data: {} })

            await webAuthService.disconnectPlatform('gmail')

            expect(mockedAxios.delete).toHaveBeenCalledWith('/api/v1/platforms/gmail')
        })

        it('should get platform status', async () => {
            const mockStatus = { connected: true, lastSync: new Date().toISOString() }
            mockedAxios.get.mockResolvedValue({ data: mockStatus })

            const status = await webAuthService.getPlatformStatus('gmail')

            expect(status).toEqual(mockStatus)
            expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/platforms/gmail/status')
        })
    })

    describe('Session Management', () => {
        it('should get active sessions', async () => {
            const mockSessions = [
                {
                    deviceId: 'device-1',
                    deviceName: 'Chrome Browser',
                    platform: 'web',
                    lastActivity: new Date().toISOString(),
                    isCurrentDevice: true
                }
            ]
            mockedAxios.get.mockResolvedValue({ data: mockSessions })

            const sessions = await webAuthService.getActiveSessions()

            expect(sessions).toEqual(mockSessions)
            expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/auth/sessions')
        })

        it('should revoke session', async () => {
            mockedAxios.delete.mockResolvedValue({ data: {} })

            await webAuthService.revokeSession('session-123')

            expect(mockedAxios.delete).toHaveBeenCalledWith('/api/v1/auth/sessions/session-123')
        })
    })

    describe('Security Events', () => {
        it('should log and retrieve security events', async () => {
            // Trigger a login to generate a security event
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })
            await webAuthService.login({ email: 'test@example.com', password: 'password123' })

            const events = await webAuthService.getSecurityEvents()

            expect(events).toHaveLength(1)
            expect(events[0]).toEqual(expect.objectContaining({
                type: 'login',
                success: true,
                details: expect.objectContaining({
                    email: 'test@example.com'
                })
            }))
        })

        it('should limit security events to 100', async () => {
            // Create 150 mock events
            const manyEvents = Array.from({ length: 150 }, (_, i) => ({
                type: 'login' as const,
                timestamp: new Date(),
                deviceId: 'device-123',
                success: true,
                id: i
            }))
            localStorageMock.getItem.mockReturnValue(JSON.stringify(manyEvents))

            // Trigger a new event
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })
            await webAuthService.login({ email: 'test@example.com', password: 'password123' })

            // Check that only 100 events are stored
            const setItemCalls = localStorageMock.setItem.mock.calls.filter(
                call => call[0] === 'remi_security_events'
            )
            expect(setItemCalls.length).toBeGreaterThan(0)

            const lastCall = setItemCalls[setItemCalls.length - 1]
            const storedEvents = JSON.parse(lastCall[1])
            expect(storedEvents).toHaveLength(100)
        })
    })

    describe('Password Reset', () => {
        it('should send forgot password request', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await webAuthService.forgotPassword('test@example.com')

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/forgot-password',
                { email: 'test@example.com' }
            )
        })

        it('should reset password', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await webAuthService.resetPassword('reset-token-123', 'newpassword123')

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/reset-password',
                {
                    token: 'reset-token-123',
                    newPassword: 'newpassword123'
                }
            )
        })
    })

    describe('Web-specific Features', () => {
        it('should check notification permission', async () => {
            // Mock Notification API
            Object.defineProperty(window, 'Notification', {
                value: {
                    permission: 'default',
                    requestPermission: jest.fn().mockResolvedValue('granted')
                }
            })

            const result = await webAuthService.requestNotificationPermission()

            expect(result).toBe(true)
            expect(window.Notification.requestPermission).toHaveBeenCalled()
        })

        it('should check PWA installability', async () => {
            // Mock service worker and BeforeInstallPromptEvent
            Object.defineProperty(navigator, 'serviceWorker', { value: {} })
            Object.defineProperty(window, 'BeforeInstallPromptEvent', { value: {} })

            const result = await webAuthService.canInstallPWA()

            expect(result).toBe(true)
        })
    })

    describe('Error Handling', () => {
        it('should handle network errors gracefully', async () => {
            mockedAxios.post.mockRejectedValue(new Error('Network Error'))

            await expect(webAuthService.login({
                email: 'test@example.com',
                password: 'password123'
            })).rejects.toThrow('Network Error')
        })

        it('should handle localStorage errors gracefully', async () => {
            localStorageMock.setItem.mockImplementation(() => {
                throw new Error('Storage quota exceeded')
            })

            await expect(webAuthService.storeTokens(mockTokens)).rejects.toThrow('Failed to store authentication tokens')
        })

        it('should handle JSON parsing errors gracefully', async () => {
            localStorageMock.getItem.mockReturnValue('invalid-json')

            const tokens = await webAuthService.getStoredTokens()

            expect(tokens).toBeNull()
        })
    })
})