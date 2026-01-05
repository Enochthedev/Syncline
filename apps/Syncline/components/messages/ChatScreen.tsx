import React, { useState, useEffect } from 'react';
import { 
    View, 
    Text, 
    StyleSheet, 
    FlatList, 
    TouchableOpacity,
    RefreshControl,
    Alert
} from 'react-native';
import { ChatThread, messagesAPI } from '../../src/api/endpoints/messages';
import { ChatThreadItem } from './ChatThreadItem';
import { ChatMessagesView } from './ChatMessagesView';
import { theme } from '../../src/theme';

interface ChatScreenProps {
    platform?: string;
}

export const ChatScreen: React.FC<ChatScreenProps> = ({ platform = 'whatsapp' }) => {
    const [threads, setThreads] = useState<ChatThread[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedThread, setSelectedThread] = useState<ChatThread | null>(null);

    useEffect(() => {
        loadThreads();
    }, [platform]);

    const loadThreads = async () => {
        try {
            setLoading(true);
            const response = await messagesAPI.getChatThreads({
                platform,
                limit: 50
            });
            setThreads(response.threads);
        } catch (error) {
            console.error('Failed to load chat threads:', error);
            Alert.alert('Error', 'Failed to load chats');
        } finally {
            setLoading(false);
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await loadThreads();
        setRefreshing(false);
    };

    const handleThreadPress = (thread: ChatThread) => {
        setSelectedThread(thread);
    };

    const handleBackToThreads = () => {
        setSelectedThread(null);
        // Refresh threads when coming back
        loadThreads();
    };

    const handleNewChat = () => {
        Alert.alert(
            'New Chat',
            'Feature coming soon! You can start a new chat by sending a message to a contact.',
            [{ text: 'OK' }]
        );
    };

    const handleLinkContact = (thread: ChatThread) => {
        Alert.alert(
            'Link Contact',
            `Link this chat to a contact in your address book?`,
            [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Link', onPress: () => {
                    // TODO: Implement contact linking
                    Alert.alert('Coming Soon', 'Contact linking will be available soon!');
                }}
            ]
        );
    };

    const renderThread = ({ item }: { item: ChatThread }) => (
        <ChatThreadItem
            thread={item}
            onPress={() => handleThreadPress(item)}
            onLinkContact={() => handleLinkContact(item)}
        />
    );

    const renderEmptyState = () => (
        <View style={styles.emptyState}>
            <Text style={styles.emptyTitle}>No Active Chats</Text>
            <Text style={styles.emptyMessage}>
                Your {platform} account is connected (+2349167674418) but there are no recent conversations to display.
                {'\n\n'}
                To see chats here:
                {'\n'}• Send or receive messages on WhatsApp
                {'\n'}• Wait a few minutes for sync
                {'\n'}• Pull down to refresh
            </Text>
            <TouchableOpacity style={styles.refreshButton} onPress={handleRefresh}>
                <Text style={styles.refreshButtonText}>Refresh Chats</Text>
            </TouchableOpacity>
        </View>
    );

    // Show chat messages view if a thread is selected
    if (selectedThread) {
        return (
            <ChatMessagesView
                threadId={selectedThread.id}
                platform={selectedThread.platform}
                contactName={selectedThread.contact_name}
                onBack={handleBackToThreads}
            />
        );
    }

    // Show threads list
    return (
        <View style={styles.container}>
            <View style={styles.header}>
                <Text style={styles.headerTitle}>
                    {platform.charAt(0).toUpperCase() + platform.slice(1)} Chats
                </Text>
                <TouchableOpacity style={styles.newChatIcon} onPress={handleNewChat}>
                    <Text style={styles.newChatIconText}>+</Text>
                </TouchableOpacity>
            </View>

            <FlatList
                data={threads}
                renderItem={renderThread}
                keyExtractor={(item) => item.id}
                style={styles.threadsList}
                contentContainerStyle={threads.length === 0 ? styles.emptyContainer : undefined}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={handleRefresh}
                        tintColor={theme.colors.primary}
                    />
                }
                ListEmptyComponent={!loading ? renderEmptyState : null}
                showsVerticalScrollIndicator={false}
            />
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: theme.spacing.m,
        backgroundColor: theme.colors.surface,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    headerTitle: {
        ...theme.typography.h2,
    },
    newChatIcon: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: theme.colors.primary,
        justifyContent: 'center',
        alignItems: 'center',
    },
    newChatIconText: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
    },
    threadsList: {
        flex: 1,
        padding: theme.spacing.m,
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    emptyState: {
        alignItems: 'center',
        padding: theme.spacing.xl,
    },
    emptyTitle: {
        ...theme.typography.h3,
        marginBottom: theme.spacing.m,
        textAlign: 'center',
    },
    emptyMessage: {
        ...theme.typography.body,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: theme.spacing.xl,
        lineHeight: 22,
    },
    newChatButton: {
        backgroundColor: theme.colors.primary,
        paddingHorizontal: theme.spacing.xl,
        paddingVertical: theme.spacing.m,
        borderRadius: theme.borderRadius.lg,
    },
    newChatButtonText: {
        ...theme.typography.body,
        color: 'white',
        fontWeight: '600',
    },
    refreshButton: {
        backgroundColor: theme.colors.secondary,
        paddingHorizontal: theme.spacing.xl,
        paddingVertical: theme.spacing.m,
        borderRadius: theme.borderRadius.lg,
        marginTop: theme.spacing.m,
    },
    refreshButtonText: {
        ...theme.typography.body,
        color: 'white',
        fontWeight: '600',
    },
});