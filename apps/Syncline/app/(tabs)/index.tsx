import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, ScrollView, TouchableOpacity, Dimensions, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/Card/Card';
import { theme } from '../../src/theme';
import { BriefingModal } from '../../components/HomeModals/BriefingModal';
import { ThreadModal } from '../../components/HomeModals/ThreadModal';
import { contactsAPI } from '../../src/api/endpoints/contacts';
import { messagesAPI } from '../../src/api/endpoints/messages';

const { width } = Dimensions.get('window');

// Platform config
const PLATFORM_CONFIG: Record<string, { icon: string; color: string }> = {
    'slack': { icon: 'logo-slack', color: '#4A154B' },
    'gmail': { icon: 'mail', color: '#EA4335' },
    'discord': { icon: 'logo-discord', color: '#5865F2' },
    'whatsapp': { icon: 'logo-whatsapp', color: '#25D366' },
    'twitter': { icon: 'logo-twitter', color: '#1DA1F2' },
    'telegram': { icon: 'paper-plane', color: '#0088cc' },
};

// Mock Data: AI Daily Briefing (still mock for now)
const DAILY_BRIEFING = {
    greeting: "Good Morning, Alex",
    summary: "Based on your last message with **Sarah** on **Slack**, she's waiting for the Q4 designs. Also, **Mike** sent the updated budget on **Gmail** and mentioned you need to review it before the 2 PM meeting.",
    highlighted: true,
};

// Mock Data: Suggested Actions (derived from briefing)
const SUGGESTED_ACTIONS = [
    {
        id: '1',
        title: 'Send Q4 Designs',
        subtitle: 'to Sarah via Slack',
        type: 'urgent',
        icon: 'images-outline',
        platformIcon: 'logo-slack',
        platformColor: '#4A154B',
    },
    {
        id: '2',
        title: 'Review Budget',
        subtitle: 'from Mike via Gmail',
        type: 'review',
        icon: 'document-text-outline',
        platformIcon: 'mail',
        platformColor: '#EA4335',
    },
    {
        id: '3',
        title: 'Prepare for Board Mtg',
        subtitle: '2:00 PM • Calendar',
        type: 'meeting',
        icon: 'calendar-outline',
        platformIcon: 'calendar',
        platformColor: '#4285F4',
    },
];

interface RecentThread {
    id: string;
    sender: string;
    role: string;
    time: string;
    platform: string;
    icon: string;
    summary: string;
    unread: boolean;
    contactId?: string;
}

export default function HomeScreen() {
    const router = useRouter();
    const [briefingVisible, setBriefingVisible] = useState(false);
    const [selectedThread, setSelectedThread] = useState<RecentThread | null>(null);
    const [recentContext, setRecentContext] = useState<RecentThread[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchRecentContext();
    }, []);

    const fetchRecentContext = async () => {
        try {
            setLoading(true);

            // Fetch contacts and messages
            const [contactsData, messagesData] = await Promise.all([
                contactsAPI.listContacts({ limit: 20 }),
                messagesAPI.listMessages({ limit: 20 })
            ]);

            // Build a map of contact names to their IDs
            const contactMap = new Map<string, { id: string; role?: string }>();
            contactsData.contacts.forEach(contact => {
                contactMap.set(contact.canonical_name, {
                    id: contact.id,
                    role: contact.contact_metadata?.role || 'Contact'
                });
            });

            // Transform messages into recent context threads
            // Group by sender to show unique conversations
            const seenSenders = new Set<string>();
            const threads: RecentThread[] = [];

            for (const msg of messagesData.messages) {
                if (seenSenders.has(msg.sender)) continue;
                seenSenders.add(msg.sender);

                const contactInfo = contactMap.get(msg.sender);
                const platformConfig = PLATFORM_CONFIG[msg.platform.toLowerCase()] || { icon: 'chatbubble', color: '#888' };

                threads.push({
                    id: msg.id,
                    sender: msg.sender,
                    role: contactInfo?.role || 'Contact',
                    time: formatRelativeTime(msg.timestamp),
                    platform: msg.platform.charAt(0).toUpperCase() + msg.platform.slice(1),
                    icon: platformConfig.icon,
                    summary: msg.content,
                    unread: true, // Mock for now
                    contactId: contactInfo?.id,
                });

                if (threads.length >= 5) break; // Limit to 5 recent threads
            }

            setRecentContext(threads);
        } catch (error) {
            console.error('Error fetching recent context:', error);
        } finally {
            setLoading(false);
        }
    };

    const formatRelativeTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) {
            return `${diffMins} min ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        }
    };

    // Helper to render rich text summary
    const renderSummary = (text: string) => {
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return (
            <Text style={styles.briefingText}>
                {parts.map((part, index) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                        return (
                            <Text key={index} style={styles.highlightText}>
                                {part.slice(2, -2)}
                            </Text>
                        );
                    }
                    return <Text key={index}>{part}</Text>;
                })}
            </Text>
        );
    };

    return (
        <View style={styles.container}>
            <ScrollView
                style={styles.content}
                showsVerticalScrollIndicator={false}
                contentContainerStyle={styles.scrollContainer}
                bounces={false}
            >
                {/* Header Area */}
                <LinearGradient
                    colors={[theme.colors.primary, theme.colors.primaryDark]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 1 }}
                    style={styles.headerGradient}
                >
                    <View style={styles.headerContent}>
                        <View>
                            <Text style={styles.dateText}>
                                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
                            </Text>
                            <Text style={styles.greetingText}>{DAILY_BRIEFING.greeting}</Text>
                        </View>
                        <TouchableOpacity
                            style={styles.avatarButton}
                            onPress={() => router.push('/profile')}
                        >
                            <View style={styles.avatar}>
                                <Text style={styles.avatarText}>A</Text>
                            </View>
                        </TouchableOpacity>
                    </View>
                </LinearGradient>

                {/* Daily Briefing Card (Overlapping Header) */}
                <View style={styles.briefingContainer}>
                    <TouchableOpacity activeOpacity={0.9} onPress={() => setBriefingVisible(true)}>
                        <Card style={styles.briefingCard} shadow="lg">
                            <LinearGradient
                                colors={['#F0F9FF', '#FFFFFF']}
                                start={{ x: 0, y: 0 }}
                                end={{ x: 0, y: 1 }}
                                style={StyleSheet.absoluteFill}
                            />
                            <View style={styles.briefingContent}>
                                <View style={styles.briefingHeader}>
                                    <View style={styles.aiBadge}>
                                        <LinearGradient
                                            colors={[theme.colors.primary, theme.colors.primaryDark]}
                                            start={{ x: 0, y: 0 }}
                                            end={{ x: 1, y: 1 }}
                                            style={StyleSheet.absoluteFill}
                                        />
                                        <Ionicons name="sparkles" size={14} color="white" />
                                        <Text style={styles.aiBadgeText}>Daily Briefing</Text>
                                    </View>
                                    <TouchableOpacity style={styles.playButton} onPress={() => setBriefingVisible(true)}>
                                        <Ionicons name="play" size={20} color="white" style={{ marginLeft: 2 }} />
                                    </TouchableOpacity>
                                </View>
                                {renderSummary(DAILY_BRIEFING.summary)}

                                <TouchableOpacity
                                    style={styles.readMoreContainer}
                                    onPress={() => setBriefingVisible(true)}
                                >
                                    <Text style={styles.readMoreText}>View full summary</Text>
                                    <Ionicons name="arrow-forward" size={14} color={theme.colors.textTertiary} />
                                </TouchableOpacity>
                            </View>
                        </Card>
                    </TouchableOpacity>
                </View>

                {/* Suggested Actions */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Suggested Actions</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
                        {SUGGESTED_ACTIONS.map((action) => (
                            <TouchableOpacity key={action.id} activeOpacity={0.8}>
                                <Card style={styles.actionCard} shadow="sm">
                                    <View style={[styles.actionIcon, { backgroundColor: action.platformColor + '20' }]}>
                                        <Ionicons name={action.icon as any} size={24} color={action.platformColor} />
                                        <View style={[styles.platformBadge, { backgroundColor: action.platformColor }]}>
                                            <Ionicons name={action.platformIcon as any} size={10} color="white" />
                                        </View>
                                    </View>
                                    <Text style={styles.actionTitle}>{action.title}</Text>
                                    <Text style={styles.actionSubtitle}>{action.subtitle}</Text>
                                    <View style={styles.actionButton}>
                                        <Text style={[styles.actionButtonText, { color: action.platformColor }]}>Do it now</Text>
                                        <Ionicons name="arrow-forward" size={14} color={action.platformColor} />
                                    </View>
                                </Card>
                            </TouchableOpacity>
                        ))}
                    </ScrollView>
                </View>

                {/* Quick Access - Hidden Screens */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Quick Access</Text>
                    <View style={styles.quickAccessGrid}>
                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/(tabs)/commitments')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#FEF3C7' }]}>
                                <Ionicons name="checkbox-outline" size={24} color="#F59E0B" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Commitments</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/(tabs)/nudges')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#DBEAFE' }]}>
                                <Ionicons name="notifications-outline" size={24} color="#3B82F6" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Nudges</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/(tabs)/ai-memory')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#EDE9FE' }]}>
                                <Ionicons name="sparkles-outline" size={24} color="#8B5CF6" />
                            </View>
                            <Text style={styles.quickAccessLabel}>AI Memory</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/unified-conversation')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#FCE7F3' }]}>
                                <Ionicons name="git-merge-outline" size={24} color="#EC4899" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Unified Chat</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/daily-summary')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#FFEDD5' }]}>
                                <Ionicons name="stats-chart-outline" size={24} color="#F97316" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Summary</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/screenshot-index')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#CFFAFE' }]}>
                                <Ionicons name="camera-outline" size={24} color="#0891B2" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Screenshots</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.quickAccessItem}
                            onPress={() => router.push('/profile')}
                        >
                            <View style={[styles.quickAccessIcon, { backgroundColor: '#D1FAE5' }]}>
                                <Ionicons name="settings-outline" size={24} color="#10B981" />
                            </View>
                            <Text style={styles.quickAccessLabel}>Settings</Text>
                        </TouchableOpacity>
                    </View>
                </View>


                {/* Recent Context / Source Threads */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Recent Context</Text>
                    {loading ? (
                        <View style={styles.loadingContainer}>
                            <ActivityIndicator size="small" color={theme.colors.primary} />
                        </View>
                    ) : (
                        <View style={styles.threadsList}>
                            {recentContext.map((thread) => (
                                <TouchableOpacity
                                    key={thread.id}
                                    activeOpacity={0.8}
                                    onPress={() => setSelectedThread(thread)}
                                >
                                    <Card style={styles.threadCard} shadow="sm">
                                        <View style={styles.threadHeader}>
                                            <View style={styles.senderInfo}>
                                                <View style={styles.senderAvatar}>
                                                    <Text style={styles.senderInitial}>{thread.sender[0]}</Text>
                                                    <View style={[styles.platformIconBadge, { backgroundColor: PLATFORM_CONFIG[thread.platform.toLowerCase()]?.color || '#888' }]}>
                                                        <Ionicons name={thread.icon as any} size={10} color="white" />
                                                    </View>
                                                </View>
                                                <View>
                                                    <Text style={styles.senderName}>{thread.sender}</Text>
                                                    <Text style={styles.senderRole}>{thread.role} • {thread.time}</Text>
                                                </View>
                                            </View>
                                        </View>
                                        <Text style={styles.messageText} numberOfLines={2}>{thread.summary}</Text>
                                    </Card>
                                </TouchableOpacity>
                            ))}
                        </View>
                    )}
                </View>

                <View style={{ height: 100 }} />
            </ScrollView>

            {/* Modals */}
            <BriefingModal
                visible={briefingVisible}
                onClose={() => setBriefingVisible(false)}
                summary={DAILY_BRIEFING.summary}
            />

            <ThreadModal
                visible={!!selectedThread}
                onClose={() => setSelectedThread(null)}
                thread={selectedThread}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    loadingContainer: {
        padding: 32,
        alignItems: 'center',
    },
    headerGradient: {
        paddingTop: Platform.OS === 'ios' ? 60 : 40,
        paddingBottom: 80, // Extra space for overlapping card
        paddingHorizontal: 24,
        borderBottomLeftRadius: 32,
        borderBottomRightRadius: 32,
    },
    headerContent: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
    },
    dateText: {
        color: 'rgba(255,255,255,0.8)',
        fontSize: 14,
        fontWeight: '600',
        marginBottom: 4,
        textTransform: 'uppercase',
    },
    greetingText: {
        color: 'white',
        fontSize: 28,
        fontWeight: 'bold',
    },
    avatarButton: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(255,255,255,0.2)',
        padding: 2,
    },
    avatar: {
        flex: 1,
        backgroundColor: 'white',
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        color: theme.colors.primary,
        fontWeight: 'bold',
        fontSize: 18,
    },
    briefingContainer: {
        marginTop: -60, // Negative margin for overlap
        marginHorizontal: 24,
        marginBottom: 32,
    },
    briefingCard: {
        backgroundColor: 'white',
        borderRadius: 24,
        overflow: 'hidden', // Ensure gradient respects border radius
    },
    briefingContent: {
        padding: 20,
    },
    briefingHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    aiBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
        gap: 6,
        overflow: 'hidden', // For gradient background
    },
    aiBadgeText: {
        color: 'white',
        fontSize: 12,
        fontWeight: 'bold',
    },
    playButton: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
        ...theme.shadows.sm,
    },
    briefingText: {
        fontSize: 18,
        lineHeight: 28,
        color: theme.colors.text,
        marginBottom: 16,
    },
    highlightText: {
        fontWeight: 'bold',
        color: theme.colors.primary,
    },
    readMoreContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    readMoreText: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.textTertiary,
    },
    content: {
        flex: 1,
    },
    scrollContainer: {
        paddingTop: 0, // Removed padding since header is inside
    },
    section: {
        marginBottom: 32,
        paddingHorizontal: 24,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 16,
    },
    horizontalScroll: {
        marginHorizontal: -24,
        paddingHorizontal: 24,
    },
    actionCard: {
        width: 160,
        marginRight: 16,
        padding: 16,
        backgroundColor: 'white',
        borderRadius: 20,
        height: 180,
        justifyContent: 'space-between',
    },
    actionIcon: {
        width: 48,
        height: 48,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
    },
    platformBadge: {
        position: 'absolute',
        bottom: -4,
        right: -4,
        width: 20,
        height: 20,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: 'white',
    },
    actionTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginTop: 12,
    },
    actionSubtitle: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    actionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        marginTop: 12,
    },
    actionButtonText: {
        fontSize: 12,
        fontWeight: 'bold',
    },
    threadsList: {
        gap: 12,
    },
    threadCard: {
        padding: 16,
        borderRadius: 20,
        backgroundColor: 'white',
    },
    threadHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 12,
    },
    senderInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    senderAvatar: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
    },
    senderInitial: {
        fontSize: 16,
        fontWeight: 'bold',
        color: theme.colors.textSecondary,
    },
    platformIconBadge: {
        position: 'absolute',
        bottom: 0,
        right: 0,
        width: 16,
        height: 16,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: 'white',
    },
    senderName: {
        fontSize: 14,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    senderRole: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    messageText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
    },
    quickAccessGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
    },
    quickAccessItem: {
        width: (width - 48 - 12) / 2,
        backgroundColor: theme.colors.background,
        borderRadius: 16,
        padding: 16,
        alignItems: 'center',
        gap: 10,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    quickAccessIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    quickAccessLabel: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
    },
});
