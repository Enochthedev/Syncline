import { apiClient } from '../client';
import { Message } from '../../types';

export const messagesAPI = {
    listMessages: async (filters?: {
        platform?: string;
        start_date?: string;
        end_date?: string;
        limit?: number;
        skip?: number;
    }): Promise<{ messages: Message[]; total: number }> => {
        const { data } = await apiClient.get('/messages', { params: filters });
        return data;
    },

    searchMessages: async (query: string): Promise<{ results: Message[]; total: number }> => {
        const { data } = await apiClient.get('/messages/search', {
            params: { query }
        });
        return data;
    },

    getMessage: async (messageId: string): Promise<Message> => {
        const { data } = await apiClient.get(`/messages/${messageId}`);
        return data;
    },
};
