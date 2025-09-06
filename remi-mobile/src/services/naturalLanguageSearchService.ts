/**
 * Natural Language Search Service
 * 
 * Service for processing natural language queries and managing search history
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiClient } from './apiClient';
import { SearchResult } from '@/types';

export interface NaturalLanguageQueryResult {
    intent: string;
    processed_text: string;
    contacts: any[];
    filters: Record<string, any>;
    temporal_constraints: Record<string, any>;
    entities: any[];
}

export interface SearchHistoryItem {
    query: string;
    timestamp: Date;
    intent?: string;
    resultCount?: number;
}

export interface QuerySuggestion {
    text: string;
    type: 'template' | 'history' | 'contact' | 'entity';
    metadata?: Record<string, any>;
}

class NaturalLanguageSearchService {
    private readonly SEARCH_HISTORY_KEY = 'nl_search_history';
    private readonly MAX_HISTORY_ITEMS = 50;

    /**
     * Process natural language query to extract intent and entities
     */
    async processNaturalLanguageQuery(query: string): Promise<NaturalLanguageQueryResult> {
        try {
            const response = await apiClient.post('/contacts/search/natural-language', {
                query,
            });
            return response.data;
        } catch (error) {
            console.error('Natural language query processing failed:', error);
            throw error;
        }
    }

    /**
     * Get search suggestions based on partial query
     */
    async getSearchSuggestions(partialQuery: string, limit: number = 5): Promise<QuerySuggestion[]> {
        try {
            const suggestions: QuerySuggestion[] = [];

            // Get template suggestions
            const templateSuggestions = this.getTemplateSuggestions(partialQuery);
            suggestions.push(...templateSuggestions.slice(0, Math.ceil(limit / 2)));

            // Get history-based suggestions
            const historySuggestions = await this.getHistorySuggestions(partialQuery);
            suggestions.push(...historySuggestions.slice(0, Math.floor(limit / 2)));

            // Get contact-based suggestions if query mentions names
            if (this.containsPersonReference(partialQuery)) {
                const contactSuggestions = await this.getContactSuggestions(partialQuery);
                suggestions.push(...contactSuggestions.slice(0, 2));
            }

            return suggestions.slice(0, limit);
        } catch (error) {
            console.error('Failed to get search suggestions:', error);
            return [];
        }
    }

    /**
     * Get template-based suggestions for common query patterns
     */
    private getTemplateSuggestions(partialQuery: string): QuerySuggestion[] {
        const templates = [
            'messages with [contact name]',
            'files from [contact name]',
            'commitments to [contact name]',
            'calls with [contact name]',
            'emails from [contact name]',
            'shared links with [contact name]',
            'photos from [contact name]',
            'documents shared by [contact name]',
            'meetings with [contact name]',
            'tasks assigned to [contact name]',
            'messages about [topic]',
            'files about [topic]',
            'conversations last week',
            'important messages',
            'unread messages',
        ];

        const query = partialQuery.toLowerCase();
        return templates
            .filter(template => template.toLowerCase().includes(query) || query.includes(template.split(' ')[0]))
            .map(template => ({
                text: template,
                type: 'template' as const,
                metadata: { category: 'template' },
            }));
    }

    /**
     * Get suggestions based on search history
     */
    private async getHistorySuggestions(partialQuery: string): Promise<QuerySuggestion[]> {
        try {
            const history = await this.getSearchHistory();
            const query = partialQuery.toLowerCase();

            return history
                .filter(item => item.query.toLowerCase().includes(query))
                .slice(0, 5)
                .map(item => ({
                    text: item.query,
                    type: 'history' as const,
                    metadata: {
                        timestamp: item.timestamp,
                        intent: item.intent,
                        resultCount: item.resultCount,
                    },
                }));
        } catch (error) {
            console.error('Failed to get history suggestions:', error);
            return [];
        }
    }

    /**
     * Get contact-based suggestions
     */
    private async getContactSuggestions(partialQuery: string): Promise<QuerySuggestion[]> {
        try {
            // This would integrate with the contact search service
            // For now, return empty array
            return [];
        } catch (error) {
            console.error('Failed to get contact suggestions:', error);
            return [];
        }
    }

    /**
     * Check if query contains person reference
     */
    private containsPersonReference(query: string): boolean {
        const personKeywords = ['with', 'from', 'to', 'by'];
        const queryLower = query.toLowerCase();
        return personKeywords.some(keyword => queryLower.includes(keyword));
    }

    /**
     * Save search query to history
     */
    async saveToHistory(query: string, intent?: string, resultCount?: number): Promise<void> {
        try {
            const history = await this.getSearchHistory();

            // Remove duplicate if exists
            const filteredHistory = history.filter(item => item.query !== query);

            // Add new item at the beginning
            const newItem: SearchHistoryItem = {
                query,
                timestamp: new Date(),
                intent,
                resultCount,
            };

            const updatedHistory = [newItem, ...filteredHistory].slice(0, this.MAX_HISTORY_ITEMS);

            await AsyncStorage.setItem(this.SEARCH_HISTORY_KEY, JSON.stringify(updatedHistory));
        } catch (error) {
            console.error('Failed to save search history:', error);
        }
    }

    /**
     * Get search history
     */
    async getSearchHistory(): Promise<SearchHistoryItem[]> {
        try {
            const historyJson = await AsyncStorage.getItem(this.SEARCH_HISTORY_KEY);
            if (!historyJson) return [];

            const history = JSON.parse(historyJson);
            return history.map((item: any) => ({
                ...item,
                timestamp: new Date(item.timestamp),
            }));
        } catch (error) {
            console.error('Failed to get search history:', error);
            return [];
        }
    }

    /**
     * Clear search history
     */
    async clearHistory(): Promise<void> {
        try {
            await AsyncStorage.removeItem(this.SEARCH_HISTORY_KEY);
        } catch (error) {
            console.error('Failed to clear search history:', error);
        }
    }

    /**
     * Remove specific item from history
     */
    async removeFromHistory(query: string): Promise<void> {
        try {
            const history = await this.getSearchHistory();
            const filteredHistory = history.filter(item => item.query !== query);
            await AsyncStorage.setItem(this.SEARCH_HISTORY_KEY, JSON.stringify(filteredHistory));
        } catch (error) {
            console.error('Failed to remove from search history:', error);
        }
    }

    /**
     * Get popular search patterns
     */
    async getPopularPatterns(): Promise<{ pattern: string; count: number }[]> {
        try {
            const history = await this.getSearchHistory();
            const patterns: Record<string, number> = {};

            history.forEach(item => {
                if (item.intent) {
                    patterns[item.intent] = (patterns[item.intent] || 0) + 1;
                }
            });

            return Object.entries(patterns)
                .map(([pattern, count]) => ({ pattern, count }))
                .sort((a, b) => b.count - a.count)
                .slice(0, 10);
        } catch (error) {
            console.error('Failed to get popular patterns:', error);
            return [];
        }
    }

    /**
     * Search for commitments based on natural language query
     */
    async searchCommitments(
        person?: string,
        topic?: string,
        timeframe?: string,
        limit: number = 20
    ): Promise<SearchResult[]> {
        try {
            const response = await apiClient.post('/search/commitments', {
                person,
                topic,
                timeframe,
                limit,
            });

            return this.convertToSearchResults(response.data.results, 'commitment');
        } catch (error) {
            console.error('Commitment search failed:', error);
            return [];
        }
    }

    /**
     * Search for files based on natural language query
     */
    async searchFiles(
        contact?: string,
        fileType?: string,
        limit: number = 20
    ): Promise<SearchResult[]> {
        try {
            const response = await apiClient.post('/search/files', {
                contact,
                file_type: fileType,
                limit,
            });

            return this.convertToSearchResults(response.data.results, 'file');
        } catch (error) {
            console.error('File search failed:', error);
            return [];
        }
    }

    /**
     * Perform general search with natural language processing
     */
    async performGeneralSearch(
        query: string,
        filters?: Record<string, any>,
        limit: number = 50
    ): Promise<SearchResult[]> {
        try {
            const response = await apiClient.post('/search/', {
                query,
                ...filters,
                limit,
                include_suggestions: true,
                include_facets: false,
            });

            return this.convertToSearchResults(response.data.results);
        } catch (error) {
            console.error('General search failed:', error);
            return [];
        }
    }

    /**
     * Convert API search results to SearchResult format
     */
    private convertToSearchResults(apiResults: any[], defaultType?: string): SearchResult[] {
        return apiResults.map((result: any) => ({
            id: result.id,
            type: result.type || defaultType || 'message',
            title: result.title,
            snippet: result.snippet,
            content: result.content,
            relevanceScore: result.ranking?.combined_score || 1.0,
            timestamp: new Date(result.timestamp),
            contact: result.contact,
            platform: result.platform,
            thread: result.thread,
            highlights: result.highlights || [],
            quickActions: result.quickActions || [],
        }));
    }

    /**
     * Get example queries for user guidance
     */
    getExampleQueries(): string[] {
        return [
            'messages with John Smith',
            'files from Sarah last week',
            'commitments to the team',
            'photos shared by mom',
            'documents about project alpha',
            'calls with clients this month',
            'emails from support',
            'shared links about AI',
            'meetings scheduled today',
            'tasks assigned to me',
        ];
    }

    /**
     * Validate natural language query
     */
    validateQuery(query: string): { isValid: boolean; error?: string } {
        if (!query || query.trim().length === 0) {
            return { isValid: false, error: 'Query cannot be empty' };
        }

        if (query.length > 500) {
            return { isValid: false, error: 'Query is too long (max 500 characters)' };
        }

        if (query.length < 2) {
            return { isValid: false, error: 'Query is too short (min 2 characters)' };
        }

        return { isValid: true };
    }
}

export const naturalLanguageSearchService = new NaturalLanguageSearchService();