import { apiClient } from '../client';
import { Connection, Platform } from '../../types';

export const connectionsAPI = {
    initiateConnection: async (platform: Platform, userId: string) => {
        const { data } = await apiClient.post(
            `/connections/${platform}/initiate`,
            { user_id: userId }
        );
        return data;
    },

    listConnections: async (userId: string): Promise<Connection[]> => {
        const { data } = await apiClient.get('/connections', {
            params: { user_id: userId }
        });
        return data.connections;
    },

    disconnectPlatform: async (connectionId: string) => {
        await apiClient.delete(`/connections/${connectionId}/disconnect`);
    },

    checkHealth: async (connectionId: string) => {
        const { data } = await apiClient.get(`/connections/${connectionId}/health`);
        return data;
    },
};
