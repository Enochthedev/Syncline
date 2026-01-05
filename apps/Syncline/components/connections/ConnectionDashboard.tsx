/**
 * Connection Dashboard Component
 * 
 * Provides overview of all platform connections:
 * - All platform connections overview
 * - Health status monitoring
 * - Sync status and controls
 * - Connection management actions
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { 
    View, 
    Text, 
    ScrollView, 
    TouchableOpacity, 
    RefreshControl,
    ActivityIndicator,
    Alert
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Plus, 
    Check, 
    AlertCircle, 
    Sync, 
    Settings,
    Activity,
    RefreshCw,
    Zap,
    Clock,
    Users,
    MessageCircle,
    TrendingUp,
    TrendingDown,
    Minus,
    ChevronRight
} from '@tamagui/lucide-icons';
import { usePlatforms } from '../../src/hooks/usePlatforms';
import { PlatformConnection, Platform } from '../../src/types';
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

const StatsContainer = styled(View, {
    flexDirection: 'row',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    backgroundColor: '$gray1',
});

const StatCard = styled(View, {
    flex: 1,
    alignItems: 'center',
    paddingVertical: '$2',
});

const StatValue = styled(Text, {
    fontSize: '$6',
    fontWeight: '700',
    color: '$color',
});

const StatLabel = styled(Text, {
    fontSize: '$2',
    color: '$gray11',
    marginTop: '$1',
});

const SectionHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    backgroundColor: '$gray2',
});

const ConnectionCard = styled(TouchableOpacity, {
    backgroundColor: '$background',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$4',
    borderWidth: 1,
    borderColor: '$gray4',
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
});

const ConnectionHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$3',
});

const PlatformInfo = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
});

const PlatformLogo = styled(View, {
    width: 32,
    height: 32,
    borderRadius: 8,
    marginRight: '$3',
    justifyContent: 'center',
    alignItems: 'center',
});

const StatusBadge = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const MetricsRow = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: '$2',
});

const MetricItem = styled(View, {
    alignItems: 'center',
    flex: 1,
});

const QuickActions = styled(View, {
    flexDirection: 'row',
    marginTop: '$3',
});

const ActionButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const SecondaryButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const AddConnectionCard = styled(TouchableOpacity, {
    backgroundColor: '$gray1',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$6',
    borderWidth: 2,
    borderColor: '$gray4',
    borderStyle: 'dashed',
    alignItems: 'center',
});

const EmptyState = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$8',
});

// =============================================================================
// Helper Functions
// =============================================================================

const getStatusColor = (status: string) => {
    switch (status) {
        case 'active': return { bg: '$green3', text: '$green11', icon: '$green9' };
        case 'inactive': return { bg: '$gray3', text: '$gray11', icon: '$gray9' };
        case 'error': return { bg: '$red3', text: '$red11', icon: '$red9' };
        case 'pending': return { bg: '$yellow3', text: '$yellow11', icon: '$yellow9' };
        default: return { bg: '$gray3', text: '$gray11', icon: '$gray9' };
    }
};

const getStatusIcon = (status: string) => {
    switch (status) {
        case 'active': return Check;
        case 'error': return AlertCircle;
        case 'pending': return RefreshCw;
        default: return AlertCircle;
    }
};

const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
};

const getPlatformIcon = (platform: Platform) => {
    switch (platform) {
        case 'gmail': return MessageCircle;
        case 'slack': return MessageCircle;
        case 'discord': return Users;
        case 'whatsapp': return MessageCircle;
        default: return MessageCircle;
    }
};

// =============================================================================
// Main Component
// =============================================================================

interface ConnectionDashboardProps {
    onPlatformSelect?: (platform: Platform) => void;
    onAddConnection?: () => void;
}

export const ConnectionDashboard: React.FC<ConnectionDashboardProps> = ({
    onPlatformSelect,
    onAddConnection,
}) => {
    const [refreshing, setRefreshing] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);

    const {
        connections,
        loading,
        error,
        syncPlatform,
        disconnectPlatform,
        getConnectionHealth,
        refreshConnections,
    } = usePlatforms();

    // Calculate statistics
    const stats = useMemo(() => {
        const activeConnections = connections.filter(conn => conn.status === 'active').length;
        const totalConnections = connections.length;
        const platforms = new Set(connections.map(conn => conn.platform)).size;
        const recentSync = connections.reduce((latest, conn) => {
            if (!conn.last_sync_at) return latest;
            const syncDate = new Date(conn.last_sync_at);
            return !latest || syncDate > latest ? syncDate : latest;
        }, null as Date | null);

        return {
            active: activeConnections,
            total: totalConnections,
            platforms,
            lastSync: recentSync ? formatDate(recentSync.toISOString()) : 'Never',
        };
    }, [connections]);

    // Group connections by platform
    const connectionsByPlatform = useMemo(() => {
        const grouped: Record<Platform, PlatformConnection[]> = {} as any;
        connections.forEach(conn => {
            if (!grouped[conn.platform]) {
                grouped[conn.platform] = [];
            }
            grouped[conn.platform].push(conn);
        });
        return grouped;
    }, [connections]);

    // Handle refresh
    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await refreshConnections();
        } finally {
            setRefreshing(false);
        }
    }, [refreshConnections]);

    // Handle sync
    const handleSync = useCallback(async (connectionId: string) => {
        try {
            await syncPlatform(connectionId);
            Alert.alert('Success', 'Sync started successfully');
        } catch (err) {
            Alert.alert('Error', 'Failed to start sync');
        }
    }, [syncPlatform]);

    // Handle disconnect
    const handleDisconnect = useCallback(async (connectionId: string, platform: Platform) => {
        Alert.alert(
            `Disconnect ${PLATFORM_NAMES[platform]}`,
            'Are you sure you want to disconnect this account? This will stop message syncing.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Disconnect',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await disconnectPlatform(connectionId);
                            Alert.alert('Success', 'Account disconnected');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to disconnect account');
                        }
                    },
                },
            ]
        );
    }, [disconnectPlatform]);

    // Render connection card
    const renderConnection = useCallback((connection: PlatformConnection) => {
        const statusStyle = getStatusColor(connection.status);
        const StatusIcon = getStatusIcon(connection.status);
        const PlatformIcon = getPlatformIcon(connection.platform);
        const platformColor = PLATFORM_COLORS[connection.platform];

        return (
            <ConnectionCard
                key={connection.id}
                onPress={() => onPlatformSelect?.(connection.platform)}
            >
                <ConnectionHeader>
                    <PlatformInfo>
                        <PlatformLogo style={{ backgroundColor: platformColor + '20' }}>
                            <PlatformIcon size={20} color={platformColor} />
                        </PlatformLogo>
                        <View style={{ flex: 1 }}>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                                {PLATFORM_NAMES[connection.platform]}
                            </Text>
                            <Text style={{ fontSize: 12, color: '$gray11', marginTop: 2 }}>
                                Connected {formatDate(connection.connected_at)}
                            </Text>
                        </View>
                    </PlatformInfo>
                    
                    <View style={{ alignItems: 'flex-end' }}>
                        <StatusBadge style={{ backgroundColor: statusStyle.bg }}>
                            <StatusIcon size={12} color={statusStyle.icon} />
                            <Text style={{ 
                                marginLeft: 4, 
                                fontSize: 11, 
                                color: statusStyle.text,
                                textTransform: 'capitalize',
                            }}>
                                {connection.status}
                            </Text>
                        </StatusBadge>
                        <ChevronRight size={16} color="$gray9" style={{ marginTop: 4 }} />
                    </View>
                </ConnectionHeader>

                {/* Metrics */}
                <MetricsRow>
                    <MetricItem>
                        <Text style={{ fontSize: 12, color: '$gray11' }}>Last Sync</Text>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '$color', marginTop: 2 }}>
                            {formatDate(connection.last_sync_at)}
                        </Text>
                    </MetricItem>
                    <MetricItem>
                        <Text style={{ fontSize: 12, color: '$gray11' }}>Status</Text>
                        <Text style={{ 
                            fontSize: 14, 
                            fontWeight: '600', 
                            color: statusStyle.text,
                            marginTop: 2,
                            textTransform: 'capitalize',
                        }}>
                            {connection.status}
                        </Text>
                    </MetricItem>
                    <MetricItem>
                        <Text style={{ fontSize: 12, color: '$gray11' }}>Platform</Text>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '$color', marginTop: 2 }}>
                            {PLATFORM_NAMES[connection.platform]}
                        </Text>
                    </MetricItem>
                </MetricsRow>

                {/* Quick Actions */}
                <QuickActions>
                    <ActionButton onPress={() => handleSync(connection.id)}>
                        <Sync size={14} color="white" />
                        <Text style={{ marginLeft: 4, color: 'white', fontSize: 12 }}>Sync</Text>
                    </ActionButton>
                    
                    <SecondaryButton onPress={() => handleDisconnect(connection.id, connection.platform)}>
                        <Settings size={14} color="$gray11" />
                        <Text style={{ marginLeft: 4, color: '$gray11', fontSize: 12 }}>Manage</Text>
                    </SecondaryButton>
                </QuickActions>
            </ConnectionCard>
        );
    }, [onPlatformSelect, handleSync, handleDisconnect]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Connections
                    </Text>
                </Header>
                <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                    <ActivityIndicator size="large" color="$blue9" />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Loading connections...
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
                        Connections
                    </Text>
                </Header>
                <EmptyState>
                    <AlertCircle size={48} color="$red8" />
                    <Text style={{ color: '$red11', marginTop: 16, textAlign: 'center' }}>
                        Failed to load connections
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
                    Connections
                </Text>
                <TouchableOpacity onPress={handleRefresh}>
                    <RefreshCw size={20} color="$blue9" />
                </TouchableOpacity>
            </Header>

            {/* Statistics */}
            <StatsContainer>
                <StatCard>
                    <StatValue style={{ color: '$green9' }}>{stats.active}</StatValue>
                    <StatLabel>Active</StatLabel>
                </StatCard>
                <StatCard>
                    <StatValue>{stats.total}</StatValue>
                    <StatLabel>Total</StatLabel>
                </StatCard>
                <StatCard>
                    <StatValue style={{ color: '$blue9' }}>{stats.platforms}</StatValue>
                    <StatLabel>Platforms</StatLabel>
                </StatCard>
                <StatCard>
                    <StatValue style={{ color: '$purple9', fontSize: 14 }}>{stats.lastSync}</StatValue>
                    <StatLabel>Last Sync</StatLabel>
                </StatCard>
            </StatsContainer>

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
                {/* Active Connections */}
                {connections.length > 0 && (
                    <>
                        <SectionHeader>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                                Connected Platforms
                            </Text>
                            <Text style={{ fontSize: 14, color: '$gray11' }}>
                                {connections.length} total
                            </Text>
                        </SectionHeader>
                        {connections.map(renderConnection)}
                    </>
                )}

                {/* Add New Connection */}
                <SectionHeader>
                    <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                        Add Platform
                    </Text>
                </SectionHeader>

                <AddConnectionCard onPress={onAddConnection}>
                    <Plus size={32} color="$gray8" />
                    <Text style={{ 
                        fontSize: 16, 
                        fontWeight: '600', 
                        color: '$color',
                        marginTop: 12,
                    }}>
                        Connect New Platform
                    </Text>
                    <Text style={{ 
                        fontSize: 14, 
                        color: '$gray11',
                        marginTop: 4,
                        textAlign: 'center',
                    }}>
                        Add Gmail, Slack, Discord, or other platforms
                    </Text>
                </AddConnectionCard>

                {/* Empty State */}
                {connections.length === 0 && (
                    <EmptyState>
                        <Activity size={48} color="$gray8" />
                        <Text style={{ 
                            fontSize: 18, 
                            fontWeight: '600', 
                            color: '$color',
                            marginTop: 16,
                        }}>
                            No Connections Yet
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            marginTop: 8,
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            Connect your first platform to start{'\n'}
                            syncing messages and generating insights
                        </Text>
                        <TouchableOpacity
                            onPress={onAddConnection}
                            style={{
                                backgroundColor: '$blue8',
                                paddingHorizontal: 20,
                                paddingVertical: 12,
                                borderRadius: 8,
                                marginTop: 20,
                            }}
                        >
                            <Text style={{ color: 'white', fontWeight: '500' }}>
                                Get Started
                            </Text>
                        </TouchableOpacity>
                    </EmptyState>
                )}
            </ScrollView>
        </Container>
    );
};

export default ConnectionDashboard;