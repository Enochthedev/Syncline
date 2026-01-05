/**
 * Authentication Guard Component
 * 
 * Handles navigation based on authentication state:
 * - Redirects to login if not authenticated
 * - Redirects to main app if authenticated
 */

import React, { useEffect } from 'react';
import { useRouter, useSegments } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';

interface AuthGuardProps {
    children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();
    const segments = useSegments();

    useEffect(() => {
        if (isLoading) return; // Wait for auth state to load

        const inAuthGroup = segments[0] === '(auth)';

        // Only redirect if we're not already in the correct place
        if (!isAuthenticated && !inAuthGroup) {
            // User is not authenticated and not in auth screens, redirect to login
            console.log('AuthGuard: Redirecting to login - not authenticated');
            router.replace('/(auth)/login');
        } else if (isAuthenticated && inAuthGroup) {
            // User is authenticated but in auth screens, redirect to main app
            console.log('AuthGuard: Redirecting to main app - authenticated');
            router.replace('/(tabs)');
        }
    }, [isAuthenticated, isLoading, segments, router]);

    return <>{children}</>;
};