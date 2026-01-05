import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';

/**
 * Handle failed OAuth connection callback
 * 
 * Deep link: syncline://connection/error?platform=gmail&error=xxx
 */
export default function ConnectionErrorScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ platform?: string; error?: string }>();

    const platform = params.platform || 'unknown';
    const error = params.error || 'Unknown error occurred';

    const getPlatformName = (p: string) => {
        const names: Record<string, string> = {
            gmail: 'Gmail',
            google_chat: 'Google Chat',
            slack: 'Slack',
            linkedin: 'LinkedIn',
            discord: 'Discord',
            whatsapp: 'WhatsApp',
            telegram: 'Telegram',
        };
        return names[p] || p;
    };

    const getErrorMessage = (err: string) => {
        const messages: Record<string, string> = {
            'access_denied': 'You denied access to your account.',
            'invalid_state': 'The connection request expired. Please try again.',
            'token_exchange_failed': 'Failed to complete authentication. Please try again.',
        };
        return messages[err] || err;
    };

    const handleRetry = () => {
        router.replace('/(tabs)/connections');
    };

    const handleBack = () => {
        router.back();
    };

    return (
        <View style={styles.container}>
            <View style={styles.content}>
                <View style={styles.iconContainer}>
                    <Ionicons name="close-circle" size={80} color="#F44336" />
                </View>

                <Text style={styles.title}>Connection Failed</Text>

                <Text style={styles.subtitle}>
                    Could not connect to {getPlatformName(platform)}
                </Text>

                <View style={styles.errorBox}>
                    <Text style={styles.errorText}>
                        {getErrorMessage(error)}
                    </Text>
                </View>

                <TouchableOpacity style={styles.retryButton} onPress={handleRetry}>
                    <Ionicons name="refresh" size={20} color="#FFFFFF" />
                    <Text style={styles.retryButtonText}>Try Again</Text>
                </TouchableOpacity>

                <TouchableOpacity style={styles.backButton} onPress={handleBack}>
                    <Text style={styles.backButtonText}>Go Back</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
        justifyContent: 'center',
        alignItems: 'center',
    },
    content: {
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    iconContainer: {
        marginBottom: 24,
    },
    title: {
        fontSize: 28,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    subtitle: {
        fontSize: 16,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 20,
    },
    errorBox: {
        backgroundColor: '#FFEBEE',
        borderRadius: 12,
        padding: 16,
        marginBottom: 32,
        width: '100%',
    },
    errorText: {
        fontSize: 14,
        color: '#C62828',
        textAlign: 'center',
    },
    retryButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 32,
        paddingVertical: 14,
        borderRadius: 12,
        gap: 8,
        marginBottom: 16,
    },
    retryButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    backButton: {
        paddingHorizontal: 24,
        paddingVertical: 12,
    },
    backButtonText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
});
