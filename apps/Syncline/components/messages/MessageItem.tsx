import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Message, Platform } from '../../src/types';
import { Card } from '../Card/Card';
import { Badge } from '../Badge/Badge';
import { theme } from '../../src/theme';

interface MessageItemProps {
    message: Message;
    onPress: () => void;
    showSender?: boolean;
    isInChat?: boolean;
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

const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    
    if (diffHours < 1) {
        return 'now';
    } else if (diffHours < 24) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
};

export const MessageItem: React.FC<MessageItemProps> = ({ 
    message, 
    onPress, 
    showSender = true,
    isInChat = false 
}) => {
    const platformColor = getPlatformColor(message.platform);
    const timeStr = formatTime(message.timestamp);

    // Clean sender name - remove Matrix IDs and show readable names
    const cleanSender = (sender: string) => {
        // If it's a Matrix ID like @whatsapp_1234567890:localhost
        if (sender.includes('@whatsapp_') && sender.includes(':')) {
            const phoneMatch = sender.split('@whatsapp_')[1]?.split(':')[0];
            if (phoneMatch) {
                return `+${phoneMatch}`;
            }
        }
        
        // If it's already a clean name, return as is
        if (!sender.includes('@') || sender.includes(' ')) {
            return sender;
        }
        
        // Fallback for other Matrix-style IDs
        return sender.split('@')[0] || sender;
    };

    const displaySender = cleanSender(message.sender);

    return (
        <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
            <Card 
                padding="m" 
                shadow="sm" 
                style={[
                    styles.container,
                    isInChat && styles.chatContainer
                ]}
            >
                <View style={styles.header}>
                    {showSender && (
                        <View style={[styles.avatar, { backgroundColor: platformColor + '20' }]}>
                            <Text style={[styles.avatarText, { color: platformColor }]}>
                                {displaySender[0]?.toUpperCase() || '?'}
                            </Text>
                        </View>
                    )}

                    <View style={[styles.contentContainer, !showSender && styles.contentFullWidth]}>
                        {showSender && (
                            <View style={styles.headerRow}>
                                <Text style={styles.sender} numberOfLines={1}>
                                    {displaySender}
                                </Text>
                                <Text style={styles.time}>{timeStr}</Text>
                            </View>
                        )}

                        <Text 
                            style={[
                                styles.content,
                                !showSender && styles.contentNoSender
                            ]} 
                            numberOfLines={isInChat ? undefined : 2}
                        >
                            {message.content}
                        </Text>

                        <View style={styles.footer}>
                            <Badge variant="secondary" size="sm">
                                {message.platform}
                            </Badge>

                            {message.has_attachments && (
                                <Text style={styles.attachmentIcon}>📎</Text>
                            )}
                            
                            {!showSender && (
                                <Text style={styles.timeFooter}>{timeStr}</Text>
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
    chatContainer: {
        marginBottom: theme.spacing.xs,
        backgroundColor: theme.colors.surface,
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
    contentFullWidth: {
        marginLeft: 0,
    },
    headerRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    sender: {
        ...theme.typography.h4,
        flex: 1,
    },
    time: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
    },
    content: {
        ...theme.typography.body,
        color: theme.colors.text,
        lineHeight: 20,
    },
    contentNoSender: {
        ...theme.typography.body,
        marginBottom: theme.spacing.xs,
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.s,
    },
    attachmentIcon: {
        fontSize: 14,
    },
    timeFooter: {
        ...theme.typography.caption,
        color: theme.colors.textSecondary,
        marginLeft: 'auto',
    },
});
