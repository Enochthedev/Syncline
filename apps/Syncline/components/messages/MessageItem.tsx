import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Message, Platform } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { theme } from '../../src/theme';

interface MessageItemProps {
    message: Message;
    onPress: () => void;
}

const getPlatformColor = (platform: Platform) => {
    const colors: Record<Platform, string> = {
        gmail: '#EA4335',
        slack: '#4A154B',
        discord: '#5865F2',
        telegram: '#0088CC',
        twitter: '#1DA1F2',
        whatsapp: '#25D366',
    };
    return colors[platform] || theme.colors.textSecondary;
};

export const MessageItem: React.FC<MessageItemProps> = ({ message, onPress }) => {
    const platformColor = getPlatformColor(message.platform);
    const date = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // TODO: Animation - Slide in on new message
    // TODO: Animation - Highlight on search match

    return (
        <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
            <Card padding="m" shadow="sm" style={styles.container}>
                <View style={styles.header}>
                    <View style={[styles.avatar, { backgroundColor: platformColor + '20' }]}>
                        <Text style={[styles.avatarText, { color: platformColor }]}>
                            {message.sender[0].toUpperCase()}
                        </Text>
                    </View>

                    <View style={styles.contentContainer}>
                        <View style={styles.headerRow}>
                            <Text style={styles.sender}>{message.sender}</Text>
                            <Text style={styles.time}>{date}</Text>
                        </View>

                        <Text style={styles.content} numberOfLines={2}>
                            {message.content}
                        </Text>

                        <View style={styles.footer}>
                            <Badge variant="secondary" size="sm">
                                {message.platform}
                            </Badge>

                            {message.has_attachments && (
                                <Text style={styles.attachmentIcon}>📎</Text>
                            )}
                        </View>
                    </View>
                </View>
            </Card>
        </TouchableOpacity>
    );
};

const styles = StyleSheet.create({
    container: {
        marginBottom: theme.spacing.s,
    },
    header: {
        flexDirection: 'row',
    },
    avatar: {
        width: 40,
        height: 40,
        borderRadius: theme.borderRadius.full,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: theme.spacing.m,
    },
    avatarText: {
        fontWeight: 'bold',
        fontSize: 16,
    },
    contentContainer: {
        flex: 1,
        gap: theme.spacing.xs,
    },
    headerRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    sender: {
        ...theme.typography.h4,
    },
    time: {
        ...theme.typography.caption,
    },
    content: {
        ...theme.typography.body,
        color: theme.colors.textSecondary,
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.s,
    },
    attachmentIcon: {
        fontSize: 14,
    },
});
