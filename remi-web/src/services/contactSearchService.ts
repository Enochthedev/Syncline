/**
 * Contact Search Service (Web Version)
 * 
 * Service for integrating with the contact auto-search API endpoints
 */

import { apiClient } from './apiClient';

export interface ContactSearchResult {
    contacts: any[];
    suggestions: any[];
    query: string;
    normalized_query: string;
    total_results: number;
    has_more: boolean;
}

export interface NaturalLanguageQueryResult {
    intent: string;
    processed_text: string;
    contacts: any[];
    filters: Record<string, any>;
    temporal_constraints: Record<string, any>;
    entities: any[];
}

class ContactSearchService {
    /**
     * Perform real-time contact search with fuzzy matching
     */
    async searchContactsRealtime(
        query: string,
        limit: number = 10,
        includeSuggestions: boolean = true
    ): Promise<ContactSearchResult> {
        try {
            const response = await apiClient.get('/api/v1/contacts/search/realtime', {
                params: {
                    q: query,
                    limit,
                    suggestions: includeSuggestions,
                },
            });
            return response.data;
        } catch (error) {
            console.error('Real-time contact search failed:', error);
            throw error;
        }
    }

    /**
     * Process natural language queries like "messages with John"
     */
    async processNaturalLanguageQuery(query: string): Promise<NaturalLanguageQueryResult> {
        try {
            const response = await apiClient.post('/api/v1/contacts/search/natural-language', {
                query,
            });
            return response.data;
        } catch (error) {
            console.error('Natural language query processing failed:', error);
            throw error;
        }
    }

    /**
     * Get contact search suggestions
     */
    async getSearchSuggestions(query: string, limit: number = 5): Promise<any[]> {
        try {
            const response = await apiClient.get(`/api/v1/contacts/search/suggestions/${encodeURIComponent(query)}`, {
                params: { limit },
            });
            return response.data.suggestions || [];
        } catch (error) {
            console.error('Search suggestions failed:', error);
            return [];
        }
    }
}

export const contactSearchService = new ContactSearchService();