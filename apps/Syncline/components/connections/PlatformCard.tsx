import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions, Alert } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Platform, Connection } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { theme } from '../../src/theme';
import { GmailIcon } from '../GmailIcon/GmailIcon';
import { SlackIcon } from '../SlackIcon/SlackIcon';
import { DiscordIcon } from '../DiscordIcon/DiscordIcon';
import { TelegramIcon } from '../TelegramIcon/TelegramIcon';
import { TwitterIcon } from '../TwitterIcon/TwitterIcon';
import { WhatsAppIcon } from '../WhatsAppIcon/WhatsAppIcon';

const { width } = Dimensions.get('window');

// Map platforms to proper icons and gradients
const PLATFORM_CONFIG: Record<Platform, {
    icon: React.FC<{ size?: number }>;
    label: string;
    gradient: [string, string];
    connectedGradient: [string, string];
}> = {
    gmail: {
        icon: GmailIcon,
        label: 'Gmail',
        gradient: ['#EA4335', '#C5221F'],
        connectedGradient: ['#EA4335', '#C5221F'],
    },
    slack: {
        icon: SlackIcon,
        label: 'Slack',
        gradient: ['#4A154B', '#611f69'],
        connectedGradient: ['#4A154B', '#611f69'],
    },
    discord: {
        icon: DiscordIcon,
        label: 'Discord',
        gradient: ['#5865F2', '#404EBC'],
        connectedGradient: ['#5865F2', '#404EBC'],
    },
    telegram: {
        icon: TelegramIcon,
        label: 'Telegram',
        gradient: ['#0088CC', '#006699'],
        connectedGradient: ['#0088CC', '#006699'],
    },
    twitter: {
        icon: TwitterIcon,
        label: 'X (Twitter)',
        gradient: ['#000000', '#14171A'],
        connectedGradient: ['#000000', '#14171A'],
    },
    whatsapp: {
        icon: WhatsAppIcon,
        label: 'WhatsApp',
        gradient: ['#25D366', '#1DA851'],
        connectedGradient: ['#25D366', '#1DA851'],
    },
};

interface PlatformCardProps {
    platform: Platform;
    connection?: Connection;
    onConnect: () => void;
    onDisconnect: () => void;
}

export const PlatformCard: React.FC<PlatformCardProps> = ({
    platform,
    connection,
    onConnect,
    onDisconnect
}) => {
    const [disconnecting, setDisconnecting] = useState(false);
    const config = PLATFORM_CONFIG[platform];
    const isConnected = connection?.status === 'active';
    const IconComp = config.icon;

    const handleDisconnect = () => {
        Alert.alert(
            `Disconnect ${config.label}?`,
            `This will stop syncing messages from ${config.label}. You can reconnect anytime.`,
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Disconnect',
                    style: 'destructive',
                    onPress: async () => {
                        setDisconnecting(true);
                        try {
                            await onDisconnect();
                        } finally {
                            setDisconnecting(false);
                        }
                    }
                }
            ]
        );
    };

    const formatLastSync = () => {
        if (!connection?.last_sync_at && !connection?.updated_at) {
            return 'Just connected';
        }
        const date = new Date(connection?.last_sync_at || connection?.updated_at || '');
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffHours < 1) return 'Synced just now';
        if (diffHours < 24) return `Synced ${diffHours}h ago`;
        if (diffDays < 7) return `Synced ${diffDays}d ago`;
        return `Synced ${date.toLocaleDateString()}`;
    };

    return (
        <Card shadow="md" style={styles.cardContainer}>
            {/* Header with gradient */}
            <LinearGradient
                colors={isConnected ? config.connectedGradient : ['#6b7280', '#4b5563']}
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
                            <Text style={styles.notConnectedText}>Not connected</Text>
                        )}
                    </View>
                </View>
            </LinearGradient>

            {/* Content area */}
            <View style={[styles.cardContent, isConnected && styles.connectedContent]}>
                {isConnected ? (
                    <>
                        <View style={styles.statsRow}>
                            <View style={styles.statItem}>
                                <Ionicons name="sync-outline" size={18} color={theme.colors.textSecondary} />
                                <Text style={styles.statText}>{formatLastSync()}</Text>
                            </View>
                        </View>

                        <View style={styles.buttonRow}>
                            <TouchableOpacity
                                style={styles.manageButton}
                                onPress={onConnect}
                                activeOpacity={0.7}
                            >
                                <Ionicons name="settings-outline" size={18} color={theme.colors.primary} />
                                <Text style={styles.manageButtonText}>Manage</Text>
                            </TouchableOpacity>

                            <TouchableOpacity
                                style={styles.disconnectButton}
                                onPress={handleDisconnect}
                                disabled={disconnecting}
                                activeOpacity={0.7}
                            >
                                <Ionicons name="unlink-outline" size={18} color={theme.colors.error} />
                                <Text style={styles.disconnectButtonText}>
                                    {disconnecting ? 'Disconnecting...' : 'Disconnect'}
                                </Text>
                            </TouchableOpacity>
                        </View>
                    </>
                ) : (
                    <>
                        <Text style={styles.descriptionText}>
                            Connect to sync your messages and conversations
                        </Text>

                        <TouchableOpacity
                            style={styles.connectButton}
                            onPress={onConnect}
                            activeOpacity={0.8}
                        >
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
};

const styles = StyleSheet.create({
    cardContainer: {
        marginBottom: theme.spacing.m,
        overflow: 'hidden',
        borderRadius: theme.borderRadius.l,
        padding: 0,
    },
    gradientHeader: {
        padding: theme.spacing.l,
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
        borderRadius: theme.borderRadius.m,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: theme.spacing.m,
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
        padding: theme.spacing.l,
        backgroundColor: theme.colors.surface,
    },
    connectedContent: {
        backgroundColor: theme.colors.background,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    statsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: theme.spacing.m,
    },
    statItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    statText: {
        color: theme.colors.textSecondary,
        fontSize: 13,
    },
    buttonRow: {
        flexDirection: 'row',
        gap: theme.spacing.m,
    },
    manageButton: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        paddingVertical: 12,
        borderRadius: theme.borderRadius.m,
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
        borderRadius: theme.borderRadius.m,
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
        marginBottom: theme.spacing.m,
        textAlign: 'center',
    },
    connectButton: {
        overflow: 'hidden',
        borderRadius: theme.borderRadius.m,
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
