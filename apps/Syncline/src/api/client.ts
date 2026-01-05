import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage keys (must match AuthContext)
const AUTH_TOKEN_KEY = '@syncline/auth_token';
const REFRESH_TOKEN_KEY = '@syncline/refresh_token';

// Helper to get the local IP address for development
const getBaseUrl = () => {
    if (!__DEV__) {
        return 'https://api.syncline.com/api/v1'; // Production URL
    }

    // For Android Emulator
    if (Platform.OS === 'android') {
        return 'http://10.0.2.2:8000/api/v1';
    }

    // For iOS Simulator or physical device via LAN
    const debuggerHost = Constants.expoConfig?.hostUri;
    const localhost = debuggerHost?.split(':')[0] || 'localhost';
    return `http://${localhost}:8000/api/v1`;
};

export const API_BASE_URL = getBaseUrl();

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000,
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token!);
        }
    });
    failedQueue = [];
};

// Check if token is expired
const isTokenExpired = (token: string): boolean => {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        // Add 30 second buffer
        return payload.exp * 1000 < Date.now() + 30000;
    } catch {
        return true;
    }
};

// Refresh the access token
const refreshAccessToken = async (): Promise<string | null> => {
    try {
        const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
        if (!refreshToken) {
            return null;
        }

        // Make refresh request without using interceptors
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Save new tokens
        await AsyncStorage.setItem(AUTH_TOKEN_KEY, access_token);
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);

        console.log('API Client: Token refreshed successfully');
        return access_token;
    } catch (error) {
        console.error('API Client: Token refresh failed:', error);
        // Clear tokens on refresh failure
        await AsyncStorage.multiRemove([AUTH_TOKEN_KEY, REFRESH_TOKEN_KEY]);
        return null;
    }
};

// Request interceptor - add auth header
apiClient.interceptors.request.use(async (config) => {
    let token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);

    // Check if token is expired and refresh if needed
    if (token && isTokenExpired(token)) {
        console.log('API Client: Token expired, refreshing...');
        const newToken = await refreshAccessToken();
        if (newToken) {
            token = newToken;
        } else {
            token = null;
        }
    }

    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
});

// Response interceptor - handle 401 errors with token refresh
apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
            // Don't attempt to refresh token if the failed request was for login or refresh
            if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
                return Promise.reject(error);
            }

            if (isRefreshing) {
                // Wait for the refresh to complete
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return apiClient(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const newToken = await refreshAccessToken();

                if (newToken) {
                    processQueue(null, newToken);
                    originalRequest.headers.Authorization = `Bearer ${newToken}`;
                    return apiClient(originalRequest);
                } else {
                    processQueue(new Error('Token refresh failed'), null);
                    // Redirect to login will be handled by the app
                    return Promise.reject(error);
                }
            } catch (refreshError) {
                processQueue(refreshError, null);
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        // Handle timeout errors
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
            console.warn('API request timed out:', originalRequest?.url);
        }

        return Promise.reject(error);
    }
);
