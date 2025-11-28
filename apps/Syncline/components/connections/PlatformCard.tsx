import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Platform, Connection } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { theme } from '../../src/theme';
import { MaterialCommunityIcons, FontAwesome5, Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

// Map platforms to proper icons and gradients
const PLATFORM_CONFIG: Record<Platform, {
    icon: string;
    iconFamily: 'MaterialCommunityIcons' | 'FontAwesome5' | 'Ionicons';
    label: string;
    gradient: [string, string];
}> = {
    gmail: {
        icon: 'gmail',
        iconFamily: 'MaterialCommunityIcons',
        label: 'Gmail',
        gradient: ['#EA4335', '#C5221F']
    },
    slack: {
        icon: 'slack',
        iconFamily: 'FontAwesome5',
        label: 'Slack',
        gradient: ['#4A154B', '#611f69']
    },
    discord: {
        icon: 'discord',
        iconFamily: 'MaterialCommunityIcons',
        label: 'Discord',
        gradient: ['#5865F2', '#404EBC']
    },
    telegram: {
        icon: 'telegram',
        iconFamily: 'FontAwesome5',
        label: 'Telegram',
        gradient: ['#0088CC', '#006699']
    },
    twitter: {
        icon: 'twitter',
        iconFamily: 'FontAwesome5',
        label: 'Twitter',
        gradient: ['#1DA1F2', '#0C85D0']
    },
    whatsapp: {
        icon: 'whatsapp',
        iconFamily: 'FontAwesome5',
        label: 'WhatsApp',
        gradient: ['#25D366', '#1DA851']
    },
};

const IconComponent = ({
    family,
    name,
    size,
    color
}: {
    family: 'MaterialCommunityIcons' | 'FontAwesome5' | 'Ionicons';
    name: string;
    size: number;
    color: string;
}) => {
    switch (family) {
        case 'MaterialCommunityIcons':
            return <MaterialCommunityIcons name={name as any} size={size} color={color} />;
        case 'FontAwesome5':
            return <FontAwesome5 name={name as any} size={size} color={color} />;
        case 'Ionicons':
            return <Ionicons name={name as any} size={size} color={color} />;
    }
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
    const config = PLATFORM_CONFIG[platform];
    const isConnected = connection?.status === 'active';

    return (
        <Card padding="m" shadow="lg" style={styles.cardContainer}>
            <LinearGradient
                colors={config.gradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.gradientHeader}
            >
                <View style={styles.iconContainer}>
                    <IconComponent
                        family={config.iconFamily}
                        name={config.icon}
                        size={32}
                        color="white"
                    />
                </View>
                <View style={styles.headerContent}>
                    <Text style={styles.platformLabel}>{config.label}</Text>
                    {isConnected && (
                        <Badge variant="success" size="sm">Connected</Badge>
                    )}
                </View>
            </LinearGradient>

            <View style={styles.cardContent}>
                <Text style={styles.statusText}>
                    {isConnected
                        ? `Last synced ${connection?.connected_at ? new Date(connection.connected_at).toLocaleDateString() : 'recently'}`
                        : 'Not connected'}
                </Text>

                <TouchableOpacity
                    style={[
                        styles.button,
                        isConnected ? styles.disconnectButton : styles.connectButton
                    ]}
                    onPress={isConnected ? onDisconnect : onConnect}
                    activeOpacity={0.8}
                >
                    <Text style={[styles.buttonText, isConnected && styles.disconnectText]}>
                        {isConnected ? 'Disconnect' : 'Connect'}
                    </Text>
                </TouchableOpacity>
            </View>
        </Card>
    );
};

const styles = StyleSheet.create({
    cardContainer: {
        marginBottom: theme.spacing.m,
        padding: 0,
        overflow: 'hidden',
    },
    gradientHeader: {
        padding: theme.spacing.l,
        flexDirection: 'row',
        alignItems: 'center',
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
        gap: theme.spacing.xs,
    },
    platformLabel: {
        ...theme.typography.h3,
        color: 'white',
    },
    cardContent: {
        padding: theme.spacing.l,
        gap: theme.spacing.m,
    },
    statusText: {
        ...theme.typography.bodySmall,
    },
    button: {
        paddingVertical: theme.spacing.m,
        borderRadius: theme.borderRadius.m,
        alignItems: 'center',
    },
    connectButton: {
        backgroundColor: theme.colors.primary,
    },
    disconnectButton: {
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    buttonText: {
        ...theme.typography.button,
        color: theme.colors.white,
    },
    disconnectText: {
        color: theme.colors.textSecondary,
    },
});
