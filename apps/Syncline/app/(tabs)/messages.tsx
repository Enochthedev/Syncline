/**
 * Messages Tab - Unified Chat Inbox
 * 
 * Shows active chat threads from connected platforms (WhatsApp, etc.)
 * sorted by most recent message.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    StyleSheet,
    View,
    Text,
    FlatList,
    TouchableOpacity,
    ActivityIndicator,
    RefreshControl,
    Alert,
    TextInput,
    ScrollView,
} from 'react-native';
import { useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';
import { messagesAPI, ChatThread, ChatMessage } from '../../src/api/endpoints/messages';
import { useAuth } from '../../src/contexts/AuthContext';
import { PLATFORM_COLORS, Platform as PlatformType } from '../../src/types';

// Platform configuration
const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    'gmail': { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    'google_chat': { icon: 'chatbubbles', color: '#00AC47', label: 'Chat' },
    'linkedin': { icon: 'logo-linkedin', color: '#0077B5', label: 'LinkedIn' },
    'slack': { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    'discord': { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    'twitter': { icon: 'logo-twitter', color: '#000000', label: 'X' },
    'telegram': { icon: 'paper-plane', color: '#0088cc', label: 'Telegram' },
};

// Available platforms in tabs
const PLATFORMS = ['all', 'gmail', 'google_chat', 'slack'];

export default function MessagesScreen() {
    const router = useRouter();
    const { user, isAuthenticated } = useAuth();

    const [threads, setThreads] = useState<ChatThread[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchThreads();
    }, [selectedPlatform]);

    const fetchThreads = async () => {
        try {
            setLoading(true);

            const response = await messagesAPI.getChatThreads({
                platform: selectedPlatform === 'all' ? undefined : selectedPlatform,
                limit: 50
            });

            setThreads(response.threads);

        } catch (error) {
            console.error('Failed to fetch chat threads:', error);
            // Show empty state instead of error for now
            setThreads([]);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        fetchThreads();
    }, [selectedPlatform]);

    const formatTime = (timestamp?: string) => {
        if (!timestamp) return '';

        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = diffMs / (1000 * 60 * 60);
        const diffDays = diffMs / (1000 * 60 * 60 * 24);

        if (diffHours < 1) {
            const diffMins = Math.floor(diffMs / (1000 * 60));
            return diffMins < 1 ? 'now' : `${diffMins}m`;
        } else if (diffHours < 24) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays < 7) {
            return date.toLocaleDateString([], { weekday: 'short' });
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    };

    const handleThreadPress = (thread: ChatThread) => {
        // Navigate to chat detail view
        router.push({
            pathname: '/(tabs)/chat',
            params: {
                threadId: thread.id,
                platform: thread.platform,
                contactName: thread.contact_name || thread.phone_number || 'Chat',
            }
        });
    };

    const handleNewMessage = () => {
        Alert.alert(
            'New Conversation',
            'To start a new WhatsApp conversation, send a message from your phone. It will appear here automatically.',
            [{ text: 'OK' }]
        );
    };

    // Filter threads by search query
    const filteredThreads = threads.filter(thread => {
        if (!searchQuery.trim()) return true;
        const query = searchQuery.toLowerCase();
        return (
            thread.contact_name?.toLowerCase().includes(query) ||
            thread.phone_number?.toLowerCase().includes(query) ||
            thread.last_message?.toLowerCase().includes(query)
        );
    });

    const renderPlatformTabs = () => (
        <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.platformTabs}
            contentContainerStyle={styles.platformTabsContent}
        >
            {PLATFORMS.map((platform) => {
                const isSelected = selectedPlatform === platform;
                const config = PLATFORM_CONFIG[platform];

                return (
                    <TouchableOpacity
                        key={platform}
                        style={[
                            styles.platformTab,
                            isSelected && styles.platformTabSelected,
                            isSelected && config && { borderColor: config.color }
                        ]}
                        onPress={() => setSelectedPlatform(platform)}
                    >
                        {config ? (
                            <Ionicons
                                name={config.icon as any}
                                size={18}
                                color={isSelected ? config.color : theme.colors.textSecondary}
                            />
                        ) : (
                            <Text style={[
                                styles.platformTabText,
                                isSelected && styles.platformTabTextSelected
                            ]}>
                                All
                            </Text>
                        )}
                        {platform !== 'all' && (
                            <Text style={[
                                styles.platformTabLabel,
                                isSelected && { color: config?.color }
                            ]}>
                                {config?.label}
                            </Text>
                        )}
                    </TouchableOpacity>
                );
            })}
        </ScrollView>
    );

    const renderThreadItem = ({ item }: { item: ChatThread }) => {
        const platformConfig = PLATFORM_CONFIG[item.platform.toLowerCase()] ||
            { icon: 'chatbubble', color: theme.colors.textSecondary, label: item.platform };

        const displayName = item.contact_name || item.phone_number || `${item.platform} Chat`;
        const initial = displayName[0]?.toUpperCase() || '?';

        return (
            <TouchableOpacity onPress={() => handleThreadPress(item)} activeOpacity={0.7}>
                <Card style={styles.threadCard}>
                    <View style={styles.threadContent}>
                        {/* Avatar */}
                        <View style={[styles.avatar, { backgroundColor: platformConfig.color + '20' }]}>
                            <Text style={[styles.avatarText, { color: platformConfig.color }]}>
                                {initial}
                            </Text>
                        </View>

                        {/* Thread Info */}
                        <View style={styles.threadInfo}>
                            <View style={styles.threadHeader}>
                                <View style={styles.nameRow}>
                                    <Text style={styles.threadName} numberOfLines={1}>
                                        {displayName}
                                    </Text>
                                    {!item.is_linked && item.phone_number && (
                                        <View style={styles.linkBadge}>
                                            <Text style={styles.linkBadgeText}>Unlinked</Text>
                                        </View>
                                    )}
                                </View>
                                <View style={styles.timeContainer}>
                                    <Text style={styles.threadTime}>
                                        {formatTime(item.last_message_time)}
                                    </Text>
                                    {item.unread_count > 0 && (
                                        <View style={[styles.unreadBadge, { backgroundColor: platformConfig.color }]}>
                                            <Text style={styles.unreadText}>
                                                {item.unread_count > 99 ? '99+' : item.unread_count}
                                            </Text>
                                        </View>
                                    )}
                                </View>
                            </View>

                            <Text style={styles.lastMessage} numberOfLines={2}>
                                {item.last_message || 'No messages yet'}
                            </Text>

                            {/* Platform & Phone */}
                            <View style={styles.threadMeta}>
                                <View style={styles.platformBadge}>
                                    <Ionicons
                                        name={platformConfig.icon as any}
                                        size={12}
                                        color={platformConfig.color}
                                    />
                                    <Text style={[styles.platformLabel, { color: platformConfig.color }]}>
                                        {platformConfig.label}
                                    </Text>
                                </View>
                                {item.phone_number && (
                                    <Text style={styles.phoneNumber} numberOfLines={1}>
                                        {item.phone_number}
                                    </Text>
                                )}
                            </View>
                        </View>
                    </View>
                </Card>
            </TouchableOpacity>
        );
    };

    const renderEmptyState = () => (
        <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={80} color={theme.colors.textTertiary} />
            <Text style={styles.emptyTitle}>No Conversations Yet</Text>
            <Text style={styles.emptySubtitle}>
                {isAuthenticated
                    ? "Connect your accounts to see conversations.\nMessages from all platforms will appear here."
                    : "Please login to see your messages."
                }
            </Text>

            {isAuthenticated && (
                <TouchableOpacity
                    style={styles.emptyButton}
                    onPress={() => router.push('/(tabs)/connections')}
                >
                    <Ionicons name="link" size={20} color="white" />
                    <Text style={styles.emptyButtonText}>Connect Accounts</Text>
                </TouchableOpacity>
            )}

            <TouchableOpacity
                style={styles.refreshButton}
                onPress={onRefresh}
            >
                <Ionicons name="refresh" size={18} color={theme.colors.primary} />
                <Text style={styles.refreshButtonText}>Refresh</Text>
            </TouchableOpacity>
        </View>
    );

    const renderSearchBar = () => (
        <View style={styles.searchContainer}>
            <View style={styles.searchBar}>
                <Ionicons name="search" size={20} color={theme.colors.textTertiary} />
                <TextInput
                    style={styles.searchInput}
                    placeholder="Search conversations..."
                    placeholderTextColor={theme.colors.textTertiary}
                    value={searchQuery}
                    onChangeText={setSearchQuery}
                />
                {searchQuery.length > 0 && (
                    <TouchableOpacity onPress={() => setSearchQuery('')}>
                        <Ionicons name="close-circle" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                )}
            </View>
        </View>
    );

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: 'Messages',
                    headerLargeTitle: true,
                    headerLeft: () => (
                        <TouchableOpacity
                            onPress={handleNewMessage}
                            style={styles.headerButton}
                        >
                            <Ionicons name="create-outline" size={24} color={theme.colors.primary} />
                        </TouchableOpacity>
                    ),
                    headerRight: () => (
                        <TouchableOpacity
                            onPress={onRefresh}
                            style={styles.headerButton}
                            disabled={refreshing}
                        >
                            {refreshing ? (
                                <ActivityIndicator size="small" color={theme.colors.primary} />
                            ) : (
                                <Ionicons name="refresh" size={22} color={theme.colors.primary} />
                            )}
                        </TouchableOpacity>
                    ),
                }}
            />

            {renderSearchBar()}
            {renderPlatformTabs()}

            {loading && !refreshing ? (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.colors.primary} />
                    <Text style={styles.loadingText}>Loading conversations...</Text>
                </View>
            ) : (
                <FlatList
                    data={filteredThreads}
                    keyExtractor={(item) => item.id}
                    renderItem={renderThreadItem}
                    contentContainerStyle={[
                        styles.listContent,
                        filteredThreads.length === 0 && styles.emptyListContent
                    ]}
                    ListEmptyComponent={renderEmptyState}
                    refreshControl={
                        <RefreshControl
                            refreshing={refreshing}
                            onRefresh={onRefresh}
                            tintColor={theme.colors.primary}
                        />
                    }
                    showsVerticalScrollIndicator={false}
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    headerButton: {
        padding: 8,
    },
    searchContainer: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        backgroundColor: theme.colors.background,
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 12,
        paddingVertical: 10,
        gap: 8,
    },
    searchInput: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
    },
    platformTabs: {
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        maxHeight: 60,
    },
    platformTabsContent: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 12,
        paddingVertical: 12,
    },
    platformTab: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: theme.colors.surface,
        borderWidth: 1.5,
        borderColor: 'transparent',
        gap: 6,
        height: 36,
        marginRight: 8,
    },
    platformTabSelected: {
        backgroundColor: theme.colors.background,
    },
    platformTabText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    platformTabTextSelected: {
        color: theme.colors.primary,
    },
    platformTabLabel: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
    },
    loadingText: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    listContent: {
        padding: 16,
        gap: 12,
    },
    emptyListContent: {
        flex: 1,
    },
    threadCard: {
        padding: 0,
        marginBottom: 0,
    },
    threadContent: {
        flexDirection: 'row',
        padding: 16,
        gap: 12,
    },
    avatar: {
        width: 52,
        height: 52,
        borderRadius: 26,
        justifyContent: 'center',
        alignItems: 'center',
    },
    avatarText: {
        fontSize: 20,
        fontWeight: 'bold',
    },
    threadInfo: {
        flex: 1,
        gap: 4,
    },
    threadHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    nameRow: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    threadName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        flex: 1,
    },
    linkBadge: {
        paddingHorizontal: 6,
        paddingVertical: 2,
        backgroundColor: theme.colors.warning + '20',
        borderRadius: 4,
    },
    linkBadgeText: {
        fontSize: 10,
        color: theme.colors.warning,
        fontWeight: '600',
    },
    timeContainer: {
        alignItems: 'flex-end',
        gap: 4,
    },
    threadTime: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    unreadBadge: {
        minWidth: 20,
        height: 20,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 6,
    },
    unreadText: {
        fontSize: 11,
        color: 'white',
        fontWeight: 'bold',
    },
    lastMessage: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
    },
    threadMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginTop: 4,
    },
    platformBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 8,
        paddingVertical: 2,
        backgroundColor: theme.colors.surface,
        borderRadius: 10,
    },
    platformLabel: {
        fontSize: 11,
        fontWeight: '500',
    },
    phoneNumber: {
        fontSize: 12,
        color: theme.colors.textTertiary,
        flex: 1,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 32,
        gap: 16,
    },
    emptyTitle: {
        fontSize: 22,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 8,
    },
    emptySubtitle: {
        fontSize: 15,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 22,
    },
    emptyButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 25,
        marginTop: 8,
    },
    emptyButtonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
    refreshButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 16,
        paddingVertical: 8,
        marginTop: 8,
    },
    refreshButtonText: {
        color: theme.colors.primary,
        fontSize: 14,
        fontWeight: '500',
    },
});
