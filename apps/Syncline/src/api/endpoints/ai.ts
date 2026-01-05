/**
 * AI and Memory API Endpoints
 * 
 * Handles AI-powered features:
 * - Memory search and management
 * - Proactive recommendations
 * - Entity extraction
 * - Semantic search
 * - AI insights and analytics
 */

import { apiClient } from '../client';
import {
    Memory,
    MemorySearchResult,
    MemoryRecommendation,
    MemoryExtractionResult,
    AIInsight,
    EntityExtraction,
    SemanticSearchResult,
    SearchFilters,
    SearchResults,
    MemoryStats,
    MemoryType,
    MemoryImportance,
} from '../../types';

// =============================================================================
// Memory Management
// =============================================================================

export const memoryAPI = {
    /**
     * Search memories using semantic and metadata filters
     */
    searchMemories: async (
        query: string,
        options?: {
            contact_id?: string;
            memory_types?: MemoryType[];
            importance_min?: MemoryImportance;
            platform?: string;
            limit?: number;
        }
    ): Promise<MemorySearchResult[]> => {
        const { data } = await apiClient.get('/ai/memories/search', {
            params: { query, ...options },
        });
        return data.results;
    },

    /**
     * Get proactive memory recommendations
     */
    getRecommendations: async (
        context?: {
            current_contact?: string;
            current_thread?: string;
            current_platform?: string;
            keywords?: string[];
        }
    ): Promise<MemoryRecommendation[]> => {
        const { data } = await apiClient.post('/ai/memories/recommendations', context || {});
        return data.recommendations;
    },

    /**
     * Get memory by ID
     */
    getMemory: async (memoryId: string): Promise<Memory> => {
        const { data } = await apiClient.get(`/ai/memories/${memoryId}`);
        return data;
    },

    /**
     * Create a new memory
     */
    createMemory: async (memory: {
        type: MemoryType;
        content: string;
        importance: MemoryImportance;
        contact_id?: string;
        thread_id?: string;
        platform?: string;
        metadata?: Record<string, any>;
    }): Promise<Memory> => {
        const { data } = await apiClient.post('/ai/memories', memory);
        return data;
    },

    /**
     * Update memory
     */
    updateMemory: async (
        memoryId: string,
        updates: {
            content?: string;
            importance?: MemoryImportance;
            metadata?: Record<string, any>;
        }
    ): Promise<Memory> => {
        const { data } = await apiClient.patch(`/ai/memories/${memoryId}`, updates);
        return data;
    },

    /**
     * Delete memory
     */
    deleteMemory: async (memoryId: string): Promise<void> => {
        await apiClient.delete(`/ai/memories/${memoryId}`);
    },

    /**
     * Extract memories from a message
     */
    extractFromMessage: async (messageId: string): Promise<MemoryExtractionResult> => {
        const { data } = await apiClient.post(`/ai/memories/extract/${messageId}`);
        return data;
    },

    /**
     * Get memory statistics
     */
    getStats: async (): Promise<MemoryStats> => {
        const { data } = await apiClient.get('/ai/memories/stats');
        return data;
    },

    /**
     * Get memories for a specific contact
     */
    getContactMemories: async (
        contactId: string,
        options?: {
            memory_types?: MemoryType[];
            limit?: number;
        }
    ): Promise<Memory[]> => {
        const { data } = await apiClient.get(`/ai/memories/contact/${contactId}`, {
            params: options,
        });
        return data.memories;
    },

    /**
     * Get memories for a specific thread
     */
    getThreadMemories: async (
        threadId: string,
        options?: {
            memory_types?: MemoryType[];
            limit?: number;
        }
    ): Promise<Memory[]> => {
        const { data } = await apiClient.get(`/ai/memories/thread/${threadId}`, {
            params: options,
        });
        return data.memories;
    },
};

// =============================================================================
// AI Search and Analysis
// =============================================================================

export const aiAPI = {
    /**
     * Perform semantic search across messages
     */
    semanticSearch: async (
        query: string,
        filters?: SearchFilters,
        limit: number = 20
    ): Promise<SemanticSearchResult[]> => {
        const { data } = await apiClient.post('/ai/search/semantic', {
            query,
            filters,
            limit,
        });
        return data.results;
    },

    /**
     * Unified search across messages and memories
     */
    unifiedSearch: async (
        query: string,
        filters?: SearchFilters,
        limit: number = 20
    ): Promise<SearchResults> => {
        const { data } = await apiClient.post('/ai/search/unified', {
            query,
            filters,
            limit,
        });
        return data;
    },

    /**
     * Extract entities from text
     */
    extractEntities: async (text: string): Promise<EntityExtraction[]> => {
        const { data } = await apiClient.post('/ai/entities/extract', { text });
        return data.entities;
    },

    /**
     * Generate summary for a thread
     */
    generateSummary: async (
        threadId: string,
        summaryType: 'brief' | 'detailed' | 'insight' = 'brief'
    ): Promise<{
        content: string;
        type: string;
        confidence: number;
        key_topics: string[];
    }> => {
        const { data } = await apiClient.post(`/ai/summarize/thread/${threadId}`, {
            summary_type: summaryType,
        });
        return data;
    },

    /**
     * Generate insights for a contact
     */
    generateContactInsights: async (contactId: string): Promise<AIInsight[]> => {
        const { data } = await apiClient.post(`/ai/insights/contact/${contactId}`);
        return data.insights;
    },

    /**
     * Analyze conversation patterns
     */
    analyzePatterns: async (
        options?: {
            contact_id?: string;
            platform?: string;
            date_range?: {
                start: string;
                end: string;
            };
        }
    ): Promise<{
        communication_frequency: Record<string, number>;
        topic_trends: Array<{
            topic: string;
            frequency: number;
            trend: 'increasing' | 'decreasing' | 'stable';
        }>;
        sentiment_analysis: {
            overall_sentiment: 'positive' | 'neutral' | 'negative';
            sentiment_over_time: Array<{
                date: string;
                sentiment: number;
            }>;
        };
        response_patterns: {
            avg_response_time: number;
            response_rate: number;
        };
    }> => {
        const { data } = await apiClient.post('/ai/analyze/patterns', options || {});
        return data;
    },

    /**
     * Get AI processing status
     */
    getProcessingStatus: async (): Promise<{
        status: 'active' | 'inactive' | 'error';
        models_available: string[];
        current_model: string;
        processing_queue: number;
        last_processing: string;
    }> => {
        const { data } = await apiClient.get('/ai/status');
        return data;
    },

    /**
     * Trigger AI processing for recent messages
     */
    triggerProcessing: async (
        options?: {
            platform?: string;
            contact_id?: string;
            since?: string;
            force_reprocess?: boolean;
        }
    ): Promise<{
        job_id: string;
        messages_queued: number;
        estimated_completion: string;
    }> => {
        const { data } = await apiClient.post('/ai/process/trigger', options || {});
        return data;
    },
};

// =============================================================================
// Platform-Specific AI Features
// =============================================================================

export const platformAI = {
    /**
     * Get Slack-specific insights
     */
    getSlackInsights: async (connectionId: string): Promise<{
        channel_activity: Record<string, number>;
        user_engagement: Record<string, number>;
        topic_distribution: Record<string, number>;
        peak_hours: number[];
    }> => {
        const { data } = await apiClient.get(`/ai/platforms/slack/${connectionId}/insights`);
        return data;
    },

    /**
     * Get Discord-specific insights
     */
    getDiscordInsights: async (connectionId: string): Promise<{
        guild_activity: Record<string, number>;
        channel_engagement: Record<string, number>;
        user_activity: Record<string, number>;
        message_types: Record<string, number>;
    }> => {
        const { data } = await apiClient.get(`/ai/platforms/discord/${connectionId}/insights`);
        return data;
    },

    /**
     * Get Gmail-specific insights
     */
    getGmailInsights: async (connectionId: string): Promise<{
        sender_frequency: Record<string, number>;
        label_distribution: Record<string, number>;
        email_volume_trends: Array<{
            date: string;
            count: number;
        }>;
        response_patterns: {
            avg_response_time: number;
            response_rate: number;
        };
    }> => {
        const { data } = await apiClient.get(`/ai/platforms/gmail/${connectionId}/insights`);
        return data;
    },

    /**
     * Get WhatsApp-specific insights
     */
    getWhatsAppInsights: async (connectionId: string): Promise<{
        contact_frequency: Record<string, number>;
        message_types: Record<string, number>;
        activity_patterns: Array<{
            hour: number;
            message_count: number;
        }>;
        group_vs_individual: {
            group_messages: number;
            individual_messages: number;
        };
    }> => {
        const { data } = await apiClient.get(`/ai/platforms/whatsapp/${connectionId}/insights`);
        return data;
    },
};