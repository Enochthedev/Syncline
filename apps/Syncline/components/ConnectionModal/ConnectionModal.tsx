import React, { useState } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    Alert,
    Linking,
} from 'react-native';
import { GmailIcon } from '../../components/GmailIcon/GmailIcon';
import { AppleIcon } from '../../components/AppleIcon/AppleIcon';
import { FacebookIcon } from '../../components/FacebookIcon/FacebookIcon';
import { SlackIcon } from '../../components/SlackIcon/SlackIcon';
import { DiscordIcon } from '../../components/DiscordIcon/DiscordIcon';
import { TelegramIcon } from '../../components/TelegramIcon/TelegramIcon';
import { TwitterIcon } from '../../components/TwitterIcon/TwitterIcon';
import { WhatsAppIcon } from '../../components/WhatsAppIcon/WhatsAppIcon';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Platform } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { connectionsAPI } from '../../src/api/endpoints/connections';

const IconMap: Record<Platform, React.FC<{ size?: number; color?: string }>> = {
    gmail: GmailIcon,
    slack: SlackIcon,
    discord: DiscordIcon,
    telegram: TelegramIcon,
    twitter: TwitterIcon,
    whatsapp: WhatsAppIcon,
};

const PLATFORM_CONFIG: Record<Platform, {
    icon: string;
    iconFamily: 'MaterialCommunityIcons' | 'FontAwesome5' | 'Ionicons';
    label: string;
    gradient: [string, string];
    description: string;
}> = {
    gmail: {
        icon: 'gmail',
        iconFamily: 'MaterialCommunityIcons',
        label: 'Gmail',
        gradient: ['#EA4335', '#C5221F'],
        description: 'Connect your Gmail account to sync emails and messages',
    },
    slack: {
        icon: 'slack',
        iconFamily: 'FontAwesome5',
        label: 'Slack',
        gradient: ['#4A154B', '#611f69'],
        description: 'Sync Slack workspaces and direct messages',
    },
    discord: {
        icon: 'discord',
        iconFamily: 'MaterialCommunityIcons',
        label: 'Discord',
        gradient: ['#5865F2', '#404EBC'],
        description: 'Connect Discord servers and channels',
    },
    telegram: {
        icon: 'telegram',
        iconFamily: 'FontAwesome5',
        label: 'Telegram',
        gradient: ['#0088CC', '#006699'],
        description: 'Sync Telegram chats and groups',
    },
    twitter: {
        icon: 'twitter',
        iconFamily: 'FontAwesome5',
        label: 'X (Twitter)',
        gradient: ['#000000', '#14171A'],
        description: 'Connect your X (formerly Twitter) account',
    },
    whatsapp: {
        icon: 'whatsapp',
        iconFamily: 'FontAwesome5',
        label: 'WhatsApp',
        gradient: ['#25D366', '#1DA851'],
        description: 'Sync WhatsApp conversations',
    },
};

interface ConnectionModalProps {
    visible: boolean;
    platform: Platform;
    userId: string;
    onClose: () => void;
    onConnect: (connectionId: string) => void;
}

export const ConnectionModal: React.FC<ConnectionModalProps> = ({
    visible,
    platform,
    userId,
    onClose,
    onConnect,
}) => {
    const config = PLATFORM_CONFIG[platform];
    const [loading, setLoading] = useState(false);

    const handleConnect = async () => {
        setLoading(true);

        try {
            // Step 1: Initiate OAuth flow with backend
            const response = await connectionsAPI.initiateConnection(
                platform,
                userId,
                // Deep link for mobile app to return after OAuth
                'syncline://oauth/callback'
            );

            // Step 2: Open OAuth URL in browser
            const canOpen = await Linking.canOpenURL(response.authorization_url);
            if (!canOpen) {
                throw new Error('Cannot open authorization URL');
            }

            await Linking.openURL(response.authorization_url);

            // User completes OAuth in browser/external app
            // The callback will be handled by deep linking
            // For now, close modal and show success
            onConnect(response.connection_id);
            onClose();

            Alert.alert(
                'OAuth Started',
                `Complete the ${config.label} authorization in your browser. The app will reconnect automatically.`,
                [{ text: 'OK' }]
            );

        } catch (error: any) {
            console.error('Connection error:', error);
            Alert.alert(
                'Connection Failed',
                error.message || `Failed to connect to ${config.label}. Please try again.`,
                [{ text: 'OK' }]
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.modalContainer}>
                    <LinearGradient
                        colors={config.gradient}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={styles.header}
                    >
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <Ionicons name="close" size={28} color="white" />
                        </TouchableOpacity>

                        <View style={styles.iconWrapper}>
                            {(() => {
                                const IconComp = IconMap[platform];
                                return <IconComp size={48} color="white" />;
                            })()}
                        </View>

                        <Text style={styles.modalTitle}>{config.label}</Text>
                        <Text style={styles.modalSubtitle}>{config.description}</Text>
                    </LinearGradient>

                    <ScrollView style={styles.content}>
                        <Card padding="l" style={styles.infoCard}>
                            <View style={styles.infoRow}>
                                <Ionicons name="checkmark-circle" size={24} color={theme.colors.success} />
                                <Text style={styles.infoText}>Auto-sync messages</Text>
                            </View>
                            <View style={styles.infoRow}>
                                <Ionicons name="checkmark-circle" size={24} color={theme.colors.success} />
                                <Text style={styles.infoText}>Smart search & summaries</Text>
                            </View>
                            <View style={styles.infoRow}>
                                <Ionicons name="checkmark-circle" size={24} color={theme.colors.success} />
                                <Text style={styles.infoText}>Secure & encrypted</Text>
                            </View>
                        </Card>

                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Connection Details</Text>
                            <Text style={styles.sectionText}>
                                Syncline will request access to your {config.label} account.
                                We only read messages to provide search and AI features.
                            </Text>
                        </View>

                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>What we access:</Text>
                            <View style={styles.permissionsList}>
                                <Badge variant="info" size="sm">Read messages</Badge>
                                <Badge variant="info" size="sm">Message metadata</Badge>
                                <Badge variant="info" size="sm">Contact info</Badge>
                            </View>
                        </View>
                    </ScrollView>

                    <View style={styles.footer}>
                        <TouchableOpacity
                            style={[styles.button, { backgroundColor: config.gradient[0] }]}
                            onPress={handleConnect}
                            disabled={loading}
                        >
                            <Text style={styles.buttonText}>
                                {loading ? 'Connecting...' : `Connect ${config.label}`}
                            </Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: theme.colors.overlay,
        justifyContent: 'flex-end',
    },
    modalContainer: {
        backgroundColor: theme.colors.background,
        borderTopLeftRadius: theme.borderRadius.xl,
        borderTopRightRadius: theme.borderRadius.xl,
        maxHeight: '90%',
        overflow: 'hidden',
    },
    header: {
        padding: theme.spacing.xl,
        paddingTop: theme.spacing.xxl,
        alignItems: 'center',
    },
    closeButton: {
        position: 'absolute',
        top: theme.spacing.m,
        right: theme.spacing.m,
        zIndex: 10,
    },
    iconWrapper: {
        width: 96,
        height: 96,
        borderRadius: theme.borderRadius.l,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: theme.spacing.m,
    },
    modalTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: theme.spacing.s,
    },
    modalSubtitle: {
        fontSize: 14,
        color: 'rgba(255, 255, 255, 0.9)',
        textAlign: 'center',
    },
    content: {
        padding: theme.spacing.l,
    },
    infoCard: {
        marginBottom: theme.spacing.l,
        gap: theme.spacing.m,
    },
    infoRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.m,
    },
    infoText: {
        ...theme.typography.body,
        flex: 1,
    },
    section: {
        marginBottom: theme.spacing.l,
    },
    sectionTitle: {
        ...theme.typography.h4,
        marginBottom: theme.spacing.s,
    },
    sectionText: {
        ...theme.typography.bodySmall,
        lineHeight: 20,
    },
    permissionsList: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: theme.spacing.s,
    },
    footer: {
        padding: theme.spacing.l,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    button: {
        padding: theme.spacing.m,
        borderRadius: theme.borderRadius.m,
        alignItems: 'center',
    },
    buttonText: {
        ...theme.typography.button,
        color: 'white',
    },
});
