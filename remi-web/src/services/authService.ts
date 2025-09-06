// Web Authentication Service for R.E.M.I Progressive Web App
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

interface SessionInfo {
    deviceId: string
    deviceName: string
    platform: string
    lastActivity: string
    isCurrentDevice: boolean
}

interface SecurityEvent {
    type: 'login' | 'logout' | 'token_refresh' | 'oauth_connect'
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

// API Configuration
const API_CONFIG = {
    baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    }
}

const API_ENDPOINTS = {
    AUTH: {
        LOGIN: '/api/v1/auth/login',
        REFRESH: '/api/v1/auth/refresh',
        LOGOUT: '/api/v1/auth/logout',
        REGISTER: '/api/v1/auth/register',
        FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
        RESET_PASSWORD: '/api/v1/auth/reset-password',
    },
    PLATFORMS: {
        CONNECT: '/api/v1/platforms/{platform}/connect',
        STATUS: '/api/v1/platforms/{platform}/status',
        DISCONNECT: '/api/v1/platforms/{platform}',
    }
}

// Constants
const TOKEN_STORAGE_KEY = 'remi_auth_tokens'
const USER_STORAGE_KEY = 'remi_user_data'
const DEVICE_ID_KEY = 'remi_device_id'
const SECURITY_EVENTS_KEY = 'remi_security_events'

class WebAuthService {
    private baseURL = API_CONFIG.baseURL
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
            let deviceId = localStorage.getItem(DEVICE_ID_KEY)
            if (!deviceId) {
                deviceId = this.generateDeviceId()
                localStorage.setItem(DEVICE_ID_KEY, deviceId)
            }
            this.deviceId = deviceId
        } catch (error) {
            console.error('Failed to initialize device ID:', error)
            this.deviceId = 'unknown-device'
        }
    }

    private generateDeviceId(): string {
        // Generate a unique device ID for web
        const timestamp = Date.now().toString(36)
        const randomPart = Math.random().toString(36).substr(2, 9)
        return `web-${timestamp}-${randomPart}`
    }

    private async getDeviceInfo(): Promise<DeviceInfo> {
        const userAgent = navigator.userAgent
        const platform = navigator.platform

        return {
            deviceId: this.deviceId || this.generateDeviceId(),
            deviceName: `${platform} Browser`,
            platform: 'web',
            version: userAgent,
            appVersion: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
        }
    }

    // Token Management
    async storeTokens(tokens: TokenPair): Promise<void> {
        try {
            const tokenData = {
                ...tokens,
                storedAt: new Date().toISOString()
            }
            localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokenData))
        } catch (error) {
            console.error('Failed to store tokens:', error)
            throw new Error('Failed to store authentication tokens')
        }
    }

    async getStoredTokens(): Promise<TokenPair | null> {
        try {
            const tokenData = localStorage.getItem(TOKEN_STORAGE_KEY)
            if (!tokenData) return null

            const parsed = JSON.parse(tokenData)
            return {
                accessToken: parsed.accessToken,
                refreshToken: parsed.refreshToken,
                expiresIn: parsed.expiresIn,
                tokenType: parsed.tokenType || 'Bearer'
            }
        } catch (error) {
            console.error('Failed to retrieve tokens:', error)
            return null
        }
    }

    async clearTokens(): Promise<void> {
        try {
            localStorage.removeItem(TOKEN_STORAGE_KEY)
            localStorage.removeItem(USER_STORAGE_KEY)
        } catch (error) {
            console.error('Failed to clear tokens:', error)
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
            return loginData
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
                console.warn('Server logout failed, continuing with local logout:', error)
            }

            // Clear local data
            await this.clearTokens()
            await this.clearUser()
        } catch (error) {
            console.error('Logout failed:', error)
            throw error
        }
    }

    // User Data Management
    async storeUser(user: User): Promise<void> {
        try {
            localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
        } catch (error) {
            console.error('Failed to store user data:', error)
        }
    }

    async getStoredUser(): Promise<User | null> {
        try {
            const userData = localStorage.getItem(USER_STORAGE_KEY)
            return userData ? JSON.parse(userData) : null
        } catch (error) {
            console.error('Failed to retrieve user data:', error)
            return null
        }
    }

    async clearUser(): Promise<void> {
        try {
            localStorage.removeItem(USER_STORAGE_KEY)
        } catch (error) {
            console.error('Failed to clear user data:', error)
        }
    }

    // Token Refresh
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
            return newTokens
        } catch (error) {
            console.error('Token refresh failed:', error)
            return null
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
}

// Export singleton instance
export const webAuthService = new WebAuthService()
export default webAuthService

// React Hooks for Web Authentication
export const useAuth = () => {
    return {
        login: async (credentials: LoginCredentials) => webAuthService.login(credentials),
        logout: async () => webAuthService.logout(),
        isAuthenticated: async () => webAuthService.isAuthenticated(),
        getUser: async () => webAuthService.getStoredUser(),
        refreshTokens: async () => webAuthService.refreshTokens(),
    }
}