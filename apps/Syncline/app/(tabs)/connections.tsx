import React, { useEffect, useState } from 'react';
import { StyleSheet, View, ScrollView, Alert, Text, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { PlatformCard } from '../../components/connections/PlatformCard';
import { connectionsAPI } from '../../src/api/endpoints/connections';
import { Platform, Connection } from '../../src/types';
import { useAuth } from '../../src/contexts/AuthContext';
import { theme } from '../../src/theme';

import { ConnectionModal } from '../../components/ConnectionModal/ConnectionModal';

const PLATFORMS: Platform[] = ['gmail', 'slack', 'discord', 'telegram', 'twitter', 'whatsapp'];

export default function ConnectionsScreen() {
    const router = useRouter();
    const [connections, setConnections] = useState<Connection[]>([]);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
    const [loading, setLoading] = useState(true);

    // Get user from auth context - no fallback, require authentication
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();

    useEffect(() => {
        if (!authLoading && isAuthenticated && user?.id) {
            loadConnections();
        } else if (!authLoading && !isAuthenticated) {
            setLoading(false);
        }
    }, [user?.id, isAuthenticated, authLoading]);

    const loadConnections = async () => {
        if (!user?.id) return;

        try {
            setLoading(true);
            const data = await connectionsAPI.listConnections(user.id);
            const formattedConnections = (data.connections || []).map(conn => ({
                ...conn,
                platform: conn.platform as Platform,
                status: conn.status as Connection['status']
            }));
            setConnections(formattedConnections);
        } catch (error) {
            console.error('Failed to load connections:', error);
            setConnections([]);
        } finally {
            setLoading(false);
        }
    };

    const handleConnectPress = (platform: Platform) => {
        setSelectedPlatform(platform);
        setModalVisible(true);
    };

    const handleConnectionComplete = (connectionId: string) => {
        console.log('Connected:', connectionId);
        loadConnections();
        setModalVisible(false);
        setSelectedPlatform(null);
    };

    const handleDisconnect = async (connectionId: string) => {
        try {
            await connectionsAPI.disconnect(connectionId);
            loadConnections();
            Alert.alert('Success', 'Disconnected successfully');
        } catch (error: any) {
            // Handle 404 errors gracefully - connection already doesn't exist
            if (error.response?.status === 404) {
                // Connection not found means it's already disconnected
                loadConnections(); // Refresh to clear stale UI state
                Alert.alert('Success', 'Already disconnected');
            } else {
                console.error('Disconnect error:', error);
                Alert.alert('Error', 'Failed to disconnect');
            }
        }
    };

    const handleLogin = () => {
        router.replace('/(auth)/login');
    };

    // Show loading while checking auth
    if (authLoading || loading) {
        return (
            <View style={styles.centerContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
                <Text style={styles.loadingText}>Loading...</Text>
            </View>
        );
    }

    // Not authenticated - show login prompt
    if (!isAuthenticated || !user?.id) {
        return (
            <View style={styles.centerContainer}>
                <Ionicons name="lock-closed-outline" size={64} color={theme.colors.textSecondary} />
                <Text style={styles.authTitle}>Sign in Required</Text>
                <Text style={styles.authSubtitle}>
                    Please sign in to manage your platform connections
                </Text>
                <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
                    <Text style={styles.loginButtonText}>Sign In</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <ScrollView style={styles.container}>
            <View style={styles.content}>
                {PLATFORMS.map((platform) => {
                    const connection = connections.find(c => c.platform === platform);

                    return (
                        <PlatformCard
                            key={platform}
                            platform={platform}
                            connection={connection}
                            onConnect={() => handleConnectPress(platform)}
                            onDisconnect={() => connection && handleDisconnect(connection.id)}
                        />
                    );
                })}
            </View>

            {selectedPlatform && user?.id && (
                <ConnectionModal
                    visible={modalVisible}
                    platform={selectedPlatform}
                    userId={user.id}
                    onClose={() => {
                        setModalVisible(false);
                        setSelectedPlatform(null);
                    }}
                    onConnect={handleConnectionComplete}
                />
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    content: {
        padding: 16,
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 32,
        backgroundColor: theme.colors.background,
    },
    loadingText: {
        marginTop: 16,
        ...theme.typography.body,
        color: theme.colors.textSecondary,
    },
    authTitle: {
        marginTop: 16,
        ...theme.typography.h2,
        color: theme.colors.text,
    },
    authSubtitle: {
        marginTop: 8,
        ...theme.typography.body,
        color: theme.colors.textSecondary,
        textAlign: 'center',
    },
    loginButton: {
        marginTop: 24,
        paddingHorizontal: 32,
        paddingVertical: 14,
        backgroundColor: theme.colors.primary,
        borderRadius: theme.borderRadius.m,
    },
    loginButtonText: {
        ...theme.typography.button,
        color: 'white',
    },
});

