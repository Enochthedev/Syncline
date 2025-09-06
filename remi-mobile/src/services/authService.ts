import { API_CONFIG, API_ENDPOINTS } from '@/constants/api'
import { ApiResponse } from '@/types'
import Keychain from 'react-native-keychain'
import ReactNativeBiometrics from 'react-native-biometrics'
import AsyncStorage from '@react-native-async-storage/async-storage'
import DeviceInfo from 'react-native-device-info'
import axios, { AxiosInstance, AxiosError } from 'axios'

// Types
interface User {
    id: string
    email: string
    name: string
    avatar?: string
    isVerified: boolean
    lastLogin?: string
    preferences: UserPreferences
}

interface UserPreferences {
    biometricEnabled: boolean
    notificationsEnabled: boolean
    theme: 'light' | 'dark' | 'system'
    language: string
}

interface LoginCredentials {
    email: string
    password: string
    deviceInfo?: DeviceInfo
}

interface RegisterCredentials extends LoginCredentials {
    name: string
    confirmPassword: string
}

interface LoginResponse {
    user: User
    accessToken: string
    refreshToken: string
    expiresIn: number
    tokenType: 'Bearer'
}

interface RegisterResponse extends LoginResponse { }

interface TokenPair {
    accessToken: string
    refreshToken: string
    expiresIn: number
    tokenType: 'Bearer'
}

interface BiometricAuthResult {
    success: boolean
    signature?: string
    error?: string
}

interface OAuthProvider {
    name: string
    clientId: string
    redirectUri: string
    scopes: string[]
}

interface SessionInfo {
    deviceId: string
    deviceName: string
    platform: string
    lastActivity: string
    isCurrentDevice: boolean
}

interface SecurityEvent {
    type: 'login' | 'logout' | 'token_refresh' | 'biometric_auth' | 'oauth_connect'
    timestamp: Date
    deviceId: string
    success: boolean
    details?: Record<string, any>
}

interface DeviceInfo {
    deviceId: string
    deviceName: string
    platform: string
    version: string
    appVersion: string
}

// Constants
const KEYCHAIN_SERVICE = 'remi-auth'
const BIOMETRIC_PROMPT_MESSAGE = 'Authenticate to access R.E.M.I'
const TOKEN_STORAGE_KEY = 'auth_tokens'
const USER_STORAGE_KEY = 'user_data'
const DEVICE_ID_KEY = 'device_id'
const BIOMETRIC_KEY = 'biometric_key'
const SECURITY_EVENTS_KEY = 'security_events'

class AuthService {
    private baseURL = API_CONFIG.baseURL
    private biometrics = new ReactNativeBiometrics()
    private deviceId: string | null = null
    private apiClient: AxiosInstance
    private refreshPromise: Promise<TokenPair> | null = null

    constructor() {
        this.initializeDeviceId()
        this.setupApiClient()
    }

    // API Client Setup with Interceptors
    private setupApiClient(): void {
        this.apiClient = axios.create({
            baseURL: this.baseURL,
            timeout: API_CONFIG.timeout,
            headers: API_CONFIG.headers,
        })

        // Request interceptor to add auth token
        this.apiClient.interceptors.request.use(
            async (config) => {
                const tokens = await this.getStoredTokens()
                if (tokens?.accessToken) {
                    config.headers.Authorization = `${tokens.tokenType} ${tokens.accessToken}`
                }
                return config
            },
            (error) => Promise.reject(error)
        )

        // Response interceptor for token refresh
        this.apiClient.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as any

                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true

                    try {
                        const newTokens = await this.refreshTokens()
                        if (newTokens) {
                            originalRequest.headers.Authorization = `${newTokens.tokenType} ${newTokens.accessToken}`
                            return this.apiClient(originalRequest)
                        }
                    } catch (refreshError) {
                        await this.logout()
                        throw refreshError
                    }
                }

                return Promise.reject(error)
            }
        )
    }

    // Device Management
    private async initializeDeviceId(): Promise<void> {
        try {
            let deviceId = await AsyncStorage.getItem(DEVICE_ID_KEY)
            if (!deviceId) {
                deviceId = await DeviceInfo.getUniqueId()
                await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId)
            }
            this.deviceId = deviceId
        } catch (error) {
            console.error('Failed to initialize device ID:', error)
            this.deviceId = 'unknown-device'
        }
    }

    private async getDeviceInfo(): Promise<DeviceInfo> {
        return {
            deviceId: this.deviceId || await DeviceInfo.getUniqueId(),
            deviceName: await DeviceInfo.getDeviceName(),
            platform: await DeviceInfo.getSystemName(),
            version: await DeviceInfo.getSystemVersion(),
            appVersion: DeviceInfo.getVersion(),
        }
    }

    // Token Management
    async storeTokens(tokens: TokenPair): Promise<void> {
        try {
            const tokenData = {
                ...tokens,
                storedAt: new Date().toISOString()
            }

            // Store in secure keychain
            await Keychain.setInternetCredentials(
                KEYCHAIN_SERVICE,
                'tokens',
                JSON.stringify(tokenData)
            )

            // Also store in AsyncStorage for quick access
            await AsyncStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokenData))
        } catch (error) {
            console.error('Failed to store tokens:', error)
            throw new Error('Failed to store authentication tokens')
        }
    }

    async getStoredTokens(): Promise<TokenPair | null> {
        try {
            // Try keychain first
            const credentials = await Keychain.getInternetCredentials(KEYCHAIN_SERVICE)
            if (credentials && credentials.password) {
                const parsed = JSON.parse(credentials.password)
                return {
                    accessToken: parsed.accessToken,
                    refreshToken: parsed.refreshToken,
                    expiresIn: parsed.expiresIn,
                    tokenType: parsed.tokenType || 'Bearer'
                }
            }

            // Fallback to AsyncStorage
            const storedTokens = await AsyncStorage.getItem(TOKEN_STORAGE_KEY)
            if (storedTokens) {
                const parsed = JSON.parse(storedTokens)
                return {
                    accessToken: parsed.accessToken,
                    refreshToken: parsed.refreshToken,
                    expiresIn: parsed.expiresIn,
                    tokenType: parsed.tokenType || 'Bearer'
                }
            }

            return null
        } catch (error) {
            console.error('Failed to retrieve tokens:', error)
            return null
        }
    }

    async clearTokens(): Promise<void> {
        try {
            await Keychain.resetInternetCredentials(KEYCHAIN_SERVICE)
            await AsyncStorage.removeItem(TOKEN_STORAGE_KEY)
            await AsyncStorage.removeItem(USER_STORAGE_KEY)
        } catch (error) {
            console.error('Failed to clear tokens:', error)
        }
    }

    // Token Refresh with Deduplication
    async refreshTokens(): Promise<TokenPair | null> {
        if (this.refreshPromise) {
            return this.refreshPromise
        }

        this.refreshPromise = this.performTokenRefresh()

        try {
            const result = await this.refreshPromise
            return result
        } finally {
            this.refreshPromise = null
        }
    }

    private async performTokenRefresh(): Promise<TokenPair | null> {
        try {
            const currentTokens = await this.getStoredTokens()
            if (!currentTokens?.refreshToken) {
                throw new Error('No refresh token available')
            }

            const deviceInfo = await this.getDeviceInfo()
            const response = await axios.post(`${this.baseURL}${API_ENDPOINTS.AUTH.REFRESH}`, {
                refreshToken: currentTokens.refreshToken,
                deviceInfo
            })

            const newTokens: TokenPair = response.data
            await this.storeTokens(newTokens)

            await this.logSecurityEvent({
                type: 'token_refresh',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: true
            })

            return newTokens
        } catch (error) {
            console.error('Token refresh failed:', error)
            await this.logSecurityEvent({
                type: 'token_refresh',
                timestamp: new Date(),
                deviceId: this.deviceId || 'unknown',
                success: false,
                details: { error: error instanceof Error ? error.message : 'Unknown error' }
            })
            return null
        }
    }

    // Biometric Authentication
    async isBiometricAvailable(): Promise<{ available: boolean; biometryType?: string }> {
        try {
            const { available, biometryType } = await this.biometrics.isSensorAvailable()
            return { available, biometryType }
        } catch (error) {
            console.error('Biometric check failed:', error)
            return { available: false }
        }
    }

    async setupBiometricAuth(): Promise<boolean> {
        try {
            const { available } = await this.isBiometricAvailable()
            if (!available) {
                return false
            }

            // Create biometric key
            const { success } = await this.biometrics.createKeys()
            if (success) {
                await AsyncStorage.setItem(BIOMETRIC_KEY, 'enabled')
                return true
            }
            return false
        } catch (error) {
            console.error('Biometric setup failed:', error)
            return false
        }
    }

    async authenticateWithBiometric(): Promise<BiometricAuthResult> {
        try {
            const { available } = await this.isBiometricAvailable()
            if (!available) {
                return { success: false, error: 'Biometric authentication not available' }
            }

            const { success, signature } = await this.biometrics.createSignature({
                promptMessage: BIOMETRIC_PROMPT_MESSAGE,
                payload: `${Date.now()}-${this.deviceId}`,
            })

            const deviceInfo = await this.getDeviceInfo()
            await this.logSecurityEvent({
                type: 'biometric_auth',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success
            })

            return { success, signature }
        } catch (error) {
            console.error('Biometric authentication failed:', error)
            return { success: false, error: error instanceof Error ? error.message : 'Unknown error' }
        }
    }

    async disableBiometricAuth(): Promise<void> {
        try {
            await this.biometrics.deleteKeys()
            await AsyncStorage.removeItem(BIOMETRIC_KEY)
        } catch (error) {
            console.error('Failed to disable biometric auth:', error)
        }
    }

    async isBiometricEnabled(): Promise<boolean> {
        try {
            const enabled = await AsyncStorage.getItem(BIOMETRIC_KEY)
            return enabled === 'enabled'
        } catch (error) {
            return false
        }
    }

    // Authentication Methods
    async login(credentials: LoginCredentials): Promise<LoginResponse> {
        try {
            const deviceInfo = await this.getDeviceInfo()
            const response = await this.apiClient.post(API_ENDPOINTS.AUTH.LOGIN, {
                ...credentials,
                deviceInfo
            })

            const loginData: LoginResponse = response.data

            // Store tokens and user data
            await this.storeTokens({
                accessToken: loginData.accessToken,
                refreshToken: loginData.refreshToken,
                expiresIn: loginData.expiresIn,
                tokenType: loginData.tokenType
            })

            await this.storeUser(loginData.user)

            await this.logSecurityEvent({
                type: 'login',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: true,
                details: { email: credentials.email }
            })

            return loginData
        } catch (error) {
            const deviceInfo = await this.getDeviceInfo()
            await this.logSecurityEvent({
                type: 'login',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: false,
                details: {
                    email: credentials.email,
                    error: error instanceof Error ? error.message : 'Unknown error'
                }
            })
            throw error
        }
    }

    async register(credentials: RegisterCredentials): Promise<RegisterResponse> {
        try {
            const deviceInfo = await this.getDeviceInfo()
            const response = await this.apiClient.post(API_ENDPOINTS.AUTH.REGISTER, {
                ...credentials,
                deviceInfo
            })

            const registerData: RegisterResponse = response.data

            // Store tokens and user data
            await this.storeTokens({
                accessToken: registerData.accessToken,
                refreshToken: registerData.refreshToken,
                expiresIn: registerData.expiresIn,
                tokenType: registerData.tokenType
            })

            await this.storeUser(registerData.user)

            return registerData
        } catch (error) {
            throw error
        }
    }

    async logout(): Promise<void> {
        try {
            const deviceInfo = await this.getDeviceInfo()

            // Attempt to notify server
            try {
                await this.apiClient.post(API_ENDPOINTS.AUTH.LOGOUT, { deviceInfo })
            } catch (error) {
                // Continue with local logout even if server call fails
                console.warn('Server logout failed, continuing with local logout:', error)
            }

            // Clear local data
            await this.clearTokens()
            await this.clearUser()

            await this.logSecurityEvent({
                type: 'logout',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: true
            })
        } catch (error) {
            console.error('Logout failed:', error)
            throw error
        }
    }

    // User Data Management
    async storeUser(user: User): Promise<void> {
        try {
            await AsyncStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
        } catch (error) {
            console.error('Failed to store user data:', error)
        }
    }

    async getStoredUser(): Promise<User | null> {
        try {
            const userData = await AsyncStorage.getItem(USER_STORAGE_KEY)
            return userData ? JSON.parse(userData) : null
        } catch (error) {
            console.error('Failed to retrieve user data:', error)
            return null
        }
    }

    async clearUser(): Promise<void> {
        try {
            await AsyncStorage.removeItem(USER_STORAGE_KEY)
        } catch (error) {
            console.error('Failed to clear user data:', error)
        }
    }

    // OAuth 2.0 Platform Connections
    async connectPlatform(platform: string, authCode: string): Promise<void> {
        try {
            const deviceInfo = await this.getDeviceInfo()
            await this.apiClient.post(API_ENDPOINTS.PLATFORMS.CONNECT.replace('{platform}', platform), {
                authCode,
                deviceInfo
            })

            await this.logSecurityEvent({
                type: 'oauth_connect',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: true,
                details: { platform }
            })
        } catch (error) {
            const deviceInfo = await this.getDeviceInfo()
            await this.logSecurityEvent({
                type: 'oauth_connect',
                timestamp: new Date(),
                deviceId: deviceInfo.deviceId,
                success: false,
                details: {
                    platform,
                    error: error instanceof Error ? error.message : 'Unknown error'
                }
            })
            throw error
        }
    }

    async disconnectPlatform(platform: string): Promise<void> {
        try {
            await this.apiClient.delete(API_ENDPOINTS.PLATFORMS.DISCONNECT.replace('{platform}', platform))
        } catch (error) {
            throw error
        }
    }

    async getPlatformStatus(platform: string): Promise<any> {
        try {
            const response = await this.apiClient.get(API_ENDPOINTS.PLATFORMS.STATUS.replace('{platform}', platform))
            return response.data
        } catch (error) {
            throw error
        }
    }

    // Session Management
    async getActiveSessions(): Promise<SessionInfo[]> {
        try {
            const response = await this.apiClient.get('/api/v1/auth/sessions')
            return response.data
        } catch (error) {
            throw error
        }
    }

    async revokeSession(sessionId: string): Promise<void> {
        try {
            await this.apiClient.delete(`/api/v1/auth/sessions/${sessionId}`)
        } catch (error) {
            throw error
        }
    }

    // Security Event Logging
    private async logSecurityEvent(event: SecurityEvent): Promise<void> {
        try {
            const events = await this.getSecurityEvents()
            events.push(event)

            // Keep only last 100 events
            const recentEvents = events.slice(-100)
            await AsyncStorage.setItem(SECURITY_EVENTS_KEY, JSON.stringify(recentEvents))
        } catch (error) {
            console.error('Failed to log security event:', error)
        }
    }

    async getSecurityEvents(): Promise<SecurityEvent[]> {
        try {
            const events = await AsyncStorage.getItem(SECURITY_EVENTS_KEY)
            return events ? JSON.parse(events) : []
        } catch (error) {
            console.error('Failed to retrieve security events:', error)
            return []
        }
    }

    // Authentication State
    async isAuthenticated(): Promise<boolean> {
        try {
            const tokens = await this.getStoredTokens()
            if (!tokens) return false

            // Check if token is expired
            const now = Date.now()
            const tokenAge = now - new Date(tokens.expiresIn).getTime()

            if (tokenAge > 0) {
                // Token expired, try to refresh
                const refreshed = await this.refreshTokens()
                return refreshed !== null
            }

            return true
        } catch (error) {
            console.error('Authentication check failed:', error)
            return false
        }
    }

    // Password Reset
    async forgotPassword(email: string): Promise<void> {
        try {
            await this.apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email })
        } catch (error) {
            throw error
        }
    }

    async resetPassword(token: string, newPassword: string): Promise<void> {
        try {
            await this.apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD, {
                token,
                newPassword
            })
        } catch (error) {
            throw error
        }
    }
}

// Export singleton instance
export const authService = new AuthService()
export default authService

// React Query Hooks for Authentication
export const useAuth = () => {
    return {
        login: async (credentials: LoginCredentials) => authService.login(credentials),
        register: async (credentials: RegisterCredentials) => authService.register(credentials),
        logout: async () => authService.logout(),
        isAuthenticated: async () => authService.isAuthenticated(),
        getUser: async () => authService.getStoredUser(),
        refreshTokens: async () => authService.refreshTokens(),
    }
}

export const useBiometric = () => {
    return {
        isAvailable: async () => authService.isBiometricAvailable(),
        isEnabled: async () => authService.isBiometricEnabled(),
        setup: async () => authService.setupBiometricAuth(),
        authenticate: async () => authService.authenticateWithBiometric(),
        disable: async () => authService.disableBiometricAuth(),
    }
}

export const usePlatformConnection = () => {
    return {
        connect: async (platform: string, authCode: string) => authService.connectPlatform(platform, authCode),
        disconnect: async (platform: string) => authService.disconnectPlatform(platform),
        getStatus: async (platform: string) => authService.getPlatformStatus(platform),
    }
}

export const useSession = () => {
    return {
        getActiveSessions: async () => authService.getActiveSessions(),
        revokeSession: async (sessionId: string) => authService.revokeSession(sessionId),
        getSecurityEvents: async () => authService.getSecurityEvents(),
    }
}