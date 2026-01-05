/**
 * Chat Screen
 * 
 * Shows conversation messages for either:
 * - A contact (contactId param) - unified view across platforms
 * - A chat thread (threadId + platform params) - platform-specific chat
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    StyleSheet,
    View,
    Text,
    FlatList,
    TouchableOpacity,
    TextInput,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons'
import { theme } from '../../src/theme';
import { messagesAPI, ChatMessage } from '../../src/api/endpoints/messages';

// Platform colors
const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    'whatsapp': { icon: 'logo-whatsapp', color: '#25D366', label: 'WhatsApp' },
    'gmail': { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    'slack': { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    'discord': { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    'twitter': { icon: 'logo-twitter', color: '#1DA1F2', label: 'X' },
    'telegram': { icon: 'paper-plane', color: '#0088cc', label: 'Telegram' },
};

export default function ChatScreen() {
    const params = useLocalSearchParams();
    const router = useRouter();
    const flatListRef = useRef<FlatList>(null);

    // Get params - support both thread-based and contact-based views
    const threadId = params.threadId as string | undefined;
    const platform = params.platform as string | undefined;
    const contactName = params.contactName as string || 'Chat';

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [messageText, setMessageText] = useState('');

    useEffect(() => {
        if (threadId && platform) {
            fetchMessages();
        } else {
            // No thread specified, show empty state
            setLoading(false);
        }
    }, [threadId, platform]);

    const fetchMessages = async () => {
        try {
            setLoading(true);

            const response = await messagesAPI.getChatMessages(threadId!, platform!, {
                limit: 50
            });

            setMessages(response.messages);

        } catch (error) {
            console.error('Failed to fetch messages:', error);
            setMessages([]);
        } finally {
            setLoading(false);
        }
    };

    const handleSendMessage = async () => {
        if (!messageText.trim() || sending || !threadId || !platform) return;

        try {
            setSending(true);

            const response = await messagesAPI.sendMessage(
                threadId,
                platform,
                messageText.trim()
            );

            if (response.success) {
                setMessageText('');
                // Refresh messages
                await fetchMessages();
                // Scroll to bottom
                setTimeout(() => {
                    flatListRef.current?.scrollToEnd({ animated: true });
                }, 100);
            } else {
                Alert.alert('Error', response.message || 'Failed to send message');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            Alert.alert('Error', 'Failed to send message. Please try again.');
        } finally {
            setSending(false);
        }
    };

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const formatDateSeparator = (timestamp: string) => {
        const date = new Date(timestamp);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
        }
    };

    const platformConfig = PLATFORM_CONFIG[platform?.toLowerCase() || ''] ||
        { icon: 'chatbubble', color: theme.colors.primary, label: platform || 'Chat' };

    const renderMessage = ({ item, index }: { item: ChatMessage; index: number }) => {
        const isFromMe = item.is_from_me;

        // Check if we need a date separator
        const showDateSeparator = index === 0 ||
            new Date(item.timestamp).toDateString() !== new Date(messages[index - 1].timestamp).toDateString();

        return (
            <>
                {showDateSeparator && (
                    <View style={styles.dateSeparator}>
                        <View style={styles.dateLine} />
                        <Text style={styles.dateText}>{formatDateSeparator(item.timestamp)}</Text>
                        <View style={styles.dateLine} />
                    </View>
                )}

                <View style={[styles.messageRow, isFromMe ? styles.messageSent : styles.messageReceived]}>
                    {!isFromMe && (
                        <View style={[styles.avatar, { backgroundColor: platformConfig.color + '20' }]}>
                            <Text style={[styles.avatarText, { color: platformConfig.color }]}>
                                {item.sender_name?.[0]?.toUpperCase() || '?'}
                            </Text>
                        </View>
                    )}

                    <View style={isFromMe ? styles.bubbleSent : styles.bubbleReceived}>
                        {!isFromMe && (
                            <Text style={styles.senderName}>{item.sender_name}</Text>
                        )}

                        <Text style={isFromMe ? styles.messageTextSent : styles.messageText}>
                            {item.content}
                        </Text>

                        <View style={styles.messageFooter}>
                            {item.has_attachments && (
                                <Ionicons name="attach" size={12} color={isFromMe ? 'rgba(255,255,255,0.7)' : theme.colors.textTertiary} />
                            )}
                            <Text style={isFromMe ? styles.messageTimeSent : styles.messageTime}>
                                {formatTime(item.timestamp)}
                            </Text>
                        </View>
                    </View>
                </View>
            </>
        );
    };

    const renderEmptyState = () => (
        <View style={styles.emptyContainer}>
            <Ionicons name="chatbubbles-outline" size={64} color={theme.colors.textTertiary} />
            <Text style={styles.emptyText}>No messages yet</Text>
            <Text style={styles.emptySubtext}>
                {threadId
                    ? `Start a conversation with ${contactName}`
                    : 'Select a conversation from the messages tab'
                }
            </Text>
        </View>
    );

    const renderHeader = () => (
        <View style={styles.conversationHeader}>
            <View style={[styles.platformBadge, { backgroundColor: platformConfig.color + '20' }]}>
                <Ionicons name={platformConfig.icon as any} size={14} color={platformConfig.color} />
                <Text style={[styles.platformLabel, { color: platformConfig.color }]}>
                    {platformConfig.label}
                </Text>
            </View>
            <Text style={styles.headerSubtitle}>
                {threadId ? `Chat in ${platformConfig.label}` : 'No conversation selected'}
            </Text>
        </View>
    );

    if (loading) {
        return (
            <View style={[styles.container, styles.loadingContainer]}>
                <Stack.Screen options={{ title: contactName }} />
                <ActivityIndicator size="large" color={theme.colors.primary} />
                <Text style={styles.loadingText}>Loading messages...</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: contactName,
                    headerBackTitle: 'Messages',
                    headerRight: () => (
                        <TouchableOpacity
                            onPress={fetchMessages}
                            style={styles.headerButton}
                        >
                            <Ionicons name="refresh" size={22} color={theme.colors.primary} />
                        </TouchableOpacity>
                    ),
                }}
            />

            {renderHeader()}

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.contentContainer}
                keyboardVerticalOffset={100}
            >
                {messages.length === 0 ? (
                    renderEmptyState()
                ) : (
                    <FlatList
                        ref={flatListRef}
                        data={messages}
                        keyExtractor={(item) => item.id}
                        renderItem={renderMessage}
                        contentContainerStyle={styles.messagesContent}
                        showsVerticalScrollIndicator={false}
                        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
                    />
                )}

                {/* Message Input */}
                {threadId && platform && (
                    <View style={styles.footer}>
                        <View style={styles.inputContainer}>
                            <TextInput
                                style={styles.input}
                                placeholder={`Message via ${platformConfig.label}...`}
                                placeholderTextColor={theme.colors.textTertiary}
                                value={messageText}
                                onChangeText={setMessageText}
                                multiline
                                maxLength={1000}
                            />
                            <TouchableOpacity
                                style={[
                                    styles.sendButton,
                                    { backgroundColor: platformConfig.color },
                                    (!messageText.trim() || sending) && styles.sendButtonDisabled
                                ]}
                                onPress={handleSendMessage}
                                disabled={!messageText.trim() || sending}
                            >
                                {sending ? (
                                    <ActivityIndicator size="small" color="white" />
                                ) : (
                                    <Ionicons name="send" size={18} color="white" />
                                )}
                            </TouchableOpacity>
                        </View>
                    </View>
                )}
            </KeyboardAvoidingView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    loadingContainer: {
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
    },
    loadingText: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    headerButton: {
        padding: 8,
    },
    conversationHeader: {
        backgroundColor: 'white',
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    platformBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    platformLabel: {
        fontSize: 13,
        fontWeight: '600',
    },
    headerSubtitle: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    contentContainer: {
        flex: 1,
    },
    messagesContent: {
        padding: 16,
        gap: 8,
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 32,
    },
    emptyText: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginTop: 16,
    },
    emptySubtext: {
        fontSize: 14,
        color: theme.colors.textTertiary,
        marginTop: 4,
        textAlign: 'center',
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
        backgroundColor: theme.colors.border,
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
        marginBottom: 4,
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
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 14,
        fontWeight: 'bold',
    },
    bubbleReceived: {
        backgroundColor: 'white',
        padding: 12,
        borderRadius: 18,
        borderBottomLeftRadius: 4,
        maxWidth: '80%',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    bubbleSent: {
        backgroundColor: theme.colors.primary,
        padding: 12,
        borderRadius: 18,
        borderBottomRightRadius: 4,
        maxWidth: '80%',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
        elevation: 1,
    },
    senderName: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginBottom: 4,
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
    messageFooter: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        marginTop: 4,
        alignSelf: 'flex-end',
    },
    messageTime: {
        fontSize: 11,
        color: theme.colors.textTertiary,
    },
    messageTimeSent: {
        fontSize: 11,
        color: 'rgba(255,255,255,0.7)',
    },
    footer: {
        padding: 12,
        paddingBottom: Platform.OS === 'ios' ? 28 : 12,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        backgroundColor: 'white',
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        backgroundColor: theme.colors.surface,
        borderRadius: 24,
        paddingLeft: 16,
        paddingRight: 6,
        paddingVertical: 6,
        gap: 8,
    },
    input: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
        maxHeight: 100,
        paddingVertical: 8,
    },
    sendButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    sendButtonDisabled: {
        opacity: 0.5,
    },
});
