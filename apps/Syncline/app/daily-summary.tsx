/**
 * Daily Summary / Communication Digest Screen
 * 
 * AI-generated daily summary providing an overview of the day's communications.
 * Shows activity by contact, action items, new commitments, and patterns.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Dimensions,
    ActivityIndicator,
    RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { aiAPI } from '../src/api/endpoints/ai';
import { messagesAPI } from '../src/api/endpoints/messages';
import { useAuth } from '../src/contexts/AuthContext';

const { width } = Dimensions.get('window');

interface SummaryData {
    overview: {
        totalMessages: number;
        platformsUsed: number;
        uniqueConversations: number;
        activeContacts: number;
        newCommitments: number;
        filesShared: number;
    };
    sentiment: {
        score: number;
        label: 'positive' | 'neutral' | 'negative';
        trend: 'improving' | 'declining' | 'stable';
    };
    topContacts: Array<{
        contact: string;
        messageCount: number;
        sentiment: 'positive' | 'neutral' | 'negative';
        lastInteraction: string;
    }>;
    actionItems: Array<{
        id: string;
        title: string;
        priority: 'High' | 'Medium' | 'Low';
        source: string;
        completed: boolean;
    }>;
}

export default function DailySummaryScreen() {
    const router = useRouter();
    const { isAuthenticated } = useAuth();
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [summaryData, setSummaryData] = useState<SummaryData | null>(null);

    const today = new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });

    const fetchSummaryData = useCallback(async () => {
        if (!isAuthenticated) return;

        try {
            // Calculate date range for "today" (last 24h)
            const endDate = new Date();
            const startDate = new Date();
            startDate.setHours(startDate.getHours() - 24);

            // Fetch messages and patterns in parallel
            const [messagesRes, patternsRes] = await Promise.all([
                messagesAPI.listMessages({
                    start_date: startDate.toISOString(),
                    end_date: endDate.toISOString(),
                    limit: 100
                }),
                aiAPI.analyzePatterns({
                    date_range: {
                        start: startDate.toISOString(),
                        end: endDate.toISOString()
                    }
                }).catch(() => null) // Handle error gracefully if AI service fails
            ]);

            const messages = messagesRes.messages || [];

            // Calculate Overview Stats
            const uniquePlatforms = new Set(messages.map(m => m.platform)).size;
            const uniqueSenders = new Set(messages.map(m => m.sender)).size;
            const uniqueThreads = new Set(messages.map(m => m.thread_id)).size;

            // Build Top Contacts
            const contactCounts: Record<string, number> = {};
            messages.forEach(m => {
                const sender = m.sender || 'Unknown';
                contactCounts[sender] = (contactCounts[sender] || 0) + 1;

                // Simple check for "attached" or "file" in content to simulate file sharing count if metadata missing
                // but real `has_attachments` is available in latest API
            });

            const topContacts = Object.entries(contactCounts)
                .map(([contact, count]) => ({
                    contact,
                    messageCount: count,
                    sentiment: 'neutral' as const, // Default, updated if AI data exists
                    lastInteraction: messages.find(m => m.sender === contact)?.timestamp || new Date().toISOString()
                }))
                .sort((a, b) => b.messageCount - a.messageCount)
                .slice(0, 5);

            // Construct Summary Object
            const data: SummaryData = {
                overview: {
                    totalMessages: messages.length,
                    platformsUsed: uniquePlatforms,
                    uniqueConversations: uniqueThreads,
                    activeContacts: uniqueSenders,
                    newCommitments: 0, // Placeholder until commitments API is ready
                    filesShared: messages.filter(m => m.has_attachments).length
                },
                sentiment: patternsRes?.sentiment_analysis ? {
                    score: patternsRes.sentiment_analysis.sentiment_over_time[0]?.sentiment || 0,
                    label: patternsRes.sentiment_analysis.overall_sentiment,
                    trend: 'stable' // Simplified
                } : {
                    score: 0,
                    label: 'neutral',
                    trend: 'stable'
                },
                topContacts,
                actionItems: [], // Placeholder
            };

            setSummaryData(data);
        } catch (error) {
            console.error('Failed to fetch daily summary:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [isAuthenticated]);

    useEffect(() => {
        fetchSummaryData();
    }, [fetchSummaryData]);

    const onRefresh = () => {
        setRefreshing(true);
        fetchSummaryData();
    };

    if (loading && !refreshing) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
                <Text style={styles.loadingText}>Generating daily summary...</Text>
            </View>
        );
    }

    if (!summaryData && !loading) {
        return (
            <View style={styles.container}>
                <View style={styles.emptyState}>
                    <Ionicons name="stats-chart" size={64} color={theme.colors.textTertiary} />
                    <Text style={styles.emptyTitle}>No Data Available</Text>
                    <Text style={styles.emptyText}>Could not generate summary for today.</Text>
                    <TouchableOpacity style={styles.retryButton} onPress={fetchSummaryData}>
                        <Text style={styles.retryButtonText}>Retry</Text>
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    const summary = summaryData!;

    return (
        <View style={styles.container}>
            {/* Header */}
            <LinearGradient
                colors={[theme.colors.primary, theme.colors.primaryDark]}
                style={styles.header}
            >
                <View style={styles.headerContent}>
                    <View style={styles.aiBadge}>
                        <Ionicons name="sparkles" size={14} color="white" />
                        <Text style={styles.aiBadgeText}>AI Generated</Text>
                    </View>
                    <Text style={styles.headerTitle}>Daily Summary</Text>
                    <Text style={styles.headerDate}>{today}</Text>
                </View>
            </LinearGradient>

            <ScrollView
                style={styles.content}
                showsVerticalScrollIndicator={false}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="white" />}
            >
                {/* Overview Card */}
                <Card style={styles.overviewCard}>
                    <Text style={styles.overviewTitle}>Today's Activity</Text>
                    <View style={styles.statsGrid}>
                        <View style={styles.statItem}>
                            <Text style={styles.statNumber}>{summary.overview.totalMessages}</Text>
                            <Text style={styles.statLabel}>Messages</Text>
                        </View>
                        <View style={styles.statItem}>
                            <Text style={styles.statNumber}>{summary.overview.platformsUsed}</Text>
                            <Text style={styles.statLabel}>Platforms</Text>
                        </View>
                        <View style={styles.statItem}>
                            <Text style={styles.statNumber}>{summary.overview.uniqueConversations}</Text>
                            <Text style={styles.statLabel}>Conversations</Text>
                        </View>
                        <View style={styles.statItem}>
                            <Text style={styles.statNumber}>{summary.overview.activeContacts}</Text>
                            <Text style={styles.statLabel}>Contacts</Text>
                        </View>
                    </View>
                    <View style={styles.overviewFooter}>
                        <View style={styles.overviewBadge}>
                            <Ionicons name="git-commit" size={14} color={theme.colors.primary} />
                            <Text style={styles.overviewBadgeText}>
                                {summary.overview.newCommitments} new commitments
                            </Text>
                        </View>
                        <View style={styles.overviewBadge}>
                            <Ionicons name="document-attach" size={14} color={theme.colors.primary} />
                            <Text style={styles.overviewBadgeText}>
                                {summary.overview.filesShared} files shared
                            </Text>
                        </View>
                    </View>
                </Card>

                {/* Sentiment Analysis */}
                <Text style={styles.sectionHeader}>Sentiment & Mood</Text>
                <Card style={styles.sentimentCard}>
                    <View style={styles.sentimentHeader}>
                        <Text style={styles.sentimentTitle}>Overall Tone</Text>
                        <View style={[styles.trendBadge, {
                            backgroundColor: summary.sentiment.trend === 'improving' ? '#D1FAE5' : '#FEF3C7'
                        }]}>
                            <Ionicons
                                name={summary.sentiment.trend === 'improving' ? 'trending-up' : 'remove'}
                                size={14}
                                color={summary.sentiment.trend === 'improving' ? '#10B981' : '#F59E0B'}
                            />
                            <Text style={[styles.trendText, {
                                color: summary.sentiment.trend === 'improving' ? '#10B981' : '#F59E0B'
                            }]}>
                                {summary.sentiment.trend.charAt(0).toUpperCase() + summary.sentiment.trend.slice(1)}
                            </Text>
                        </View>
                    </View>
                    <Text style={styles.sentimentDescription}>
                        Your communications today were generally {summary.sentiment.label}.
                    </Text>
                </Card>

                {/* Top Contacts */}
                <Text style={styles.sectionHeader}>Top Interactions</Text>
                {summary.topContacts.length === 0 ? (
                    <Text style={styles.noDataText}>No interactions recorded today.</Text>
                ) : (
                    summary.topContacts.map((item, index) => (
                        <Card key={index} style={styles.contactStatCard}>
                            <View style={styles.contactStatLeft}>
                                <View style={styles.avatarPlaceholder}>
                                    <Text style={styles.avatarInitials}>
                                        {item.contact.charAt(0).toUpperCase()}
                                    </Text>
                                </View>
                                <View>
                                    <Text style={styles.contactName}>{item.contact}</Text>
                                    <Text style={styles.lastInteraction}>
                                        {new Date(item.lastInteraction).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </Text>
                                </View>
                            </View>
                            <View style={styles.contactStatRight}>
                                <Text style={styles.messageCount}>{item.messageCount} msgs</Text>
                            </View>
                        </Card>
                    ))
                )}

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
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: theme.colors.backgroundSecondary,
    },
    loadingText: {
        marginTop: 16,
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 32,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
    },
    emptyText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginTop: 8,
    },
    retryButton: {
        marginTop: 24,
        paddingHorizontal: 24,
        paddingVertical: 12,
        backgroundColor: theme.colors.primary,
        borderRadius: 8,
    },
    retryButtonText: {
        color: 'white',
        fontWeight: '600',
    },
    header: {
        paddingTop: 60,
        paddingBottom: 24,
        paddingHorizontal: 20,
        borderBottomLeftRadius: 24,
        borderBottomRightRadius: 24,
    },
    headerContent: {
        alignItems: 'flex-start',
    },
    aiBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
        marginBottom: 12,
        gap: 6,
    },
    aiBadgeText: {
        color: 'white',
        fontSize: 12,
        fontWeight: '600',
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    headerDate: {
        fontSize: 16,
        color: 'rgba(255,255,255,0.9)',
    },
    content: {
        flex: 1,
        padding: 20,
        marginTop: -20,
    },
    overviewCard: {
        padding: 20,
        backgroundColor: 'white',
        marginBottom: 24,
    },
    overviewTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 20,
    },
    statItem: {
        flex: 1,
        minWidth: '40%',
        alignItems: 'center',
        padding: 12,
        backgroundColor: theme.colors.backgroundSecondary,
        borderRadius: 12,
    },
    statNumber: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.primary,
        marginBottom: 4,
    },
    statLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    overviewFooter: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.borderLight,
    },
    overviewBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    overviewBadgeText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    sectionHeader: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 12,
        marginLeft: 4,
    },
    sentimentCard: {
        padding: 16,
        backgroundColor: 'white',
        marginBottom: 24,
    },
    sentimentHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    sentimentTitle: {
        fontSize: 16,
        fontWeight: '500',
    },
    trendBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
        gap: 4,
    },
    trendText: {
        fontSize: 12,
        fontWeight: '600',
    },
    sentimentDescription: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
    },
    noDataText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        fontStyle: 'italic',
        marginLeft: 4,
    },
    contactStatCard: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 12,
        marginBottom: 12,
        backgroundColor: 'white',
    },
    contactStatLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    avatarPlaceholder: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: theme.colors.primaryLighter,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarInitials: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    contactName: {
        fontSize: 15,
        fontWeight: '500',
        color: theme.colors.text,
    },
    lastInteraction: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    contactStatRight: {
        alignItems: 'flex-end',
    },
    messageCount: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
    },
});
