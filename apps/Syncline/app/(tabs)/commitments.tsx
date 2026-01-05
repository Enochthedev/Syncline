/**
 * Commitment Tracking Screen (Section 4.11.6)
 * 
 * Displays all detected obligations and deadlines extracted from messages.
 * Shows commitment status (pending, overdue, completed) with source context.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Modal,
    useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';
import { DUMMY_COMMITMENTS } from '../../src/data/dummyData';

type CommitmentStatus = 'overdue' | 'pending' | 'completed';
type FilterOption = 'all' | 'pending' | 'completed' | 'overdue';

const STATUS_CONFIG: Record<CommitmentStatus, { color: string; bgColor: string; icon: string; label: string }> = {
    overdue: { color: '#EF4444', bgColor: '#FEE2E2', icon: 'alert-circle', label: 'Overdue' },
    pending: { color: '#F59E0B', bgColor: '#FEF3C7', icon: 'time', label: 'Pending' },
    completed: { color: '#10B981', bgColor: '#D1FAE5', icon: 'checkmark-circle', label: 'Completed' },
};

const PLATFORM_ICONS: Record<string, string> = {
    'Slack': 'logo-slack',
    'Gmail': 'mail',
    'Discord': 'logo-discord',
    'WhatsApp': 'logo-whatsapp',
};

export default function CommitmentsScreen() {
    const insets = useSafeAreaInsets();
    const { width } = useWindowDimensions();
    const isSmallScreen = width < 375;

    const [filter, setFilter] = useState<FilterOption>('all');
    const [selectedCommitment, setSelectedCommitment] = useState<typeof DUMMY_COMMITMENTS[0] | null>(null);

    // Stats
    const stats = {
        pending: DUMMY_COMMITMENTS.filter(c => c.status === 'pending').length,
        overdue: DUMMY_COMMITMENTS.filter(c => c.status === 'overdue').length,
        completed: DUMMY_COMMITMENTS.filter(c => c.status === 'completed').length,
    };

    // Filtered commitments
    const filteredCommitments = filter === 'all'
        ? DUMMY_COMMITMENTS
        : DUMMY_COMMITMENTS.filter(c => c.status === filter);

    const formatDueDate = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

        if (diffDays < 0) {
            return `${Math.abs(diffDays)} days ago`;
        } else if (diffDays === 0) {
            return 'Today';
        } else if (diffDays === 1) {
            return 'Tomorrow';
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
    };

    const getStatusBorderColor = (status: CommitmentStatus) => {
        switch (status) {
            case 'overdue': return '#EF4444';
            case 'pending': return '#F59E0B';
            case 'completed': return '#10B981';
        }
    };

    return (
        <View style={styles.container}>
            {/* Header Stats */}
            <View style={styles.headerStats}>
                <View style={styles.statCard}>
                    <Text style={[styles.statNumber, { color: '#F59E0B' }]}>{stats.pending}</Text>
                    <Text style={styles.statLabel}>Pending</Text>
                </View>
                <View style={[styles.statCard, styles.statCardHighlight]}>
                    <Text style={[styles.statNumber, { color: '#EF4444' }]}>{stats.overdue}</Text>
                    <Text style={styles.statLabel}>Overdue</Text>
                </View>
                <View style={styles.statCard}>
                    <Text style={[styles.statNumber, { color: '#10B981' }]}>{stats.completed}</Text>
                    <Text style={styles.statLabel}>Today</Text>
                </View>
            </View>

            {/* Filter Pills */}
            <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.filterContainer}
                contentContainerStyle={styles.filterContent}
            >
                {(['all', 'pending', 'completed', 'overdue'] as FilterOption[]).map((option) => (
                    <TouchableOpacity
                        key={option}
                        style={[styles.filterPill, filter === option && styles.filterPillActive]}
                        onPress={() => setFilter(option)}
                    >
                        <Text style={[styles.filterText, filter === option && styles.filterTextActive]}>
                            {option.charAt(0).toUpperCase() + option.slice(1)}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {/* Commitments List */}
            <ScrollView style={styles.listContainer} showsVerticalScrollIndicator={false}>
                {filteredCommitments.map((commitment) => {
                    const statusConfig = STATUS_CONFIG[commitment.status];
                    const borderColor = getStatusBorderColor(commitment.status);

                    return (
                        <TouchableOpacity
                            key={commitment.id}
                            activeOpacity={0.8}
                            onPress={() => setSelectedCommitment(commitment)}
                        >
                            <Card
                                style={[
                                    styles.commitmentCard,
                                    { borderLeftWidth: 4, borderLeftColor: borderColor }
                                ]}
                            >
                                {/* Status Badge */}
                                <View style={styles.cardHeader}>
                                    <View style={[styles.statusBadge, { backgroundColor: statusConfig.bgColor }]}>
                                        <Ionicons name={statusConfig.icon as any} size={14} color={statusConfig.color} />
                                        <Text style={[styles.statusText, { color: statusConfig.color }]}>
                                            {statusConfig.label}
                                        </Text>
                                    </View>
                                    <View style={styles.confidenceBadge}>
                                        <Ionicons name="analytics" size={12} color={theme.colors.textSecondary} />
                                        <Text style={styles.confidenceText}>{commitment.confidence}%</Text>
                                    </View>
                                </View>

                                {/* Description */}
                                <Text style={styles.commitmentDescription}>
                                    {commitment.description}
                                </Text>

                                {/* Meta Info */}
                                <View style={styles.metaContainer}>
                                    <View style={styles.metaItem}>
                                        <Ionicons name="calendar-outline" size={14} color={theme.colors.textSecondary} />
                                        <Text style={[
                                            styles.metaText,
                                            commitment.status === 'overdue' && styles.overdueText
                                        ]}>
                                            {formatDueDate(commitment.dueDate)}
                                        </Text>
                                    </View>
                                    <View style={styles.metaItem}>
                                        <Ionicons name="person-outline" size={14} color={theme.colors.textSecondary} />
                                        <Text style={styles.metaText}>{commitment.committedTo}</Text>
                                    </View>
                                </View>

                                {/* Source */}
                                <View style={styles.sourceContainer}>
                                    <Ionicons
                                        name={PLATFORM_ICONS[commitment.sourceMessage.platform] as any || 'chatbubble'}
                                        size={12}
                                        color={theme.colors.textTertiary}
                                    />
                                    <Text style={styles.sourceText}>
                                        View original message
                                    </Text>
                                    <Ionicons name="chevron-forward" size={12} color={theme.colors.textTertiary} />
                                </View>

                                {/* Actions */}
                                <View style={styles.actionsContainer}>
                                    <TouchableOpacity style={styles.actionButton}>
                                        <Ionicons name="checkmark-circle-outline" size={18} color={theme.colors.success} />
                                        <Text style={[styles.actionText, { color: theme.colors.success }]}>Complete</Text>
                                    </TouchableOpacity>
                                    <TouchableOpacity style={styles.actionButton}>
                                        <Ionicons name="calendar-outline" size={18} color={theme.colors.primary} />
                                        <Text style={[styles.actionText, { color: theme.colors.primary }]}>Reschedule</Text>
                                    </TouchableOpacity>
                                    <TouchableOpacity style={styles.actionButton}>
                                        <Ionicons name="close-circle-outline" size={18} color={theme.colors.textSecondary} />
                                        <Text style={styles.actionText}>Dismiss</Text>
                                    </TouchableOpacity>
                                </View>
                            </Card>
                        </TouchableOpacity>
                    );
                })}
                <View style={{ height: insets.bottom + 40 }} />
            </ScrollView>

            {/* Commitment Detail Modal */}
            <Modal
                visible={!!selectedCommitment}
                animationType="slide"
                presentationStyle="pageSheet"
                onRequestClose={() => setSelectedCommitment(null)}
            >
                {selectedCommitment && (
                    <View style={styles.modalContainer}>
                        <View style={[styles.modalHeader, { paddingTop: insets.top + 8 }]}>
                            <Text style={styles.modalTitle}>Commitment Details</Text>
                            <TouchableOpacity
                                onPress={() => setSelectedCommitment(null)}
                                style={styles.closeButton}
                            >
                                <Ionicons name="close" size={24} color={theme.colors.text} />
                            </TouchableOpacity>
                        </View>

                        <ScrollView style={styles.modalContent}>
                            {/* Full Description */}
                            <View style={styles.detailSection}>
                                <Text style={styles.detailLabel}>Full Description</Text>
                                <Text style={styles.detailValue}>{selectedCommitment.fullDescription}</Text>
                            </View>

                            {/* Due Date */}
                            <View style={styles.detailSection}>
                                <Text style={styles.detailLabel}>Due Date</Text>
                                <Text style={styles.detailValue}>
                                    {new Date(selectedCommitment.dueDate).toLocaleDateString('en-US', {
                                        weekday: 'long',
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric',
                                        hour: 'numeric',
                                        minute: '2-digit',
                                    })}
                                </Text>
                            </View>

                            {/* Committed To */}
                            <View style={styles.detailRow}>
                                <View style={styles.detailHalf}>
                                    <Text style={styles.detailLabel}>Committed By</Text>
                                    <Text style={styles.detailValue}>{selectedCommitment.committedBy}</Text>
                                </View>
                                <View style={styles.detailHalf}>
                                    <Text style={styles.detailLabel}>Committed To</Text>
                                    <Text style={styles.detailValue}>{selectedCommitment.committedTo}</Text>
                                </View>
                            </View>

                            {/* Confidence */}
                            <View style={styles.detailSection}>
                                <Text style={styles.detailLabel}>Confidence Score</Text>
                                <View style={styles.confidenceDetail}>
                                    <View style={styles.confidenceBar}>
                                        <View style={[styles.confidenceFill, { width: `${selectedCommitment.confidence}%` }]} />
                                    </View>
                                    <Text style={styles.confidencePercent}>{selectedCommitment.confidence}%</Text>
                                </View>
                            </View>

                            {/* Source Message Context */}
                            <View style={styles.detailSection}>
                                <Text style={styles.detailLabel}>Source Message Context</Text>
                                <View style={styles.contextBox}>
                                    <View style={styles.contextHeader}>
                                        <Ionicons
                                            name={PLATFORM_ICONS[selectedCommitment.sourceMessage.platform] as any || 'chatbubble'}
                                            size={16}
                                            color={theme.colors.primary}
                                        />
                                        <Text style={styles.contextPlatform}>
                                            {selectedCommitment.sourceMessage.platform}
                                        </Text>
                                        <Text style={styles.contextDate}>
                                            {new Date(selectedCommitment.sourceMessage.timestamp).toLocaleString()}
                                        </Text>
                                    </View>
                                    {selectedCommitment.sourceMessage.context.map((msg, idx) => (
                                        <View key={idx} style={styles.contextMessage}>
                                            <Text style={styles.contextSender}>{msg.sender}:</Text>
                                            <Text style={styles.contextContent}>{msg.content}</Text>
                                        </View>
                                    ))}
                                </View>
                            </View>

                            {/* Detected Patterns */}
                            <View style={styles.detailSection}>
                                <Text style={styles.detailLabel}>Detected Patterns</Text>
                                <View style={styles.patternsBox}>
                                    <View style={styles.patternRow}>
                                        <Text style={styles.patternLabel}>Commitment phrase:</Text>
                                        <Text style={styles.patternValue}>"{selectedCommitment.patterns.commitmentPhrase}"</Text>
                                    </View>
                                    <View style={styles.patternRow}>
                                        <Text style={styles.patternLabel}>Recipient:</Text>
                                        <Text style={styles.patternValue}>"{selectedCommitment.patterns.recipient}"</Text>
                                    </View>
                                    <View style={styles.patternRow}>
                                        <Text style={styles.patternLabel}>Deadline:</Text>
                                        <Text style={styles.patternValue}>"{selectedCommitment.patterns.deadline}"</Text>
                                    </View>
                                    <View style={styles.patternRow}>
                                        <Text style={styles.patternLabel}>Date resolution:</Text>
                                        <Text style={styles.patternValue}>{selectedCommitment.patterns.dateResolution}</Text>
                                    </View>
                                </View>
                            </View>
                        </ScrollView>

                        {/* Modal Actions */}
                        <View style={styles.modalActions}>
                            <TouchableOpacity style={styles.modalActionPrimary}>
                                <Ionicons name="checkmark-circle" size={20} color="white" />
                                <Text style={styles.modalActionPrimaryText}>Mark as Complete</Text>
                            </TouchableOpacity>
                            <View style={styles.modalSecondaryActions}>
                                <TouchableOpacity style={styles.modalActionSecondary}>
                                    <Text style={styles.modalActionSecondaryText}>Reschedule</Text>
                                </TouchableOpacity>
                                <TouchableOpacity style={styles.modalActionSecondary}>
                                    <Text style={styles.modalActionSecondaryText}>Edit</Text>
                                </TouchableOpacity>
                                <TouchableOpacity style={[styles.modalActionSecondary, styles.modalActionDanger]}>
                                    <Text style={styles.modalActionDangerText}>Dismiss</Text>
                                </TouchableOpacity>
                            </View>
                        </View>
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
    headerStats: {
        flexDirection: 'row',
        paddingHorizontal: 16,
        paddingVertical: 16,
        gap: 12,
        backgroundColor: theme.colors.background,
    },
    statCard: {
        flex: 1,
        alignItems: 'center',
        paddingVertical: 16,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
    },
    statCardHighlight: {
        backgroundColor: '#FEE2E2',
    },
    statNumber: {
        fontSize: 24,
        fontWeight: 'bold',
    },
    statLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    filterContainer: {
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        maxHeight: 60,
    },
    filterContent: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 12,
    },
    filterPill: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: theme.colors.surface,
        marginRight: 8,
        height: 36,
        justifyContent: 'center',
    },
    filterPillActive: {
        backgroundColor: theme.colors.primary,
    },
    filterText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    filterTextActive: {
        color: 'white',
    },
    listContainer: {
        flex: 1,
        padding: 16,
    },
    commitmentCard: {
        marginBottom: 12,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    statusBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
        gap: 4,
    },
    statusText: {
        fontSize: 12,
        fontWeight: '600',
    },
    confidenceBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    confidenceText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    commitmentDescription: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 12,
    },
    metaContainer: {
        flexDirection: 'row',
        gap: 16,
        marginBottom: 12,
    },
    metaItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    metaText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    overdueText: {
        color: '#EF4444',
        fontWeight: '600',
    },
    sourceContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingVertical: 8,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    sourceText: {
        flex: 1,
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    actionsContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        justifyContent: 'flex-start',
        gap: 12,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    actionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingVertical: 4,
        paddingHorizontal: 2,
    },
    actionText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    modalContainer: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    modalHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        paddingTop: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    closeButton: {
        padding: 4,
    },
    modalTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    modalContent: {
        flex: 1,
        padding: 16,
    },
    detailSection: {
        marginBottom: 20,
    },
    detailLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginBottom: 6,
        textTransform: 'uppercase',
    },
    detailValue: {
        fontSize: 16,
        color: theme.colors.text,
    },
    detailRow: {
        flexDirection: 'row',
        gap: 16,
        marginBottom: 20,
    },
    detailHalf: {
        flex: 1,
    },
    confidenceDetail: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    confidenceBar: {
        flex: 1,
        height: 8,
        backgroundColor: theme.colors.surface,
        borderRadius: 4,
        overflow: 'hidden',
    },
    confidenceFill: {
        height: '100%',
        backgroundColor: theme.colors.success,
        borderRadius: 4,
    },
    confidencePercent: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.success,
    },
    contextBox: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
    },
    contextHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 12,
        paddingBottom: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    contextPlatform: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    contextDate: {
        fontSize: 12,
        color: theme.colors.textTertiary,
        marginLeft: 'auto',
    },
    contextMessage: {
        marginBottom: 8,
    },
    contextSender: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    contextContent: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        fontStyle: 'italic',
    },
    patternsBox: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
    },
    patternRow: {
        flexDirection: 'row',
        marginBottom: 8,
    },
    patternLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        width: 130,
    },
    patternValue: {
        flex: 1,
        fontSize: 13,
        color: theme.colors.text,
    },
    modalActions: {
        padding: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    modalActionPrimary: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: theme.colors.success,
        paddingVertical: 14,
        borderRadius: 12,
        marginBottom: 12,
    },
    modalActionPrimaryText: {
        fontSize: 16,
        fontWeight: '600',
        color: 'white',
    },
    modalSecondaryActions: {
        flexDirection: 'row',
        gap: 12,
    },
    modalActionSecondary: {
        flex: 1,
        alignItems: 'center',
        paddingVertical: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
    },
    modalActionSecondaryText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.text,
    },
    modalActionDanger: {
        backgroundColor: '#FEE2E2',
    },
    modalActionDangerText: {
        fontSize: 14,
        fontWeight: '500',
        color: '#EF4444',
    },
});
