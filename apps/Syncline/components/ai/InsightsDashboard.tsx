/**
 * AI Insights Dashboard Component
 * 
 * Displays comprehensive AI-powered insights:
 * - Contact insights and patterns
 * - Communication frequency analysis
 * - Sentiment analysis over time
 * - Topic trends and entity extraction
 * - Platform-specific analytics
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    RefreshControl,
    Dimensions,
    ActivityIndicator
} from 'react-native';
import { styled } from '@tamagui/core';
import {
    TrendingUp,
    TrendingDown,
    Minus,
    User,
    MessageCircle,
    Calendar,
    BarChart3,
    PieChart,
    Activity,
    Brain,
    Heart,
    Frown,
    Smile,
    Meh,
    Clock,
    Hash,
    Filter,
    RefreshCw
} from '@tamagui/lucide-icons';
import { useContactInsights, usePatternAnalysis, usePlatformInsights } from '../../src/hooks/useAI';
import { AIInsight, Platform } from '../../src/types';
import { PLATFORM_COLORS, PLATFORM_NAMES } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: 'transparent',
});

const Header = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
});

const RefreshButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e0e7ff',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
});

const FilterContainer = styled(View, {
    flexDirection: 'row',
    paddingHorizontal: '$4',
    paddingVertical: '$2',
    backgroundColor: '#f8f8f8',
});

const FilterChip = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e5e5e5',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const InsightCard = styled(View, {
    backgroundColor: '#ffffff',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$4',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
});

const CardHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$3',
});

const CardTitle = styled(Text, {
    fontSize: '$5',
    fontWeight: '600',
    color: '$color',
});

const MetricContainer = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: '$2',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const MetricValue = styled(Text, {
    fontSize: '$4',
    fontWeight: '600',
    color: '$color',
});

const MetricLabel = styled(Text, {
    fontSize: '$3',
    color: '$gray11',
});

const TrendIndicator = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const TopicChip = styled(View, {
    backgroundColor: '$blue3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
    marginBottom: '$2',
});

const SentimentBar = styled(View, {
    height: 8,
    borderRadius: 4,
    marginVertical: '$2',
});

const EmptyState = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$8',
});

const LoadingContainer = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
});

// =============================================================================
// Helper Functions
// =============================================================================

const getSentimentColor = (sentiment: 'positive' | 'neutral' | 'negative') => {
    switch (sentiment) {
        case 'positive': return '$green8';
        case 'negative': return '$red8';
        default: return '$gray8';
    }
};

const getSentimentIcon = (sentiment: 'positive' | 'neutral' | 'negative') => {
    switch (sentiment) {
        case 'positive': return <Smile size={16} color="$green9" />;
        case 'negative': return <Frown size={16} color="$red9" />;
        default: return <Meh size={16} color="$gray9" />;
    }
};

const getTrendIcon = (trend: 'increasing' | 'decreasing' | 'stable') => {
    switch (trend) {
        case 'increasing': return <TrendingUp size={14} color="$green9" />;
        case 'decreasing': return <TrendingDown size={14} color="$red9" />;
        default: return <Minus size={14} color="$gray9" />;
    }
};

const getTrendColor = (trend: 'increasing' | 'decreasing' | 'stable') => {
    switch (trend) {
        case 'increasing': return '$green3';
        case 'decreasing': return '$red3';
        default: return '$gray3';
    }
};

const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
};

const formatPercentage = (value: number) => {
    return `${Math.round(value * 100)}%`;
};

// =============================================================================
// Main Component
// =============================================================================

interface InsightsDashboardProps {
    contactId?: string;
    platform?: Platform;
    connectionId?: string;
    dateRange?: {
        start: string;
        end: string;
    };
}

export const InsightsDashboard: React.FC<InsightsDashboardProps> = ({
    contactId,
    platform,
    connectionId,
    dateRange,
}) => {
    const [refreshing, setRefreshing] = useState(false);
    const [selectedFilter, setSelectedFilter] = useState<'all' | 'contact' | 'platform'>('all');

    const {
        insights: contactInsights,
        loading: contactLoading,
        error: contactError,
        generateInsights: fetchContactInsights
    } = useContactInsights(contactId);

    const {
        analysis: patternAnalysis,
        loading: patternLoading,
        error: patternError,
        analyzePatterns
    } = usePatternAnalysis();

    const {
        insights: platformInsights,
        loading: platformLoading,
        error: platformError,
        fetchInsights: fetchPlatformInsights
    } = usePlatformInsights(platform || 'gmail', connectionId);

    // Fetch data on mount and when dependencies change
    useEffect(() => {
        if (selectedFilter === 'all' || selectedFilter === 'contact') {
            if (contactId) {
                fetchContactInsights();
            }
        }

        if (selectedFilter === 'all' || selectedFilter === 'platform') {
            analyzePatterns({
                contact_id: contactId,
                platform: platform,
                date_range: dateRange,
            });

            if (platform && connectionId) {
                fetchPlatformInsights();
            }
        }
    }, [
        contactId,
        platform,
        connectionId,
        dateRange,
        selectedFilter,
        fetchContactInsights,
        analyzePatterns,
        fetchPlatformInsights
    ]);

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            const promises = [];

            if (selectedFilter === 'all' || selectedFilter === 'contact') {
                if (contactId) {
                    promises.push(fetchContactInsights());
                }
            }

            if (selectedFilter === 'all' || selectedFilter === 'platform') {
                promises.push(analyzePatterns({
                    contact_id: contactId,
                    platform: platform,
                    date_range: dateRange,
                }));

                if (platform && connectionId) {
                    promises.push(fetchPlatformInsights());
                }
            }

            await Promise.all(promises);
        } finally {
            setRefreshing(false);
        }
    }, [
        selectedFilter,
        contactId,
        platform,
        connectionId,
        dateRange,
        fetchContactInsights,
        analyzePatterns,
        fetchPlatformInsights
    ]);

    // Loading state
    const loading = contactLoading || patternLoading || platformLoading;
    const error = contactError || patternError || platformError;

    // Render communication frequency chart
    const renderCommunicationFrequency = useCallback(() => {
        if (!patternAnalysis?.communication_frequency) return null;

        const frequencies = Object.entries(patternAnalysis.communication_frequency)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5);

        return (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <BarChart3 size={20} color="$blue9" />
                        <CardTitle style={{ marginLeft: 8 }}>Communication Frequency</CardTitle>
                    </View>
                </CardHeader>

                {frequencies.map(([contact, count]) => {
                    const maxCount = Math.max(...frequencies.map(([, c]) => c));
                    const percentage = (count / maxCount) * 100;

                    return (
                        <View key={contact} style={{ marginBottom: 12 }}>
                            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                                <Text style={{ fontSize: 14, color: '$color' }}>{contact}</Text>
                                <Text style={{ fontSize: 14, fontWeight: '600', color: '$color' }}>{count}</Text>
                            </View>
                            <View style={{
                                height: 6,
                                backgroundColor: '$gray3',
                                borderRadius: 3,
                                overflow: 'hidden',
                            }}>
                                <View style={{
                                    height: '100%',
                                    width: `${percentage}%`,
                                    backgroundColor: '$blue8',
                                }} />
                            </View>
                        </View>
                    );
                })}
            </InsightCard>
        );
    }, [patternAnalysis]);

    // Render sentiment analysis
    const renderSentimentAnalysis = useCallback(() => {
        if (!patternAnalysis?.sentiment_analysis) return null;

        const { overall_sentiment, sentiment_over_time } = patternAnalysis.sentiment_analysis;
        const recentSentiments = sentiment_over_time.slice(-7); // Last 7 data points

        return (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Heart size={20} color="$pink9" />
                        <CardTitle style={{ marginLeft: 8 }}>Sentiment Analysis</CardTitle>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        {getSentimentIcon(overall_sentiment)}
                        <Text style={{
                            marginLeft: 6,
                            fontSize: 14,
                            fontWeight: '600',
                            color: getSentimentColor(overall_sentiment),
                            textTransform: 'capitalize',
                        }}>
                            {overall_sentiment}
                        </Text>
                    </View>
                </CardHeader>

                <Text style={{ fontSize: 14, color: '$gray11', marginBottom: 12 }}>
                    Recent sentiment trend:
                </Text>

                <View style={{ flexDirection: 'row', alignItems: 'end', height: 60, marginBottom: 12 }}>
                    {recentSentiments.map((item, index) => {
                        const height = Math.abs(item.sentiment) * 50; // Scale to 50px max
                        const isPositive = item.sentiment > 0;

                        return (
                            <View key={index} style={{ flex: 1, alignItems: 'center' }}>
                                <View style={{
                                    width: 20,
                                    height: Math.max(height, 2),
                                    backgroundColor: isPositive ? '$green8' : item.sentiment < 0 ? '$red8' : '$gray8',
                                    borderRadius: 2,
                                    marginBottom: 4,
                                }} />
                                <Text style={{ fontSize: 10, color: '$gray9' }}>
                                    {new Date(item.date).getDate()}
                                </Text>
                            </View>
                        );
                    })}
                </View>

                <SentimentBar style={{
                    backgroundColor: getSentimentColor(overall_sentiment),
                    opacity: 0.3,
                }} />
            </InsightCard>
        );
    }, [patternAnalysis]);

    // Render topic trends
    const renderTopicTrends = useCallback(() => {
        if (!patternAnalysis?.topic_trends) return null;

        const topTopics = patternAnalysis.topic_trends
            .sort((a, b) => b.frequency - a.frequency)
            .slice(0, 8);

        return (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Hash size={20} color="$purple9" />
                        <CardTitle style={{ marginLeft: 8 }}>Topic Trends</CardTitle>
                    </View>
                </CardHeader>

                <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                    {topTopics.map((topic, index) => (
                        <View key={index} style={{
                            flexDirection: 'row',
                            alignItems: 'center',
                            marginRight: 12,
                            marginBottom: 8,
                        }}>
                            <TopicChip>
                                <Text style={{ fontSize: 12, color: '$blue11' }}>
                                    {topic.topic}
                                </Text>
                            </TopicChip>
                            <TrendIndicator style={{ backgroundColor: getTrendColor(topic.trend) }}>
                                {getTrendIcon(topic.trend)}
                                <Text style={{
                                    marginLeft: 4,
                                    fontSize: 12,
                                    color: '$gray11',
                                }}>
                                    {topic.frequency}
                                </Text>
                            </TrendIndicator>
                        </View>
                    ))}
                </View>
            </InsightCard>
        );
    }, [patternAnalysis]);

    // Render response patterns
    const renderResponsePatterns = useCallback(() => {
        if (!patternAnalysis?.response_patterns) return null;

        const { avg_response_time, response_rate } = patternAnalysis.response_patterns;

        return (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Clock size={20} color="$orange9" />
                        <CardTitle style={{ marginLeft: 8 }}>Response Patterns</CardTitle>
                    </View>
                </CardHeader>

                <MetricContainer>
                    <MetricLabel>Average Response Time</MetricLabel>
                    <MetricValue>{formatResponseTime(avg_response_time)}</MetricValue>
                </MetricContainer>

                <MetricContainer style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>Response Rate</MetricLabel>
                    <MetricValue>{formatPercentage(response_rate)}</MetricValue>
                </MetricContainer>
            </InsightCard>
        );
    }, [patternAnalysis]);

    // Render platform-specific insights
    const renderPlatformInsights = useCallback(() => {
        if (!platformInsights || !platform) return null;

        const renderSlackInsights = () => (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <View style={{
                            width: 20,
                            height: 20,
                            borderRadius: 10,
                            backgroundColor: PLATFORM_COLORS.slack,
                        }} />
                        <CardTitle style={{ marginLeft: 8 }}>Slack Insights</CardTitle>
                    </View>
                </CardHeader>

                <MetricContainer>
                    <MetricLabel>Most Active Channel</MetricLabel>
                    <MetricValue>
                        {Object.entries(platformInsights.channel_activity || {})
                            .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[0] || 'N/A'}
                    </MetricValue>
                </MetricContainer>

                <MetricContainer>
                    <MetricLabel>Peak Hour</MetricLabel>
                    <MetricValue>
                        {platformInsights.peak_hours?.[0] ? `${platformInsights.peak_hours[0]}:00` : 'N/A'}
                    </MetricValue>
                </MetricContainer>

                <MetricContainer style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>User Engagement</MetricLabel>
                    <MetricValue>
                        {Object.keys(platformInsights.user_engagement || {}).length} users
                    </MetricValue>
                </MetricContainer>
            </InsightCard>
        );

        const renderDiscordInsights = () => (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <View style={{
                            width: 20,
                            height: 20,
                            borderRadius: 10,
                            backgroundColor: PLATFORM_COLORS.discord,
                        }} />
                        <CardTitle style={{ marginLeft: 8 }}>Discord Insights</CardTitle>
                    </View>
                </CardHeader>

                <MetricContainer>
                    <MetricLabel>Most Active Guild</MetricLabel>
                    <MetricValue>
                        {Object.entries(platformInsights.guild_activity || {})
                            .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[0] || 'N/A'}
                    </MetricValue>
                </MetricContainer>

                <MetricContainer style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>Message Types</MetricLabel>
                    <MetricValue>
                        {Object.keys(platformInsights.message_types || {}).length} types
                    </MetricValue>
                </MetricContainer>
            </InsightCard>
        );

        const renderGmailInsights = () => (
            <InsightCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <View style={{
                            width: 20,
                            height: 20,
                            borderRadius: 10,
                            backgroundColor: PLATFORM_COLORS.gmail,
                        }} />
                        <CardTitle style={{ marginLeft: 8 }}>Gmail Insights</CardTitle>
                    </View>
                </CardHeader>

                <MetricContainer>
                    <MetricLabel>Top Sender</MetricLabel>
                    <MetricValue>
                        {Object.entries(platformInsights.sender_frequency || {})
                            .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[0] || 'N/A'}
                    </MetricValue>
                </MetricContainer>

                <MetricContainer style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>Response Rate</MetricLabel>
                    <MetricValue>
                        {formatPercentage(platformInsights.response_patterns?.response_rate || 0)}
                    </MetricValue>
                </MetricContainer>
            </InsightCard>
        );

        switch (platform) {
            case 'slack': return renderSlackInsights();
            case 'discord': return renderDiscordInsights();
            case 'gmail': return renderGmailInsights();
            default: return null;
        }
    }, [platformInsights, platform]);

    if (loading && !refreshing) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        AI Insights
                    </Text>
                </Header>
                <LoadingContainer>
                    <ActivityIndicator size="large" color="$blue9" />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Analyzing patterns and generating insights...
                    </Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error && !patternAnalysis && !contactInsights && !platformInsights) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        AI Insights
                    </Text>
                </Header>
                <EmptyState>
                    <Brain size={48} color="$red8" />
                    <Text style={{ color: '$red11', marginTop: 16, textAlign: 'center' }}>
                        Failed to load insights
                    </Text>
                    <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                        {error}
                    </Text>
                    <TouchableOpacity
                        onPress={handleRefresh}
                        style={{
                            backgroundColor: '$blue8',
                            paddingHorizontal: 16,
                            paddingVertical: 8,
                            borderRadius: 6,
                            marginTop: 16,
                        }}
                    >
                        <Text style={{ color: 'white' }}>Retry</Text>
                    </TouchableOpacity>
                </EmptyState>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    AI Insights
                </Text>
                <RefreshButton onPress={handleRefresh} disabled={loading}>
                    <RefreshCw size={16} color="$blue11" />
                    <Text style={{ marginLeft: 6, color: '$blue11' }}>Refresh</Text>
                </RefreshButton>
            </Header>

            {/* Filters */}
            <FilterContainer>
                {(['all', 'contact', 'platform'] as const).map((filter) => (
                    <FilterChip
                        key={filter}
                        onPress={() => setSelectedFilter(filter)}
                        style={{
                            backgroundColor: selectedFilter === filter ? '$blue3' : '$gray3',
                            borderWidth: 1,
                            borderColor: selectedFilter === filter ? '$blue8' : 'transparent',
                        }}
                    >
                        <Filter size={14} color={selectedFilter === filter ? '$blue11' : '$gray11'} />
                        <Text style={{
                            marginLeft: 6,
                            fontSize: 14,
                            color: selectedFilter === filter ? '$blue11' : '$gray11',
                            fontWeight: selectedFilter === filter ? '600' : 'normal',
                            textTransform: 'capitalize',
                        }}>
                            {filter}
                        </Text>
                    </FilterChip>
                ))}
            </FilterContainer>

            <ScrollView
                showsVerticalScrollIndicator={false}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={handleRefresh}
                        colors={['$blue9']}
                        tintColor="$blue9"
                    />
                }
            >
                {/* Communication Frequency */}
                {(selectedFilter === 'all' || selectedFilter === 'contact') && renderCommunicationFrequency()}

                {/* Sentiment Analysis */}
                {(selectedFilter === 'all' || selectedFilter === 'contact') && renderSentimentAnalysis()}

                {/* Topic Trends */}
                {(selectedFilter === 'all' || selectedFilter === 'contact') && renderTopicTrends()}

                {/* Response Patterns */}
                {(selectedFilter === 'all' || selectedFilter === 'contact') && renderResponsePatterns()}

                {/* Platform-Specific Insights */}
                {(selectedFilter === 'all' || selectedFilter === 'platform') && renderPlatformInsights()}

                {/* Empty State */}
                {!patternAnalysis && !contactInsights && !platformInsights && !loading && (
                    <EmptyState>
                        <Brain size={48} color="$gray8" />
                        <Text style={{ color: '$gray11', marginTop: 16, textAlign: 'center' }}>
                            No insights available
                        </Text>
                        <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                            Start a conversation to generate AI insights
                        </Text>
                    </EmptyState>
                )}
            </ScrollView>
        </Container>
    );
};

export default InsightsDashboard;