/**
 * Platform Connection API Endpoints
 * 
 * Handles connections to various platforms:
 * - Slack workspace integration
 * - Discord server integration
 * - Gmail account integration
 * - Platform-specific operations
 */

import { apiClient } from '../client';
import {
    Connection,
    SlackConnection,
    DiscordConnection,
    GmailConnection,
    PlatformConnection,
    Platform,
} from '../../types';

// =============================================================================
// Generic Platform Operations
// =============================================================================

export const platformAPI = {
    /**
     * List all platform connections
     */
    listConnections: async (): Promise<PlatformConnection[]> => {
        const { data } = await apiClient.get('/connections');
        return data.connections;
    },

    /**
     * Get connection by ID
     */
    getConnection: async (connectionId: string): Promise<PlatformConnection> => {
        const { data } = await apiClient.get(`/connections/${connectionId}`);
        return data;
    },

    /**
     * Delete connection
     */
    deleteConnection: async (connectionId: string): Promise<void> => {
        await apiClient.delete(`/connections/${connectionId}`);
    },

    /**
     * Get connection health status
     */
    getConnectionHealth: async (connectionId: string): Promise<{
        status: 'healthy' | 'degraded' | 'unhealthy';
        last_check: string;
        details: Record<string, any>;
    }> => {
        const { data } = await apiClient.get(`/connections/${connectionId}/health`);
        return data;
    },

    /**
     * Trigger manual sync for a connection
     */
    triggerSync: async (connectionId: string): Promise<{
        job_id: string;
        status: string;
        estimated_completion: string;
    }> => {
        const { data } = await apiClient.post(`/connections/${connectionId}/sync`);
        return data;
    },
};

// =============================================================================
// Slack Integration
// =============================================================================

export const slackAPI = {
    /**
     * Initiate Slack OAuth flow
     */
    initiateOAuth: async (): Promise<{
        authorization_url: string;
        state: string;
    }> => {
        const { data } = await apiClient.post('/platforms/slack/oauth/initiate');
        return data;
    },

    /**
     * Complete Slack OAuth flow
     */
    completeOAuth: async (code: string, state: string): Promise<SlackConnection> => {
        const { data } = await apiClient.post('/platforms/slack/oauth/complete', {
            code,
            state,
        });
        return data.connection;
    },

    /**
     * List Slack workspaces
     */
    listWorkspaces: async (connectionId: string): Promise<Array<{
        id: string;
        name: string;
        domain: string;
        icon?: string;
        member_count?: number;
    }>> => {
        const { data } = await apiClient.get(`/platforms/slack/${connectionId}/workspaces`);
        return data.workspaces;
    },

    /**
     * List Slack channels
     */
    listChannels: async (
        connectionId: string,
        options?: {
            types?: ('public_channel' | 'private_channel' | 'im' | 'mpim')[];
            exclude_archived?: boolean;
        }
    ): Promise<Array<{
        id: string;
        name: string;
        is_channel: boolean;
        is_group: boolean;
        is_im: boolean;
        is_mpim: boolean;
        is_private: boolean;
        is_archived: boolean;
        is_member: boolean;
        topic?: string;
        purpose?: string;
        num_members?: number;
    }>> => {
        const { data } = await apiClient.get(`/platforms/slack/${connectionId}/channels`, {
            params: options,
        });
        return data.channels;
    },

    /**
     * List Slack users
     */
    listUsers: async (connectionId: string): Promise<Array<{
        id: string;
        name: string;
        real_name?: string;
        display_name?: string;
        email?: string;
        avatar_url?: string;
        is_bot: boolean;
        is_deleted: boolean;
        team_id: string;
    }>> => {
        const { data } = await apiClient.get(`/platforms/slack/${connectionId}/users`);
        return data.users;
    },

    /**
     * Fetch Slack messages
     */
    fetchMessages: async (
        connectionId: string,
        channelId: string,
        options?: {
            oldest?: string;
            latest?: string;
            limit?: number;
            inclusive?: boolean;
        }
    ): Promise<Array<{
        ts: string;
        channel: string;
        user?: string;
        bot_id?: string;
        text: string;
        type: string;
        subtype?: string;
        thread_ts?: string;
        reply_count?: number;
        files?: any[];
        reactions?: any[];
        edited?: any;
    }>> => {
        const { data } = await apiClient.get(`/platforms/slack/${connectionId}/messages/${channelId}`, {
            params: options,
        });
        return data.messages;
    },

    /**
     * Fetch all Slack messages
     */
    fetchAllMessages: async (
        connectionId: string,
        options?: {
            since?: string;
            until?: string;
            limit_per_channel?: number;
        }
    ): Promise<{
        messages_collected: number;
        channels_processed: number;
        errors: number;
    }> => {
        const { data } = await apiClient.post(`/platforms/slack/${connectionId}/messages/fetch-all`, options || {});
        return data;
    },
};

// =============================================================================
// Discord Integration
// =============================================================================

export const discordAPI = {
    /**
     * Add Discord bot to server
     */
    getBotInviteUrl: async (): Promise<{
        invite_url: string;
        bot_id: string;
        permissions: string[];
    }> => {
        const { data } = await apiClient.get('/platforms/discord/bot/invite-url');
        return data;
    },

    /**
     * Register Discord connection after bot is added
     */
    registerConnection: async (botToken: string): Promise<DiscordConnection> => {
        const { data } = await apiClient.post('/platforms/discord/connections', {
            bot_token: botToken,
        });
        return data.connection;
    },

    /**
     * List Discord guilds (servers)
     */
    listGuilds: async (connectionId: string): Promise<Array<{
        id: string;
        name: string;
        icon?: string;
        description?: string;
        owner_id: string;
        permissions?: string;
        features: string[];
        approximate_member_count?: number;
        approximate_presence_count?: number;
    }>> => {
        const { data } = await apiClient.get(`/platforms/discord/${connectionId}/guilds`);
        return data.guilds;
    },

    /**
     * List Discord channels
     */
    listChannels: async (
        connectionId: string,
        guildId?: string
    ): Promise<Array<{
        id: string;
        type: number;
        guild_id?: string;
        position?: number;
        name?: string;
        topic?: string;
        nsfw: boolean;
        last_message_id?: string;
        parent_id?: string;
        rate_limit_per_user?: number;
        is_text_channel: boolean;
    }>> => {
        const { data } = await apiClient.get(`/platforms/discord/${connectionId}/channels`, {
            params: guildId ? { guild_id: guildId } : {},
        });
        return data.channels;
    },

    /**
     * Get Discord user
     */
    getUser: async (connectionId: string, userId: string): Promise<{
        id: string;
        username: string;
        discriminator: string;
        global_name?: string;
        avatar?: string;
        bot: boolean;
        system: boolean;
        verified?: boolean;
        email?: string;
        flags?: number;
        premium_type?: number;
        public_flags?: number;
        display_name: string;
        avatar_url?: string;
    }> => {
        const { data } = await apiClient.get(`/platforms/discord/${connectionId}/users/${userId}`);
        return data.user;
    },

    /**
     * Fetch Discord messages
     */
    fetchMessages: async (
        connectionId: string,
        channelId: string,
        options?: {
            before?: string;
            after?: string;
            around?: string;
            limit?: number;
        }
    ): Promise<Array<{
        id: string;
        channel_id: string;
        guild_id?: string;
        author: any;
        content: string;
        timestamp: string;
        edited_timestamp?: string;
        tts: boolean;
        mention_everyone: boolean;
        mentions: any[];
        mention_roles: string[];
        mention_channels: any[];
        attachments: any[];
        embeds: any[];
        reactions?: any[];
        pinned: boolean;
        webhook_id?: string;
        type: number;
        flags?: number;
        referenced_message?: any;
        thread?: any;
    }>> => {
        const { data } = await apiClient.get(`/platforms/discord/${connectionId}/messages/${channelId}`, {
            params: options,
        });
        return data.messages;
    },

    /**
     * Fetch all Discord messages
     */
    fetchAllMessages: async (
        connectionId: string,
        options?: {
            since?: string;
            until?: string;
            limit_per_channel?: number;
        }
    ): Promise<{
        messages_collected: number;
        channels_processed: number;
        errors: number;
    }> => {
        const { data } = await apiClient.post(`/platforms/discord/${connectionId}/messages/fetch-all`, options || {});
        return data;
    },
};

// =============================================================================
// Gmail Integration
// =============================================================================

export const gmailAPI = {
    /**
     * Initiate Gmail OAuth flow
     */
    initiateOAuth: async (): Promise<{
        authorization_url: string;
        state: string;
    }> => {
        const { data } = await apiClient.post('/platforms/gmail/oauth/initiate');
        return data;
    },

    /**
     * Complete Gmail OAuth flow
     */
    completeOAuth: async (code: string, state: string): Promise<GmailConnection> => {
        const { data } = await apiClient.post('/platforms/gmail/oauth/complete', {
            code,
            state,
        });
        return data.connection;
    },

    /**
     * Get Gmail profile
     */
    getProfile: async (connectionId: string): Promise<{
        email: string;
        name?: string;
        picture?: string;
        verified_email: boolean;
        hd?: string;
    }> => {
        const { data } = await apiClient.get(`/platforms/gmail/${connectionId}/profile`);
        return data.profile;
    },

    /**
     * List Gmail labels
     */
    listLabels: async (connectionId: string): Promise<Array<{
        id: string;
        name: string;
        type: 'system' | 'user';
        messages_total?: number;
        messages_unread?: number;
        threads_total?: number;
        threads_unread?: number;
    }>> => {
        const { data } = await apiClient.get(`/platforms/gmail/${connectionId}/labels`);
        return data.labels;
    },

    /**
     * Fetch Gmail messages
     */
    fetchMessages: async (
        connectionId: string,
        options?: {
            query?: string;
            label_ids?: string[];
            max_results?: number;
            page_token?: string;
            include_spam_trash?: boolean;
        }
    ): Promise<{
        messages: Array<{
            id: string;
            thread_id: string;
            label_ids: string[];
            snippet: string;
            payload: any;
            size_estimate: number;
            history_id: string;
            internal_date: string;
        }>;
        next_page_token?: string;
        result_size_estimate: number;
    }> => {
        const { data } = await apiClient.get(`/platforms/gmail/${connectionId}/messages`, {
            params: options,
        });
        return data;
    },

    /**
     * Setup Gmail push notifications
     */
    setupPushNotifications: async (connectionId: string): Promise<{
        topic_name: string;
        subscription_name: string;
        expiration: string;
        history_id: string;
    }> => {
        const { data } = await apiClient.post(`/platforms/gmail/${connectionId}/push/setup`);
        return data;
    },

    /**
     * Fetch all Gmail messages
     */
    fetchAllMessages: async (
        connectionId: string,
        options?: {
            since?: string;
            until?: string;
            labels?: string[];
            max_results?: number;
        }
    ): Promise<{
        messages_collected: number;
        threads_processed: number;
        errors: number;
    }> => {
        const { data } = await apiClient.post(`/platforms/gmail/${connectionId}/messages/fetch-all`, options || {});
        return data;
    },
};

export { platformAPI, slackAPI, discordAPI, gmailAPI };