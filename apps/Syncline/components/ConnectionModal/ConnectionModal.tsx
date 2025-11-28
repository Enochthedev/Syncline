import React, { useState } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    TextInput,
    ScrollView,
    Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Platform } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';

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
        label: 'Twitter',
        gradient: ['#1DA1F2', '#0C85D0'],
        description: 'Connect your Twitter/X account',
    },
    whatsapp: {
        icon: 'whatsapp',
        iconFamily: 'FontAwesome5',
        label: 'WhatsApp',
        gradient: ['#25D366', '#1DA851'],
        description: 'Sync WhatsApp conversations',
    },
};

const IconComponent = ({
    family,
    name,
    size,
    color,
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

interface ConnectionModalProps {
    visible: boolean;
    platform: Platform;
    onClose: () => void;
    onConnect: (credentials?: any) => void;
}

export const ConnectionModal: React.FC<ConnectionModalProps> = ({
    visible,
    platform,
    onClose,
    onConnect,
}) => {
    const config = PLATFORM_CONFIG[platform];
    const [loading, setLoading] = useState(false);

    const handleConnect = () => {
        setLoading(true);
        // Simulate connection
        setTimeout(() => {
            setLoading(false);
            onConnect();
            onClose();
            Alert.alert('Success', `Connected to ${config.label}!`);
        }, 1500);
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
                            <IconComponent
                                family={config.iconFamily}
                                name={config.icon}
                                size={48}
                                color="white"
                            />
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
