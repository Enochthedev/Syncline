/**
 * Insights Service
 * 
 * Service for fetching relationship insights, timeline data, and network analysis
 */

import { apiClient } from './apiClient';
import {
    RelationshipInsight,
    TimelineData,
    SentimentData,
    NetworkData,
    ComprehensiveAnalysis
} from '../types';

class InsightsService {
    /**
     * Get comprehensive relationship analysis for a contact
     */
    async getComprehensiveAnalysis(contactId: string): Promise<ComprehensiveAnalysis> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/comprehensive-analysis`);
            return response.data;
        } catch (error) {
            console.error('Error fetching comprehensive analysis:', error);
            throw error;
        }
    }

    /**
     * Get relationship insights for a contact
     */
    async getRelationshipInsights(contactId: string): Promise<RelationshipInsight[]> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/insights`);
            return response.data.insights || [];
        } catch (error) {
            console.error('Error fetching relationship insights:', error);
            throw error;
        }
    }

    /**
     * Get communication timeline data
     */
    async getCommunicationTimeline(
        contactId: string,
        daysBack: number = 365
    ): Promise<TimelineData> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/timeline`, {
                params: { days_back: daysBack }
            });
            return response.data;
        } catch (error) {
            console.error('Error fetching communication timeline:', error);
            throw error;
        }
    }

    /**
     * Get sentiment analysis data
     */
    async getSentimentAnalysis(
        contactId: string,
        daysBack: number = 90
    ): Promise<SentimentData> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/sentiment`, {
                params: { days_back: daysBack }
            });
            return response.data;
        } catch (error) {
            console.error('Error fetching sentiment analysis:', error);
            throw error;
        }
    }

    /**
     * Get network analysis data
     */
    async getNetworkAnalysis(contactId: string): Promise<NetworkData> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/network`);
            return response.data;
        } catch (error) {
            console.error('Error fetching network analysis:', error);
            throw error;
        }
    }

    /**
     * Get interaction heatmap data
     */
    async getInteractionHeatmap(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/heatmap`);
            return response.data;
        } catch (error) {
            console.error('Error fetching interaction heatmap:', error);
            throw error;
        }
    }

    /**
     * Refresh all insights for a contact
     */
    async refreshInsights(contactId: string): Promise<{ success: boolean; insights_generated: number }> {
        try {
            const response = await apiClient.post(`/contacts/${contactId}/insights/refresh`);
            return response.data;
        } catch (error) {
            console.error('Error refreshing insights:', error);
            throw error;
        }
    }

    /**
     * Submit feedback for an insight
     */
    async submitInsightFeedback(
        insightId: string,
        feedback: 'helpful' | 'not_helpful' | 'incorrect'
    ): Promise<void> {
        try {
            await apiClient.post(`/insights/${insightId}/feedback`, {
                feedback
            });
        } catch (error) {
            console.error('Error submitting insight feedback:', error);
            throw error;
        }
    }

    /**
     * Get insight accuracy metrics
     */
    async getInsightAccuracyMetrics(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/insights/accuracy`);
            return response.data;
        } catch (error) {
            console.error('Error fetching insight accuracy metrics:', error);
            throw error;
        }
    }

    /**
     * Get visualization data for charts
     */
    async getVisualizationData(
        contactId: string,
        type: 'timeline' | 'sentiment' | 'heatmap' | 'network'
    ): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/visualization/${type}`);
            return response.data;
        } catch (error) {
            console.error(`Error fetching ${type} visualization data:`, error);
            throw error;
        }
    }

    /**
     * Get relationship strength calculation details
     */
    async getRelationshipStrengthDetails(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/relationship-strength`);
            return response.data;
        } catch (error) {
            console.error('Error fetching relationship strength details:', error);
            throw error;
        }
    }

    /**
     * Get communication patterns analysis
     */
    async getCommunicationPatterns(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/patterns`);
            return response.data;
        } catch (error) {
            console.error('Error fetching communication patterns:', error);
            throw error;
        }
    }

    /**
     * Get mutual connections analysis
     */
    async getMutualConnections(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/mutual-connections`);
            return response.data;
        } catch (error) {
            console.error('Error fetching mutual connections:', error);
            throw error;
        }
    }

    /**
     * Generate AI insights on demand
     */
    async generateInsights(
        contactId: string,
        insightTypes?: string[]
    ): Promise<RelationshipInsight[]> {
        try {
            const response = await apiClient.post(`/contacts/${contactId}/insights/generate`, {
                insight_types: insightTypes
            });
            return response.data.insights || [];
        } catch (error) {
            console.error('Error generating insights:', error);
            throw error;
        }
    }

    /**
     * Get trending insights across all contacts
     */
    async getTrendingInsights(): Promise<RelationshipInsight[]> {
        try {
            const response = await apiClient.get('/insights/trending');
            return response.data.insights || [];
        } catch (error) {
            console.error('Error fetching trending insights:', error);
            throw error;
        }
    }

    /**
     * Get insights summary for dashboard
     */
    async getInsightsSummary(): Promise<any> {
        try {
            const response = await apiClient.get('/insights/summary');
            return response.data;
        } catch (error) {
            console.error('Error fetching insights summary:', error);
            throw error;
        }
    }

    /**
     * Export insights data
     */
    async exportInsights(
        contactId: string,
        format: 'json' | 'csv' | 'pdf' = 'json'
    ): Promise<Blob> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/insights/export`, {
                params: { format },
                responseType: 'blob'
            });
            return response.data;
        } catch (error) {
            console.error('Error exporting insights:', error);
            throw error;
        }
    }

    /**
     * Get real-time insight updates
     */
    async subscribeToInsightUpdates(
        contactId: string,
        callback: (insight: RelationshipInsight) => void
    ): Promise<() => void> {
        // This would implement WebSocket or Server-Sent Events for real-time updates
        // For now, return a no-op unsubscribe function
        return () => { };
    }

    /**
     * Cache management
     */
    async clearInsightsCache(contactId?: string): Promise<void> {
        try {
            const endpoint = contactId
                ? `/contacts/${contactId}/insights/cache`
                : '/insights/cache';
            await apiClient.delete(endpoint);
        } catch (error) {
            console.error('Error clearing insights cache:', error);
            throw error;
        }
    }

    /**
     * Get cached insights status
     */
    async getCacheStatus(contactId: string): Promise<any> {
        try {
            const response = await apiClient.get(`/contacts/${contactId}/insights/cache-status`);
            return response.data;
        } catch (error) {
            console.error('Error fetching cache status:', error);
            throw error;
        }
    }
}

export const insightsService = new InsightsService();