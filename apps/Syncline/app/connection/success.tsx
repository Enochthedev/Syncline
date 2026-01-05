import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';

/**
 * Handle successful OAuth connection callback
 * 
 * Deep link: syncline://connection/success?platform=gmail&connection_id=xxx
 */
export default function ConnectionSuccessScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ platform?: string; connection_id?: string }>();
    const [countdown, setCountdown] = useState(3);

    const platform = params.platform || 'unknown';
    const connectionId = params.connection_id;

    useEffect(() => {
        // Auto redirect after 3 seconds
        const timer = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    clearInterval(timer);
                    // Navigate to connections tab
                    router.replace('/(tabs)/connections');
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [router]);

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

    return (
        <View style={styles.container}>
            <View style={styles.content}>
                <View style={styles.iconContainer}>
                    <Ionicons name="checkmark-circle" size={80} color="#4CAF50" />
                </View>

                <Text style={styles.title}>Connected!</Text>

                <Text style={styles.subtitle}>
                    Successfully connected to {getPlatformName(platform)}
                </Text>

                <Text style={styles.countdownText}>
                    Redirecting in {countdown}...
                </Text>

                <ActivityIndicator
                    size="small"
                    color={theme.colors.primary}
                    style={styles.loader}
                />
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
        marginBottom: 32,
    },
    countdownText: {
        fontSize: 14,
        color: theme.colors.textTertiary,
        marginBottom: 16,
    },
    loader: {
        marginTop: 8,
    },
});
