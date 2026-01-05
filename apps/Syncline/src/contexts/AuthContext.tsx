/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app:
 * - Current user info
 * - Login/logout functions
 * - Token management
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI, TokenResponse } from '../api/endpoints/auth';
import { User } from '../types';

// Storage keys
const AUTH_TOKEN_KEY = '@syncline/auth_token';
const REFRESH_TOKEN_KEY = '@syncline/refresh_token';
const USER_DATA_KEY = '@syncline/user_data';

// Context types
interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (email: string, username: string, password: string, fullName?: string) => Promise<void>;
    logout: () => Promise<void>;
    getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Load saved auth state on mount
    useEffect(() => {
        loadAuthState();
    }, []);

    const loadAuthState = async () => {
        try {
            console.log('AuthContext: Loading auth state...');
            const [token, userData] = await Promise.all([
                AsyncStorage.getItem(AUTH_TOKEN_KEY),
                AsyncStorage.getItem(USER_DATA_KEY),
            ]);

            console.log('AuthContext: Token exists:', !!token);
            console.log('AuthContext: User data exists:', !!userData);

            if (token && userData) {
                const user = JSON.parse(userData);
                setUser(user);
                console.log('AuthContext: User restored:', user.email || user.id);
            } else {
                console.log('AuthContext: No saved auth state found');
            }
        } catch (error) {
            console.error('Failed to load auth state:', error);
        } finally {
            setIsLoading(false);
            console.log('AuthContext: Auth state loading completed');
        }
    };

    const saveAuthState = async (tokens: TokenResponse, userData: User) => {
        await Promise.all([
            AsyncStorage.setItem(AUTH_TOKEN_KEY, tokens.access_token),
            AsyncStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token),
            AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(userData)),
        ]);
    };

    const clearAuthState = async () => {
        await Promise.all([
            AsyncStorage.removeItem(AUTH_TOKEN_KEY),
            AsyncStorage.removeItem(REFRESH_TOKEN_KEY),
            AsyncStorage.removeItem(USER_DATA_KEY),
        ]);
    };

    const login = async (username: string, password: string) => {
        try {
            const tokens = await authAPI.login(username, password);

            // Decode user info from token (or fetch from /me endpoint)
            // For now, create user from token payload
            const payload = JSON.parse(atob(tokens.access_token.split('.')[1]));
            const userData: User = {
                id: payload.sub,
                email: payload.email,
                full_name: payload.full_name,
            };

            await saveAuthState(tokens, userData);
            setUser(userData);
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    };

    const register = async (email: string, username: string, password: string, fullName?: string) => {
        try {
            const newUser = await authAPI.register(email, username, password, fullName);

            // After registration, log them in
            await login(username, password);
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    };

    const logout = async () => {
        try {
            console.log('AuthContext: Starting logout...');
            await clearAuthState();
            setUser(null);
            console.log('AuthContext: Logout completed, user cleared');
        } catch (error) {
            console.error('Logout failed:', error);
            throw error;
        }
    };

    const getAccessToken = async (): Promise<string | null> => {
        try {
            const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);

            if (!token) return null;

            // Check if token is expired
            const payload = JSON.parse(atob(token.split('.')[1]));
            const isExpired = payload.exp * 1000 < Date.now();

            if (isExpired) {
                // Try to refresh
                const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
                if (refreshToken) {
                    try {
                        const newTokens = await authAPI.refreshToken(refreshToken);
                        await AsyncStorage.setItem(AUTH_TOKEN_KEY, newTokens.access_token);
                        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, newTokens.refresh_token);
                        return newTokens.access_token;
                    } catch {
                        // Refresh failed, need to re-login
                        await clearAuthState();
                        setUser(null);
                        return null;
                    }
                }
                return null;
            }

            return token;
        } catch (error) {
            console.error('Get access token failed:', error);
            return null;
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                isLoading,
                login,
                register,
                logout,
                getAccessToken,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

// Hook for using auth context
export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};

export default AuthContext;
