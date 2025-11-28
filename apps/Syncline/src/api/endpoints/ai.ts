import { apiClient } from '../client';
import { ThreadSummary, ContactInsight, Message } from '../../types';

export const aiAPI = {
    summarizeThread: async (
        threadId: string,
        type: 'brief' | 'detailed' | 'bullet_points' = 'brief'
    ): Promise<ThreadSummary> => {
        const { data } = await apiClient.post(`/ai/summarize/${threadId}`, {
            summary_type: type,
            force_regenerate: false
        });
        return data;
    },

    semanticSearch: async (query: string, filters?: any): Promise<{ results: Message[]; total: number }> => {
        const { data } = await apiClient.post('/ai/search', {
            query,
            ...filters,
            limit: 20
        });
        return data;
    },

    askAI: async (question: string): Promise<{ answer: string; sources: Message[]; confidence: number }> => {
        const { data } = await apiClient.post('/ai/ask', {
            question,
            limit: 10
        });
        return data;
    },

    getInsights: async (contactId: string, days: number = 30): Promise<{ insights: ContactInsight[] }> => {
        const { data } = await apiClient.post(
            `/ai/insights/${contactId}`,
            null,
            { params: { days } }
        );
        return data;
    },

    getEntities: async (messageId: string) => {
        const { data } = await apiClient.get(`/ai/entities/${messageId}`);
        return data;
    },
};
