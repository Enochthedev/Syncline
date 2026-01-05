import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    StyleSheet,
    View,
    Text,
    FlatList,
    TouchableOpacity,
    ActivityIndicator,
    Image,
    Platform,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { messagesAPI } from '../../src/api/endpoints/messages';

// Platform configuration
const PLATFORM_CONFIG: Record<string, { icon: string; color: string; name: string }> = {
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', name: 'WhatsApp' },
    linkedin: { icon: 'logo-linkedin', color: '#0A66C2', name: 'LinkedIn' },
    google_chat: { icon: 'chatbubbles', color: '#4285F4', name: 'Google Chat' },
    slack: { icon: 'logo-slack', color: '#4A154B', name: 'Slack' },
    discord: { icon: 'logo-discord', color: '#5865F2', name: 'Discord' },
    twitter: { icon: 'logo-twitter', color: '#1DA1F2', name: 'Twitter' },
    instagram: { icon: 'logo-instagram', color: '#E4405F', name: 'Instagram' },
    facebook: { icon: 'logo-facebook', color: '#1877F2', name: 'Facebook' },
    telegram: { icon: 'paper-plane', color: '#0088CC', name: 'Telegram' },
};

interface Message {
    id: string;
    platform: string;
    sender: string;
    sender_name?: string;
    content: string;
    timestamp: string;
    thread_id?: string;
    is_from_me?: boolean;
}

interface GroupedMessages {
    date: string;
    messages: Message[];
}

// Helper to format date headers
const formatDateHeader = (date: Date): string => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const messageDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (messageDate.getTime() === today.getTime()) {
        return 'Today';
    } else if (messageDate.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    } else if (now.getTime() - messageDate.getTime() < 7 * 24 * 60 * 60 * 1000) {
        return date.toLocaleDateString([], { weekday: 'long' });
    } else {
        return date.toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' });
    }
};

// Helper to format time
const formatTime = (timestamp: string): string => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export default function UnifiedConversationScreen() {
    const params = useLocalSearchParams();
    const router = useRouter();
    const [messages, setMessages] = useState<Message[]>([]);
    const [groupedMessages, setGroupedMessages] = useState<GroupedMessages[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
    const flatListRef = useRef<FlatList>(null);

    const contactId = params.contactId as string;
    const contactName = params.contactName as string;

    useEffect(() => {
        fetchMessages();
    }, [contactId]);

    // Group messages by date
    useEffect(() => {
        const grouped: Record<string, Message[]> = {};

        const filteredMessages = selectedPlatform
            ? messages.filter(m => m.platform?.toLowerCase() === selectedPlatform.toLowerCase())
            : messages;

        filteredMessages.forEach(msg => {
            if (!msg.timestamp) return;
            const date = new Date(msg.timestamp);
            const dateKey = date.toDateString();
            if (!grouped[dateKey]) {
                grouped[dateKey] = [];
            }
            grouped[dateKey].push(msg);
        });

        // Convert to array and sort
        const sortedGroups = Object.entries(grouped)
            .map(([date, msgs]) => ({
                date,
                messages: msgs.sort((a, b) =>
                    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                ),
            }))
            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        setGroupedMessages(sortedGroups);
    }, [messages, selectedPlatform]);

    const fetchMessages = async () => {
        try {
            setLoading(true);
            const response = await messagesAPI.listMessages({
                contact_id: contactId,
                limit: 100
            });
            setMessages(response.messages || []);
        } catch (error) {
            console.error('Error fetching messages:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        await fetchMessages();
        setRefreshing(false);
    }, [contactId]);

    // Get unique platforms from messages
    const platforms = [...new Set(messages.map(m => m.platform?.toLowerCase()).filter(Boolean))];

    const renderMessage = useCallback(({ item: msg }: { item: Message }) => {
        const platformConfig = PLATFORM_CONFIG[msg.platform?.toLowerCase()] || {
            icon: 'chatbubble',
            color: '#666',
            name: msg.platform,
        };

        const isFromMe = msg.is_from_me || msg.sender === 'me';

        return (
            <View style={[
                styles.messageContainer,
                isFromMe ? styles.messageFromMe : styles.messageFromThem,
            ]}>
                {!isFromMe && (
                    <View style={[styles.platformIndicator, { backgroundColor: platformConfig.color }]}>
                        <Ionicons name={platformConfig.icon as any} size={12} color="white" />
                    </View>
                )}
                <View style={[
                    styles.messageBubble,
                    isFromMe ? styles.bubbleFromMe : styles.bubbleFromThem,
                ]}>
                    {!isFromMe && (
                        <View style={styles.messageHeader}>
                            <Text style={[styles.senderName, { color: platformConfig.color }]}>
                                {msg.sender_name || msg.sender}
                            </Text>
                            <Text style={styles.platformLabel}>{platformConfig.name}</Text>
                        </View>
                    )}
                    <Text style={[
                        styles.messageText,
                        isFromMe && styles.messageTextFromMe,
                    ]}>{msg.content}</Text>
                    <Text style={[
                        styles.messageTime,
                        isFromMe && styles.messageTimeFromMe,
                    ]}>
                        {formatTime(msg.timestamp)}
                        {isFromMe && (
                            <Text style={styles.platformLabelSmall}> via {platformConfig.name}</Text>
                        )}
                    </Text>
                </View>
            </View>
        );
    }, []);

    const renderDateHeader = useCallback((date: string) => {
        return (
            <View style={styles.dateHeader}>
                <Text style={styles.dateHeaderText}>
                    {formatDateHeader(new Date(date))}
                </Text>
            </View>
        );
    }, []);

    const renderPlatformFilter = () => (
        <View style={styles.filterContainer}>
            <TouchableOpacity
                style={[
                    styles.filterChip,
                    !selectedPlatform && styles.filterChipActive,
                ]}
                onPress={() => setSelectedPlatform(null)}
            >
                <Text style={[
                    styles.filterChipText,
                    !selectedPlatform && styles.filterChipTextActive,
                ]}>All</Text>
            </TouchableOpacity>
            {platforms.map(platform => {
                const config = PLATFORM_CONFIG[platform] || { color: '#666', name: platform };
                const isActive = selectedPlatform === platform;
                return (
                    <TouchableOpacity
                        key={platform}
                        style={[
                            styles.filterChip,
                            isActive && { backgroundColor: config.color + '20', borderColor: config.color },
                        ]}
                        onPress={() => setSelectedPlatform(isActive ? null : platform)}
                    >
                        <Ionicons
                            name={PLATFORM_CONFIG[platform]?.icon as any || 'chatbubble'}
                            size={14}
                            color={isActive ? config.color : theme.colors.textSecondary}
                        />
                        <Text style={[
                            styles.filterChipText,
                            isActive && { color: config.color },
                        ]}>{config.name}</Text>
                    </TouchableOpacity>
                );
            })}
        </View>
    );

    if (loading) {
        return (
            <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: contactName || 'Conversation',
                    headerStyle: { backgroundColor: theme.colors.background },
                    headerTitleStyle: { fontSize: 18, fontWeight: '600' },
                    headerLeft: () => (
                        <TouchableOpacity
                            onPress={() => router.back()}
                            style={styles.backButton}
                        >
                            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    ),
                }}
            />

            {/* Platform Filter */}
            {platforms.length > 1 && renderPlatformFilter()}

            {/* Messages List */}
            {groupedMessages.length === 0 ? (
                <View style={styles.emptyContainer}>
                    <Ionicons name="chatbubbles-outline" size={60} color={theme.colors.textTertiary} />
                    <Text style={styles.emptyTitle}>No Messages</Text>
                    <Text style={styles.emptySubtitle}>
                        Messages from connected platforms will appear here in a unified timeline
                    </Text>
                </View>
            ) : (
                <FlatList
                    ref={flatListRef}
                    data={groupedMessages}
                    keyExtractor={(item) => item.date}
                    renderItem={({ item }) => (
                        <View>
                            {renderDateHeader(item.date)}
                            {item.messages.map((msg: Message, index: number) => (
                                <View key={msg.id || index}>
                                    {renderMessage({ item: msg })}
                                </View>
                            ))}
                        </View>
                    )}
                    contentContainerStyle={styles.messagesList}
                    refreshing={refreshing}
                    onRefresh={handleRefresh}
                    showsVerticalScrollIndicator={false}
                    inverted={false}
                    // Scroll to bottom on load
                    onContentSizeChange={() => {
                        if (groupedMessages.length > 0) {
                            flatListRef.current?.scrollToEnd({ animated: false });
                        }
                    }}
                />
            )}

            {/* V2: Message Input would go here */}
            <View style={styles.inputPlaceholder}>
                <Ionicons name="lock-closed-outline" size={16} color={theme.colors.textTertiary} />
                <Text style={styles.inputPlaceholderText}>
                    Sending messages coming in v2
                </Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    backButton: {
        padding: 8,
        marginLeft: Platform.OS === 'ios' ? 0 : 8,
    },
    filterContainer: {
        flexDirection: 'row',
        paddingHorizontal: 16,
        paddingVertical: 12,
        gap: 8,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
        backgroundColor: theme.colors.background,
    },
    filterChip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: theme.colors.border,
        backgroundColor: theme.colors.background,
    },
    filterChipActive: {
        backgroundColor: theme.colors.primary,
        borderColor: theme.colors.primary,
    },
    filterChipText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    filterChipTextActive: {
        color: 'white',
    },
    messagesList: {
        padding: 16,
        paddingBottom: 80,
    },
    dateHeader: {
        alignItems: 'center',
        marginVertical: 16,
    },
    dateHeaderText: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textTertiary,
        backgroundColor: theme.colors.surface,
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 12,
    },
    messageContainer: {
        flexDirection: 'row',
        marginBottom: 8,
        alignItems: 'flex-end',
    },
    messageFromMe: {
        justifyContent: 'flex-end',
    },
    messageFromThem: {
        justifyContent: 'flex-start',
    },
    platformIndicator: {
        width: 24,
        height: 24,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 8,
    },
    messageBubble: {
        maxWidth: '75%',
        padding: 12,
        borderRadius: 18,
    },
    bubbleFromMe: {
        backgroundColor: theme.colors.primary,
        borderBottomRightRadius: 4,
    },
    bubbleFromThem: {
        backgroundColor: theme.colors.surface,
        borderBottomLeftRadius: 4,
    },
    messageHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginBottom: 4,
    },
    senderName: {
        fontSize: 12,
        fontWeight: '600',
    },
    platformLabel: {
        fontSize: 10,
        color: theme.colors.textTertiary,
    },
    platformLabelSmall: {
        fontSize: 10,
        color: 'rgba(255,255,255,0.7)',
    },
    messageText: {
        fontSize: 15,
        color: theme.colors.text,
        lineHeight: 20,
    },
    messageTextFromMe: {
        color: 'white',
    },
    messageTime: {
        fontSize: 10,
        color: theme.colors.textTertiary,
        marginTop: 4,
        alignSelf: 'flex-end',
    },
    messageTimeFromMe: {
        color: 'rgba(255,255,255,0.7)',
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
    },
    emptySubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginTop: 8,
        lineHeight: 20,
    },
    inputPlaceholder: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 16,
        backgroundColor: theme.colors.surface,
        borderTopWidth: 1,
        borderTopColor: theme.colors.borderLight,
    },
    inputPlaceholderText: {
        fontSize: 14,
        color: theme.colors.textTertiary,
    },
});
