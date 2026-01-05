/**
 * Platform Connections - Screenshot Demo Version (Section 4.11.1)
 * 
 * Shows platform connection dashboard with dummy data for documentation screenshots.
 * Displays connected platforms with status indicators, sync timestamps, and message counts.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    ScrollView,
    Text,
    TouchableOpacity,
    Dimensions,
    useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_CONNECTIONS } from '../src/data/dummyData';
import { GmailIcon } from '../components/GmailIcon/GmailIcon';
import { SlackIcon } from '../components/SlackIcon/SlackIcon';
import { DiscordIcon } from '../components/DiscordIcon/DiscordIcon';
import { TelegramIcon } from '../components/TelegramIcon/TelegramIcon';
import { TwitterIcon } from '../components/TwitterIcon/TwitterIcon';
import { WhatsAppIcon } from '../components/WhatsAppIcon/WhatsAppIcon';

// Platform configuration with icons and gradients
const PLATFORM_CONFIG: Record<string, {
    icon: React.FC<{ size?: number }>;
    label: string;
    gradient: [string, string];
}> = {
    gmail: {
        icon: GmailIcon,
        label: 'Gmail',
        gradient: ['#EA4335', '#C5221F'],
    },
    slack: {
        icon: SlackIcon,
        label: 'Slack',
        gradient: ['#4A154B', '#611f69'],
    },
    discord: {
        icon: DiscordIcon,
        label: 'Discord',
        gradient: ['#5865F2', '#404EBC'],
    },
    telegram: {
        icon: TelegramIcon,
        label: 'Telegram',
        gradient: ['#0088CC', '#006699'],
    },
    twitter: {
        icon: TwitterIcon,
        label: 'X (Twitter)',
        gradient: ['#000000', '#14171A'],
    },
    whatsapp: {
        icon: WhatsAppIcon,
        label: 'WhatsApp',
        gradient: ['#25D366', '#1DA851'],
    },
};

export default function ConnectionsDemoScreen() {
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const isSmallScreen = width < 375;

    const formatLastSync = (lastSyncAt: string | null) => {
        if (!lastSyncAt) return null;
        const date = new Date(lastSyncAt);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minutes ago`;
        if (diffHours < 24) return `${diffHours} hours ago`;
        return date.toLocaleDateString();
    };

    const formatMessageCount = (count: number) => {
        if (count >= 1000) {
            return `${(count / 1000).toFixed(1)}K`;
        }
        return count.toString();
    };

    return (
        <ScrollView style={styles.container}>
            <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
                <Text style={[styles.headerTitle, isSmallScreen && { fontSize: 24 }]}>Platform Connections</Text>
                <Text style={styles.headerSubtitle}>
                    Connect your communication accounts to MESH
                </Text>
            </View>

            <View style={styles.content}>
                {DUMMY_CONNECTIONS.map((connection) => {
                    const config = PLATFORM_CONFIG[connection.platform];
                    if (!config) return null;

                    const isConnected = connection.status === 'active';
                    const IconComp = config.icon;

                    return (
                        <Card key={connection.id} shadow="md" style={styles.cardContainer}>
                            {/* Header with gradient */}
                            <LinearGradient
                                colors={isConnected ? config.gradient : ['#6b7280', '#4b5563']}
                                start={{ x: 0, y: 0 }}
                                end={{ x: 1, y: 1 }}
                                style={styles.gradientHeader}
                            >
                                {/* Connected indicator */}
                                {isConnected && (
                                    <View style={styles.connectedIndicator}>
                                        <Ionicons name="checkmark-circle" size={16} color="#fff" />
                                    </View>
                                )}

                                <View style={styles.iconContainer}>
                                    <IconComp size={32} />
                                </View>

                                <View style={styles.headerContent}>
                                    <Text style={styles.platformLabel}>{config.label}</Text>
                                    <View style={styles.statusBadgeRow}>
                                        {isConnected ? (
                                            <View style={styles.connectedBadge}>
                                                <View style={styles.pulsingDot} />
                                                <Text style={styles.connectedText}>Connected</Text>
                                            </View>
                                        ) : (
                                            <Text style={styles.notConnectedText}>Disconnected</Text>
                                        )}
                                    </View>
                                </View>
                            </LinearGradient>

                            {/* Content area */}
                            <View style={[styles.cardContent, isConnected && styles.connectedContent]}>
                                {isConnected ? (
                                    <>
                                        {/* Sync Stats */}
                                        <View style={styles.statsContainer}>
                                            <View style={styles.statRow}>
                                                <Ionicons name="sync-outline" size={16} color={theme.colors.textSecondary} />
                                                <Text style={styles.statText}>
                                                    Last synced: {formatLastSync(connection.last_sync_at)}
                                                </Text>
                                            </View>
                                            <View style={styles.statRow}>
                                                <Ionicons name="mail-outline" size={16} color={theme.colors.textSecondary} />
                                                <Text style={styles.statText}>
                                                    {formatMessageCount(connection.message_count)} messages synchronized
                                                </Text>
                                            </View>
                                            {connection.email && (
                                                <View style={styles.statRow}>
                                                    <Ionicons name="person-outline" size={16} color={theme.colors.textSecondary} />
                                                    <Text style={styles.statText}>{connection.email}</Text>
                                                </View>
                                            )}
                                            {connection.workspace && (
                                                <View style={styles.statRow}>
                                                    <Ionicons name="business-outline" size={16} color={theme.colors.textSecondary} />
                                                    <Text style={styles.statText}>{connection.workspace}</Text>
                                                </View>
                                            )}
                                        </View>

                                        {/* Action Buttons */}
                                        <View style={styles.buttonRow}>
                                            <TouchableOpacity style={styles.manageButton}>
                                                <Ionicons name="settings-outline" size={18} color={theme.colors.primary} />
                                                <Text style={styles.manageButtonText}>Manage</Text>
                                            </TouchableOpacity>

                                            <TouchableOpacity style={styles.disconnectButton}>
                                                <Ionicons name="unlink-outline" size={18} color={theme.colors.error} />
                                                <Text style={styles.disconnectButtonText}>Disconnect</Text>
                                            </TouchableOpacity>
                                        </View>
                                    </>
                                ) : (
                                    <>
                                        <Text style={styles.descriptionText}>
                                            Connect to sync your messages and conversations
                                        </Text>

                                        <TouchableOpacity style={styles.connectButton}>
                                            <LinearGradient
                                                colors={config.gradient}
                                                start={{ x: 0, y: 0 }}
                                                end={{ x: 1, y: 0 }}
                                                style={styles.connectButtonGradient}
                                            >
                                                <Ionicons name="add-circle-outline" size={20} color="#fff" />
                                                <Text style={styles.connectButtonText}>Connect {config.label}</Text>
                                            </LinearGradient>
                                        </TouchableOpacity>
                                    </>
                                )}
                            </View>
                        </Card>
                    );
                })}
            </View>

            <View style={{ height: insets.bottom + 40 }} />
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        padding: 20,
        paddingTop: 20,
        backgroundColor: theme.colors.background,
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 4,
    },
    headerSubtitle: {
        fontSize: 15,
        color: theme.colors.textSecondary,
    },
    content: {
        padding: 16,
    },
    cardContainer: {
        marginBottom: 16,
        overflow: 'hidden',
        borderRadius: 16,
        padding: 0,
    },
    gradientHeader: {
        padding: 20,
        flexDirection: 'row',
        alignItems: 'center',
        position: 'relative',
    },
    connectedIndicator: {
        position: 'absolute',
        top: 12,
        right: 12,
        backgroundColor: 'rgba(255,255,255,0.2)',
        borderRadius: 12,
        padding: 4,
    },
    iconContainer: {
        width: 56,
        height: 56,
        borderRadius: 12,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 16,
    },
    headerContent: {
        flex: 1,
        gap: 4,
    },
    platformLabel: {
        fontSize: 20,
        fontWeight: '700',
        color: 'white',
    },
    statusBadgeRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    connectedBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    pulsingDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#10b981',
    },
    connectedText: {
        color: 'rgba(255,255,255,0.9)',
        fontSize: 13,
        fontWeight: '500',
    },
    notConnectedText: {
        color: 'rgba(255,255,255,0.7)',
        fontSize: 13,
    },
    cardContent: {
        padding: 20,
        backgroundColor: theme.colors.surface,
    },
    connectedContent: {
        backgroundColor: theme.colors.background,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    statsContainer: {
        marginBottom: 16,
        gap: 8,
    },
    statRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    statText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    buttonRow: {
        flexDirection: 'row',
        gap: 12,
    },
    manageButton: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        paddingVertical: 12,
        borderRadius: 12,
        backgroundColor: theme.colors.surface,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    manageButtonText: {
        color: theme.colors.primary,
        fontWeight: '600',
        fontSize: 14,
    },
    disconnectButton: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        paddingVertical: 12,
        borderRadius: 12,
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 1,
        borderColor: 'rgba(239, 68, 68, 0.3)',
    },
    disconnectButtonText: {
        color: theme.colors.error,
        fontWeight: '600',
        fontSize: 14,
    },
    descriptionText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
        marginBottom: 16,
        textAlign: 'center',
    },
    connectButton: {
        overflow: 'hidden',
        borderRadius: 12,
    },
    connectButtonGradient: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 14,
        paddingHorizontal: 24,
    },
    connectButtonText: {
        color: '#fff',
        fontWeight: '600',
        fontSize: 15,
    },
});
