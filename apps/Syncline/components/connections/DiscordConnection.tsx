/**
 * Discord Connection Component
 * 
 * Handles Discord server integration:
 * - Bot invite URL generation
 * - Guild and channel management
 * - Message fetching controls
 * - Permission configuration
 */

import React, { useState, useCallback, useEffect } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    ScrollView, 
    Alert,
    ActivityIndicator,
    Linking,
    TextInput
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
    RefreshCw,
    Bot,
    Copy,
    Shield
} from '@tamagui/lucide-icons';
import { usePlatforms } from '../../src/hooks/usePlatforms';
import { DiscordConnection as DiscordConnectionType } from '../../src/types';
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

const DiscordLogo = styled(View, {
    width: 24,
    height: 24,
    borderRadius: 6,
    backgroundColor: PLATFORM_COLORS.discord,
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
    backgroundColor: PLATFORM_COLORS.discord,
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

const GuildList = styled(View, {
    marginTop: '$3',
});

const GuildItem = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: '$2',
    paddingHorizontal: '$3',
    backgroundColor: '$gray1',
    borderRadius: '$2',
    marginBottom: '$2',
});

const InviteContainer = styled(View, {
    backgroundColor: '$gray1',
    borderRadius: '$3',
    padding: '$3',
    marginVertical: '$3',
});

const InviteInput = styled(TextInput, {
    backgroundColor: '$background',
    borderRadius: '$2',
    padding: '$2',
    fontSize: '$3',
    color: '$color',
    borderWidth: 1,
    borderColor: '$gray6',
    marginTop: '$2',
});

const TokenInput = styled(TextInput, {
    backgroundColor: '$background',
    borderRadius: '$2',
    padding: '$3',
    fontSize: '$3',
    color: '$color',
    borderWidth: 1,
    borderColor: '$gray6',
    marginTop: '$2',
    fontFamily: 'monospace',
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

interface DiscordConnectionProps {
    onConnectionChange?: (connections: DiscordConnectionType[]) => void;
}

export const DiscordConnection: React.FC<DiscordConnectionProps> = ({
    onConnectionChange,
}) => {
    const [connecting, setConnecting] = useState(false);
    const [showTokenInput, setShowTokenInput] = useState(false);
    const [botToken, setBotToken] = useState('');
    const [inviteUrl, setInviteUrl] = useState('');

    const {
        connections,
        loading,
        error,
        connectDiscord,
        disconnectPlatform,
        syncPlatform,
        getDiscordGuilds,
        getDiscordChannels,
        fetchAllDiscordMessages,
        getDiscordBotInviteUrl,
    } = usePlatforms();

    // Filter Discord connections
    const discordConnections = connections.filter(
        conn => conn.platform === 'discord'
    ) as DiscordConnectionType[];

    useEffect(() => {
        onConnectionChange?.(discordConnections);
    }, [discordConnections, onConnectionChange]);

    // Get bot invite URL on mount
    useEffect(() => {
        const fetchInviteUrl = async () => {
            try {
                const response = await getDiscordBotInviteUrl();
                setInviteUrl(response.invite_url);
            } catch (err) {
                console.error('Failed to get bot invite URL:', err);
            }
        };
        fetchInviteUrl();
    }, [getDiscordBotInviteUrl]);

    // Handle bot token connection
    const handleConnectWithToken = useCallback(async () => {
        if (!botToken.trim()) {
            Alert.alert('Error', 'Please enter a bot token');
            return;
        }

        setConnecting(true);
        try {
            await connectDiscord(botToken.trim());
            setBotToken('');
            setShowTokenInput(false);
            Alert.alert('Success', 'Discord bot connected successfully!');
        } catch (err) {
            Alert.alert('Error', 'Failed to connect Discord bot. Please check your token.');
        } finally {
            setConnecting(false);
        }
    }, [botToken, connectDiscord]);

    // Handle disconnect
    const handleDisconnect = useCallback(async (connectionId: string) => {
        Alert.alert(
            'Disconnect Discord',
            'Are you sure you want to disconnect this Discord bot? This will stop message syncing.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Disconnect',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            await disconnectPlatform(connectionId);
                            Alert.alert('Success', 'Discord bot disconnected');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to disconnect bot');
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
            'This will fetch all messages from all accessible channels. This may take a while.',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Start',
                    onPress: async () => {
                        try {
                            await fetchAllDiscordMessages(connectionId);
                            Alert.alert('Success', 'Message fetching started');
                        } catch (err) {
                            Alert.alert('Error', 'Failed to start message fetching');
                        }
                    },
                },
            ]
        );
    }, [fetchAllDiscordMessages]);

    // Copy invite URL to clipboard
    const handleCopyInviteUrl = useCallback(async () => {
        if (inviteUrl) {
            // Note: React Native doesn't have built-in clipboard
            // You might need to install @react-native-clipboard/clipboard
            Alert.alert('Invite URL', inviteUrl, [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Open',
                    onPress: () => Linking.openURL(inviteUrl),
                },
            ]);
        }
    }, [inviteUrl]);

    // Render connection card
    const renderConnection = useCallback((connection: DiscordConnectionType) => {
        const statusStyle = getStatusColor(connection.status);
        const statusIcon = getStatusIcon(connection.status);
        const metadata = connection.platform_metadata;

        return (
            <ConnectionCard key={connection.id}>
                <ConnectionHeader>
                    <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                            <DiscordLogo />
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                                {metadata?.bot_username || 'Discord Bot'}
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
                        <Text style={{ color: '$gray11' }}>Bot ID</Text>
                        <Text style={{ color: '$color', fontWeight: '500', fontFamily: 'monospace' }}>
                            {metadata?.bot_id || 'N/A'}
                        </Text>
                    </MetricRow>
                    <MetricRow>
                        <Text style={{ color: '$gray11' }}>Guilds</Text>
                        <Text style={{ color: '$color', fontWeight: '500' }}>
                            {metadata?.guilds_count || 0}
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

                {/* Guild Preview */}
                {metadata?.guilds_count && metadata.guilds_count > 0 && (
                    <GuildList>
                        <Text style={{ 
                            fontSize: 14, 
                            fontWeight: '600', 
                            color: '$color',
                            marginBottom: 8,
                        }}>
                            Connected Guilds
                        </Text>
                        <TouchableOpacity
                            onPress={async () => {
                                try {
                                    const guilds = await getDiscordGuilds(connection.id);
                                    Alert.alert(
                                        'Guilds',
                                        `Connected to ${guilds.length} guilds:\n${guilds.slice(0, 5).map(g => g.name).join('\n')}${guilds.length > 5 ? '\n...' : ''}`
                                    );
                                } catch (err) {
                                    Alert.alert('Error', 'Failed to fetch guilds');
                                }
                            }}
                        >
                            <GuildItem>
                                <Users size={16} color={PLATFORM_COLORS.discord} />
                                <Text style={{ marginLeft: 8, color: '$color' }}>
                                    View all guilds ({metadata.guilds_count})
                                </Text>
                                <ExternalLink size={14} color="$gray9" style={{ marginLeft: 'auto' }} />
                            </GuildItem>
                        </TouchableOpacity>
                    </GuildList>
                )}
            </ConnectionCard>
        );
    }, [handleSync, handleFetchAll, handleDisconnect, getDiscordGuilds]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <DiscordLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Discord Integration
                    </Text>
                </Header>
                <LoadingContainer>
                    <ActivityIndicator size="large" color={PLATFORM_COLORS.discord} />
                    <Text style={{ marginTop: 16, color: '$gray11' }}>
                        Loading Discord connections...
                    </Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error) {
        return (
            <Container>
                <Header>
                    <DiscordLogo />
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Discord Integration
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
                <DiscordLogo />
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Discord Integration
                </Text>
            </Header>

            <ScrollView showsVerticalScrollIndicator={false}>
                {/* Existing Connections */}
                {discordConnections.map(renderConnection)}

                {/* Add New Connection */}
                <ConnectionCard>
                    <View style={{ alignItems: 'center', paddingVertical: 20 }}>
                        <Bot size={48} color="$gray8" />
                        <Text style={{ 
                            fontSize: 16, 
                            fontWeight: '600', 
                            color: '$color',
                            marginTop: 16,
                            textAlign: 'center',
                        }}>
                            Connect Discord Bot
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            marginTop: 8,
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            Add our bot to your Discord server to sync messages{'\n'}
                            and enable AI-powered insights
                        </Text>

                        {/* Bot Invite Section */}
                        {inviteUrl && (
                            <InviteContainer>
                                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                                    <Shield size={16} color={PLATFORM_COLORS.discord} />
                                    <Text style={{ 
                                        marginLeft: 6, 
                                        fontSize: 14, 
                                        fontWeight: '600', 
                                        color: '$color',
                                    }}>
                                        Step 1: Invite Bot to Server
                                    </Text>
                                </View>
                                <Text style={{ fontSize: 12, color: '$gray11', marginBottom: 8 }}>
                                    Click the button below to invite our bot to your Discord server
                                </Text>
                                <ActionButton onPress={handleCopyInviteUrl}>
                                    <ExternalLink size={16} color="white" />
                                    <Text style={{ marginLeft: 6, color: 'white', fontWeight: '500' }}>
                                        Invite Bot to Server
                                    </Text>
                                </ActionButton>
                            </InviteContainer>
                        )}

                        {/* Token Input Section */}
                        <InviteContainer>
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                                <Bot size={16} color={PLATFORM_COLORS.discord} />
                                <Text style={{ 
                                    marginLeft: 6, 
                                    fontSize: 14, 
                                    fontWeight: '600', 
                                    color: '$color',
                                }}>
                                    Step 2: Connect with Bot Token
                                </Text>
                            </View>
                            <Text style={{ fontSize: 12, color: '$gray11', marginBottom: 8 }}>
                                Enter your Discord bot token to establish the connection
                            </Text>
                            
                            {!showTokenInput ? (
                                <SecondaryButton onPress={() => setShowTokenInput(true)}>
                                    <Plus size={16} color="$gray11" />
                                    <Text style={{ marginLeft: 6, color: '$gray11' }}>
                                        Enter Bot Token
                                    </Text>
                                </SecondaryButton>
                            ) : (
                                <View>
                                    <TokenInput
                                        value={botToken}
                                        onChangeText={setBotToken}
                                        placeholder="Enter your Discord bot token..."
                                        placeholderTextColor="$gray9"
                                        secureTextEntry
                                        autoCapitalize="none"
                                        autoCorrect={false}
                                    />
                                    <View style={{ flexDirection: 'row', marginTop: 12 }}>
                                        <ActionButton 
                                            onPress={handleConnectWithToken} 
                                            disabled={connecting || !botToken.trim()}
                                            style={{ flex: 1 }}
                                        >
                                            {connecting ? (
                                                <ActivityIndicator size="small" color="white" />
                                            ) : (
                                                <Check size={16} color="white" />
                                            )}
                                            <Text style={{ 
                                                marginLeft: 6, 
                                                color: 'white', 
                                                fontWeight: '500',
                                            }}>
                                                {connecting ? 'Connecting...' : 'Connect Bot'}
                                            </Text>
                                        </ActionButton>
                                        <SecondaryButton 
                                            onPress={() => {
                                                setShowTokenInput(false);
                                                setBotToken('');
                                            }}
                                            style={{ marginLeft: 8 }}
                                        >
                                            <Text style={{ color: '$gray11' }}>Cancel</Text>
                                        </SecondaryButton>
                                    </View>
                                </View>
                            )}
                        </InviteContainer>
                    </View>
                </ConnectionCard>

                {/* Empty State */}
                {discordConnections.length === 0 && (
                    <View style={{ padding: 20, alignItems: 'center' }}>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray9',
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            No Discord bots connected yet.{'\n'}
                            Follow the steps above to connect your first bot.
                        </Text>
                    </View>
                )}
            </ScrollView>
        </Container>
    );
};

export default DiscordConnection;