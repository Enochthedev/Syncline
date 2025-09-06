// React Query Authentication Hooks Tests for React Native
import { renderHook, waitFor } from '@testing-library/react-native'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import {
    useAuth,
    useBiometric,
    usePlatformConnection,
    useLoginMutation,
    useLogoutMutation,
    useUserQuery,
    useAuthStatusQuery
} from '@/hooks/useAuthQuery'
import { authService } from '@/services/authService'

// Mock the auth service
jest.mock('@/services/authService')
const mockedAuthService = authService as jest.Mocked<typeof authService>

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
    expiresIn: Date.now() + 3600000,
    tokenType: 'Bearer' as const
}

const mockLoginResponse = {
    user: mockUser,
    ...mockTokens
}

// Test wrapper with QueryClient
const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
            mutations: {
                retry: false,
            },
        },
    })

    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client= { queryClient } >
        { children }
        < /QueryClientProvider>
    )
}

describe('useAuthQuery Hooks', () => {
    beforeEach(() => {
        jest.clearAllMocks()
    })

    describe('useUserQuery', () => {
        it('should fetch user data successfully', async () => {
            mockedAuthService.getStoredUser.mockResolvedValue(mockUser)

            const { result } = renderHook(() => useUserQuery(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(result.current.data).toEqual(mockUser)
            expect(mockedAuthService.getStoredUser).toHaveBeenCalledTimes(1)
        })

        it('should handle user data fetch error', async () => {
            mockedAuthService.getStoredUser.mockRejectedValue(new Error('Storage error'))

            const { result } = renderHook(() => useUserQuery(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isError).toBe(true)
            })

            expect(result.current.error).toEqual(new Error('Storage error'))
        })

        it('should return null when no user data', async () => {
            mockedAuthService.getStoredUser.mockResolvedValue(null)

            const { result } = renderHook(() => useUserQuery(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(result.current.data).toBeNull()
        })
    })

    describe('useAuthStatusQuery', () => {
        it('should return true when authenticated', async () => {
            mockedAuthService.isAuthenticated.mockResolvedValue(true)

            const { result } = renderHook(() => useAuthStatusQuery(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(result.current.data).toBe(true)
        })

        it('should return false when not authenticated', async () => {
            mockedAuthService.isAuthenticated.mockResolvedValue(false)

            const { result } = renderHook(() => useAuthStatusQuery(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(result.current.data).toBe(false)
        })
    })

    describe('useLoginMutation', () => {
        it('should login successfully', async () => {
            mockedAuthService.login.mockResolvedValue(mockLoginResponse)

            const { result } = renderHook(() => useLoginMutation(), {
                wrapper: createWrapper(),
            })

            const loginCredentials = {
                email: 'test@example.com',
                password: 'password123'
            }

            result.current.mutate(loginCredentials)

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(result.current.data).toEqual(mockLoginResponse)
            expect(mockedAuthService.login).toHaveBeenCalledWith(loginCredentials)
        })

        it('should handle login failure', async () => {
            const loginError = new Error('Invalid credentials')
            mockedAuthService.login.mockRejectedValue(loginError)

            const { result } = renderHook(() => useLoginMutation(), {
                wrapper: createWrapper(),
            })

            result.current.mutate({
                email: 'test@example.com',
                password: 'wrongpassword'
            })

            await waitFor(() => {
                expect(result.current.isError).toBe(true)
            })

            expect(result.current.error).toEqual(loginError)
        })
    })

    describe('useLogoutMutation', () => {
        it('should logout successfully', async () => {
            mockedAuthService.logout.mockResolvedValue()

            const { result } = renderHook(() => useLogoutMutation(), {
                wrapper: createWrapper(),
            })

            result.current.mutate()

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true)
            })

            expect(mockedAuthService.logout).toHaveBeenCalledTimes(1)
        })

        it('should handle logout failure', async () => {
            const logoutError = new Error('Network error')
            mockedAuthService.logout.mockRejectedValue(logoutError)

            const { result } = renderHook(() => useLogoutMutation(), {
                wrapper: createWrapper(),
            })

            result.current.mutate()

            await waitFor(() => {
                expect(result.current.isError).toBe(true)
            })

            expect(result.current.error).toEqual(logoutError)
        })
    })

    describe('useAuth composite hook', () => {
        it('should provide complete auth state and actions', async () => {
            mockedAuthService.getStoredUser.mockResolvedValue(mockUser)
            mockedAuthService.isAuthenticated.mockResolvedValue(true)

            const { result } = renderHook(() => useAuth(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isAuthenticated).toBe(true)
            })

            expect(result.current.user).toEqual(mockUser)
            expect(typeof result.current.login).toBe('function')
            expect(typeof result.current.logout).toBe('function')
            expect(typeof result.current.refreshTokens).toBe('function')
        })

        it('should handle loading states', async () => {
            // Mock slow responses
            mockedAuthService.getStoredUser.mockImplementation(
                () => new Promise(resolve => setTimeout(() => resolve(mockUser), 100))
            )
            mockedAuthService.isAuthenticated.mockImplementation(
                () => new Promise(resolve => setTimeout(() => resolve(true), 100))
            )

            const { result } = renderHook(() => useAuth(), {
                wrapper: createWrapper(),
            })

            expect(result.current.isLoading).toBe(true)

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false)
            })
        })
    })

    describe('useBiometric hook', () => {
        it('should check biometric availability', async () => {
            mockedAuthService.isBiometricAvailable.mockResolvedValue({
                available: true,
                biometryType: 'FaceID'
            })
            mockedAuthService.isBiometricEnabled.mockResolvedValue(true)

            const { result } = renderHook(() => useBiometric(), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.isAvailable).toBe(true)
            })

            expect(result.current.biometryType).toBe('FaceID')
            expect(result.current.isEnabled).toBe(true)
        })

        it('should setup biometric authentication', async () => {
            mockedAuthService.setupBiometricAuth.mockResolvedValue(true)

            const { result } = renderHook(() => useBiometric(), {
                wrapper: createWrapper(),
            })

            result.current.setup()

            await waitFor(() => {
                expect(result.current.isSettingUp).toBe(false)
            })

            expect(mockedAuthService.setupBiometricAuth).toHaveBeenCalledTimes(1)
        })

        it('should authenticate with biometrics', async () => {
            mockedAuthService.authenticateWithBiometric.mockResolvedValue({
                success: true,
                signature: 'biometric-signature'
            })

            const { result } = renderHook(() => useBiometric(), {
                wrapper: createWrapper(),
            })

            result.current.authenticate()

            await waitFor(() => {
                expect(result.current.isAuthenticating).toBe(false)
            })

            expect(mockedAuthService.authenticateWithBiometric).toHaveBeenCalledTimes(1)
        })

        it('should handle biometric authentication failure', async () => {
            mockedAuthService.authenticateWithBiometric.mockResolvedValue({
                success: false,
                error: 'User cancelled'
            })

            const { result } = renderHook(() => useBiometric(), {
                wrapper: createWrapper(),
            })

            result.current.authenticate()

            await waitFor(() => {
                expect(result.current.isAuthenticating).toBe(false)
            })

            // Should still complete successfully even if biometric auth failed
            expect(mockedAuthService.authenticateWithBiometric).toHaveBeenCalledTimes(1)
        })

        it('should disable biometric authentication', async () => {
            mockedAuthService.disableBiometricAuth.mockResolvedValue()

            const { result } = renderHook(() => useBiometric(), {
                wrapper: createWrapper(),
            })

            result.current.disable()

            await waitFor(() => {
                expect(result.current.isDisabling).toBe(false)
            })

            expect(mockedAuthService.disableBiometricAuth).toHaveBeenCalledTimes(1)
        })
    })

    describe('usePlatformConnection hook', () => {
        const platform = 'gmail'

        it('should get platform status', async () => {
            const mockStatus = { connected: true, lastSync: new Date().toISOString() }
            mockedAuthService.getPlatformStatus.mockResolvedValue(mockStatus)

            const { result } = renderHook(() => usePlatformConnection(platform), {
                wrapper: createWrapper(),
            })

            await waitFor(() => {
                expect(result.current.status).toEqual(mockStatus)
            })

            expect(mockedAuthService.getPlatformStatus).toHaveBeenCalledWith(platform)
        })

        it('should connect platform', async () => {
            mockedAuthService.connectPlatform.mockResolvedValue()

            const { result } = renderHook(() => usePlatformConnection(platform), {
                wrapper: createWrapper(),
            })

            const authCode = 'auth-code-123'
            result.current.connect(authCode)

            await waitFor(() => {
                expect(result.current.isConnecting).toBe(false)
            })

            expect(mockedAuthService.connectPlatform).toHaveBeenCalledWith(platform, authCode)
        })

        it('should disconnect platform', async () => {
            mockedAuthService.disconnectPlatform.mockResolvedValue()

            const { result } = renderHook(() => usePlatformConnection(platform), {
                wrapper: createWrapper(),
            })

            result.current.disconnect()

            await waitFor(() => {
                expect(result.current.isDisconnecting).toBe(false)
            })

            expect(mockedAuthService.disconnectPlatform).toHaveBeenCalledWith(platform)
        })

        it('should handle connection errors', async () => {
            const connectionError = new Error('OAuth failed')
            mockedAuthService.connectPlatform.mockRejectedValue(connectionError)

            const { result } = renderHook(() => usePlatformConnection(platform), {
                wrapper: createWrapper(),
            })

            result.current.connect('auth-code-123')

            await waitFor(() => {
                expect(result.current.connectError).toEqual(connectionError)
            })
        })
    })

    describe('Query invalidation and caching', () => {
        it('should invalidate related queries on login success', async () => {
            mockedAuthService.login.mockResolvedValue(mockLoginResponse)
            mockedAuthService.getActiveSessions.mockResolvedValue([])
            mockedAuthService.getSecurityEvents.mockResolvedValue([])

            const queryClient = new QueryClient({
                defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
            })

            const wrapper = ({ children }: { children: React.ReactNode }) => (
                <QueryClientProvider client= { queryClient } >
                { children }
                < /QueryClientProvider>
            )

        const { result } = renderHook(() => useLoginMutation(), { wrapper })

        result.current.mutate({
            email: 'test@example.com',
            password: 'password123'
        })

        await waitFor(() => {
            expect(result.current.isSuccess).toBe(true)
        })

        // Check that user data was cached
        const userData = queryClient.getQueryData(['auth', 'user'])
        expect(userData).toEqual(mockUser)

        // Check that auth status was cached
        const authStatus = queryClient.getQueryData(['auth', 'status'])
        expect(authStatus).toBe(true)
    })

    it('should clear cache on logout', async () => {
        mockedAuthService.logout.mockResolvedValue()

        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
        })

        // Pre-populate cache
        queryClient.setQueryData(['auth', 'user'], mockUser)
        queryClient.setQueryData(['auth', 'status'], true)

        const wrapper = ({ children }: { children: React.ReactNode }) => (
            <QueryClientProvider client= { queryClient } >
            { children }
            < /QueryClientProvider>
            )

    const { result } = renderHook(() => useLogoutMutation(), { wrapper })

    result.current.mutate()

    await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
    })

    // Check that cache was cleared
    const userData = queryClient.getQueryData(['auth', 'user'])
    const authStatus = queryClient.getQueryData(['auth', 'status'])

    expect(userData).toBeNull()
    expect(authStatus).toBe(false)
})
    })

describe('Error handling', () => {
    it('should handle network errors in queries', async () => {
        mockedAuthService.getStoredUser.mockRejectedValue(new Error('Network error'))

        const { result } = renderHook(() => useUserQuery(), {
            wrapper: createWrapper(),
        })

        await waitFor(() => {
            expect(result.current.isError).toBe(true)
        })

        expect(result.current.error).toEqual(new Error('Network error'))
    })

    it('should handle authentication errors in mutations', async () => {
        mockedAuthService.login.mockRejectedValue(new Error('Invalid credentials'))

        const { result } = renderHook(() => useLoginMutation(), {
            wrapper: createWrapper(),
        })

        result.current.mutate({
            email: 'test@example.com',
            password: 'wrongpassword'
        })

        await waitFor(() => {
            expect(result.current.isError).toBe(true)
        })

        expect(result.current.error).toEqual(new Error('Invalid credentials'))
    })
})

describe('Loading states', () => {
    it('should show loading state during login', async () => {
        mockedAuthService.login.mockImplementation(
            () => new Promise(resolve => setTimeout(() => resolve(mockLoginResponse), 100))
        )

        const { result } = renderHook(() => useLoginMutation(), {
            wrapper: createWrapper(),
        })

        result.current.mutate({
            email: 'test@example.com',
            password: 'password123'
        })

        expect(result.current.isPending).toBe(true)

        await waitFor(() => {
            expect(result.current.isPending).toBe(false)
        })

        expect(result.current.isSuccess).toBe(true)
    })

    it('should show loading state during biometric setup', async () => {
        mockedAuthService.setupBiometricAuth.mockImplementation(
            () => new Promise(resolve => setTimeout(() => resolve(true), 100))
        )

        const { result } = renderHook(() => useBiometric(), {
            wrapper: createWrapper(),
        })

        result.current.setup()

        expect(result.current.isSettingUp).toBe(true)

        await waitFor(() => {
            expect(result.current.isSettingUp).toBe(false)
        })
    })
})
})