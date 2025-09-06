// Authentication Service Tests for React Native
import { authService } from '@/services/authService'
import AsyncStorage from '@react-native-async-storage/async-storage'
import Keychain from 'react-native-keychain'
import ReactNativeBiometrics from 'react-native-biometrics'
import DeviceInfo from 'react-native-device-info'
import axios from 'axios'

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage')
jest.mock('react-native-keychain')
jest.mock('react-native-biometrics')
jest.mock('react-native-device-info')
jest.mock('axios')

const mockedAsyncStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>
const mockedKeychain = Keychain as jest.Mocked<typeof Keychain>
const mockedBiometrics = ReactNativeBiometrics as jest.MockedClass<typeof ReactNativeBiometrics>
const mockedDeviceInfo = DeviceInfo as jest.Mocked<typeof DeviceInfo>
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock data
const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    isVerified: true,
    preferences: {
        biometricEnabled: false,
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

const mockDeviceInfo = {
    deviceId: 'device-123',
    deviceName: 'Test Device',
    platform: 'iOS',
    version: '16.0',
    appVersion: '1.0.0'
}

describe('AuthService', () => {
    beforeEach(() => {
        jest.clearAllMocks()

        // Setup default mocks
        mockedDeviceInfo.getUniqueId.mockResolvedValue('device-123')
        mockedDeviceInfo.getDeviceName.mockResolvedValue('Test Device')
        mockedDeviceInfo.getSystemName.mockResolvedValue('iOS')
        mockedDeviceInfo.getSystemVersion.mockResolvedValue('16.0')
        mockedDeviceInfo.getVersion.mockReturnValue('1.0.0')

        mockedAsyncStorage.getItem.mockResolvedValue(null)
        mockedAsyncStorage.setItem.mockResolvedValue()
        mockedAsyncStorage.removeItem.mockResolvedValue()

        mockedKeychain.getInternetCredentials.mockResolvedValue(false as any)
        mockedKeychain.setInternetCredentials.mockResolvedValue()
        mockedKeychain.resetInternetCredentials.mockResolvedValue()
    })

    describe('Token Management', () => {
        it('should store tokens securely', async () => {
            await authService.storeTokens(mockTokens)

            expect(mockedKeychain.setInternetCredentials).toHaveBeenCalledWith(
                'remi-auth',
                'tokens',
                expect.stringContaining('accessToken')
            )
            expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith(
                'auth_tokens',
                expect.stringContaining('accessToken')
            )
        })

        it('should retrieve tokens from keychain first', async () => {
            const storedTokens = JSON.stringify(mockTokens)
            mockedKeychain.getInternetCredentials.mockResolvedValue({
                username: 'tokens',
                password: storedTokens,
                service: 'remi-auth',
                storage: 'keychain'
            })

            const tokens = await authService.getStoredTokens()

            expect(tokens).toEqual(expect.objectContaining({
                accessToken: mockTokens.accessToken,
                refreshToken: mockTokens.refreshToken,
                tokenType: mockTokens.tokenType
            }))
        })

        it('should fallback to AsyncStorage if keychain fails', async () => {
            mockedKeychain.getInternetCredentials.mockResolvedValue(false as any)
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockTokens))

            const tokens = await authService.getStoredTokens()

            expect(tokens).toEqual(expect.objectContaining({
                accessToken: mockTokens.accessToken,
                refreshToken: mockTokens.refreshToken
            }))
        })

        it('should clear all tokens and user data', async () => {
            await authService.clearTokens()

            expect(mockedKeychain.resetInternetCredentials).toHaveBeenCalledWith('remi-auth')
            expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('auth_tokens')
            expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('user_data')
        })
    })

    describe('Authentication', () => {
        it('should login successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })

            const result = await authService.login({
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
                        deviceId: 'device-123'
                    })
                })
            )
        })

        it('should handle login failure', async () => {
            const loginError = new Error('Invalid credentials')
            mockedAxios.post.mockRejectedValue(loginError)

            await expect(authService.login({
                email: 'test@example.com',
                password: 'wrongpassword'
            })).rejects.toThrow('Invalid credentials')
        })

        it('should logout successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await authService.logout()

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/logout',
                expect.objectContaining({
                    deviceInfo: expect.objectContaining({
                        deviceId: 'device-123'
                    })
                })
            )
        })

        it('should continue logout even if server call fails', async () => {
            mockedAxios.post.mockRejectedValue(new Error('Network error'))

            await expect(authService.logout()).resolves.not.toThrow()

            expect(mockedKeychain.resetInternetCredentials).toHaveBeenCalled()
            expect(mockedAsyncStorage.removeItem).toHaveBeenCalledTimes(2)
        })
    })

    describe('Biometric Authentication', () => {
        let mockBiometricsInstance: jest.Mocked<ReactNativeBiometrics>

        beforeEach(() => {
            mockBiometricsInstance = {
                isSensorAvailable: jest.fn(),
                createKeys: jest.fn(),
                createSignature: jest.fn(),
                deleteKeys: jest.fn(),
            } as any

            mockedBiometrics.mockImplementation(() => mockBiometricsInstance)
        })

        it('should check biometric availability', async () => {
            mockBiometricsInstance.isSensorAvailable.mockResolvedValue({
                available: true,
                biometryType: 'FaceID'
            })

            const result = await authService.isBiometricAvailable()

            expect(result).toEqual({
                available: true,
                biometryType: 'FaceID'
            })
        })

        it('should setup biometric authentication', async () => {
            mockBiometricsInstance.isSensorAvailable.mockResolvedValue({
                available: true,
                biometryType: 'TouchID'
            })
            mockBiometricsInstance.createKeys.mockResolvedValue({ success: true })

            const result = await authService.setupBiometricAuth()

            expect(result).toBe(true)
            expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('biometric_key', 'enabled')
        })

        it('should authenticate with biometrics', async () => {
            mockBiometricsInstance.isSensorAvailable.mockResolvedValue({
                available: true,
                biometryType: 'FaceID'
            })
            mockBiometricsInstance.createSignature.mockResolvedValue({
                success: true,
                signature: 'biometric-signature-123'
            })

            const result = await authService.authenticateWithBiometric()

            expect(result).toEqual({
                success: true,
                signature: 'biometric-signature-123'
            })
        })

        it('should handle biometric authentication failure', async () => {
            mockBiometricsInstance.isSensorAvailable.mockResolvedValue({
                available: true,
                biometryType: 'TouchID'
            })
            mockBiometricsInstance.createSignature.mockResolvedValue({
                success: false,
                error: 'User cancelled'
            })

            const result = await authService.authenticateWithBiometric()

            expect(result).toEqual({
                success: false,
                signature: undefined
            })
        })

        it('should disable biometric authentication', async () => {
            await authService.disableBiometricAuth()

            expect(mockBiometricsInstance.deleteKeys).toHaveBeenCalled()
            expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('biometric_key')
        })
    })

    describe('Token Refresh', () => {
        it('should refresh tokens successfully', async () => {
            const currentTokens = { ...mockTokens, expiresIn: Date.now() - 1000 } // Expired
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(currentTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            const result = await authService.refreshTokens()

            expect(result).toEqual(mockTokens)
            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/auth/refresh',
                expect.objectContaining({
                    refreshToken: currentTokens.refreshToken
                })
            )
        })

        it('should handle refresh token failure', async () => {
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockTokens))
            mockedAxios.post.mockRejectedValue(new Error('Invalid refresh token'))

            const result = await authService.refreshTokens()

            expect(result).toBeNull()
        })

        it('should deduplicate concurrent refresh requests', async () => {
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            // Make multiple concurrent refresh requests
            const promises = [
                authService.refreshTokens(),
                authService.refreshTokens(),
                authService.refreshTokens()
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
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(validTokens))

            const isAuthenticated = await authService.isAuthenticated()

            expect(isAuthenticated).toBe(true)
        })

        it('should attempt refresh for expired tokens', async () => {
            const expiredTokens = { ...mockTokens, expiresIn: Date.now() - 1000 }
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(expiredTokens))
            mockedAxios.post.mockResolvedValue({ data: mockTokens })

            const isAuthenticated = await authService.isAuthenticated()

            expect(isAuthenticated).toBe(true)
            expect(mockedAxios.post).toHaveBeenCalledWith('/api/v1/auth/refresh', expect.any(Object))
        })

        it('should return false for no tokens', async () => {
            mockedAsyncStorage.getItem.mockResolvedValue(null)

            const isAuthenticated = await authService.isAuthenticated()

            expect(isAuthenticated).toBe(false)
        })
    })

    describe('Platform Connections', () => {
        it('should connect platform successfully', async () => {
            mockedAxios.post.mockResolvedValue({ data: {} })

            await authService.connectPlatform('gmail', 'auth-code-123')

            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/v1/platforms/gmail/connect',
                expect.objectContaining({
                    authCode: 'auth-code-123',
                    deviceInfo: expect.objectContaining({
                        deviceId: 'device-123'
                    })
                })
            )
        })

        it('should disconnect platform successfully', async () => {
            mockedAxios.delete.mockResolvedValue({ data: {} })

            await authService.disconnectPlatform('gmail')

            expect(mockedAxios.delete).toHaveBeenCalledWith('/api/v1/platforms/gmail')
        })

        it('should get platform status', async () => {
            const mockStatus = { connected: true, lastSync: new Date().toISOString() }
            mockedAxios.get.mockResolvedValue({ data: mockStatus })

            const status = await authService.getPlatformStatus('gmail')

            expect(status).toEqual(mockStatus)
            expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/platforms/gmail/status')
        })
    })

    describe('Security Events', () => {
        it('should log security events', async () => {
            const mockEvents = [
                {
                    type: 'login' as const,
                    timestamp: new Date(),
                    deviceId: 'device-123',
                    success: true
                }
            ]
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockEvents))

            // Trigger a login to generate a security event
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })
            await authService.login({ email: 'test@example.com', password: 'password123' })

            expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith(
                'security_events',
                expect.stringContaining('login')
            )
        })

        it('should retrieve security events', async () => {
            const mockEvents = [
                {
                    type: 'login' as const,
                    timestamp: new Date(),
                    deviceId: 'device-123',
                    success: true
                }
            ]
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockEvents))

            const events = await authService.getSecurityEvents()

            expect(events).toHaveLength(1)
            expect(events[0].type).toBe('login')
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
            mockedAsyncStorage.getItem.mockResolvedValue(JSON.stringify(manyEvents))

            // Trigger a new event
            mockedAxios.post.mockResolvedValue({ data: mockLoginResponse })
            await authService.login({ email: 'test@example.com', password: 'password123' })

            // Should store only the last 100 events
            const setItemCall = mockedAsyncStorage.setItem.mock.calls.find(
                call => call[0] === 'security_events'
            )
            expect(setItemCall).toBeDefined()

            const storedEvents = JSON.parse(setItemCall![1])
            expect(storedEvents).toHaveLength(100)
        })
    })

    describe('Error Handling', () => {
        it('should handle network errors gracefully', async () => {
            mockedAxios.post.mockRejectedValue(new Error('Network Error'))

            await expect(authService.login({
                email: 'test@example.com',
                password: 'password123'
            })).rejects.toThrow('Network Error')
        })

        it('should handle storage errors gracefully', async () => {
            mockedAsyncStorage.setItem.mockRejectedValue(new Error('Storage full'))

            await expect(authService.storeTokens(mockTokens)).rejects.toThrow('Failed to store authentication tokens')
        })

        it('should handle keychain errors gracefully', async () => {
            mockedKeychain.setInternetCredentials.mockRejectedValue(new Error('Keychain error'))
            mockedAsyncStorage.setItem.mockResolvedValue() // AsyncStorage should still work

            await expect(authService.storeTokens(mockTokens)).rejects.toThrow('Failed to store authentication tokens')
        })
    })
})