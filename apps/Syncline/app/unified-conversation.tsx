/**
 * Unified Conversation Demo - Multi-Platform Thread View
 * 
 * Shows a conversation with a single contact across multiple platforms.
 * Demonstrates MESH's ability to aggregate and display messages from different sources.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../src/theme';

// Platform configuration
const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    gmail: { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    slack: { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', label: 'WhatsApp' },
    discord: { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    telegram: { icon: 'paper-plane', color: '#0088CC', label: 'Telegram' },
};

// Unified conversation with a real contact across platforms
const UNIFIED_CONTACT = {
    id: 'contact-sarah-001',
    name: 'Sarah Johnson',
    role: 'Product Manager',
    company: 'TechCorp Inc.',
    avatar: 'SJ',
    platforms: ['gmail', 'slack', 'whatsapp'],
    relationshipStrength: 87,
    totalMessages: 156,
    lastActive: '2 hours ago',
};

// Messages from multiple platforms, sorted by time (most recent first)
const UNIFIED_MESSAGES = [
    {
        id: 'msg-1',
        platform: 'whatsapp',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Hey! Just saw your email about the Q4 roadmap. The timeline looks ambitious but achievable. Let's discuss tomorrow?",
        timestamp: '2026-01-05T09:45:00Z',
        read: true,
    },
    {
        id: 'msg-2',
        platform: 'whatsapp',
        sender: 'You',
        isMe: true,
        content: "Sounds good! I'll block 30 mins in the morning. Coffee at 10am?",
        timestamp: '2026-01-05T09:47:00Z',
        read: true,
    },
    {
        id: 'msg-3',
        platform: 'whatsapp',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Perfect! ☕ See you then",
        timestamp: '2026-01-05T09:48:00Z',
        read: true,
    },
    {
        id: 'msg-4',
        platform: 'slack',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Quick update on the design review - the team loved the new dashboard mockups! 🎉",
        timestamp: '2026-01-04T16:30:00Z',
        read: true,
        channel: '#product-design',
    },
    {
        id: 'msg-5',
        platform: 'slack',
        sender: 'You',
        isMe: true,
        content: "That's amazing news! I'll share the Figma link in the channel for everyone to comment.",
        timestamp: '2026-01-04T16:35:00Z',
        read: true,
        channel: '#product-design',
    },
    {
        id: 'msg-6',
        platform: 'gmail',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Hi,\n\nAttached is the updated Q4 Product Roadmap with the changes we discussed in yesterday's meeting.\n\nKey highlights:\n• Mobile app launch pushed to Feb 15\n• Analytics dashboard ready for beta testing next week\n• Customer feedback integration complete\n\nLet me know if you have any questions!\n\nBest,\nSarah",
        timestamp: '2026-01-04T14:20:00Z',
        read: true,
        subject: 'RE: Q4 Product Roadmap - Updated Timeline',
        hasAttachment: true,
        attachmentName: 'Q4_Roadmap_v3.pdf',
    },
    {
        id: 'msg-7',
        platform: 'gmail',
        sender: 'You',
        isMe: true,
        content: "Thanks Sarah! This looks great. I've reviewed the timeline and have a few thoughts on the mobile launch date. Can we push it to Feb 22 to allow more time for QA?\n\nI'll update the stakeholder deck accordingly.",
        timestamp: '2026-01-04T15:10:00Z',
        read: true,
        subject: 'RE: Q4 Product Roadmap - Updated Timeline',
    },
    {
        id: 'msg-8',
        platform: 'whatsapp',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Just sent you the roadmap doc via email. Let me know what you think!",
        timestamp: '2026-01-04T14:25:00Z',
        read: true,
    },
    {
        id: 'msg-9',
        platform: 'discord',
        sender: 'Sarah Johnson',
        isMe: false,
        content: "Are you joining the gaming session tonight? We need one more for the raid!",
        timestamp: '2026-01-03T19:00:00Z',
        read: true,
        server: 'TechCorp Gaming',
    },
    {
        id: 'msg-10',
        platform: 'discord',
        sender: 'You',
        isMe: true,
        content: "Count me in! I'll be online around 8pm 🎮",
        timestamp: '2026-01-03T19:15:00Z',
        read: true,
        server: 'TechCorp Gaming',
    },
];

export default function UnifiedConversationScreen() {
    const insets = useSafeAreaInsets();
    const router = useRouter();
    const { width } = useWindowDimensions();
    const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (diffDays === 1) return 'Yesterday ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
            date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const filteredMessages = selectedPlatform
        ? UNIFIED_MESSAGES.filter(m => m.platform === selectedPlatform)
        : UNIFIED_MESSAGES;

    return (
        <View style={styles.container}>
            {/* Header */}
            <LinearGradient
                colors={[theme.colors.primary, theme.colors.primaryDark]}
                style={[styles.header, { paddingTop: insets.top + 12 }]}
            >
                <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                    <Ionicons name="arrow-back" size={24} color="white" />
                </TouchableOpacity>

                <View style={styles.contactInfo}>
                    <View style={styles.avatarContainer}>
                        <Text style={styles.avatarText}>{UNIFIED_CONTACT.avatar}</Text>
                        <View style={styles.onlineIndicator} />
                    </View>
                    <View style={styles.contactDetails}>
                        <Text style={styles.contactName}>{UNIFIED_CONTACT.name}</Text>
                        <Text style={styles.contactRole}>{UNIFIED_CONTACT.role} • {UNIFIED_CONTACT.company}</Text>
                        <View style={styles.platformIcons}>
                            {UNIFIED_CONTACT.platforms.map((platform) => {
                                const config = PLATFORM_CONFIG[platform];
                                return (
                                    <View key={platform} style={[styles.miniPlatformBadge, { backgroundColor: config.color }]}>
                                        <Ionicons name={config.icon as any} size={10} color="white" />
                                    </View>
                                );
                            })}
                            <Text style={styles.platformCount}>+{UNIFIED_CONTACT.platforms.length} platforms</Text>
                        </View>
                    </View>
                </View>

                <TouchableOpacity style={styles.menuButton}>
                    <Ionicons name="ellipsis-vertical" size={20} color="white" />
                </TouchableOpacity>
            </LinearGradient>

            {/* Unified Conversation Info Banner */}
            <View style={styles.infoBanner}>
                <Ionicons name="git-merge-outline" size={18} color={theme.colors.primary} />
                <Text style={styles.infoBannerText}>
                    Unified view • {UNIFIED_CONTACT.totalMessages} messages across {UNIFIED_CONTACT.platforms.length} platforms
                </Text>
            </View>

            {/* Platform Filter */}
            <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.platformFilter}
                contentContainerStyle={styles.platformFilterContent}
            >
                <TouchableOpacity
                    style={[styles.filterChip, !selectedPlatform && styles.filterChipActive]}
                    onPress={() => setSelectedPlatform(null)}
                >
                    <Text style={[styles.filterChipText, !selectedPlatform && styles.filterChipTextActive]}>All</Text>
                </TouchableOpacity>
                {UNIFIED_CONTACT.platforms.map((platform) => {
                    const config = PLATFORM_CONFIG[platform];
                    const isSelected = selectedPlatform === platform;
                    return (
                        <TouchableOpacity
                            key={platform}
                            style={[styles.filterChip, isSelected && { backgroundColor: config.color }]}
                            onPress={() => setSelectedPlatform(isSelected ? null : platform)}
                        >
                            <Ionicons name={config.icon as any} size={14} color={isSelected ? 'white' : config.color} />
                            <Text style={[styles.filterChipText, isSelected && styles.filterChipTextActive]}>
                                {config.label}
                            </Text>
                        </TouchableOpacity>
                    );
                })}
            </ScrollView>

            {/* Messages */}
            <ScrollView style={styles.messagesContainer} showsVerticalScrollIndicator={false}>
                {filteredMessages.map((message, index) => {
                    const config = PLATFORM_CONFIG[message.platform];
                    const showDateSeparator = index === 0 ||
                        new Date(message.timestamp).toDateString() !==
                        new Date(filteredMessages[index - 1].timestamp).toDateString();

                    return (
                        <View key={message.id}>
                            {showDateSeparator && (
                                <View style={styles.dateSeparator}>
                                    <Text style={styles.dateSeparatorText}>
                                        {new Date(message.timestamp).toLocaleDateString([], {
                                            weekday: 'long',
                                            month: 'long',
                                            day: 'numeric'
                                        })}
                                    </Text>
                                </View>
                            )}

                            <View style={[
                                styles.messageRow,
                                message.isMe && styles.messageRowMe
                            ]}>
                                {/* Platform indicator */}
                                {!message.isMe && (
                                    <View style={[styles.platformIndicator, { backgroundColor: config.color + '20' }]}>
                                        <Ionicons name={config.icon as any} size={16} color={config.color} />
                                    </View>
                                )}

                                <View style={[
                                    styles.messageBubble,
                                    message.isMe ? styles.messageBubbleMe : styles.messageBubbleOther,
                                    message.platform === 'gmail' && styles.emailBubble
                                ]}>
                                    {/* Platform context for emails/slack */}
                                    {(message.subject || message.channel || message.server) && (
                                        <View style={styles.messageContext}>
                                            <Ionicons name={config.icon as any} size={12} color={config.color} />
                                            <Text style={[styles.contextText, { color: config.color }]}>
                                                {message.subject || message.channel || message.server}
                                            </Text>
                                        </View>
                                    )}

                                    <Text style={[
                                        styles.messageText,
                                        message.isMe && styles.messageTextMe
                                    ]}>
                                        {message.content}
                                    </Text>

                                    {/* Attachment indicator */}
                                    {message.hasAttachment && (
                                        <View style={styles.attachmentRow}>
                                            <Ionicons name="attach" size={14} color={theme.colors.textSecondary} />
                                            <Text style={styles.attachmentName}>{message.attachmentName}</Text>
                                        </View>
                                    )}

                                    <View style={styles.messageFooter}>
                                        <View style={[styles.platformMicroBadge, { backgroundColor: config.color }]}>
                                            <Ionicons name={config.icon as any} size={8} color="white" />
                                        </View>
                                        <Text style={styles.messageTime}>{formatTime(message.timestamp)}</Text>
                                        {message.isMe && (
                                            <Ionicons name="checkmark-done" size={14} color={theme.colors.primary} />
                                        )}
                                    </View>
                                </View>

                                {/* Platform indicator for sent messages */}
                                {message.isMe && (
                                    <View style={[styles.platformIndicator, { backgroundColor: config.color + '20' }]}>
                                        <Ionicons name={config.icon as any} size={16} color={config.color} />
                                    </View>
                                )}
                            </View>
                        </View>
                    );
                })}
                <View style={{ height: insets.bottom + 100 }} />
            </ScrollView>

            {/* Read-only footer */}
            <View style={[styles.footer, { paddingBottom: insets.bottom + 12 }]}>
                <View style={styles.readOnlyBanner}>
                    <Ionicons name="eye-outline" size={18} color={theme.colors.textSecondary} />
                    <Text style={styles.readOnlyText}>
                        View-only mode • Replies coming soon
                    </Text>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingBottom: 16,
    },
    backButton: {
        padding: 8,
        marginRight: 8,
    },
    contactInfo: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    avatarContainer: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
    },
    avatarText: {
        fontSize: 18,
        fontWeight: 'bold',
        color: 'white',
    },
    onlineIndicator: {
        position: 'absolute',
        bottom: 2,
        right: 2,
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: '#10B981',
        borderWidth: 2,
        borderColor: theme.colors.primary,
    },
    contactDetails: {
        flex: 1,
    },
    contactName: {
        fontSize: 18,
        fontWeight: 'bold',
        color: 'white',
    },
    contactRole: {
        fontSize: 13,
        color: 'rgba(255,255,255,0.8)',
        marginTop: 2,
    },
    platformIcons: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 6,
        gap: 4,
    },
    miniPlatformBadge: {
        width: 18,
        height: 18,
        borderRadius: 9,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformCount: {
        fontSize: 11,
        color: 'rgba(255,255,255,0.7)',
        marginLeft: 4,
    },
    menuButton: {
        padding: 8,
    },
    infoBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 10,
        backgroundColor: theme.colors.primaryLighter,
    },
    infoBannerText: {
        fontSize: 13,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    platformFilter: {
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        maxHeight: 56,
    },
    platformFilterContent: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 10,
    },
    filterChip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 14,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: theme.colors.surface,
        marginRight: 8,
        height: 34,
    },
    filterChipActive: {
        backgroundColor: theme.colors.primary,
    },
    filterChipText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    filterChipTextActive: {
        color: 'white',
    },
    messagesContainer: {
        flex: 1,
        padding: 16,
    },
    dateSeparator: {
        alignItems: 'center',
        marginVertical: 16,
    },
    dateSeparatorText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        backgroundColor: theme.colors.backgroundSecondary,
        paddingHorizontal: 16,
        paddingVertical: 4,
        borderRadius: 12,
    },
    messageRow: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        marginBottom: 12,
        gap: 8,
    },
    messageRowMe: {
        flexDirection: 'row-reverse',
    },
    platformIndicator: {
        width: 32,
        height: 32,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
    },
    messageBubble: {
        maxWidth: '75%',
        padding: 12,
        borderRadius: 16,
    },
    messageBubbleMe: {
        backgroundColor: theme.colors.primary,
        borderBottomRightRadius: 4,
    },
    messageBubbleOther: {
        backgroundColor: theme.colors.background,
        borderBottomLeftRadius: 4,
    },
    emailBubble: {
        borderLeftWidth: 3,
        borderLeftColor: '#EA4335',
    },
    messageContext: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginBottom: 8,
        paddingBottom: 8,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    contextText: {
        fontSize: 12,
        fontWeight: '500',
    },
    messageText: {
        fontSize: 15,
        lineHeight: 22,
        color: theme.colors.text,
    },
    messageTextMe: {
        color: 'white',
    },
    attachmentRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginTop: 8,
        paddingTop: 8,
        borderTopWidth: 1,
        borderTopColor: 'rgba(0,0,0,0.1)',
    },
    attachmentName: {
        fontSize: 13,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    messageFooter: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginTop: 8,
    },
    platformMicroBadge: {
        width: 14,
        height: 14,
        borderRadius: 7,
        alignItems: 'center',
        justifyContent: 'center',
    },
    messageTime: {
        fontSize: 11,
        color: theme.colors.textTertiary,
    },
    footer: {
        backgroundColor: theme.colors.background,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        paddingTop: 12,
        paddingHorizontal: 16,
    },
    readOnlyBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
    },
    readOnlyText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
});
