/**
 * Slack Connection Component
 * 
 * Handles Slack workspace integration:
 * - OAuth flow initiation
 * - Workspace and channel selection
 * - Message sync configuration
 * - Connection health monitoring
 */

import React, { useState, useCallback, useEffect } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    ScrollView, 
    Alert,
    ActivityIndicator,
    Linking
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Plus, 
    Check, 
    AlertCircle, 
    Settings, 
    Users, 
    Hash,
    Sync,
    ExternalLink,
    Trash2,
    RefreshCw
} from '@tamagui/lucide-icons';
import { usePlatforms } from '../../src/hooks/usePlatforms';
import { SlackConnection as SlackConnectionType } from '../../src/types';
import { PLATFORM_COLORS } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '$background',
});

const Header = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
});

const SlackLogo = styled(View, {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: PLATFORM_COLORS.slack,
    marginRight: '$3',
});

const ConnectionCard = styled(View, {
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

const StatusBadge = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const ActionButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginTop: '$3',
});

const SecondaryButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginTop: '$2',
    marginLeft: '$2',
});

const DeleteButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$red2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginTop: '$2',
});

const MetricRow = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: '$2',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const ChannelList = styled(View, {
    marginTop: '$3',
});

const ChannelItem = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: '$2',
    paddingHorizontal: '$3',
    backgroundColor: '$gray1',
    borderRadius: '$2',
    marginBottom: '$2',
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

const getStatusColor = (status: string) => {
    switch (status) {
        case 'active': return { bg: '$green3', text: '$green11' };
        case 'inactive': return { bg: '$gray3', text: '$gray11' };
        case 'error': return { bg: '$red3', text: '$red11' };
        case 'pending': return { bg: '$yellow3', text: '$yellow11' };
        default: return { bg: '$gray3', text: '$gray11' };
    }
};

const getStatusIcon = (status: string) => {
    switch (status) {
        case 'active': return <Check size={14} color="$green9" />;
        case 'error': return <AlertCircle size={14} color="$red9" />;
        case 'pending': return <RefreshCw size={14} color="$yellow9" />;
        default: return <AlertCircle size={14} color="$gray9" />;
    }
};

const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
};

// =============================================================================
// Main Component
// =============================================================================

interface SlackConnectionProps {
    onConnectionChange?: (connections: SlackConnectionType[]) => void;
}

export const SlackConnection: React.FC<SlackConnectionProps> = ({
    onConnectionChange,
}) => {
    const [connecting, setConnecting] = useState(false);
    const [selectedConnection, setSelectedConnection] = useState<string | null>(null);

    const {
        connections,
        loading,
        error,
        connectSlack,
        disconnectPlatform,
        syncPlatform,
        getSlackChannels,
        getSlackWorkspaces,
        fetchAllSlackMessages,
    } = usePlatforms();

    // Filter Slack connections
    const slackConnections = connections.filter(
        conn => conn.platform === 'slack'
    ) as SlackConnectionType[];

    useEffect(() => {
        onConnectionChange?.(slackConnections);
    }, [slackConnections, onConnectionChange]);

    // Handle OAuth connection
    const handleConnect = useCallback(async () => {
        setConnecting(true);
        try {
            await connectSlack();
            Alert.alert('Success', 'Slack workspace connected successfully!');
        } catch (err) {
            Alert.alert('Error', 'Failed to connect Slack workspace');
        } finally {
            setConnecting(false);
        }
    }, [connectSlack]);

    // Handle disconnect
    const handleDisconnect = useCallback(async (connectionId: string) => {
        Alert.alert(
            'Disconnect Slack',
            'Are you sure you want to disconnect this Slack workspace? This will stop message syncing.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Disconnect',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await disconnectPlatform(connectionId);
                            Alert.alert('Success', 'Slack workspace disconnected');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to disconnect workspace');
                        }
                    },
                },
            ]
        );
    }, [disconnectPlatform]);

    // Handle sync
    const handleSync = useCallback(async (connectionId: string) => {
        try {
            await syncPlatform(connectionId);
            Alert.alert('Success', 'Sync started successfully');
        } catch (err) {
            Alert.alert('Error', 'Failed to start sync');
        }
    }, [syncPlatform]);

    // Handle fetch all messages
    const handleFetchAll = useCallback(async (connectionId: string) => {
        Alert.alert(
            'Fetch All Messages',
            'This will fetch all messages from all channels. This may take a while.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Start',
                    onPress: async () => {
                        try {
                            await fetchAllSlackMessages(connectionId);
                            Alert.alert('Success', 'Message fetching started');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to start message fetching');
                        }
                    },
                },
            ]
        );
    }, [fetchAllSlackMessages]);

    // Render connection card
    const renderConnection = useCallback((connection: SlackConnectionType) => {
        const statusStyle = getStatusColor(connection.status);
        const statusIcon = getStatusIcon(connection.status);
        const metadata = connection.platform_metadata;

        return (
            <ConnectionCard key={connection.id}>
                <ConnectionHeader>
                    <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                            <SlackLogo />
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                                {metadata?.team_name || 'Slack Workspace'}
                            </Text>
                        </View>
                        <StatusBadge style={{ backgroundColor: statusStyle.bg, alignSelf: 'flex-start' }}>
                            {statusIcon}
                            <Text style={{ 
                                marginLeft: 6, 
                                fontSize: 12, 
                                color: statusStyle.text,
                                textTransform: 'capitalize',
                            }}>
                                {connection.status}
                            </Text>
                        </StatusBadge>
                    </View>
                </ConnectionHeader>

                {/* Connection Metrics */}
                <View>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Team ID</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {metadata?.team_id || 'N/A'}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Channels</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {metadata?.channels_count || 0}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Connected</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {formatDate(connection.connected_at)}
                        </Text>
                    </MetricRow>
                    <MetricRow style={{ borderBottomWidth: 0 }}>
                        <Text style={{ color: '$gray11' }}>Last Sync</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {formatDate(connection.last_sync_at)}
                        </Text>
                    </MetricRow>
                </View>

                {/* Actions */}
                <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                    <ActionButton onPress={() => handleSync(connection.id)}>
                        <Sync size={16} color="white" />
                        <Text style={{ marginLeft: 6, color: 'white', fontWeight: '500' }}>
                            Sync Now
                        </Text>
                    </ActionButton>

                    <SecondaryButton onPress={() => handleFetchAll(connection.id)}>
                        <RefreshCw size={16} color="$gray11" />
                        <Text style={{ marginLeft: 6, color: '$gray11' }}>
                            Fetch All
                        </Text>
                    </SecondaryButton>

                    <DeleteButton onPress={() => handleDisconnect(connection.id)}>
                        <Trash2 size={16} color="$red11" />
                        <Text style={{ marginLeft: 6, color: '$red11' }}>
                            Disconnect
                        </Text>
                    </DeleteButton>
                </View>

                {/* Channel Preview */}
                {metadata?.channels_count && metadata.channels_count > 0 && (
                    <ChannelList>
                        <Text style={{ 
                            fontSize: 14, 
                            fontWeight: '600', 
                            color: '$color',
                            marginBottom: 8,
                        }}>
                            Recent Channels
                        </Text>
                        <TouchableOpacity
                            onPress={async () => {
                                try {
                                    const channels = await getSlackChannels(connection.id);
                                    Alert.alert(
                                        'Channels',
                                        `Found ${channels.length} channels:\n${channels.slice(0, 5).map(c => `#${c.name}`).join('\n')}${channels.length > 5 ? '\n...' : ''}`
                                    );
                                } catch (err) {
                                    Alert.alert('Error', 'Failed to fetch channels');
                                }
                            }}
                        >
                            <ChannelItem>
                                <Hash size={16} color="$blue9" />
                                <Text style={{ marginLeft: 8, color: '$color' }}>
                                    View all channels ({metadata.channels_count})
                                </Text>
                                <ExternalLink size={14} color="$gray9" style={{ marginLeft: 'auto' }} />
                            </ChannelItem>
                        </TouchableOpacity>
                    </ChannelList>
                )}
            </ConnectionCard>
        );
    }, [handleSync, handleFetchAll, handleDisconnect, getSlackChannels]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <SlackLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Slack Integration
                    </Text>
                </Header>
                <LoadingContainer>
                    <ActivityIndicator size="large" color={PLATFORM_COLORS.slack} />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Loading Slack connections...
                    </Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error) {
        return (
            <Container>
                <Header>
                    <SlackLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Slack Integration
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
                </EmptyState>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <SlackLogo />
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Slack Integration
                </Text>
            </Header>

            <ScrollView showsVerticalScrollIndicator={false}>
                {/* Existing Connections */}
                {slackConnections.map(renderConnection)}

                {/* Add New Connection */}
                <ConnectionCard>
                    <View style={{ alignItems: 'center', paddingVertical: 20 }}>
                        <Plus size={48} color="$gray8" />
                        <Text style={{ 
                            fontSize: 16, 
                            fontWeight: '600', 
                            color: '$color',
                            marginTop: 16,
                            textAlign: 'center',
                        }}>
                            Connect Slack Workspace
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            marginTop: 8,
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            Connect your Slack workspace to sync messages{'\n'}
                            and enable AI-powered insights
                        </Text>
                        
                        <ActionButton 
                            onPress={handleConnect} 
                            disabled={connecting}
                            style={{ marginTop: 20 }}
                        >
                            {connecting ? (
                                <ActivityIndicator size="small" color="white" />
                            ) : (
                                <Plus size={16} color="white" />
                            )}
                            <Text style={{ 
                                marginLeft: 6, 
                                color: 'white', 
                                fontWeight: '500',
                            }}>
                                {connecting ? 'Connecting...' : 'Connect Workspace'}
                            </Text>
                        </ActionButton>
                    </View>
                </ConnectionCard>

                {/* Empty State */}
                {slackConnections.length === 0 && (
                    <View style={{ padding: 20, alignItems: 'center' }}>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray9',
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            No Slack workspaces connected yet.{'\n'}
                            Connect your first workspace to get started.
                        </Text>
                    </View>
                )}
            </ScrollView>
        </Container>
    );
};

export default SlackConnection;