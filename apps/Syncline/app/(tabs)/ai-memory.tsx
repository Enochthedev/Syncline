/**
 * AI & Memory Tab
 * 
 * Main AI and memory interface:
 * - Memory search and recommendations
 * - AI insights dashboard
 * - Processing status and controls
 * - Semantic search interface
 */

import React, { useState, useCallback } from 'react';
import {
    View,
    Text, 
    TouchableOpacity,
    Platform
} from 'react-native';
import { styled, Stack, XStack, YStack } from 'tamagui';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import {
    Brain,
    Search,
    BarChart3,
    Settings,
    Activity,
    Sparkles
} from '@tamagui/lucide-icons';
import { SafeAreaView } from 'react-native-safe-area-context';

// Import components
import MemorySearch from '../../components/memory/MemorySearch';
import MemoryRecommendations from '../../components/memory/MemoryRecommendations';
import SemanticSearch from '../../components/ai/SemanticSearch';
import InsightsDashboard from '../../components/ai/InsightsDashboard';
import { useMemoryStats, useMemoryRecommendations } from '../../src/hooks/useMemory';
import { useAIProcessingStatus } from '../../src/hooks/useAI';
import { useTheme } from '../../src/contexts/ThemeContext';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '#f8f9fa',
});

const GradientHeader = styled(LinearGradient, {
    paddingTop: Platform.OS === 'android' ? 40 : 10,
    paddingBottom: 20,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
    shadowColor: '#4f46e5',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 4,
    marginBottom: 0,
    zIndex: 1,
});

const HeaderTop = styled(XStack, {
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
});

const Title = styled(Text, {
    fontSize: 28,
    fontWeight: '800',
    color: 'white',
    letterSpacing: 0.5,
});

const Subtitle = styled(Text, {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    fontWeight: '500',
});

const StatsRow = styled(XStack, {
    justifyContent: 'space-between',
    paddingHorizontal: 5,
    marginTop: 10,
});

const StatCard = styled(View, {
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 10,
    minWidth: 80,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
});

const StatValue = styled(Text, {
    fontSize: 20,
    fontWeight: '700',
    color: 'white',
    marginBottom: 4,
});

const StatLabel = styled(Text, {
    fontSize: 11,
    color: 'rgba(255,255,255,0.8)',
    fontWeight: '600',
    textTransform: 'uppercase',
});

const TabContainer = styled(View, {
    paddingHorizontal: 20,
    marginTop: 15,
    marginBottom: 5,
});

const TabSelector = styled(View, {
    flexDirection: 'row',
    backgroundColor: '#f1f1f1',
    borderRadius: 20,
    padding: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 5,
});

const TabOption = styled(TouchableOpacity, {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 16,
});

const TabText = styled(Text, {
    fontSize: 13,
    fontWeight: '600',
    marginLeft: 6,
});

const ContentContainer = styled(View, {
    flex: 1,
});

// =============================================================================
// Types
// =============================================================================

type TabType = 'overview' | 'search' | 'insights';

const TABS: Array<{
    type: TabType;
    label: string;
    icon: React.FC<any>;
}> = [
        {
            type: 'overview',
            label: 'Overview',
            icon: Sparkles,
        },
        {
            type: 'search',
            label: 'Search',
            icon: Search,
        },
        {
            type: 'insights',
            label: 'Insights',
            icon: BarChart3,
        },
    ];

// =============================================================================
// Main Component
// =============================================================================

export default function AIMemoryTab() {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [refreshing, setRefreshing] = useState(false);
    const { isDark } = useTheme();

    // Hooks for data
    const { stats: memoryStats, loading: statsLoading, refetch: refetchStats } = useMemoryStats();
    const {
        recommendations,
        loading: recommendationsLoading,
        refreshRecommendations
    } = useMemoryRecommendations();
    const {
        status: aiStatus,
        loading: aiStatusLoading,
        fetchStatus: fetchAIStatus
    } = useAIProcessingStatus();

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await Promise.all([
                refetchStats(),
                refreshRecommendations(),
                fetchAIStatus(),
            ]);
        } finally {
            setRefreshing(false);
        }
    }, [refetchStats, refreshRecommendations, fetchAIStatus]);

    // Render tab content
    const renderTabContent = useCallback(() => {
        switch (activeTab) {
            case 'search':
                return (
                    <MemorySearch
                        placeholder="Search everything..."
                        onMemorySelect={(memory) => {
                            console.log('Selected memory:', memory);
                        }}
                    />
                );

            case 'overview':
                return (
                    <MemoryRecommendations
                        onRecommendationAction={(recommendation, action) => {
                            console.log('Recommendation action:', recommendation, action);
                        }}
                    />
                );

            case 'insights':
                return (
                    <InsightsDashboard
                        dateRange={{
                            start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                            end: new Date().toISOString().split('T')[0],
                        }}
                    />
                );

            default:
                return null;
        }
    }, [activeTab]);

    // Calculate stats for display
    const displayStats = {
        memories: memoryStats?.total_memories || 0,
        recommendations: recommendations.length || 0,
        aiStatus: aiStatus?.status || 'Active',
        processing: aiStatus?.processing_queue || 0,
    };

    return (
        <Container>
            <GradientHeader
                colors={isDark ? ['#4c1d95', '#2e1065'] : ['#6366f1', '#4f46e5']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
            >
                <SafeAreaView edges={['top']} style={{ paddingBottom: 0 }}>
                    <HeaderTop>
                        <View>
                            <XStack alignItems="center">
                                <View style={{ backgroundColor: 'rgba(255,255,255,0.2)', padding: 6, borderRadius: 10, marginRight: 10 }}>
                                    <Brain size={24} color="white" />
                                </View>
                                <View>
                                    <Title>Memory AI</Title>
                                    <Subtitle>Synchronized Intelligence</Subtitle>
                                </View>
                            </XStack>
                        </View>
                        <TouchableOpacity style={{ padding: 8, backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 20 }}>
                            <Settings size={22} color="white" />
                        </TouchableOpacity>
                    </HeaderTop>

                    <StatsRow>
                        <StatCard>
                            <StatValue>{displayStats.memories}</StatValue>
                            <StatLabel>Memories</StatLabel>
                        </StatCard>
                        <StatCard>
                            <StatValue>{displayStats.recommendations}</StatValue>
                            <StatLabel>Actions</StatLabel>
                        </StatCard>
                        <StatCard>
                            <StatValue>{displayStats.processing}</StatValue>
                            <StatLabel>Queue</StatLabel>
                        </StatCard>
                        <StatCard>
                            <Activity size={24} color="white" style={{ marginBottom: 4 }} />
                            <StatLabel>{displayStats.aiStatus}</StatLabel>
                        </StatCard>
                    </StatsRow>
                </SafeAreaView>
            </GradientHeader>

            <TabContainer>
                <TabSelector>
                    {TABS.map((tab) => {
                        const isActive = activeTab === tab.type;
                        const Icon = tab.icon;
                        return (
                            <TouchableOpacity
                                key={tab.type}
                                onPress={() => {
                                    console.log('Tab pressed:', tab.type);
                                    setActiveTab(tab.type);
                                }}
                                style={{
                                    flex: 1,
                                    flexDirection: 'row',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    paddingVertical: 10,
                                    borderRadius: 16,
                                    backgroundColor: isActive ? '#ffffff' : 'transparent',
                                }}
                            >
                                <Icon
                                    size={16}
                                    color={isActive ? '#4f46e5' : '#6b7280'}
                                />
                                <Text style={{
                                    fontSize: 13,
                                    fontWeight: '600',
                                    marginLeft: 6,
                                    color: isActive ? '#1f2937' : '#6b7280',
                                }}>
                                    {tab.label}
                                </Text>
                            </TouchableOpacity>
                        );
                    })}
                </TabSelector>
            </TabContainer>

            <ContentContainer>
                {renderTabContent()}
            </ContentContainer>
        </Container>
    );
}