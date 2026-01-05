/**
 * Gmail Connection Component
 * 
 * Handles Gmail account integration:
 * - OAuth flow for Gmail
 * - Label management and filtering
 * - Push notification setup
 * - Sync configuration
 */

import React, { useState, useCallback, useEffect } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    ScrollView, 
    Alert,
    ActivityIndicator,
    Switch
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Plus, 
    Check, 
    AlertCircle, 
    Mail, 
    Tag,
    Sync,
    Bell,
    Trash2,
    RefreshCw,
    Settings,
    Filter
} from '@tamagui/lucide-icons';
import { usePlatforms } from '../../src/hooks/usePlatforms';
import { GmailConnection as GmailConnectionType } from '../../src/types';
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

const GmailLogo = styled(View, {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: PLATFORM_COLORS.gmail,
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
    backgroundColor: PLATFORM_COLORS.gmail,
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

const SettingRow = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const LabelList = styled(View, {
    marginTop: '$3',
});

const LabelItem = styled(View, {
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

const formatWatchExpiration = (dateString?: string) => {
    if (!dateString) return 'Not set';
    const date = new Date(dateString);
    const now = new Date();
    const diffHours = Math.round((date.getTime() - now.getTime()) / (1000 * 60 * 60));
    
    if (diffHours < 0) return 'Expired';
    if (diffHours < 24) return `${diffHours}h remaining`;
    return `${Math.round(diffHours / 24)}d remaining`;
};

// =============================================================================
// Main Component
// =============================================================================

interface GmailConnectionProps {
    onConnectionChange?: (connections: GmailConnectionType[]) => void;
}

export const GmailConnection: React.FC<GmailConnectionProps> = ({
    onConnectionChange,
}) => {
    const [connecting, setConnecting] = useState(false);
    const [pushNotifications, setPushNotifications] = useState<Record<string, boolean>>({});

    const {
        connections,
        loading,
        error,
        connectGmail,
        disconnectPlatform,
        syncPlatform,
        getGmailLabels,
        getGmailProfile,
        fetchAllGmailMessages,
        setupGmailPushNotifications,
    } = usePlatforms();

    // Filter Gmail connections
    const gmailConnections = connections.filter(
        conn => conn.platform === 'gmail'
    ) as GmailConnectionType[];

    useEffect(() => {
        onConnectionChange?.(gmailConnections);
    }, [gmailConnections, onConnectionChange]);

    // Initialize push notification states
    useEffect(() => {
        const initialStates: Record<string, boolean> = {};
        gmailConnections.forEach(conn => {
            initialStates[conn.id] = !!conn.platform_metadata?.watch_expiration;
        });
        setPushNotifications(initialStates);
    }, [gmailConnections]);

    // Handle OAuth connection
    const handleConnect = useCallback(async () => {
        setConnecting(true);
        try {
            await connectGmail();
            Alert.alert('Success', 'Gmail account connected successfully!');
        } catch (err) {
            Alert.alert('Error', 'Failed to connect Gmail account');
        } finally {
            setConnecting(false);
        }
    }, [connectGmail]);

    // Handle disconnect
    const handleDisconnect = useCallback(async (connectionId: string) => {
        Alert.alert(
            'Disconnect Gmail',
            'Are you sure you want to disconnect this Gmail account? This will stop message syncing.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Disconnect',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await disconnectPlatform(connectionId);
                            Alert.alert('Success', 'Gmail account disconnected');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to disconnect account');
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
            'This will fetch all messages from your Gmail account. This may take a while.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Start',
                    onPress: async () => {
                        try {
                            await fetchAllGmailMessages(connectionId);
                            Alert.alert('Success', 'Message fetching started');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to start message fetching');
                        }
                    },
                },
            ]
        );
    }, [fetchAllGmailMessages]);

    // Handle push notifications toggle
    const handlePushToggle = useCallback(async (connectionId: string, enabled: boolean) => {
        try {
            if (enabled) {
                await setupGmailPushNotifications(connectionId);
                Alert.alert('Success', 'Push notifications enabled');
            } else {
                // Note: You might need to add a disable push notifications API
                Alert.alert('Info', 'Push notifications will expire automatically');
            }
            setPushNotifications(prev => ({ ...prev, [connectionId]: enabled }));
        } catch (err) {
            Alert.alert('Error', 'Failed to configure push notifications');
        }
    }, [setupGmailPushNotifications]);

    // Render connection card
    const renderConnection = useCallback((connection: GmailConnectionType) => {
        const statusStyle = getStatusColor(connection.status);
        const statusIcon = getStatusIcon(connection.status);
        const metadata = connection.platform_metadata;
        const pushEnabled = pushNotifications[connection.id] || false;

        return (
            <ConnectionCard key={connection.id}>
                <ConnectionHeader>
                    <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                            <GmailLogo />
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                                {metadata?.email || 'Gmail Account'}
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
                        <Text style={{ color: '$gray11' }}>Email</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {metadata?.email || 'N/A'}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Labels</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {metadata?.labels_count || 0}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Connected</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {formatDate(connection.connected_at)}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Last Sync</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {formatDate(connection.last_sync_at)}
                        </Text>
                    </MetricRow>
                    <MetricRow style={{ borderBottomWidth: 0 }}>
                        <Text style={{ color: '$gray11' }}>Push Notifications</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {formatWatchExpiration(metadata?.watch_expiration)}
                        </Text>
                    </MetricRow>
                </View>

                {/* Settings */}
                <View style={{ marginTop: 16 }}>
                    <Text style={{ fontSize: 14, fontWeight: '600', color: '$color', marginBottom: 8 }}>
                        Settings
                    </Text>
                    <SettingRow style={{ borderBottomWidth: 0 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                            <Bell size={16} color="$blue9" />
                            <Text style={{ marginLeft: 8, color: '$color' }}>
                                Push Notifications
                            </Text>
                        </View>
                        <Switch
                            value={pushEnabled}
                            onValueChange={(value) => handlePushToggle(connection.id, value)}
                            trackColor={{ false: '$gray6', true: '$blue8' }}
                            thumbColor={pushEnabled ? '$blue9' : '$gray9'}
                        />
                    </SettingRow>
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

                {/* Labels Preview */}
                {metadata?.labels_count && metadata.labels_count > 0 && (
                    <LabelList>
                        <Text style={{ 
                            fontSize: 14, 
                            fontWeight: '600', 
                            color: '$color',
                            marginBottom: 8,
                        }}>
                            Gmail Labels
                        </Text>
                        <TouchableOpacity
                            onPress={async () => {
                                try {
                                    const labels = await getGmailLabels(connection.id);
                                    Alert.alert(
                                        'Labels',
                                        `Found ${labels.length} labels:\n${labels.slice(0, 5).map(l => l.name).join('\n')}${labels.length > 5 ? '\n...' : ''}`
                                    );
                                } catch (err) {
                                    Alert.alert('Error', 'Failed to fetch labels');
                                }
                            }}
                        >
                            <LabelItem>
                                <Tag size={16} color={PLATFORM_COLORS.gmail} />
                                <Text style={{ marginLeft: 8, color: '$color' }}>
                                    View all labels ({metadata.labels_count})
                                </Text>
                                <Filter size={14} color="$gray9" style={{ marginLeft: 'auto' }} />
                            </LabelItem>
                        </TouchableOpacity>
                    </LabelList>
                )}
            </ConnectionCard>
        );
    }, [
        pushNotifications,
        handleSync,
        handleFetchAll,
        handleDisconnect,
        handlePushToggle,
        getGmailLabels
    ]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <GmailLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Gmail Integration
                    </Text>
                </Header>
                <LoadingContainer>
                    <ActivityIndicator size="large" color={PLATFORM_COLORS.gmail} />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Loading Gmail connections...
                    </Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error) {
        return (
            <Container>
                <Header>
                    <GmailLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Gmail Integration
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
                <GmailLogo />
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Gmail Integration
                </Text>
            </Header>

            <ScrollView showsVerticalScrollIndicator={false}>
                {/* Existing Connections */}
                {gmailConnections.map(renderConnection)}

                {/* Add New Connection */}
                <ConnectionCard>
                    <View style={{ alignItems: 'center', paddingVertical: 20 }}>
                        <Mail size={48} color="$gray8" />
                        <Text style={{ 
                            fontSize: 16, 
                            fontWeight: '600', 
                            color: '$color',
                            marginTop: 16,
                            textAlign: 'center',
                        }}>
                            Connect Gmail Account
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            marginTop: 8,
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            Connect your Gmail account to sync emails{'\n'}
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
                                {connecting ? 'Connecting...' : 'Connect Account'}
                            </Text>
                        </ActionButton>
                    </View>
                </ConnectionCard>

                {/* Empty State */}
                {gmailConnections.length === 0 && (
                    <View style={{ padding: 20, alignItems: 'center' }}>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray9',
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            No Gmail accounts connected yet.{'\n'}
                            Connect your first account to get started.
                        </Text>
                    </View>
                )}
            </ScrollView>
        </Container>
    );
};

export default GmailConnection;