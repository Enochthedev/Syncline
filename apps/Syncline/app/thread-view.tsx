/**
 * Thread View with AI Summary (Section 4.11.5, Figure 4.9)
 * 
 * Complete conversation thread with multiple participants and AI-powered summarization.
 * Shows thread management with decisions made, action items, and key points.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
} from 'react-native';
import { Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_THREADS } from '../src/data/dummyData';

const PLATFORM_CONFIG: Record<string, { icon: string; color: string }> = {
    gmail: { icon: 'mail', color: '#EA4335' },
    slack: { icon: 'logo-slack', color: '#4A154B' },
    discord: { icon: 'logo-discord', color: '#5865F2' },
};

export default function ThreadViewScreen() {
    const [summaryExpanded, setSummaryExpanded] = useState(true);

    // Use first dummy thread
    const thread = DUMMY_THREADS[0];
    const platformConfig = PLATFORM_CONFIG[thread.platform] || { icon: 'chatbubble', color: theme.colors.textSecondary };

    const getInitials = (name: string) => {
        return name.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        });
    };

    const getAvatarColor = (name: string) => {
        const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'];
        const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return colors[hash % colors.length];
    };

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: thread.title,
                    headerRight: () => (
                        <TouchableOpacity style={{ padding: 8 }}>
                            <Ionicons name="ellipsis-horizontal" size={22} color={theme.colors.text} />
                        </TouchableOpacity>
                    ),
                }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                {/* Thread Header */}
                <View style={styles.threadHeader}>
                    <View style={styles.headerTop}>
                        <View style={[styles.platformBadge, { backgroundColor: platformConfig.color + '20' }]}>
                            <Ionicons name={platformConfig.icon as any} size={16} color={platformConfig.color} />
                            <Text style={[styles.platformText, { color: platformConfig.color }]}>
                                {thread.platform.charAt(0).toUpperCase() + thread.platform.slice(1)}
                            </Text>
                        </View>
                        <Text style={styles.messageCount}>{thread.messageCount} messages</Text>
                    </View>

                    <Text style={styles.threadTitle}>{thread.title}</Text>

                    <Text style={styles.dateRange}>
                        {formatDate(thread.dateRange.start)} - {formatDate(thread.dateRange.end)}
                    </Text>

                    {/* Participants */}
                    <View style={styles.participantsRow}>
                        <View style={styles.avatarStack}>
                            {thread.participants.slice(0, 4).map((participant, idx) => (
                                <View
                                    key={idx}
                                    style={[
                                        styles.stackedAvatar,
                                        {
                                            marginLeft: idx === 0 ? 0 : -10,
                                            backgroundColor: getAvatarColor(participant.name),
                                            zIndex: thread.participants.length - idx,
                                        }
                                    ]}
                                >
                                    <Text style={styles.stackedAvatarText}>
                                        {getInitials(participant.name)}
                                    </Text>
                                </View>
                            ))}
                        </View>
                        <Text style={styles.participantsText}>
                            {thread.participants.map(p => p.name.split(' ')[0]).join(', ')}
                        </Text>
                    </View>
                </View>

                {/* AI Summary Panel */}
                <Card style={styles.summaryCard}>
                    <TouchableOpacity
                        style={styles.summaryHeader}
                        onPress={() => setSummaryExpanded(!summaryExpanded)}
                    >
                        <View style={styles.summaryHeaderLeft}>
                            <View style={styles.aiBadge}>
                                <Ionicons name="sparkles" size={14} color="white" />
                            </View>
                            <Text style={styles.summaryTitle}>AI-Generated Summary</Text>
                        </View>
                        <Ionicons
                            name={summaryExpanded ? 'chevron-up' : 'chevron-down'}
                            size={20}
                            color={theme.colors.textSecondary}
                        />
                    </TouchableOpacity>

                    {summaryExpanded && (
                        <View style={styles.summaryContent}>
                            {/* Overview */}
                            <View style={styles.summarySection}>
                                <Text style={styles.summarySectionTitle}>Overview</Text>
                                <Text style={styles.summaryText}>{thread.aiSummary.overview}</Text>
                            </View>

                            {/* Key Points */}
                            <View style={styles.summarySection}>
                                <Text style={styles.summarySectionTitle}>Key Points</Text>
                                {thread.aiSummary.keyPoints.map((point, idx) => (
                                    <View key={idx} style={styles.keyPointRow}>
                                        <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
                                        <Text style={styles.keyPointText}>{point}</Text>
                                    </View>
                                ))}
                            </View>

                            {/* Decisions Made */}
                            <View style={styles.summarySection}>
                                <Text style={styles.summarySectionTitle}>Decisions Made</Text>
                                {thread.aiSummary.decisions.map((decision, idx) => (
                                    <View key={idx} style={styles.decisionRow}>
                                        <View style={[
                                            styles.decisionIcon,
                                            decision.status === 'completed'
                                                ? styles.decisionCompleted
                                                : styles.decisionPending
                                        ]}>
                                            <Ionicons
                                                name={decision.status === 'completed' ? 'checkmark' : 'time'}
                                                size={12}
                                                color="white"
                                            />
                                        </View>
                                        <Text style={styles.decisionText}>{decision.text}</Text>
                                    </View>
                                ))}
                            </View>

                            {/* Action Items */}
                            <View style={styles.summarySection}>
                                <Text style={styles.summarySectionTitle}>Action Items</Text>
                                {thread.aiSummary.actionItems.map((item, idx) => (
                                    <View key={idx} style={styles.actionItemRow}>
                                        <View style={[
                                            styles.checkbox,
                                            item.completed && styles.checkboxCompleted
                                        ]}>
                                            {item.completed && (
                                                <Ionicons name="checkmark" size={12} color="white" />
                                            )}
                                        </View>
                                        <View style={styles.actionItemContent}>
                                            <Text style={[
                                                styles.actionItemText,
                                                item.completed && styles.actionItemCompleted
                                            ]}>
                                                <Text style={styles.assignee}>{item.assignee}: </Text>
                                                {item.task}
                                            </Text>
                                        </View>
                                    </View>
                                ))}
                            </View>
                        </View>
                    )}
                </Card>

                {/* Messages Section */}
                <View style={styles.messagesSection}>
                    <Text style={styles.messagesSectionTitle}>Conversation</Text>

                    {thread.messages.map((message, idx) => {
                        const isCurrentUser = message.sender === 'Alex Wave';
                        const avatarColor = getAvatarColor(message.sender);

                        return (
                            <View key={message.id} style={styles.messageContainer}>
                                {/* Avatar */}
                                {!isCurrentUser && (
                                    <View style={[styles.messageAvatar, { backgroundColor: avatarColor }]}>
                                        <Text style={styles.messageAvatarText}>
                                            {getInitials(message.sender)}
                                        </Text>
                                    </View>
                                )}

                                {/* Message Content */}
                                <View style={[
                                    styles.messageBubble,
                                    isCurrentUser ? styles.messageBubbleRight : styles.messageBubbleLeft
                                ]}>
                                    {!isCurrentUser && (
                                        <Text style={styles.messageSender}>{message.sender}</Text>
                                    )}
                                    <Text style={styles.messageText}>{message.content}</Text>

                                    {/* Attachments */}
                                    {message.attachments && message.attachments.length > 0 && (
                                        <View style={styles.attachmentContainer}>
                                            {message.attachments.map((attachment, attIdx) => (
                                                <TouchableOpacity key={attIdx} style={styles.attachmentRow}>
                                                    <Ionicons name="document-attach" size={16} color={theme.colors.primary} />
                                                    <Text style={styles.attachmentName}>{attachment.name}</Text>
                                                    <Text style={styles.attachmentSize}>{attachment.size}</Text>
                                                </TouchableOpacity>
                                            ))}
                                        </View>
                                    )}

                                    <Text style={styles.messageTime}>{formatTime(message.timestamp)}</Text>
                                </View>

                                {isCurrentUser && (
                                    <View style={[styles.messageAvatar, { backgroundColor: theme.colors.primary }]}>
                                        <Text style={styles.messageAvatarText}>AW</Text>
                                    </View>
                                )}
                            </View>
                        );
                    })}
                </View>

                <View style={{ height: 100 }} />
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    content: {
        flex: 1,
    },
    threadHeader: {
        backgroundColor: theme.colors.background,
        padding: 20,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    headerTop: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    platformBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    platformText: {
        fontSize: 12,
        fontWeight: '600',
    },
    messageCount: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    threadTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 6,
    },
    dateRange: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 16,
    },
    participantsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    avatarStack: {
        flexDirection: 'row',
    },
    stackedAvatar: {
        width: 32,
        height: 32,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: theme.colors.background,
    },
    stackedAvatarText: {
        fontSize: 11,
        fontWeight: 'bold',
        color: 'white',
    },
    participantsText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        flex: 1,
    },
    summaryCard: {
        margin: 16,
        padding: 0,
        backgroundColor: theme.colors.background,
        overflow: 'hidden',
    },
    summaryHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        backgroundColor: theme.colors.primaryLighter,
    },
    summaryHeaderLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    aiBadge: {
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
    },
    summaryTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    summaryContent: {
        padding: 16,
    },
    summarySection: {
        marginBottom: 20,
    },
    summarySectionTitle: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 10,
    },
    summaryText: {
        fontSize: 15,
        color: theme.colors.text,
        lineHeight: 22,
    },
    keyPointRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
        marginBottom: 8,
    },
    keyPointText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.text,
        lineHeight: 20,
    },
    decisionRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        marginBottom: 8,
    },
    decisionIcon: {
        width: 22,
        height: 22,
        borderRadius: 11,
        alignItems: 'center',
        justifyContent: 'center',
    },
    decisionCompleted: {
        backgroundColor: theme.colors.success,
    },
    decisionPending: {
        backgroundColor: theme.colors.warning,
    },
    decisionText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.text,
    },
    actionItemRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
        marginBottom: 10,
    },
    checkbox: {
        width: 20,
        height: 20,
        borderRadius: 4,
        borderWidth: 2,
        borderColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
    },
    checkboxCompleted: {
        backgroundColor: theme.colors.success,
        borderColor: theme.colors.success,
    },
    actionItemContent: {
        flex: 1,
    },
    actionItemText: {
        fontSize: 14,
        color: theme.colors.text,
        lineHeight: 20,
    },
    actionItemCompleted: {
        textDecorationLine: 'line-through',
        color: theme.colors.textSecondary,
    },
    assignee: {
        fontWeight: '600',
    },
    messagesSection: {
        padding: 16,
    },
    messagesSectionTitle: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 16,
    },
    messageContainer: {
        flexDirection: 'row',
        marginBottom: 16,
        gap: 10,
    },
    messageAvatar: {
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: 'center',
        justifyContent: 'center',
    },
    messageAvatarText: {
        fontSize: 12,
        fontWeight: 'bold',
        color: 'white',
    },
    messageBubble: {
        flex: 1,
        maxWidth: '75%',
        padding: 14,
        borderRadius: 16,
    },
    messageBubbleLeft: {
        backgroundColor: theme.colors.background,
        borderBottomLeftRadius: 4,
        marginRight: 46,
    },
    messageBubbleRight: {
        backgroundColor: theme.colors.primaryLighter,
        borderBottomRightRadius: 4,
        marginLeft: 'auto',
    },
    messageSender: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.primary,
        marginBottom: 4,
    },
    messageText: {
        fontSize: 15,
        color: theme.colors.text,
        lineHeight: 22,
    },
    messageTime: {
        fontSize: 11,
        color: theme.colors.textTertiary,
        marginTop: 6,
        textAlign: 'right',
    },
    attachmentContainer: {
        marginTop: 10,
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
        padding: 10,
    },
    attachmentRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    attachmentName: {
        flex: 1,
        fontSize: 13,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    attachmentSize: {
        fontSize: 11,
        color: theme.colors.textTertiary,
    },
});
