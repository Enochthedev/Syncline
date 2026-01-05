/**
 * Unified Message View - Demo Version (Section 4.11.2, Figures 4.3 & 4.4)
 * 
 * Multi-platform message inbox with AI enrichment for documentation screenshots.
 * Shows messages with platform badges, entity extraction, AI summaries, and commitment detection.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Modal,
    TextInput,
    useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_MESSAGES } from '../src/data/dummyData';

const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    gmail: { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    slack: { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    discord: { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', label: 'WhatsApp' },
    telegram: { icon: 'paper-plane', color: '#0088CC', label: 'Telegram' },
};

type Message = typeof DUMMY_MESSAGES[0];

export default function MessagesDemoScreen() {
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const isSmallScreen = width < 375;

    const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
    const [searchQuery, setSearchQuery] = useState('');

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours} hours ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    const getInitials = (name: string) => {
        return name.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2);
    };

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
                <Text style={[styles.headerTitle, isSmallScreen && { fontSize: 24 }]}>Unified Inbox</Text>
                <Text style={styles.headerSubtitle}>
                    All your messages in one place
                </Text>

                {/* Search Bar */}
                <View style={styles.searchBar}>
                    <Ionicons name="search" size={18} color={theme.colors.textTertiary} />
                    <TextInput
                        style={styles.searchInput}
                        placeholder="Search messages..."
                        placeholderTextColor={theme.colors.textTertiary}
                        value={searchQuery}
                        onChangeText={setSearchQuery}
                    />
                </View>

                {/* Platform Filters */}
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.platformFilters}>
                    <TouchableOpacity style={[styles.filterChip, styles.filterChipActive]}>
                        <Text style={[styles.filterChipText, styles.filterChipTextActive]}>All</Text>
                    </TouchableOpacity>
                    {Object.entries(PLATFORM_CONFIG).map(([key, config]) => (
                        <TouchableOpacity key={key} style={styles.filterChip}>
                            <Ionicons name={config.icon as any} size={14} color={config.color} />
                            <Text style={styles.filterChipText}>{config.label}</Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>
            </View>

            {/* Messages List */}
            <ScrollView style={styles.messagesList} showsVerticalScrollIndicator={false}>
                {DUMMY_MESSAGES.map((message) => {
                    const platform = PLATFORM_CONFIG[message.platform] ||
                        { icon: 'chatbubble', color: theme.colors.textSecondary, label: message.platform };

                    return (
                        <TouchableOpacity
                            key={message.id}
                            activeOpacity={0.8}
                            onPress={() => setSelectedMessage(message)}
                        >
                            <Card style={[
                                styles.messageCard,
                                !message.isRead && styles.unreadCard
                            ]}>
                                <View style={styles.messageContent}>
                                    {/* Avatar */}
                                    <View style={[styles.avatar, { backgroundColor: platform.color + '20' }]}>
                                        <Text style={[styles.avatarText, { color: platform.color }]}>
                                            {getInitials(message.sender)}
                                        </Text>
                                    </View>

                                    {/* Message Info */}
                                    <View style={styles.messageInfo}>
                                        <View style={styles.messageHeader}>
                                            <View style={styles.senderRow}>
                                                <Text style={[
                                                    styles.senderName,
                                                    !message.isRead && styles.unreadText
                                                ]}>
                                                    {message.sender}
                                                </Text>
                                                {!message.isRead && <View style={styles.unreadDot} />}
                                            </View>
                                            <Text style={styles.messageTime}>{formatTime(message.timestamp)}</Text>
                                        </View>

                                        {message.subject && (
                                            <Text style={styles.messageSubject} numberOfLines={1}>
                                                {message.subject}
                                            </Text>
                                        )}

                                        <Text style={styles.messagePreview} numberOfLines={2}>
                                            {message.preview}
                                        </Text>

                                        {/* Message Meta */}
                                        <View style={styles.messageMeta}>
                                            <View style={[styles.platformBadge, { backgroundColor: platform.color + '15' }]}>
                                                <Ionicons name={platform.icon as any} size={12} color={platform.color} />
                                                <Text style={[styles.platformLabel, { color: platform.color }]}>
                                                    {platform.label}
                                                </Text>
                                            </View>

                                            {message.threadCount > 0 && (
                                                <View style={styles.threadBadge}>
                                                    <Ionicons name="chatbubbles" size={12} color={theme.colors.textSecondary} />
                                                    <Text style={styles.threadCount}>{message.threadCount}</Text>
                                                </View>
                                            )}

                                            {message.hasAttachment && (
                                                <Ionicons name="attach" size={14} color={theme.colors.textSecondary} />
                                            )}
                                        </View>
                                    </View>
                                </View>
                            </Card>
                        </TouchableOpacity>
                    );
                })}

                <View style={{ height: insets.bottom + 40 }} />
            </ScrollView>

            {/* Message Detail Modal */}
            <Modal
                visible={!!selectedMessage}
                animationType="slide"
                presentationStyle="pageSheet"
                onRequestClose={() => setSelectedMessage(null)}
            >
                {selectedMessage && (
                    <View style={styles.modalContainer}>
                        {/* Modal Header */}
                        <View style={[styles.modalHeader, { paddingTop: insets.top + 10 }]}>
                            <TouchableOpacity onPress={() => setSelectedMessage(null)} style={styles.modalBackButton}>
                                <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                            </TouchableOpacity>
                            <Text style={styles.modalTitle}>Message Details</Text>
                            <TouchableOpacity>
                                <Ionicons name="ellipsis-horizontal" size={24} color={theme.colors.text} />
                            </TouchableOpacity>
                        </View>

                        <ScrollView style={styles.modalContent}>
                            {/* Header Section */}
                            <View style={styles.detailHeader}>
                                <View style={styles.detailSenderRow}>
                                    <View style={[styles.detailAvatar, { backgroundColor: selectedMessage.platformColor + '20' }]}>
                                        <Text style={[styles.detailAvatarText, { color: selectedMessage.platformColor }]}>
                                            {getInitials(selectedMessage.sender)}
                                        </Text>
                                    </View>
                                    <View style={styles.detailSenderInfo}>
                                        <Text style={styles.detailSenderName}>{selectedMessage.sender}</Text>
                                        {selectedMessage.senderEmail && (
                                            <Text style={styles.detailSenderEmail}>{selectedMessage.senderEmail}</Text>
                                        )}
                                    </View>
                                    <View style={[styles.platformBadgeLarge, { backgroundColor: selectedMessage.platformColor + '15' }]}>
                                        <Ionicons
                                            name={PLATFORM_CONFIG[selectedMessage.platform]?.icon as any || 'chatbubble'}
                                            size={16}
                                            color={selectedMessage.platformColor}
                                        />
                                    </View>
                                </View>

                                {selectedMessage.subject && (
                                    <Text style={styles.detailSubject}>{selectedMessage.subject}</Text>
                                )}

                                <Text style={styles.detailTimestamp}>
                                    {new Date(selectedMessage.timestamp).toLocaleString('en-US', {
                                        weekday: 'long',
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric',
                                        hour: 'numeric',
                                        minute: '2-digit',
                                    })}
                                </Text>

                                {selectedMessage.recipients && (
                                    <View style={styles.recipientsRow}>
                                        <Text style={styles.recipientsLabel}>To:</Text>
                                        <Text style={styles.recipientsList}>
                                            {selectedMessage.recipients.join(', ')}
                                        </Text>
                                    </View>
                                )}
                            </View>

                            {/* Content Section */}
                            <View style={styles.detailContent}>
                                <Text style={styles.messageFullText}>{selectedMessage.content}</Text>

                                {/* Attachments */}
                                {selectedMessage.attachments && selectedMessage.attachments.length > 0 && (
                                    <View style={styles.attachmentsContainer}>
                                        {selectedMessage.attachments.map((att, idx) => (
                                            <TouchableOpacity key={idx} style={styles.attachmentItem}>
                                                <Ionicons name="document-attach" size={18} color={theme.colors.primary} />
                                                <View style={styles.attachmentInfo}>
                                                    <Text style={styles.attachmentName}>{att.name}</Text>
                                                    <Text style={styles.attachmentSize}>{att.size}</Text>
                                                </View>
                                                <Ionicons name="download-outline" size={18} color={theme.colors.textSecondary} />
                                            </TouchableOpacity>
                                        ))}
                                    </View>
                                )}
                            </View>

                            {/* Metadata Panel (AI Enrichment) */}
                            <View style={styles.metadataPanel}>
                                <Text style={styles.metadataPanelTitle}>AI-Extracted Insights</Text>

                                {/* Entities */}
                                <View style={styles.metadataSection}>
                                    <Text style={styles.metadataLabel}>Detected Entities</Text>
                                    <View style={styles.entitiesGrid}>
                                        {selectedMessage.entities.people.map((person, idx) => (
                                            <View key={`person-${idx}`} style={[styles.entityTag, styles.personTag]}>
                                                <Ionicons name="person" size={10} color="#3B82F6" />
                                                <Text style={styles.entityTagText}>{person}</Text>
                                                <Text style={styles.entityType}>PERSON</Text>
                                            </View>
                                        ))}
                                        {selectedMessage.entities.topics.map((topic, idx) => (
                                            <View key={`topic-${idx}`} style={[styles.entityTag, styles.topicTag]}>
                                                <Ionicons name="pricetag" size={10} color="#8B5CF6" />
                                                <Text style={styles.entityTagText}>{topic}</Text>
                                                <Text style={styles.entityType}>TOPIC</Text>
                                            </View>
                                        ))}
                                        {selectedMessage.entities.dates.map((date, idx) => (
                                            <View key={`date-${idx}`} style={[styles.entityTag, styles.dateTag]}>
                                                <Ionicons name="calendar" size={10} color="#10B981" />
                                                <Text style={styles.entityTagText}>{date}</Text>
                                                <Text style={styles.entityType}>DATE</Text>
                                            </View>
                                        ))}
                                    </View>
                                </View>

                                {/* AI Summary */}
                                {selectedMessage.aiSummary && (
                                    <View style={styles.metadataSection}>
                                        <Text style={styles.metadataLabel}>AI-Generated Summary</Text>
                                        <View style={styles.summaryBox}>
                                            <Ionicons name="sparkles" size={16} color={theme.colors.primary} />
                                            <Text style={styles.summaryText}>{selectedMessage.aiSummary}</Text>
                                        </View>
                                    </View>
                                )}

                                {/* Commitments */}
                                {selectedMessage.commitments && selectedMessage.commitments.length > 0 && (
                                    <View style={styles.metadataSection}>
                                        <Text style={styles.metadataLabel}>Detected Commitments</Text>
                                        {selectedMessage.commitments.map((commitment, idx) => (
                                            <View key={idx} style={styles.commitmentBox}>
                                                <Ionicons name="checkbox-outline" size={16} color={theme.colors.warning} />
                                                <Text style={styles.commitmentText}>{commitment}</Text>
                                            </View>
                                        ))}
                                    </View>
                                )}

                                {/* Thread Context */}
                                {selectedMessage.threadCount > 0 && (
                                    <TouchableOpacity style={styles.threadLink}>
                                        <Ionicons name="chatbubbles" size={16} color={theme.colors.primary} />
                                        <Text style={styles.threadLinkText}>
                                            View full thread ({selectedMessage.threadCount} messages)
                                        </Text>
                                        <Ionicons name="arrow-forward" size={16} color={theme.colors.primary} />
                                    </TouchableOpacity>
                                )}
                            </View>
                        </ScrollView>
                    </View>
                )}
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        padding: 20,
        paddingTop: 20,
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    headerSubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginTop: 4,
        marginBottom: 16,
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 14,
        paddingVertical: 12,
        gap: 10,
    },
    searchInput: {
        flex: 1,
        fontSize: 15,
        color: theme.colors.text,
    },
    platformFilters: {
        marginTop: 16,
        marginHorizontal: -20,
        paddingHorizontal: 20,
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
    messagesList: {
        flex: 1,
        padding: 16,
    },
    messageCard: {
        marginBottom: 12,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    unreadCard: {
        borderLeftWidth: 3,
        borderLeftColor: theme.colors.primary,
    },
    messageContent: {
        flexDirection: 'row',
        gap: 12,
    },
    avatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 16,
        fontWeight: 'bold',
    },
    messageInfo: {
        flex: 1,
    },
    messageHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 4,
    },
    senderRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        flex: 1,
    },
    senderName: {
        fontSize: 15,
        fontWeight: '500',
        color: theme.colors.text,
    },
    unreadText: {
        fontWeight: '700',
    },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: theme.colors.primary,
    },
    messageTime: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    messageSubject: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 4,
    },
    messagePreview: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        marginBottom: 8,
    },
    messageMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    platformBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 10,
    },
    platformLabel: {
        fontSize: 11,
        fontWeight: '500',
    },
    threadBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    threadCount: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    modalContainer: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    modalHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        paddingTop: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    modalBackButton: {
        padding: 4,
    },
    modalTitle: {
        fontSize: 17,
        fontWeight: '600',
        color: theme.colors.text,
    },
    modalContent: {
        flex: 1,
    },
    detailHeader: {
        padding: 20,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    detailSenderRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    detailAvatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    detailAvatarText: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    detailSenderInfo: {
        flex: 1,
        marginLeft: 12,
    },
    detailSenderName: {
        fontSize: 17,
        fontWeight: '600',
        color: theme.colors.text,
    },
    detailSenderEmail: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    platformBadgeLarge: {
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: 'center',
        justifyContent: 'center',
    },
    detailSubject: {
        fontSize: 20,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 8,
    },
    detailTimestamp: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    recipientsRow: {
        flexDirection: 'row',
        marginTop: 8,
    },
    recipientsLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginRight: 4,
    },
    recipientsList: {
        fontSize: 13,
        color: theme.colors.text,
    },
    detailContent: {
        padding: 20,
    },
    messageFullText: {
        fontSize: 16,
        color: theme.colors.text,
        lineHeight: 24,
    },
    attachmentsContainer: {
        marginTop: 16,
    },
    attachmentItem: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 10,
        gap: 10,
        marginBottom: 8,
    },
    attachmentInfo: {
        flex: 1,
    },
    attachmentName: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.text,
    },
    attachmentSize: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    metadataPanel: {
        margin: 16,
        padding: 16,
        backgroundColor: theme.colors.surface,
        borderRadius: 16,
    },
    metadataPanelTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    metadataSection: {
        marginBottom: 16,
    },
    metadataLabel: {
        fontSize: 11,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 8,
    },
    entitiesGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 6,
    },
    entityTag: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    personTag: {
        backgroundColor: '#DBEAFE',
    },
    topicTag: {
        backgroundColor: '#EDE9FE',
    },
    dateTag: {
        backgroundColor: '#D1FAE5',
    },
    entityTagText: {
        fontSize: 12,
        color: theme.colors.text,
        fontWeight: '500',
    },
    entityType: {
        fontSize: 9,
        color: theme.colors.textSecondary,
        fontWeight: '600',
        marginLeft: 4,
    },
    summaryBox: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 10,
        padding: 12,
        backgroundColor: theme.colors.primaryLighter,
        borderRadius: 10,
    },
    summaryText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.text,
        lineHeight: 20,
    },
    commitmentBox: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        padding: 12,
        backgroundColor: '#FEF3C7',
        borderRadius: 10,
    },
    commitmentText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.text,
    },
    threadLink: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    threadLinkText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.primary,
        fontWeight: '500',
    },
});
