/**
 * Memory Recommendations Component
 * 
 * Displays proactive memory recommendations with:
 * - Priority-based grouping (high/medium/low)
 * - Action buttons for recommendations
 * - Commitment tracking and overdue alerts
 * - Contextual recommendations based on current activity
 */

import React, { useState, useCallback, useMemo } from 'react';
import { View, Text, FlatList, TouchableOpacity, Alert, RefreshControl } from 'react-native';
import { styled } from '@tamagui/core';
import {
    AlertTriangle,
    Clock,
    CheckCircle,
    User,
    MessageCircle,
    Calendar,
    ChevronRight,
    RefreshCw,
    Star
} from '@tamagui/lucide-icons';
import { useMemoryRecommendations } from '../../src/hooks/useMemory';
import { MemoryRecommendation } from '../../src/types';

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
    borderBottomColor: '$gray4',
});

const RefreshButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e0e7ff',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
});

const SectionHeader = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    backgroundColor: '#f5f5f5',
});

const RecommendationCard = styled(TouchableOpacity, {
    backgroundColor: '#ffffff',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$4',
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
});

const RecommendationHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '$2',
});

const PriorityBadge = styled(View, {
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    minWidth: 60,
    alignItems: 'center',
});

const ActionButton = styled(TouchableOpacity, {
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginTop: '$3',
    alignSelf: 'flex-start',
});

const DueDateContainer = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    backgroundColor: '#e5e5e5',
    borderRadius: '$2',
    alignSelf: 'flex-start',
});

const EmptyState = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: '$4',
});

// =============================================================================
// Helper Functions
// =============================================================================

const getPriorityColor = (priority: number) => {
    if (priority >= 0.8) return { bg: '$red3', text: '$red11', border: '$red8' };
    if (priority >= 0.6) return { bg: '$orange3', text: '$orange11', border: '$orange8' };
    if (priority >= 0.4) return { bg: '$yellow3', text: '$yellow11', border: '$yellow8' };
    return { bg: '$gray3', text: '$gray11', border: '$gray8' };
};

const getPriorityLabel = (priority: number) => {
    if (priority >= 0.8) return 'High';
    if (priority >= 0.6) return 'Medium';
    if (priority >= 0.4) return 'Low';
    return 'Info';
};

const getRecommendationIcon = (type: string) => {
    switch (type) {
        case 'overdue_commitment':
            return <AlertTriangle size={20} color="$red9" />;
        case 'upcoming_commitment':
            return <Clock size={20} color="$orange9" />;
        case 'follow_up':
            return <MessageCircle size={20} color="$blue9" />;
        case 'relationship_maintenance':
            return <User size={20} color="$purple9" />;
        case 'context_reminder':
            return <Star size={20} color="$yellow9" />;
        default:
            return <CheckCircle size={20} color="$green9" />;
    }
};

const formatDueDate = (dueDateString?: string) => {
    if (!dueDateString) return null;

    const dueDate = new Date(dueDateString);
    const now = new Date();
    const diffTime = dueDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
        return { text: `${Math.abs(diffDays)} days overdue`, color: '$red11', urgent: true };
    } else if (diffDays === 0) {
        return { text: 'Due today', color: '$orange11', urgent: true };
    } else if (diffDays === 1) {
        return { text: 'Due tomorrow', color: '$orange11', urgent: false };
    } else if (diffDays <= 7) {
        return { text: `Due in ${diffDays} days`, color: '$yellow11', urgent: false };
    } else {
        return { text: dueDate.toLocaleDateString(), color: '$gray11', urgent: false };
    }
};

// =============================================================================
// Main Component
// =============================================================================

interface MemoryRecommendationsProps {
    context?: {
        current_contact?: string;
        current_thread?: string;
        current_platform?: string;
        keywords?: string[];
    };
    onRecommendationAction?: (recommendation: MemoryRecommendation, action: string) => void;
    maxItems?: number;
}

export const MemoryRecommendations: React.FC<MemoryRecommendationsProps> = ({
    context,
    onRecommendationAction,
    maxItems,
}) => {
    const [refreshing, setRefreshing] = useState(false);

    const {
        recommendations,
        highPriorityRecommendations,
        mediumPriorityRecommendations,
        lowPriorityRecommendations,
        loading,
        error,
        refreshRecommendations,
    } = useMemoryRecommendations(context);

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await refreshRecommendations();
        } finally {
            setRefreshing(false);
        }
    }, [refreshRecommendations]);

    // Handle recommendation action
    const handleRecommendationPress = useCallback((recommendation: MemoryRecommendation) => {
        if (recommendation.suggested_action) {
            Alert.alert(
                recommendation.title,
                recommendation.description,
                [
                    { text: 'Dismiss', style: 'cancel' },
                    {
                        text: recommendation.suggested_action,
                        onPress: () => onRecommendationAction?.(recommendation, 'action'),
                    },
                ]
            );
        } else {
            onRecommendationAction?.(recommendation, 'view');
        }
    }, [onRecommendationAction]);

    // Render recommendation item
    const renderRecommendation = useCallback(({ item }: { item: MemoryRecommendation }) => {
        const priorityStyle = getPriorityColor(item.priority);
        const priorityLabel = getPriorityLabel(item.priority);
        const icon = getRecommendationIcon(item.type);
        const dueDate = formatDueDate(item.due_date);

        return (
            <RecommendationCard
                onPress={() => handleRecommendationPress(item)}
                style={{ borderLeftColor: priorityStyle.border }}
            >
                <RecommendationHeader>
                    <View style={{ flex: 1, marginRight: 12 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                            {icon}
                            <Text style={{
                                fontSize: 16,
                                fontWeight: '600',
                                color: '$color',
                                marginLeft: 8,
                                flex: 1,
                            }}>
                                {item.title}
                            </Text>
                        </View>
                        <Text style={{
                            fontSize: 14,
                            color: '$gray11',
                            lineHeight: 20,
                        }}>
                            {item.description}
                        </Text>
                    </View>

                    <PriorityBadge style={{
                        backgroundColor: priorityStyle.bg,
                    }}>
                        <Text style={{
                            fontSize: 12,
                            fontWeight: '600',
                            color: priorityStyle.text,
                        }}>
                            {priorityLabel}
                        </Text>
                    </PriorityBadge>
                </RecommendationHeader>

                {dueDate && (
                    <DueDateContainer style={{
                        backgroundColor: dueDate.urgent ? '$red2' : '$gray3',
                    }}>
                        <Calendar size={14} color={dueDate.color} />
                        <Text style={{
                            fontSize: 12,
                            color: dueDate.color,
                            marginLeft: 4,
                            fontWeight: dueDate.urgent ? '600' : 'normal',
                        }}>
                            {dueDate.text}
                        </Text>
                    </DueDateContainer>
                )}

                {item.suggested_action && (
                    <ActionButton>
                        <Text style={{ color: 'white', fontSize: 14, fontWeight: '500' }}>
                            {item.suggested_action}
                        </Text>
                    </ActionButton>
                )}
            </RecommendationCard>
        );
    }, [handleRecommendationPress]);

    // Render section
    const renderSection = useCallback((
        title: string,
        items: MemoryRecommendation[],
        icon: React.ReactNode,
        color: string
    ) => {
        if (items.length === 0) return null;

        const displayItems = maxItems ? items.slice(0, maxItems) : items;

        return (
            <>
                <SectionHeader>
                    {icon}
                    <Text style={{
                        fontSize: 16,
                        fontWeight: '600',
                        color,
                        marginLeft: 8,
                    }}>
                        {title} ({items.length})
                    </Text>
                </SectionHeader>
                <FlatList
                    data={displayItems}
                    renderItem={renderRecommendation}
                    keyExtractor={(item, index) => `${item.type}-${index}`}
                    scrollEnabled={false}
                />
            </>
        );
    }, [maxItems, renderRecommendation]);

    // Group recommendations for display
    const sections = useMemo(() => [
        {
            title: 'High Priority',
            items: highPriorityRecommendations,
            icon: <AlertTriangle size={20} color="$red9" />,
            color: '$red11',
        },
        {
            title: 'Medium Priority',
            items: mediumPriorityRecommendations,
            icon: <Clock size={20} color="$orange9" />,
            color: '$orange11',
        },
        {
            title: 'Low Priority',
            items: lowPriorityRecommendations,
            icon: <Star size={20} color="$blue9" />,
            color: '$blue11',
        },
    ], [highPriorityRecommendations, mediumPriorityRecommendations, lowPriorityRecommendations]);

    if (error) {
        return (
            <Container>
                <View style={{
                    margin: 16,
                    padding: 16,
                    backgroundColor: '$red2',
                    borderRadius: 8,
                }}>
                    <Text style={{ color: '$red11', textAlign: 'center' }}>
                        Failed to load recommendations: {error}
                    </Text>
                    <TouchableOpacity
                        onPress={handleRefresh}
                        style={{
                            marginTop: 12,
                            alignSelf: 'center',
                            backgroundColor: '$red8',
                            paddingHorizontal: 16,
                            paddingVertical: 8,
                            borderRadius: 6,
                        }}
                    >
                        <Text style={{ color: 'white', fontWeight: '500' }}>Retry</Text>
                    </TouchableOpacity>
                </View>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Recommendations
                </Text>
                <RefreshButton onPress={handleRefresh} disabled={loading || refreshing}>
                    <RefreshCw
                        size={16}
                        color="$blue11"
                        style={{
                            transform: [{ rotate: (loading || refreshing) ? '180deg' : '0deg' }]
                        }}
                    />
                    <Text style={{ color: '$blue11', marginLeft: 6, fontSize: 14 }}>
                        Refresh
                    </Text>
                </RefreshButton>
            </Header>

            {recommendations.length === 0 && !loading ? (
                <EmptyState>
                    <CheckCircle size={48} color="$green8" />
                    <Text style={{
                        fontSize: 18,
                        fontWeight: '500',
                        color: '$color',
                        marginTop: 16,
                        textAlign: 'center',
                    }}>
                        All caught up!
                    </Text>
                    <Text style={{
                        fontSize: 14,
                        color: '$gray11',
                        marginTop: 8,
                        textAlign: 'center',
                        lineHeight: 20,
                    }}>
                        No recommendations at the moment.{'\n'}
                        Check back later for proactive suggestions.
                    </Text>
                </EmptyState>
            ) : (
                <FlatList
                    data={sections}
                    renderItem={({ item }) => renderSection(
                        item.title,
                        item.items,
                        item.icon,
                        item.color
                    )}
                    keyExtractor={(item) => item.title}
                    refreshControl={
                        <RefreshControl
                            refreshing={refreshing}
                            onRefresh={handleRefresh}
                            colors={['$blue9']}
                            tintColor="$blue9"
                        />
                    }
                    showsVerticalScrollIndicator={false}
                />
            )}
        </Container>
    );
};

export default MemoryRecommendations;