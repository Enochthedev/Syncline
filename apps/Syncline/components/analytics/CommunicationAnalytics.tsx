/**
 * Communication Analytics Component
 * 
 * Displays comprehensive communication analytics:
 * - Platform usage statistics
 * - Contact interaction patterns
 * - Response time analysis
 * - Communication frequency trends
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { 
    View, 
    Text, 
    ScrollView, 
    TouchableOpacity,
    RefreshControl,
    Dimensions
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    BarChart3, 
    TrendingUp, 
    TrendingDown,
    Clock,
    Users,
    MessageCircle,
    Activity,
    Calendar,
    Zap,
    Target,
    Filter
} from '@tamagui/lucide-icons';
import { usePatternAnalysis, usePlatformInsights } from '../../src/hooks/useAI';
import { Platform } from '../../src/types';
import { PLATFORM_COLORS, PLATFORM_NAMES } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '$background',
});

const Header = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
});

const FilterContainer = styled(View, {
    flexDirection: 'row',
    paddingHorizontal: '$4',
    paddingVertical: '$2',
    backgroundColor: '$gray1',
});

const FilterChip = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const AnalyticsCard = styled(View, {
    backgroundColor: '$background',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$4',
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
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

const MetricRow = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: '$2',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const MetricLabel = styled(Text, {
    fontSize: '$3',
    color: '$gray11',
});

const MetricValue = styled(Text, {
    fontSize: '$4',
    fontWeight: '600',
    color: '$color',
});

const ChartContainer = styled(View, {
    marginVertical: '$3',
});

const BarChart = styled(View, {
    marginVertical: '$2',
});

const BarItem = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: '$2',
});

const BarLabel = styled(Text, {
    fontSize: '$3',
    color: '$color',
    width: 80,
});

const BarTrack = styled(View, {
    flex: 1,
    height: 8,
    backgroundColor: '$gray3',
    borderRadius: 4,
    marginHorizontal: '$2',
    overflow: 'hidden',
});

const BarFill = styled(View, {
    height: '100%',
    borderRadius: 4,
});

const BarValue = styled(Text, {
    fontSize: '$3',
    fontWeight: '600',
    color: '$color',
    width: 40,
    textAlign: 'right',
});

const TrendIndicator = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const PlatformChip = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
    marginBottom: '$2',
});

// =============================================================================
// Helper Functions
// =============================================================================

const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
};

const formatPercentage = (value: number) => {
    return `${Math.round(value * 100)}%`;
};

const getTrendIcon = (trend: 'increasing' | 'decreasing' | 'stable') => {
    switch (trend) {
        case 'increasing': return <TrendingUp size={12} color="$green9" />;
        case 'decreasing': return <TrendingDown size={12} color="$red9" />;
        default: return <Activity size={12} color="$gray9" />;
    }
};

const getTrendColor = (trend: 'increasing' | 'decreasing' | 'stable') => {
    switch (trend) {
        case 'increasing': return '$green3';
        case 'decreasing': return '$red3';
        default: return '$gray3';
    }
};

// =============================================================================
// Main Component
// =============================================================================

interface CommunicationAnalyticsProps {
    contactId?: string;
    platform?: Platform;
    dateRange?: {
        start: string;
        end: string;
    };
}

export const CommunicationAnalytics: React.FC<CommunicationAnalyticsProps> = ({
    contactId,
    platform,
    dateRange,
}) => {
    const [refreshing, setRefreshing] = useState(false);
    const [selectedFilter, setSelectedFilter] = useState<'all' | 'platform' | 'contact'>('all');

    const { 
        analysis, 
        loading, 
        error, 
        analyzePatterns 
    } = usePatternAnalysis();

    // Fetch analytics data
    useEffect(() => {
        analyzePatterns({
            contact_id: contactId,
            platform: platform,
            date_range: dateRange,
        });
    }, [contactId, platform, dateRange, analyzePatterns]);

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await analyzePatterns({
                contact_id: contactId,
                platform: platform,
                date_range: dateRange,
            });
        } finally {
            setRefreshing(false);
        }
    }, [contactId, platform, dateRange, analyzePatterns]);

    // Render communication frequency chart
    const renderFrequencyChart = useCallback(() => {
        if (!analysis?.communication_frequency) return null;

        const frequencies = Object.entries(analysis.communication_frequency)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10);

        const maxCount = Math.max(...frequencies.map(([,count]) => count));

        return (
            <AnalyticsCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <BarChart3 size={20} color="$blue9" />
                        <CardTitle style={{ marginLeft: 8 }}>Communication Frequency</CardTitle>
                    </View>
                </CardHeader>

                <BarChart>
                    {frequencies.map(([contact, count]) => {
                        const percentage = (count / maxCount) * 100;
                        
                        return (
                            <BarItem key={contact}>
                                <BarLabel numberOfLines={1}>{contact}</BarLabel>
                                <BarTrack>
                                    <BarFill 
                                        style={{ 
                                            width: `${percentage}%`,
                                            backgroundColor: '$blue8',
                                        }} 
                                    />
                                </BarTrack>
                                <BarValue>{count}</BarValue>
                            </BarItem>
                        );
                    })}
                </BarChart>
            </AnalyticsCard>
        );
    }, [analysis]);

    // Render response patterns
    const renderResponsePatterns = useCallback(() => {
        if (!analysis?.response_patterns) return null;

        const { avg_response_time, response_rate } = analysis.response_patterns;

        return (
            <AnalyticsCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Clock size={20} color="$orange9" />
                        <CardTitle style={{ marginLeft: 8 }}>Response Patterns</CardTitle>
                    </View>
                </CardHeader>

                <MetricRow>
                    <MetricLabel>Average Response Time</MetricLabel>
                    <MetricValue>{formatDuration(avg_response_time)}</MetricValue>
                </MetricRow>

                <MetricRow style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>Response Rate</MetricLabel>
                    <MetricValue>{formatPercentage(response_rate)}</MetricValue>
                </MetricRow>

                {/* Response Time Visualization */}
                <ChartContainer>
                    <Text style={{ fontSize: 14, fontWeight: '600', color: '$color', marginBottom: 8 }}>
                        Response Time Distribution
                    </Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                        <Text style={{ fontSize: 12, color: '$gray11', width: 60 }}>Fast</Text>
                        <View style={{ flex: 1, height: 6, backgroundColor: '$green8', borderRadius: 3, marginHorizontal: 8 }} />
                        <Text style={{ fontSize: 12, color: '$gray11' }}>{'< 1h'}</Text>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                        <Text style={{ fontSize: 12, color: '$gray11', width: 60 }}>Medium</Text>
                        <View style={{ flex: 0.7, height: 6, backgroundColor: '$yellow8', borderRadius: 3, marginHorizontal: 8 }} />
                        <Text style={{ fontSize: 12, color: '$gray11' }}>1-24h</Text>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Text style={{ fontSize: 12, color: '$gray11', width: 60 }}>Slow</Text>
                        <View style={{ flex: 0.3, height: 6, backgroundColor: '$red8', borderRadius: 3, marginHorizontal: 8 }} />
                        <Text style={{ fontSize: 12, color: '$gray11' }}>{'>24h'}</Text>
                    </View>
                </ChartContainer>
            </AnalyticsCard>
        );
    }, [analysis]);

    // Render topic trends
    const renderTopicTrends = useCallback(() => {
        if (!analysis?.topic_trends) return null;

        const topTopics = analysis.topic_trends
            .sort((a, b) => b.frequency - a.frequency)
            .slice(0, 8);

        return (
            <AnalyticsCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Target size={20} color="$purple9" />
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
                            <PlatformChip>
                                <Text style={{ fontSize: 12, color: '$color' }}>
                                    {topic.topic}
                                </Text>
                            </PlatformChip>
                            <TrendIndicator style={{ backgroundColor: getTrendColor(topic.trend) }}>
                                {getTrendIcon(topic.trend)}
                                <Text style={{ 
                                    marginLeft: 4, 
                                    fontSize: 11, 
                                    color: '$gray11',
                                }}>
                                    {topic.frequency}
                                </Text>
                            </TrendIndicator>
                        </View>
                    ))}
                </View>
            </AnalyticsCard>
        );
    }, [analysis]);

    // Render sentiment analysis
    const renderSentimentAnalysis = useCallback(() => {
        if (!analysis?.sentiment_analysis) return null;

        const { overall_sentiment, sentiment_over_time } = analysis.sentiment_analysis;
        const recentSentiments = sentiment_over_time.slice(-7);

        const getSentimentColor = (sentiment: string) => {
            switch (sentiment) {
                case 'positive': return '$green8';
                case 'negative': return '$red8';
                default: return '$gray8';
            }
        };

        return (
            <AnalyticsCard>
                <CardHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <Activity size={20} color="$pink9" />
                        <CardTitle style={{ marginLeft: 8 }}>Sentiment Analysis</CardTitle>
                    </View>
                    <View style={{
                        backgroundColor: getSentimentColor(overall_sentiment) + '20',
                        borderRadius: 4,
                        paddingHorizontal: 8,
                        paddingVertical: 4,
                    }}>
                        <Text style={{ 
                            fontSize: 12, 
                            color: getSentimentColor(overall_sentiment),
                            textTransform: 'capitalize',
                            fontWeight: '600',
                        }}>
                            {overall_sentiment}
                        </Text>
                    </View>
                </CardHeader>

                <Text style={{ fontSize: 14, color: '$gray11', marginBottom: 12 }}>
                    Recent sentiment trend (last 7 days):
                </Text>

                <View style={{ flexDirection: 'row', alignItems: 'end', height: 60, marginBottom: 12 }}>
                    {recentSentiments.map((item, index) => {
                        const height = Math.abs(item.sentiment) * 50;
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

                <MetricRow style={{ borderBottomWidth: 0 }}>
                    <MetricLabel>Overall Sentiment</MetricLabel>
                    <MetricValue style={{ 
                        color: getSentimentColor(overall_sentiment),
                        textTransform: 'capitalize',
                    }}>
                        {overall_sentiment}
                    </MetricValue>
                </MetricRow>
            </AnalyticsCard>
        );
    }, [analysis]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Communication Analytics
                    </Text>
                </Header>
                <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                    <Activity size={48} color="$blue8" />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Analyzing communication patterns...
                    </Text>
                </View>
            </Container>
        );
    }

    if (error) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Communication Analytics
                    </Text>
                </Header>
                <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                    <Text style={{ color: '$red11', textAlign: 'center' }}>
                        Failed to load analytics: {error}
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
                </View>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Communication Analytics
                </Text>
                <TouchableOpacity onPress={handleRefresh}>
                    <BarChart3 size={20} color="$blue9" />
                </TouchableOpacity>
            </Header>

            {/* Filters */}
            <FilterContainer>
                {(['all', 'platform', 'contact'] as const).map((filter) => (
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
                {renderFrequencyChart()}

                {/* Response Patterns */}
                {renderResponsePatterns()}

                {/* Topic Trends */}
                {renderTopicTrends()}

                {/* Sentiment Analysis */}
                {renderSentimentAnalysis()}

                {/* Empty State */}
                {!analysis && (
                    <View style={{ 
                        flex: 1, 
                        justifyContent: 'center', 
                        alignItems: 'center',
                        paddingVertical: 60,
                    }}>
                        <BarChart3 size={48} color="$gray8" />
                        <Text style={{ color: '$gray11', marginTop: 16, textAlign: 'center' }}>
                            No analytics data available
                        </Text>
                        <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                            Start conversations to generate insights
                        </Text>
                    </View>
                )}
            </ScrollView>
        </Container>
    );
};

export default CommunicationAnalytics;