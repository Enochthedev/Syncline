/**
 * API Client (Web Version)
 * 
 * Centralized HTTP client for API communication with authentication
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

class ApiClient {
    private client: AxiosInstance;
    private authToken: string | null = null;

    constructor() {
        this.client = axios.create({
            baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        this.setupInterceptors();
    }

    private setupInterceptors() {
        // Request interceptor to add auth token
        this.client.interceptors.request.use(
            async (config) => {
                if (!this.authToken) {
                    this.authToken = localStorage.getItem('auth_token');
                }

                if (this.authToken) {
                    config.headers.Authorization = `Bearer ${this.authToken}`;
                }

                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        // Response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                // Handle 401 unauthorized
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        // Try to refresh token
                        const refreshToken = localStorage.getItem('refresh_token');
                        if (refreshToken) {
                            const response = await this.client.post('/api/v1/auth/refresh', {
                                refresh_token: refreshToken,
                            });

                            const { access_token } = response.data;
                            localStorage.setItem('auth_token', access_token);
                            this.authToken = access_token;

                            // Retry original request
                            originalRequest.headers.Authorization = `Bearer ${access_token}`;
                            return this.client(originalRequest);
                        }
                    } catch (refreshError) {
                        // Refresh failed, redirect to login
                        this.clearAuth();
                        window.location.href = '/login';
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    async setAuthToken(token: string) {
        this.authToken = token;
        localStorage.setItem('auth_token', token);
    }

    async clearAuth() {
        this.authToken = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
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

    // Utility methods
    isNetworkError(error: any): boolean {
        return !error.response && error.request;
    }

    getErrorMessage(error: any): string {
        if (this.isNetworkError(error)) {
            return 'Network error. Please check your connection.';
        }

        if (error.response?.data?.detail) {
            return error.response.data.detail;
        }

        if (error.response?.data?.message) {
            return error.response.data.message;
        }

        return error.message || 'An unexpected error occurred.';
    }
}

export const apiClient = new ApiClient();