/**
 * Detailed Contact Profile Screen (Section 4.11.4, Figure 4.8)
 * 
 * Shows comprehensive contact intelligence aggregated from communication history.
 * Includes relationship metrics, platform identities, top topics, and AI insights.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Image,
} from 'react-native';
import { useLocalSearchParams, Stack } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_CONTACTS } from '../src/data/dummyData';

const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    gmail: { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    slack: { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    telegram: { icon: 'paper-plane', color: '#0088CC', label: 'Telegram' },
    discord: { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', label: 'WhatsApp' },
};

export default function ContactDetailScreen() {
    const params = useLocalSearchParams();
    const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'files'>('overview');

    // Find contact from dummy data
    const contact = DUMMY_CONTACTS.find(c => c.id === params.id) || DUMMY_CONTACTS[0];

    if (!contact) {
        return (
            <View style={styles.container}>
                <Text>Contact not found</Text>
            </View>
        );
    }

    const getInitials = (name: string) => {
        return name.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2);
    };

    const getRelationshipColor = (strength: number) => {
        if (strength >= 80) return '#10B981';
        if (strength >= 50) return '#F59E0B';
        return '#9CA3AF';
    };

    const getRelationshipLabel = (strength: number) => {
        if (strength >= 80) return 'Close contact';
        if (strength >= 50) return 'Regular contact';
        return 'Infrequent contact';
    };

    const formatFrequencyLabel = (freq: string) => {
        switch (freq.toLowerCase()) {
            case 'high': return 'Multiple messages per week';
            case 'medium': return 'Weekly messages';
            case 'low': return 'Monthly or less';
            default: return freq;
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });
    };

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: '',
                    headerTransparent: true,
                    headerTintColor: 'white',
                }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                {/* Profile Header */}
                <LinearGradient
                    colors={[theme.colors.primary, theme.colors.primaryDark]}
                    style={styles.headerGradient}
                >
                    <View style={styles.profileHeader}>
                        <View style={styles.avatarLarge}>
                            <Text style={styles.avatarTextLarge}>{getInitials(contact.name)}</Text>
                        </View>
                        <Text style={styles.profileName}>{contact.name}</Text>
                        <Text style={styles.profileEmail}>{contact.primaryEmail}</Text>

                        {/* Quick Actions */}
                        <View style={styles.quickActions}>
                            <TouchableOpacity style={styles.quickAction}>
                                <Ionicons name="chatbubble" size={20} color="white" />
                                <Text style={styles.quickActionText}>Message</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={styles.quickAction}>
                                <Ionicons name="search" size={20} color="white" />
                                <Text style={styles.quickActionText}>Search</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={styles.quickAction}>
                                <Ionicons name="download" size={20} color="white" />
                                <Text style={styles.quickActionText}>Export</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </LinearGradient>

                {/* Main Content */}
                <View style={styles.mainContent}>
                    {/* Platform Identities */}
                    <Card style={styles.sectionCard}>
                        <Text style={styles.sectionTitle}>Platform Identities</Text>
                        {Object.entries(contact.platformIdentities).map(([platform, identity]) => {
                            const config = PLATFORM_CONFIG[platform] || { icon: 'chatbubble', color: '#888', label: platform };
                            return (
                                <View key={platform} style={styles.platformRow}>
                                    <View style={[styles.platformIcon, { backgroundColor: config.color + '20' }]}>
                                        <Ionicons name={config.icon as any} size={18} color={config.color} />
                                    </View>
                                    <View style={styles.platformInfo}>
                                        <Text style={styles.platformLabel}>{config.label}</Text>
                                        <Text style={styles.platformIdentity}>{identity}</Text>
                                    </View>
                                    <View style={styles.verifiedBadge}>
                                        <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
                                    </View>
                                </View>
                            );
                        })}
                    </Card>

                    {/* Relationship Metrics */}
                    <Card style={styles.sectionCard}>
                        <Text style={styles.sectionTitle}>Relationship Metrics</Text>

                        {/* Relationship Strength */}
                        <View style={styles.strengthContainer}>
                            <View style={styles.strengthHeader}>
                                <Text style={styles.metricLabel}>Relationship Strength</Text>
                                <Text style={[styles.strengthScore, { color: getRelationshipColor(contact.relationshipStrength) }]}>
                                    {contact.relationshipStrength}/100
                                </Text>
                            </View>
                            <View style={styles.strengthBar}>
                                <View
                                    style={[
                                        styles.strengthFill,
                                        {
                                            width: `${contact.relationshipStrength}%`,
                                            backgroundColor: getRelationshipColor(contact.relationshipStrength),
                                        }
                                    ]}
                                />
                            </View>
                            <Text style={styles.strengthLabel}>
                                {getRelationshipLabel(contact.relationshipStrength)}
                            </Text>
                        </View>

                        {/* Stats Grid */}
                        <View style={styles.statsGrid}>
                            <View style={styles.statBox}>
                                <Text style={styles.statValue}>{contact.totalMessages}</Text>
                                <Text style={styles.statLabel}>Total Messages</Text>
                                <Text style={styles.statDetail}>
                                    ↑ {contact.sentMessages} sent • ↓ {contact.receivedMessages} received
                                </Text>
                            </View>
                            <View style={styles.statBox}>
                                <Text style={styles.statValue}>{contact.avgResponseTime}h</Text>
                                <Text style={styles.statLabel}>Avg Response</Text>
                            </View>
                        </View>

                        {/* Communication Period */}
                        <View style={styles.periodContainer}>
                            <View style={styles.periodRow}>
                                <Ionicons name="calendar" size={16} color={theme.colors.textSecondary} />
                                <Text style={styles.periodLabel}>First interaction:</Text>
                                <Text style={styles.periodValue}>{formatDate(contact.firstInteraction)}</Text>
                            </View>
                            <View style={styles.periodRow}>
                                <Ionicons name="time" size={16} color={theme.colors.textSecondary} />
                                <Text style={styles.periodLabel}>Last interaction:</Text>
                                <Text style={styles.periodValue}>2 hours ago</Text>
                            </View>
                        </View>

                        {/* Frequency */}
                        <View style={styles.frequencyContainer}>
                            <Text style={styles.frequencyLabel}>Communication Frequency</Text>
                            <View style={[
                                styles.frequencyBadge,
                                { backgroundColor: contact.communicationFrequency === 'High' ? '#D1FAE5' : '#FEF3C7' }
                            ]}>
                                <Text style={[
                                    styles.frequencyText,
                                    { color: contact.communicationFrequency === 'High' ? '#10B981' : '#F59E0B' }
                                ]}>
                                    {contact.communicationFrequency} - {formatFrequencyLabel(contact.communicationFrequency)}
                                </Text>
                            </View>
                        </View>
                    </Card>

                    {/* Top Discussion Topics */}
                    <Card style={styles.sectionCard}>
                        <Text style={styles.sectionTitle}>Top Discussion Topics</Text>
                        {contact.topTopics.map((topic, idx) => (
                            <View key={idx} style={styles.topicRow}>
                                <View style={styles.topicInfo}>
                                    <Ionicons name="pricetag" size={16} color={theme.colors.primary} />
                                    <Text style={styles.topicName}>{topic.topic}</Text>
                                </View>
                                <Text style={styles.topicCount}>{topic.count} messages</Text>
                            </View>
                        ))}
                    </Card>

                    {/* Recent Shared Files */}
                    {contact.recentFiles.length > 0 && (
                        <Card style={styles.sectionCard}>
                            <Text style={styles.sectionTitle}>Recent Shared Files</Text>
                            {contact.recentFiles.map((file, idx) => (
                                <View key={idx} style={styles.fileRow}>
                                    <View style={styles.fileIcon}>
                                        <Ionicons name="document-attach" size={18} color={theme.colors.primary} />
                                    </View>
                                    <View style={styles.fileInfo}>
                                        <Text style={styles.fileName}>{file.name}</Text>
                                        <Text style={styles.fileMeta}>
                                            {file.date} via {file.platform}
                                        </Text>
                                    </View>
                                    <TouchableOpacity>
                                        <Ionicons name="download-outline" size={20} color={theme.colors.textSecondary} />
                                    </TouchableOpacity>
                                </View>
                            ))}
                        </Card>
                    )}

                    {/* Active Commitments */}
                    {contact.activeCommitments.length > 0 && (
                        <Card style={styles.sectionCard}>
                            <Text style={styles.sectionTitle}>Active Commitments</Text>
                            {contact.activeCommitments.map((commitment, idx) => (
                                <View key={idx} style={styles.commitmentRow}>
                                    <View style={styles.commitmentCheckbox} />
                                    <View style={styles.commitmentInfo}>
                                        <Text style={styles.commitmentText}>{commitment.description}</Text>
                                        <Text style={styles.commitmentDue}>
                                            Due: {formatDate(commitment.dueDate)}
                                        </Text>
                                    </View>
                                </View>
                            ))}
                        </Card>
                    )}

                    {/* AI-Generated Insights */}
                    <Card style={[styles.sectionCard, styles.insightsCard]}>
                        <View style={styles.insightsHeader}>
                            <Ionicons name="sparkles" size={18} color={theme.colors.primary} />
                            <Text style={styles.insightsTitle}>AI-Generated Insights</Text>
                        </View>
                        {contact.aiInsights.map((insight, idx) => (
                            <View key={idx} style={styles.insightRow}>
                                <View style={styles.insightBullet}>
                                    <Ionicons name="bulb" size={14} color={theme.colors.primary} />
                                </View>
                                <Text style={styles.insightText}>{insight}</Text>
                            </View>
                        ))}
                    </Card>
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
    headerGradient: {
        paddingTop: 100,
        paddingBottom: 30,
        paddingHorizontal: 20,
    },
    profileHeader: {
        alignItems: 'center',
    },
    avatarLarge: {
        width: 100,
        height: 100,
        borderRadius: 50,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
    },
    avatarTextLarge: {
        fontSize: 36,
        fontWeight: 'bold',
        color: 'white',
    },
    profileName: {
        fontSize: 28,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    profileEmail: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.8)',
        marginBottom: 20,
    },
    quickActions: {
        flexDirection: 'row',
        gap: 24,
    },
    quickAction: {
        alignItems: 'center',
        gap: 6,
    },
    quickActionText: {
        fontSize: 12,
        color: 'rgba(255,255,255,0.9)',
    },
    mainContent: {
        padding: 16,
        marginTop: -20,
    },
    sectionCard: {
        marginBottom: 16,
        padding: 20,
        backgroundColor: theme.colors.background,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    platformRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    platformIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformInfo: {
        flex: 1,
        marginLeft: 12,
    },
    platformLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    platformIdentity: {
        fontSize: 15,
        color: theme.colors.text,
        fontWeight: '500',
    },
    verifiedBadge: {
        padding: 4,
    },
    strengthContainer: {
        marginBottom: 20,
    },
    strengthHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    metricLabel: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    strengthScore: {
        fontSize: 18,
        fontWeight: 'bold',
    },
    strengthBar: {
        height: 8,
        backgroundColor: theme.colors.surface,
        borderRadius: 4,
        overflow: 'hidden',
    },
    strengthFill: {
        height: '100%',
        borderRadius: 4,
    },
    strengthLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 6,
    },
    statsGrid: {
        flexDirection: 'row',
        gap: 12,
        marginBottom: 20,
    },
    statBox: {
        flex: 1,
        backgroundColor: theme.colors.surface,
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    statValue: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.primary,
    },
    statLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    statDetail: {
        fontSize: 10,
        color: theme.colors.textTertiary,
        marginTop: 4,
    },
    periodContainer: {
        marginBottom: 16,
    },
    periodRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingVertical: 6,
    },
    periodLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    periodValue: {
        fontSize: 13,
        color: theme.colors.text,
        fontWeight: '500',
    },
    frequencyContainer: {
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    frequencyLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 8,
    },
    frequencyBadge: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        borderRadius: 8,
        alignSelf: 'flex-start',
    },
    frequencyText: {
        fontSize: 13,
        fontWeight: '500',
    },
    topicRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingVertical: 10,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    topicInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    topicName: {
        fontSize: 15,
        color: theme.colors.text,
    },
    topicCount: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    fileRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    fileIcon: {
        width: 40,
        height: 40,
        borderRadius: 8,
        backgroundColor: theme.colors.primaryLighter,
        alignItems: 'center',
        justifyContent: 'center',
    },
    fileInfo: {
        flex: 1,
        marginLeft: 12,
    },
    fileName: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.text,
    },
    fileMeta: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    commitmentRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        paddingVertical: 10,
        gap: 12,
    },
    commitmentCheckbox: {
        width: 20,
        height: 20,
        borderRadius: 4,
        borderWidth: 2,
        borderColor: theme.colors.primary,
        marginTop: 2,
    },
    commitmentInfo: {
        flex: 1,
    },
    commitmentText: {
        fontSize: 15,
        color: theme.colors.text,
    },
    commitmentDue: {
        fontSize: 12,
        color: theme.colors.warning,
        marginTop: 4,
    },
    insightsCard: {
        backgroundColor: theme.colors.primaryLighter,
    },
    insightsHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 16,
    },
    insightsTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    insightRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 12,
        marginBottom: 12,
    },
    insightBullet: {
        marginTop: 2,
    },
    insightText: {
        flex: 1,
        fontSize: 14,
        color: theme.colors.text,
        lineHeight: 20,
    },
});
