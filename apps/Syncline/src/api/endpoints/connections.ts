import { apiClient } from '../client';
import { Platform } from '../../types';

export interface InitiateConnectionRequest {
    user_id: string;
    redirect_uri?: string;
}

export interface InitiateConnectionResponse {
    connection_id: string;
    authorization_url: string;
    state: string;
}

export interface ConnectionResponse {
    id: string;
    user_id: string;
    platform: string;
    status: string;
    last_sync_at: string | null;
    platform_metadata: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface ConnectionListResponse {
    connections: ConnectionResponse[];
    total: number;
}

export const connectionsAPI = {
    /**
     * Initiate OAuth flow for a platform
     */
    initiateConnection: async (
        platform: Platform,
        userId: string,
        redirectUri?: string
    ): Promise<InitiateConnectionResponse> => {
        const { data } = await apiClient.post(`/api/connections/initiate/${platform}`, {
            user_id: userId,
            redirect_uri: redirectUri,
        });
        return data;
    },

    /**
     * Handle OAuth callback (usually called by backend redirect)
     */
    handleCallback: async (
        platform: Platform,
        code: string,
        state: string
    ): Promise<ConnectionResponse> => {
        const { data } = await apiClient.get(`/api/connections/callback/${platform}`, {
            params: { code, state },
        });
        return data;
    },

    /**
     * List all connections for a user
     */
    listConnections: async (
        userId: string,
        platform?: Platform,
        status?: string
    ): Promise<ConnectionListResponse> => {
        const { data } = await apiClient.get('/api/connections', {
            params: {
                user_id: userId,
                platform,
                status,
            },
        });
        return data;
    },

    /**
     * Disconnect a platform
     */
    disconnect: async (connectionId: string): Promise<void> => {
        await apiClient.delete(`/api/connections/${connectionId}`);
    },

    /**
     * Check connection health
     */
    checkHealth: async (connectionId: string) => {
        const { data } = await apiClient.get(`/api/connections/${connectionId}/health`);
        return data;
    },
};
