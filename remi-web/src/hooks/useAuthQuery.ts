// React Query hooks for authentication in Web App
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { webAuthService } from '@/services/authService'

// Types
interface LoginCredentials {
    email: string
    password: string
}

interface RegisterCredentials extends LoginCredentials {
    name: string
    confirmPassword: string
}

// Query Keys
export const AUTH_QUERY_KEYS = {
    user: ['auth', 'user'] as const,
    sessions: ['auth', 'sessions'] as const,
    securityEvents: ['auth', 'security-events'] as const,
    platformStatus: (platform: string) => ['auth', 'platform', platform] as const,
}

// Authentication Queries
export const useUserQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.user,
        queryFn: () => webAuthService.getStoredUser(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    })
}

export const useAuthStatusQuery = () => {
    return useQuery({
        queryKey: ['auth', 'status'],
        queryFn: () => webAuthService.isAuthenticated(),
        staleTime: 1 * 60 * 1000, // 1 minute
        gcTime: 5 * 60 * 1000, // 5 minutes
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
    })
}

export const useActiveSessionsQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.sessions,
        queryFn: () => webAuthService.getActiveSessions(),
        staleTime: 2 * 60 * 1000, // 2 minutes
        enabled: false, // Only fetch when explicitly requested
    })
}

export const useSecurityEventsQuery = () => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.securityEvents,
        queryFn: () => webAuthService.getSecurityEvents(),
        staleTime: 1 * 60 * 1000, // 1 minute
    })
}

// Platform Connection Queries
export const usePlatformStatusQuery = (platform: string) => {
    return useQuery({
        queryKey: AUTH_QUERY_KEYS.platformStatus(platform),
        queryFn: () => webAuthService.getPlatformStatus(platform),
        staleTime: 2 * 60 * 1000, // 2 minutes
        enabled: !!platform,
    })
}

// Authentication Mutations
export const useLoginMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (credentials: LoginCredentials) => webAuthService.login(credentials),
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
        mutationFn: (credentials: RegisterCredentials) => webAuthService.register(credentials),
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
        mutationFn: () => webAuthService.logout(),
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

// Platform Connection Mutations
export const useConnectPlatformMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ platform, authCode }: { platform: string; authCode: string }) =>
            webAuthService.connectPlatform(platform, authCode),
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
        mutationFn: (platform: string) => webAuthService.disconnectPlatform(platform),
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
        mutationFn: (sessionId: string) => webAuthService.revokeSession(sessionId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEYS.sessions })
        }
    })
}

// Password Reset Mutations
export const useForgotPasswordMutation = () => {
    return useMutation({
        mutationFn: (email: string) => webAuthService.forgotPassword(email),
    })
}

export const useResetPasswordMutation = () => {
    return useMutation({
        mutationFn: ({ token, newPassword }: { token: string; newPassword: string }) =>
            webAuthService.resetPassword(token, newPassword),
    })
}

// Token Refresh Mutation
export const useRefreshTokenMutation = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: () => webAuthService.refreshTokens(),
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

// Web-specific Features
export const useWebFeaturesMutation = () => {
    return useMutation({
        mutationFn: async (feature: 'notifications' | 'pwa') => {
            if (feature === 'notifications') {
                return await webAuthService.requestNotificationPermission()
            } else if (feature === 'pwa') {
                return await webAuthService.canInstallPWA()
            }
            return false
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

export const useSession = () => {
    const sessionsQuery = useActiveSessionsQuery()
    const revokeSessionMutation = useRevokeSessionMutation()
    const securityEventsQuery = useSecurityEventsQuery()

    return {
        // State
        sessions: sessionsQuery.data,
        securityEvents: securityEventsQuery.data,
        isLoading: sessionsQuery.isLoading || securityEventsQuery.isLoading,

        // Actions
        fetchSessions: sessionsQuery.refetch,
        revokeSession: revokeSessionMutation.mutate,

        // Mutation states
        isRevokingSession: revokeSessionMutation.isPending,
        revokeError: revokeSessionMutation.error,

        // Refetch
        refetchSessions: sessionsQuery.refetch,
        refetchSecurityEvents: securityEventsQuery.refetch,
    }
}

export const useWebFeatures = () => {
    const webFeaturesMutation = useWebFeaturesMutation()

    return {
        // Actions
        requestNotificationPermission: () => webFeaturesMutation.mutate('notifications'),
        checkPWAInstallability: () => webFeaturesMutation.mutate('pwa'),

        // State
        isCheckingFeatures: webFeaturesMutation.isPending,
        featureResult: webFeaturesMutation.data,
        featureError: webFeaturesMutation.error,
    }
}