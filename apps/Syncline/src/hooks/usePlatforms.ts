/**
 * Platform Connection Hooks
 * 
 * React hooks for managing platform connections:
 * - Generic platform operations
 * - Slack integration
 * - Discord integration
 * - Gmail integration
 * - Connection health monitoring
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { platformAPI, slackAPI, discordAPI, gmailAPI } from '../api/endpoints/platforms';
import {
    PlatformConnection,
    SlackConnection,
    DiscordConnection,
    GmailConnection,
    Platform,
} from '../types';

// =============================================================================
// Generic Platform Connections Hook
// =============================================================================

export const usePlatformConnections = () => {
    const [connections, setConnections] = useState<PlatformConnection[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchConnections = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const platformConnections = await platformAPI.listConnections();
            setConnections(platformConnections);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch connections');
            setConnections([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const deleteConnection = useCallback(async (connectionId: string) => {
        try {
            await platformAPI.deleteConnection(connectionId);
            setConnections(prev => prev.filter(conn => conn.id !== connectionId));
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to delete connection');
        }
    }, []);

    const triggerSync = useCallback(async (connectionId: string) => {
        try {
            const result = await platformAPI.triggerSync(connectionId);
            // Refresh connections to get updated sync status
            await fetchConnections();
            return result;
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to trigger sync');
        }
    }, [fetchConnections]);

    useEffect(() => {
        fetchConnections();
    }, [fetchConnections]);

    // Group connections by platform
    const connectionsByPlatform = useMemo(() => {
        const grouped: Record<Platform, PlatformConnection[]> = {
            gmail: [],
            slack: [],
            discord: [],
            telegram: [],
            twitter: [],
            whatsapp: [],
            linkedin: [],
            google_chat: [],
        };

        connections.forEach(connection => {
            grouped[connection.platform].push(connection);
        });

        return grouped;
    }, [connections]);

    // Get active connections
    const activeConnections = useMemo(
        () => connections.filter(conn => conn.status === 'active'),
        [connections]
    );

    // Get connection health status
    const getConnectionHealth = useCallback(async (connectionId: string) => {
        try {
            return await platformAPI.getConnectionHealth(connectionId);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to get connection health');
        }
    }, []);

    return {
        connections,
        connectionsByPlatform,
        activeConnections,
        loading,
        error,
        fetchConnections,
        deleteConnection,
        triggerSync,
        getConnectionHealth,
    };
};

// =============================================================================
// Slack Integration Hook
// =============================================================================

export const useSlackIntegration = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const initiateOAuth = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const { authorization_url } = await slackAPI.initiateOAuth();
            // Open OAuth URL in browser
            window.open(authorization_url, '_blank');
            return authorization_url;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to initiate Slack OAuth');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const completeOAuth = useCallback(async (code: string, state: string) => {
        setLoading(true);
        setError(null);

        try {
            const connection = await slackAPI.completeOAuth(code, state);
            return connection;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to complete Slack OAuth');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        loading,
        error,
        initiateOAuth,
        completeOAuth,
    };
};

// =============================================================================
// Slack Connection Management Hook
// =============================================================================

export const useSlackConnection = (connectionId?: string) => {
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [channels, setChannels] = useState<any[]>([]);
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchWorkspaces = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const slackWorkspaces = await slackAPI.listWorkspaces(id);
            setWorkspaces(slackWorkspaces);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Slack workspaces');
            setWorkspaces([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchChannels = useCallback(async (id: string, options?: {
        types?: ('public_channel' | 'private_channel' | 'im' | 'mpim')[];
        exclude_archived?: boolean;
    }) => {
        setLoading(true);
        setError(null);

        try {
            const slackChannels = await slackAPI.listChannels(id, options);
            setChannels(slackChannels);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Slack channels');
            setChannels([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchUsers = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const slackUsers = await slackAPI.listUsers(id);
            setUsers(slackUsers);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Slack users');
            setUsers([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchMessages = useCallback(async (
        id: string,
        channelId: string,
        options?: {
            oldest?: string;
            latest?: string;
            limit?: number;
            inclusive?: boolean;
        }
    ) => {
        try {
            return await slackAPI.fetchMessages(id, channelId, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch Slack messages');
        }
    }, []);

    const fetchAllMessages = useCallback(async (
        id: string,
        options?: {
            since?: string;
            until?: string;
            limit_per_channel?: number;
        }
    ) => {
        try {
            return await slackAPI.fetchAllMessages(id, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch all Slack messages');
        }
    }, []);

    useEffect(() => {
        if (connectionId) {
            fetchWorkspaces(connectionId);
            fetchChannels(connectionId);
            fetchUsers(connectionId);
        }
    }, [connectionId, fetchWorkspaces, fetchChannels, fetchUsers]);

    return {
        workspaces,
        channels,
        users,
        loading,
        error,
        fetchMessages,
        fetchAllMessages,
        refetch: connectionId ? () => {
            fetchWorkspaces(connectionId);
            fetchChannels(connectionId);
            fetchUsers(connectionId);
        } : undefined,
    };
};

// =============================================================================
// Discord Integration Hook
// =============================================================================

export const useDiscordIntegration = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const getBotInviteUrl = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const inviteData = await discordAPI.getBotInviteUrl();
            return inviteData;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to get Discord bot invite URL');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const registerConnection = useCallback(async (botToken: string) => {
        setLoading(true);
        setError(null);

        try {
            const connection = await discordAPI.registerConnection(botToken);
            return connection;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to register Discord connection');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        loading,
        error,
        getBotInviteUrl,
        registerConnection,
    };
};

// =============================================================================
// Discord Connection Management Hook
// =============================================================================

export const useDiscordConnection = (connectionId?: string) => {
    const [guilds, setGuilds] = useState<any[]>([]);
    const [channels, setChannels] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchGuilds = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const discordGuilds = await discordAPI.listGuilds(id);
            setGuilds(discordGuilds);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Discord guilds');
            setGuilds([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchChannels = useCallback(async (id: string, guildId?: string) => {
        setLoading(true);
        setError(null);

        try {
            const discordChannels = await discordAPI.listChannels(id, guildId);
            setChannels(discordChannels);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Discord channels');
            setChannels([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const getUser = useCallback(async (id: string, userId: string) => {
        try {
            return await discordAPI.getUser(id, userId);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch Discord user');
        }
    }, []);

    const fetchMessages = useCallback(async (
        id: string,
        channelId: string,
        options?: {
            before?: string;
            after?: string;
            around?: string;
            limit?: number;
        }
    ) => {
        try {
            return await discordAPI.fetchMessages(id, channelId, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch Discord messages');
        }
    }, []);

    const fetchAllMessages = useCallback(async (
        id: string,
        options?: {
            since?: string;
            until?: string;
            limit_per_channel?: number;
        }
    ) => {
        try {
            return await discordAPI.fetchAllMessages(id, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch all Discord messages');
        }
    }, []);

    useEffect(() => {
        if (connectionId) {
            fetchGuilds(connectionId);
            fetchChannels(connectionId);
        }
    }, [connectionId, fetchGuilds, fetchChannels]);

    return {
        guilds,
        channels,
        loading,
        error,
        getUser,
        fetchMessages,
        fetchAllMessages,
        refetch: connectionId ? () => {
            fetchGuilds(connectionId);
            fetchChannels(connectionId);
        } : undefined,
    };
};

// =============================================================================
// Gmail Integration Hook
// =============================================================================

export const useGmailIntegration = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const initiateOAuth = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const { authorization_url } = await gmailAPI.initiateOAuth();
            // Open OAuth URL in browser
            window.open(authorization_url, '_blank');
            return authorization_url;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to initiate Gmail OAuth');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const completeOAuth = useCallback(async (code: string, state: string) => {
        setLoading(true);
        setError(null);

        try {
            const connection = await gmailAPI.completeOAuth(code, state);
            return connection;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to complete Gmail OAuth');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        loading,
        error,
        initiateOAuth,
        completeOAuth,
    };
};

// =============================================================================
// Gmail Connection Management Hook
// =============================================================================

export const useGmailConnection = (connectionId?: string) => {
    const [profile, setProfile] = useState<any>(null);
    const [labels, setLabels] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchProfile = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const gmailProfile = await gmailAPI.getProfile(id);
            setProfile(gmailProfile);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Gmail profile');
            setProfile(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchLabels = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const gmailLabels = await gmailAPI.listLabels(id);
            setLabels(gmailLabels);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch Gmail labels');
            setLabels([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchMessages = useCallback(async (
        id: string,
        options?: {
            query?: string;
            label_ids?: string[];
            max_results?: number;
            page_token?: string;
            include_spam_trash?: boolean;
        }
    ) => {
        try {
            return await gmailAPI.fetchMessages(id, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch Gmail messages');
        }
    }, []);

    const setupPushNotifications = useCallback(async (id: string) => {
        try {
            return await gmailAPI.setupPushNotifications(id);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to setup Gmail push notifications');
        }
    }, []);

    const fetchAllMessages = useCallback(async (
        id: string,
        options?: {
            since?: string;
            until?: string;
            labels?: string[];
            max_results?: number;
        }
    ) => {
        try {
            return await gmailAPI.fetchAllMessages(id, options);
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to fetch all Gmail messages');
        }
    }, []);

    useEffect(() => {
        if (connectionId) {
            fetchProfile(connectionId);
            fetchLabels(connectionId);
        }
    }, [connectionId, fetchProfile, fetchLabels]);

    return {
        profile,
        labels,
        loading,
        error,
        fetchMessages,
        setupPushNotifications,
        fetchAllMessages,
        refetch: connectionId ? () => {
            fetchProfile(connectionId);
            fetchLabels(connectionId);
        } : undefined,
    };
};