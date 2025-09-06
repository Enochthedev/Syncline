// React Query hooks for authentication in React Native
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/authService'
import type { LoginCredentials, RegisterCredentials, User } from '@/services/authService'

// Query Keys
export const AUTH_QUERY_KEYS = {
    user: ['auth', 'user'] as const,
    sessions: ['auth', 'sessions'] as const,
    securityEvents: ['auth', 'security-events'] as const,
    biometricStatus: ['auth', 'biometric-status'] as const,
    platformStatus: (platform: string) => ['auth', 'platform', platform] as const,
}

// Authentication Queries
export const useUserQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.user,
        queryFn: () => authService.getStoredUser(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        cacheTime: 10 * 60 * 1000, // 10 minutes
    })
}

export const useAuthStatusQuery = () => {
    return useQuery({
        queryKey: ['auth', 'status'],
        queryFn: () => authService.isAuthenticated(),
        staleTime: 1 * 60 * 1000, // 1 minute
        cacheTime: 5 * 60 * 1000, // 5 minutes
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
    })
}

export const useActiveSessionsQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.sessions,
        queryFn: () => authService.getActiveSessions(),
        staleTime: 2 * 60 * 1000, // 2 minutes
        enabled: false, // Only fetch when explicitly requested
    })
}

export const useSecurityEventsQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.securityEvents,
        queryFn: () => authService.getSecurityEvents(),
        staleTime: 1 * 60 * 1000, // 1 minute
    })
}

// Biometric Queries
export const useBiometricStatusQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.biometricStatus,
        queryFn: async () => {
            const [available, enabled] = await Promise.all([
                authService.isBiometricAvailable(),
                authService.isBiometricEnabled()
            ])
            return { available, enabled }
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    })
}

// Platform Connection Queries
export const usePlatformStatusQuery = (platform: string) => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.platformStatus(platform),
        queryFn: () => authService.getPlatformStatus(platform),
        staleTime: 2 * 60 * 1000, // 2 minutes
        enabled: !!platform,
    })
}

// Authentication Mutations
export const useLoginMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (credentials: LoginCredentials) => authService.login(credentials),
        onSuccess: (data) => {
            // Update user cache
            queryClient.setQueryData(AUTH_QUERY_KEYS.user, data.user)
            queryClient.setQueryData(['auth', 'status'], true)

            // Invalidate related queries
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.sessions })
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.securityEvents })
        },
        onError: (error) => {
            console.error('Login failed:', error)
            // Clear any stale auth data
            queryClient.setQueryData(['auth', 'status'], false)
        }
    })
}

export const useRegisterMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (credentials: RegisterCredentials) => authService.register(credentials),
        onSuccess: (data) => {
            // Update user cache
            queryClient.setQueryData(AUTH_QUERY_KEYS.user, data.user)
            queryClient.setQueryData(['auth', 'status'], true)
        },
        onError: (error) => {
            console.error('Registration failed:', error)
        }
    })
}

export const useLogoutMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: () => authService.logout(),
        onSuccess: () => {
            // Clear all auth-related cache
            queryClient.setQueryData(AUTH_QUERY_KEYS.user, null)
            queryClient.setQueryData(['auth', 'status'], false)
            queryClient.removeQueries({ queryKey: AUTH_QUERY_KEYS.sessions })
            queryClient.removeQueries({ queryKey: AUTH_QUERY_KEYS.securityEvents })

            // Clear all cached data
            queryClient.clear()
        },
        onError: (error) => {
            console.error('Logout failed:', error)
        }
    })
}

// Biometric Mutations
export const useSetupBiometricMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: () => authService.setupBiometricAuth(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.biometricStatus })
        }
    })
}

export const useBiometricAuthMutation = () => {
    return useMutation({
        mutationFn: () => authService.authenticateWithBiometric(),
        onError: (error) => {
            console.error('Biometric authentication failed:', error)
        }
    })
}

export const useDisableBiometricMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: () => authService.disableBiometricAuth(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.biometricStatus })
        }
    })
}

// Platform Connection Mutations
export const useConnectPlatformMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ platform, authCode }: { platform: string; authCode: string }) =>
            authService.connectPlatform(platform, authCode),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: AUTH_QUERY_KEYS.platformStatus(variables.platform)
            })
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.securityEvents })
        }
    })
}

export const useDisconnectPlatformMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (platform: string) => authService.disconnectPlatform(platform),
        onSuccess: (_, platform) => {
            queryClient.invalidateQueries({
                queryKey: AUTH_QUERY_KEYS.platformStatus(platform)
            })
        }
    })
}

// Session Management Mutations
export const useRevokeSessionMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (sessionId: string) => authService.revokeSession(sessionId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.sessions })
        }
    })
}

// Password Reset Mutations
export const useForgotPasswordMutation = () => {
    return useMutation({
        mutationFn: (email: string) => authService.forgotPassword(email),
    })
}

export const useResetPasswordMutation = () => {
    return useMutation({
        mutationFn: ({ token, newPassword }: { token: string; newPassword: string }) =>
            authService.resetPassword(token, newPassword),
    })
}

// Token Refresh Mutation
export const useRefreshTokenMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: () => authService.refreshTokens(),
        onSuccess: (tokens) => {
            if (tokens) {
                queryClient.setQueryData(['auth', 'status'], true)
            } else {
                queryClient.setQueryData(['auth', 'status'], false)
                queryClient.setQueryData(AUTH_QUERY_KEYS.user, null)
            }
        }
    })
}

// Composite Hooks
export const useAuth = () => {
    const userQuery = useUserQuery()
    const authStatusQuery = useAuthStatusQuery()
    const loginMutation = useLoginMutation()
    const logoutMutation = useLogoutMutation()
    const refreshTokenMutation = useRefreshTokenMutation()

    return {
        // State
        user: userQuery.data,
        isAuthenticated: authStatusQuery.data ?? false,
        isLoading: userQuery.isLoading || authStatusQuery.isLoading,
        isError: userQuery.isError || authStatusQuery.isError,

        // Actions
        login: loginMutation.mutate,
        logout: logoutMutation.mutate,
        refreshTokens: refreshTokenMutation.mutate,

        // Mutation states
        isLoggingIn: loginMutation.isPending,
        isLoggingOut: logoutMutation.isPending,
        loginError: loginMutation.error,
        logoutError: logoutMutation.error,

        // Refetch functions
        refetchUser: userQuery.refetch,
        refetchAuthStatus: authStatusQuery.refetch,
    }
}

export const useBiometric = () => {
    const biometricStatusQuery = useBiometricStatusQuery()
    const setupMutation = useSetupBiometricMutation()
    const authMutation = useBiometricAuthMutation()
    const disableMutation = useDisableBiometricMutation()

    return {
        // State
        isAvailable: biometricStatusQuery.data?.available.available ?? false,
        biometryType: biometricStatusQuery.data?.available.biometryType,
        isEnabled: biometricStatusQuery.data?.enabled ?? false,
        isLoading: biometricStatusQuery.isLoading,

        // Actions
        setup: setupMutation.mutate,
        authenticate: authMutation.mutate,
        disable: disableMutation.mutate,

        // Mutation states
        isSettingUp: setupMutation.isPending,
        isAuthenticating: authMutation.isPending,
        isDisabling: disableMutation.isPending,

        setupError: setupMutation.error,
        authError: authMutation.error,
        disableError: disableMutation.error,

        // Refetch
        refetch: biometricStatusQuery.refetch,
    }
}

export const usePlatformConnection = (platform: string) => {
    const statusQuery = usePlatformStatusQuery(platform)
    const connectMutation = useConnectPlatformMutation()
    const disconnectMutation = useDisconnectPlatformMutation()

    return {
        // State
        status: statusQuery.data,
        isLoading: statusQuery.isLoading,
        isError: statusQuery.isError,

        // Actions
        connect: (authCode: string) => connectMutation.mutate({ platform, authCode }),
        disconnect: () => disconnectMutation.mutate(platform),

        // Mutation states
        isConnecting: connectMutation.isPending,
        isDisconnecting: disconnectMutation.isPending,
        connectError: connectMutation.error,
        disconnectError: disconnectMutation.error,

        // Refetch
        refetch: statusQuery.refetch,
    }
}