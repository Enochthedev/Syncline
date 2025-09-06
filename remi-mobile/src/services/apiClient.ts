/**
 * API Client
 * 
 * Centralized HTTP client for API communication with authentication, retry logic, and error handling
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG, ERROR_CODES } from '../constants/api';
import { ApiResponse, ApiError } from '../types';

class ApiClient {
    private client: AxiosInstance;
    private authToken: string | null = null;
    private refreshPromise: Promise<string> | null = null;

    constructor() {
        this.client = axios.create({
            baseURL: API_CONFIG.baseURL,
            timeout: API_CONFIG.timeout,
            headers: {
                ...API_CONFIG.headers,
                'X-Client-Version': '1.0.0',
                'X-Platform': 'mobile',
            },
        });

        this.setupInterceptors();
    }

    private setupInterceptors() {
        // Request interceptor to add auth token and request metadata
        this.client.interceptors.request.use(
            async (config) => {
                // Add auth token
                if (!this.authToken) {
                    this.authToken = await AsyncStorage.getItem('auth_token');
                }

                if (this.authToken) {
                    config.headers.Authorization = `Bearer ${this.authToken}`;
                }

                // Add request timestamp for debugging
                config.headers['X-Request-Time'] = new Date().toISOString();

                // Add request ID for tracing
                config.headers['X-Request-ID'] = this.generateRequestId();

                return config;
            },
            (error) => {
                console.error('Request interceptor error:', error);
                return Promise.reject(error);
            }
        );

        // Response interceptor for error handling and token refresh
        this.client.interceptors.response.use(
            (response) => {
                // Log successful responses in debug mode
                if (__DEV__) {
                    console.log(`API Success: ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
                }
                return response;
            },
            async (error: AxiosError) => {
                const originalRequest = error.config as any;

                // Log errors in debug mode
                if (__DEV__) {
                    console.error(`API Error: ${originalRequest?.method?.toUpperCase()} ${originalRequest?.url} - ${error.response?.status || 'Network Error'}`);
                }

                // Handle 401 unauthorized with token refresh
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        const newToken = await this.refreshAuthToken();
                        if (newToken) {
                            originalRequest.headers.Authorization = `Bearer ${newToken}`;
                            return this.client(originalRequest);
                        }
                    } catch (refreshError) {
                        console.error('Token refresh failed:', refreshError);
                        await this.clearAuth();
                        // Emit auth error event for app-wide handling
                        this.emitAuthError();
                    }
                }

                // Handle rate limiting with retry after delay
                if (error.response?.status === 429) {
                    const retryAfter = error.response.headers['retry-after'];
                    const delay = retryAfter ? parseInt(retryAfter) * 1000 : 5000;

                    if (!originalRequest._rateLimitRetry) {
                        originalRequest._rateLimitRetry = true;
                        await this.sleep(delay);
                        return this.client(originalRequest);
                    }
                }

                return Promise.reject(this.transformError(error));
            }
        );
    }

    async setAuthToken(token: string) {
        this.authToken = token;
        await AsyncStorage.setItem('auth_token', token);
    }

    async clearAuth() {
        this.authToken = null;
        this.refreshPromise = null;
        await AsyncStorage.multiRemove(['auth_token', 'refresh_token', 'user_data']);
    }

    // Enhanced token refresh with deduplication
    private async refreshAuthToken(): Promise<string | null> {
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        this.refreshPromise = this.performTokenRefresh();

        try {
            const result = await this.refreshPromise;
            return result;
        } finally {
            this.refreshPromise = null;
        }
    }

    private async performTokenRefresh(): Promise<string | null> {
        try {
            const refreshToken = await AsyncStorage.getItem('refresh_token');
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }

            const response = await axios.post(`${API_CONFIG.baseURL}/api/v1/auth/refresh`, {
                refresh_token: refreshToken,
            }, {
                timeout: 10000,
                headers: API_CONFIG.headers,
            });

            const { access_token, refresh_token: newRefreshToken } = response.data;

            // Store new tokens
            await AsyncStorage.setItem('auth_token', access_token);
            if (newRefreshToken) {
                await AsyncStorage.setItem('refresh_token', newRefreshToken);
            }

            this.authToken = access_token;
            return access_token;
        } catch (error) {
            console.error('Token refresh failed:', error);
            return null;
        }
    }

    // HTTP methods
    async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.client.get(url, config);
    }

    async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.client.post(url, data, config);
    }

    async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.client.put(url, data, config);
    }

    async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.client.patch(url, data, config);
    }

    async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
        return this.client.delete(url, config);
    }

    // Enhanced utility methods
    isNetworkError(error: any): boolean {
        return !error.response && (error.request || error.code === 'NETWORK_ERROR');
    }

    isTimeoutError(error: any): boolean {
        return error.code === 'ECONNABORTED' || error.message?.includes('timeout');
    }

    isRetryableError(error: any): boolean {
        if (this.isNetworkError(error) || this.isTimeoutError(error)) {
            return true;
        }

        const status = error.response?.status;
        return status >= 500 || status === 408 || status === 429;
    }

    getErrorMessage(error: any): string {
        if (this.isNetworkError(error)) {
            return 'Network error. Please check your connection.';
        }

        if (this.isTimeoutError(error)) {
            return 'Request timed out. Please try again.';
        }

        if (error.response?.data?.detail) {
            return error.response.data.detail;
        }

        if (error.response?.data?.message) {
            return error.response.data.message;
        }

        if (error.response?.data?.error) {
            return error.response.data.error;
        }

        return error.message || 'An unexpected error occurred.';
    }

    // Private helper methods
    private generateRequestId(): string {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    private transformError(error: AxiosError): ApiError {
        const status = error.response?.status;
        const message = this.getErrorMessage(error);

        let code: string;
        switch (status) {
            case 400:
                code = ERROR_CODES.VALIDATION_ERROR;
                break;
            case 401:
                code = ERROR_CODES.AUTH_ERROR;
                break;
            case 404:
                code = ERROR_CODES.NOT_FOUND;
                break;
            case 408:
                code = ERROR_CODES.TIMEOUT_ERROR;
                break;
            case 429:
                code = ERROR_CODES.RATE_LIMITED;
                break;
            case 500:
            case 502:
            case 503:
            case 504:
                code = ERROR_CODES.SERVER_ERROR;
                break;
            default:
                if (this.isNetworkError(error)) {
                    code = ERROR_CODES.NETWORK_ERROR;
                } else if (this.isTimeoutError(error)) {
                    code = ERROR_CODES.TIMEOUT_ERROR;
                } else {
                    code = ERROR_CODES.SERVER_ERROR;
                }
        }

        return {
            message,
            code,
            details: {
                status,
                url: error.config?.url,
                method: error.config?.method,
                timestamp: new Date().toISOString(),
            }
        };
    }

    private emitAuthError() {
        // In a real app, you might use an event emitter or state management
        // to notify the app about auth errors
        console.warn('Authentication error occurred - user should be redirected to login');
    }

    // Request retry utility
    async requestWithRetry<T = any>(
        requestFn: () => Promise<AxiosResponse<T>>,
        maxRetries: number = 3,
        baseDelay: number = 1000
    ): Promise<AxiosResponse<T>> {
        let lastError: any;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error: any) {
                lastError = error;

                // Don't retry on non-retryable errors or last attempt
                if (!this.isRetryableError(error) || attempt === maxRetries) {
                    throw error;
                }

                // Calculate delay with exponential backoff
                const delay = baseDelay * Math.pow(2, attempt);
                const jitter = Math.random() * 0.1 * delay;
                await this.sleep(delay + jitter);

                console.warn(`Request attempt ${attempt + 1} failed, retrying in ${delay + jitter}ms`);
            }
        }

        throw lastError;
    }
}

export const apiClient = new ApiClient();