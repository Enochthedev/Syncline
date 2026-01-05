import React, { useEffect, useState } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    TextInput,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { contactsAPI } from '../../src/api/endpoints/contacts';
import { messagesAPI } from '../../src/api/endpoints/messages';

// Platform colors
const PLATFORM_COLORS: Record<string, string> = {
    'slack': '#4A154B',
    'gmail': '#EA4335',
    'discord': '#5865F2',
    'whatsapp': '#25D366',
    'twitter': '#1DA1F2',
    'telegram': '#0088cc',
};

const PLATFORM_ICONS: Record<string, string> = {
    'slack': 'logo-slack',
    'gmail': 'mail',
    'discord': 'logo-discord',
    'whatsapp': 'logo-whatsapp',
    'twitter': 'logo-twitter',
    'telegram': 'paper-plane',
};

interface UnifiedMessage {
    id: string;
    content: string;
    sender: string;
    platform: string;
    timestamp: string;
    isMe: boolean;
}

interface ThreadModalProps {
    visible: boolean;
    onClose: () => void;
    thread: {
        id: string;
        sender: string;
        role: string;
        platform: string;
        icon: string;
        summary: string;
        time: string;
        contactId?: string; // If available, fetch unified messages
    } | null;
}

export const ThreadModal: React.FC<ThreadModalProps> = ({
    visible,
    onClose,
    thread,
}) => {
    const [messages, setMessages] = useState<UnifiedMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [replyText, setReplyText] = useState('');

    useEffect(() => {
        if (visible && thread) {
            fetchUnifiedConversation();
        }
    }, [visible, thread]);

    const fetchUnifiedConversation = async () => {
        if (!thread) return;

        try {
            setLoading(true);

            // If we have a contactId, fetch all messages for that contact
            // Otherwise, just show the mock conversation based on the thread
            if (thread.contactId) {
                const messagesData = await messagesAPI.listMessages({
                    contact_id: thread.contactId,
                    limit: 50
                });

                const transformedMessages: UnifiedMessage[] = messagesData.messages.map(msg => ({
                    id: msg.id,
                    content: msg.content,
                    sender: msg.sender,
                    platform: msg.platform,
                    timestamp: msg.timestamp,
                    isMe: msg.sender === 'You' || msg.sender === 'Alex',
                })).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

                setMessages(transformedMessages);
            } else {
                // Search for messages from this sender across all platforms
                const messagesData = await messagesAPI.listMessages({ limit: 100 });

                // Filter by sender name (since we don't have contactId)
                const senderMessages = messagesData.messages.filter(
                    msg => msg.sender === thread.sender
                );

                const transformedMessages: UnifiedMessage[] = senderMessages.map(msg => ({
                    id: msg.id,
                    content: msg.content,
                    sender: msg.sender,
                    platform: msg.platform,
                    timestamp: msg.timestamp,
                    isMe: false,
                })).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

                setMessages(transformedMessages);
            }
        } catch (error) {
            console.error('Error fetching unified conversation:', error);
            // Fallback to showing just the thread summary as a message
            setMessages([{
                id: thread.id,
                content: thread.summary,
                sender: thread.sender,
                platform: thread.platform,
                timestamp: new Date().toISOString(),
                isMe: false,
            }]);
        } finally {
            setLoading(false);
        }
    };

    if (!thread) return null;

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const formatDateSeparator = (timestamp: string) => {
        const date = new Date(timestamp);
        const today = new Date();
        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        }
        return date.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
    };

    const getPlatformColor = (platform: string) => {
        return PLATFORM_COLORS[platform.toLowerCase()] || theme.colors.primary;
    };

    const getPlatformIcon = (platform: string) => {
        return PLATFORM_ICONS[platform.toLowerCase()] || 'chatbubble';
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <KeyboardAvoidingView
                    behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                    style={styles.modalContainer}
                >
                    {/* Header */}
                    <View style={styles.header}>
                        <View style={styles.headerLeft}>
                            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                                <Ionicons name="close" size={24} color={theme.colors.text} />
                            </TouchableOpacity>
                            <View style={styles.senderInfo}>
                                <Text style={styles.senderName}>{thread.sender}</Text>
                                <View style={styles.unifiedBadge}>
                                    <Ionicons name="layers-outline" size={12} color={theme.colors.primary} />
                                    <Text style={styles.unifiedText}>Unified Conversation</Text>
                                </View>
                            </View>
                        </View>
                        <TouchableOpacity style={styles.moreButton}>
                            <Ionicons name="ellipsis-horizontal" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    </View>

                    {loading ? (
                        <View style={styles.loadingContainer}>
                            <ActivityIndicator size="large" color={theme.colors.primary} />
                            <Text style={styles.loadingText}>Loading conversation...</Text>
                        </View>
                    ) : (
                        <ScrollView style={styles.content} contentContainerStyle={styles.scrollContent}>
                            {messages.length === 0 ? (
                                <View style={styles.emptyState}>
                                    <Ionicons name="chatbubbles-outline" size={48} color={theme.colors.textTertiary} />
                                    <Text style={styles.emptyText}>No messages found</Text>
                                </View>
                            ) : (
                                messages.map((msg, index) => {
                                    const platformColor = getPlatformColor(msg.platform);
                                    const showDateSeparator = index === 0 ||
                                        new Date(msg.timestamp).toDateString() !== new Date(messages[index - 1].timestamp).toDateString();

                                    return (
                                        <View key={msg.id}>
                                            {showDateSeparator && (
                                                <View style={styles.dateSeparator}>
                                                    <View style={styles.dateLine} />
                                                    <Text style={styles.dateText}>{formatDateSeparator(msg.timestamp)}</Text>
                                                    <View style={styles.dateLine} />
                                                </View>
                                            )}

                                            <View style={[styles.messageRow, msg.isMe ? styles.messageSent : styles.messageReceived]}>
                                                {!msg.isMe && (
                                                    <View style={styles.avatar}>
                                                        <Text style={styles.avatarText}>{thread.sender[0]}</Text>
                                                    </View>
                                                )}
                                                <View style={msg.isMe ? styles.bubbleSent : styles.bubbleReceived}>
                                                    {/* Platform indicator for each message */}
                                                    <View style={[styles.platformTag, { backgroundColor: platformColor + '15' }]}>
                                                        <Ionicons
                                                            name={getPlatformIcon(msg.platform) as any}
                                                            size={10}
                                                            color={platformColor}
                                                        />
                                                        <Text style={[styles.platformTagText, { color: platformColor }]}>
                                                            {msg.platform}
                                                        </Text>
                                                    </View>
                                                    <Text style={msg.isMe ? styles.messageTextSent : styles.messageText}>
                                                        {msg.content}
                                                    </Text>
                                                    <Text style={msg.isMe ? styles.messageTimeSent : styles.messageTime}>
                                                        {formatTime(msg.timestamp)}
                                                    </Text>
                                                </View>
                                            </View>
                                        </View>
                                    );
                                })
                            )}
                        </ScrollView>
                    )}

                    {/* Reply Input */}
                    <View style={styles.footer}>
                        <View style={styles.inputContainer}>
                            <TouchableOpacity style={styles.attachButton}>
                                <Ionicons name="add" size={24} color={theme.colors.textSecondary} />
                            </TouchableOpacity>
                            <TextInput
                                style={styles.input}
                                placeholder="Reply..."
                                placeholderTextColor={theme.colors.textTertiary}
                                value={replyText}
                                onChangeText={setReplyText}
                                multiline
                            />
                            <TouchableOpacity
                                style={[styles.sendButton, !replyText.trim() && styles.sendButtonDisabled]}
                                disabled={!replyText.trim()}
                            >
                                <Ionicons name="arrow-up" size={20} color="white" />
                            </TouchableOpacity>
                        </View>
                    </View>
                </KeyboardAvoidingView>
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
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        height: '90%',
        overflow: 'hidden',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
    },
    closeButton: {
        padding: 4,
    },
    senderInfo: {
        gap: 2,
    },
    senderName: {
        fontSize: 16,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    unifiedBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    unifiedText: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    moreButton: {
        padding: 4,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        gap: 12,
    },
    loadingText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingTop: 100,
        gap: 12,
    },
    emptyText: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    content: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    scrollContent: {
        padding: 16,
        gap: 8,
    },
    dateSeparator: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: 16,
        gap: 12,
    },
    dateLine: {
        flex: 1,
        height: 1,
        backgroundColor: theme.colors.borderLight,
    },
    dateText: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textTertiary,
    },
    messageRow: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        gap: 8,
        marginBottom: 8,
    },
    messageReceived: {
        justifyContent: 'flex-start',
    },
    messageSent: {
        justifyContent: 'flex-end',
    },
    avatar: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 14,
        fontWeight: 'bold',
        color: theme.colors.textSecondary,
    },
    bubbleReceived: {
        backgroundColor: 'white',
        padding: 12,
        borderRadius: 20,
        borderBottomLeftRadius: 4,
        maxWidth: '80%',
        ...theme.shadows.sm,
    },
    bubbleSent: {
        backgroundColor: theme.colors.primary,
        padding: 12,
        borderRadius: 20,
        borderBottomRightRadius: 4,
        maxWidth: '80%',
        ...theme.shadows.sm,
    },
    platformTag: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 10,
        alignSelf: 'flex-start',
        marginBottom: 6,
    },
    platformTagText: {
        fontSize: 10,
        fontWeight: '600',
    },
    messageText: {
        fontSize: 15,
        color: theme.colors.text,
        lineHeight: 22,
    },
    messageTextSent: {
        fontSize: 15,
        color: 'white',
        lineHeight: 22,
    },
    messageTime: {
        fontSize: 11,
        color: theme.colors.textTertiary,
        marginTop: 4,
        alignSelf: 'flex-end',
    },
    messageTimeSent: {
        fontSize: 11,
        color: 'rgba(255,255,255,0.7)',
        marginTop: 4,
        alignSelf: 'flex-end',
    },
    footer: {
        padding: 16,
        paddingBottom: Platform.OS === 'ios' ? 32 : 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.borderLight,
        backgroundColor: 'white',
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 24,
        padding: 8,
        gap: 8,
    },
    attachButton: {
        padding: 8,
    },
    input: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
        maxHeight: 100,
    },
    sendButton: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
    },
    sendButtonDisabled: {
        backgroundColor: theme.colors.textTertiary,
    },
});
