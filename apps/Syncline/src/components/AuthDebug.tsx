/**
 * Authentication Debug Component
 * 
 * Shows current auth state for debugging
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useAuth } from '../contexts/AuthContext';
import { useSegments } from 'expo-router';

export const AuthDebug: React.FC = () => {
    const { user, isAuthenticated, isLoading } = useAuth();
    const segments = useSegments();

    if (!__DEV__) return null; // Only show in development

    return (
        <View style={styles.container}>
            <Text style={styles.title}>Auth Debug</Text>
            <Text style={styles.text}>Loading: {isLoading ? 'Yes' : 'No'}</Text>
            <Text style={styles.text}>Authenticated: {isAuthenticated ? 'Yes' : 'No'}</Text>
            <Text style={styles.text}>User: {user ? user.email || user.id : 'None'}</Text>
            <Text style={styles.text}>Segments: {segments.join('/')}</Text>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        top: 50,
        right: 10,
        backgroundColor: 'rgba(0,0,0,0.8)',
        padding: 8,
        borderRadius: 4,
        zIndex: 1000,
    },
    title: {
        color: 'white',
        fontWeight: 'bold',
        fontSize: 12,
    },
    text: {
        color: 'white',
        fontSize: 10,
    },
});