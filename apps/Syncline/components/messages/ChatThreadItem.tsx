import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ChatThread } from '../../src/api/endpoints/messages';
import { Platform, PLATFORM_COLORS } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { theme } from '../../src/theme';

interface ChatThreadItemProps {
    thread: ChatThread;
    onPress: () => void;
    onLinkContact?: () => void;
}

const getPlatformColor = (platform: string) => {
    const normalizedPlatform = platform.toLowerCase() as Platform;
    return PLATFORM_COLORS[normalizedPlatform] || theme.colors.textSecondary;
};

const formatTime = (timestamp?: string) => {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    
    if (diffHours < 1) {
        return 'now';
    } else if (diffHours < 24) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays < 7) {
        return date.toLocaleDateString([], { weekday: 'short' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
};

export const ChatThreadItem: React.FC<ChatThreadItemProps> = ({ 
    thread, 
    onPress, 
    onLinkContact 
}) => {
    const platformColor = getPlatformColor(thread.platform);
    const timeStr = formatTime(thread.last_message_time);
    
    // Display name priority: contact_name > phone_number > platform
    const displayName = thread.contact_name || 
                       (thread.phone_number ? `${thread.phone_number}` : 
                        `${thread.platform} chat`);

    return (
        <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
            <Card padding="m" shadow="sm" style={styles.container}>
                <View style={styles.header}>
                    <View style={[styles.avatar, { backgroundColor: platformColor + '20' }]}>
                        <Text style={[styles.avatarText, { color: platformColor }]}>
                            {displayName[0].toUpperCase()}
                        </Text>
                    </View>

                    <View style={styles.contentContainer}>
                        <View style={styles.headerRow}>
                            <View style={styles.nameContainer}>
                                <Text style={styles.contactName} numberOfLines={1}>
                                    {displayName}
                                </Text>
                                {!thread.is_linked && thread.phone_number && (
                                    <TouchableOpacity 
                                        onPress={onLinkContact}
                                        style={styles.linkButton}
                                    >
                                        <Text style={styles.linkText}>Link</Text>
                                    </TouchableOpacity>
                                )}
                            </View>
                            <View style={styles.timeContainer}>
                                <Text style={styles.time}>{timeStr}</Text>
                                {thread.unread_count > 0 && (
                                    <View style={[styles.unreadBadge, { backgroundColor: platformColor }]}>
                                        <Text style={styles.unreadText}>
                                            {thread.unread_count > 99 ? '99+' : thread.unread_count}
                                        </Text>
                                    </View>
                                )}
                            </View>
                        </View>

                        <Text style={styles.lastMessage} numberOfLines={2}>
                            {thread.last_message || 'No messages yet'}
                        </Text>

                        <View style={styles.footer}>
                            <Badge variant="secondary" size="sm">
                                {thread.platform}
                            </Badge>
                            
                            {thread.phone_number && (
                                <Text style={styles.phoneNumber} numberOfLines={1}>
                                    {thread.phone_number}
                                </Text>
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
        width: 48,
        height: 48,
        borderRadius: theme.borderRadius.full,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: theme.spacing.m,
    },
    avatarText: {
        fontWeight: 'bold',
        fontSize: 18,
    },
    contentContainer: {
        flex: 1,
        gap: theme.spacing.xs,
    },
    headerRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    nameContainer: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.s,
    },
    contactName: {
        ...theme.typography.h4,
        flex: 1,
    },
    linkButton: {
        paddingHorizontal: theme.spacing.s,
        paddingVertical: theme.spacing.xs,
        backgroundColor: theme.colors.primary + '20',
        borderRadius: theme.borderRadius.sm,
    },
    linkText: {
        ...theme.typography.caption,
        color: theme.colors.primary,
        fontWeight: '600',
    },
    timeContainer: {
        alignItems: 'flex-end',
        gap: theme.spacing.xs,
    },
    time: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
    },
    unreadBadge: {
        minWidth: 20,
        height: 20,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: theme.spacing.xs,
    },
    unreadText: {
        ...theme.typography.caption,
        color: 'white',
        fontWeight: 'bold',
        fontSize: 11,
    },
    lastMessage: {
        ...theme.typography.body,
        color: theme.colors.textSecondary,
        lineHeight: 18,
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.s,
    },
    phoneNumber: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
        flex: 1,
    },
});