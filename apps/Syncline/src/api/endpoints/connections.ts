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
     * Note: baseURL already includes /api/v1
     */
    initiateConnection: async (
        platform: Platform,
        userId: string,
        redirectUri?: string
    ): Promise<InitiateConnectionResponse> => {
        const { data } = await apiClient.post(`/connections/initiate/${platform}`, {
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
        const { data } = await apiClient.get(`/connections/callback/${platform}`, {
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
        const { data } = await apiClient.get('/connections', {
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
        await apiClient.delete(`/connections/${connectionId}`);
    },

    /**
     * Check connection health
     */
    checkHealth: async (connectionId: string) => {
        const { data } = await apiClient.get(`/connections/${connectionId}/health`);
        return data;
    },

    /**
     * Update connection status (used after WhatsApp bridge login)
     */
    updateStatus: async (connectionId: string, status: 'active' | 'inactive' | 'revoked'): Promise<ConnectionResponse> => {
        const { data } = await apiClient.patch(`/connections/${connectionId}/status`, null, {
            params: { new_status: status },
        });
        return data;
    },
};

