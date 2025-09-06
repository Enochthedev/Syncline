/**
 * Contact Search Service
 * 
 * Service for integrating with the contact auto-search API endpoints
 * Provides comprehensive contact search functionality with error handling and retry logic
 */

import { apiClient } from './apiClient';
import { mockDataService } from './mockDataService';
import { API_ENDPOINTS, SEARCH_CONFIG, ERROR_CODES } from '../constants/api';
import { UnifiedContact, SearchFilters, ApiResponse, PaginatedResponse } from '../types';

// Enhanced type definitions with proper error handling
export interface ContactSearchResult {
    contacts: UnifiedContact[];
    suggestions: ContactSuggestion[];
    query: string;
    normalized_query: string;
    total_results: number;
    has_more: boolean;
    processing_time_ms?: number;
}

export interface ContactSuggestion {
    text: string;
    type: 'person' | 'query' | 'filter';
    contact_id?: string;
    confidence?: number;
    metadata?: Record<string, any>;
}

export interface NaturalLanguageQueryResult {
    intent: string;
    processed_text: string;
    contacts: UnifiedContact[];
    filters: SearchFilters;
    temporal_constraints: Record<string, any>;
    entities: ExtractedEntity[];
    confidence: number;
}

export interface ContactMessageSearchResult {
    messages?: Message[];
    threads?: ConversationThread[];
    contact?: UnifiedContact;
    total_messages?: number;
    total_threads?: number;
    query?: string;
    has_more?: boolean;
}

export interface SharedContentResult {
    contact?: UnifiedContact;
    shared_files: SharedFile[];
    shared_links: SharedLink[];
    shared_media: MediaFile[];
    total_items: number;
    has_more: boolean;
}

export interface MediaFile {
    id: string;
    name: string;
    type: 'image' | 'video' | 'audio';
    url: string;
    thumbnail_url?: string;
    size: number;
    shared_at: Date;
    platform: string;
}

export interface ExtractedEntity {
    type: string;
    text: string;
    confidence: number;
    start_offset: number;
    end_offset: number;
}

export interface Message {
    id: string;
    content: string;
    sender: UnifiedContact;
    timestamp: Date;
    platform: string;
}

export interface ConversationThread {
    id: string;
    title?: string;
    participants: UnifiedContact[];
    last_message_at: Date;
    message_count: number;
    platform: string;
}

export interface SharedFile {
    id: string;
    name: string;
    type: string;
    size: number;
    url: string;
    shared_at: Date;
    platform: string;
}

export interface SharedLink {
    id: string;
    url: string;
    title: string;
    description?: string;
    shared_at: Date;
    platform: string;
}

// Error handling types
export interface ContactSearchError {
    code: string;
    message: string;
    details?: Record<string, any>;
    retryable: boolean;
}

// Request options with retry configuration
export interface SearchRequestOptions {
    timeout?: number;
    retries?: number;
    retryDelay?: number;
    signal?: AbortSignal;
}

class ContactSearchService {
    private readonly maxRetries = 3;
    private readonly baseRetryDelay = 1000; // 1 second
    private readonly isDemoMode = process.env.NODE_ENV === 'development' || __DEV__;

    /**
     * Perform real-time contact search with fuzzy matching and retry logic
     */
    async searchContactsRealtime(
        query: string,
        limit: number = SEARCH_CONFIG.DEFAULT_LIMIT,
        includeSuggestions: boolean = true,
        options: SearchRequestOptions = {}
    ): Promise<ContactSearchResult> {
        // Validate input
        if (!query || query.trim().length < SEARCH_CONFIG.MIN_QUERY_LENGTH) {
            throw this.createError(
                ERROR_CODES.VALIDATION_ERROR,
                `Query must be at least ${SEARCH_CONFIG.MIN_QUERY_LENGTH} characters`,
                false
            );
        }

        if (limit > SEARCH_CONFIG.MAX_LIMIT) {
            limit = SEARCH_CONFIG.MAX_LIMIT;
        }

        // Use mock data in demo mode
        if (this.isDemoMode) {
            return this.searchContactsWithMockData(query, limit, includeSuggestions);
        }

        return this.executeWithRetry(async () => {
            const response = await apiClient.get<ApiResponse<ContactSearchResult>>(
                API_ENDPOINTS.CONTACT_SEARCH.REALTIME,
                {
                    params: {
                        q: query.trim(),
                        limit,
                        suggestions: includeSuggestions,
                    },
                    timeout: options.timeout || 10000,
                    signal: options.signal,
                }
            );

            return this.validateAndTransformResponse(response.data);
        }, options);
    }

    /**
     * Process natural language queries like "messages with John" with enhanced error handling
     */
    async processNaturalLanguageQuery(
        query: string,
        options: SearchRequestOptions = {}
    ): Promise<NaturalLanguageQueryResult> {
        if (!query || query.trim().length === 0) {
            throw this.createError(
                ERROR_CODES.VALIDATION_ERROR,
                'Query cannot be empty',
                false
            );
        }

        // Use mock data in demo mode
        if (this.isDemoMode) {
            return this.processNaturalLanguageWithMockData(query);
        }

        return this.executeWithRetry(async () => {
            const response = await apiClient.post<ApiResponse<NaturalLanguageQueryResult>>(
                API_ENDPOINTS.CONTACT_SEARCH.NATURAL_LANGUAGE,
                { query: query.trim() },
                {
                    timeout: options.timeout || 15000,
                    signal: options.signal,
                }
            );

            return response.data.data;
        }, options);
    }

    /**
     * Search messages filtered by specific contact with pagination and error handling
     */
    async searchMessagesByContact(
        contactId: string,
        query?: string,
        limit: number = 50,
        offset: number = 0,
        groupByThread: boolean = true,
        options: SearchRequestOptions = {}
    ): Promise<ContactMessageSearchResult> {
        if (!contactId || contactId.trim().length === 0) {
            throw this.createError(
                ERROR_CODES.VALIDATION_ERROR,
                'Contact ID is required',
                false
            );
        }

        // Use mock data in demo mode
        if (this.isDemoMode) {
            return this.searchMessagesByContactWithMockData(contactId, query, limit, offset, groupByThread);
        }

        return this.executeWithRetry(async () => {
            const endpoint = API_ENDPOINTS.CONTACT_SEARCH.MESSAGES.replace('{contactId}', contactId);
            const response = await apiClient.get<ApiResponse<ContactMessageSearchResult>>(
                endpoint,
                {
                    params: {
                        q: query?.trim(),
                        limit: Math.min(limit, SEARCH_CONFIG.MAX_LIMIT),
                        offset,
                        group_by_thread: groupByThread,
                    },
                    timeout: options.timeout || 12000,
                    signal: options.signal,
                }
            );

            return response.data.data;
        }, options);
    }

    /**
     * Get shared content with a specific contact with enhanced filtering
     */
    async getSharedContentWithContact(
        contactId: string,
        contentType?: 'files' | 'links' | 'media',
        limit: number = 50,
        offset: number = 0,
        options: SearchRequestOptions = {}
    ): Promise<SharedContentResult> {
        if (!contactId || contactId.trim().length === 0) {
            throw this.createError(
                ERROR_CODES.VALIDATION_ERROR,
                'Contact ID is required',
                false
            );
        }

        // Use mock data in demo mode
        if (this.isDemoMode) {
            return this.getSharedContentWithMockData(contactId, contentType, limit, offset);
        }

        return this.executeWithRetry(async () => {
            const endpoint = API_ENDPOINTS.CONTACT_SEARCH.SHARED_CONTENT.replace('{contactId}', contactId);
            const response = await apiClient.get<ApiResponse<SharedContentResult>>(
                endpoint,
                {
                    params: {
                        content_type: contentType,
                        limit: Math.min(limit, SEARCH_CONFIG.MAX_LIMIT),
                        offset,
                    },
                    timeout: options.timeout || 10000,
                    signal: options.signal,
                }
            );

            return response.data.data;
        }, options);
    }

    /**
     * Get contact search suggestions with fallback handling
     */
    async getSearchSuggestions(
        query: string,
        limit: number = SEARCH_CONFIG.MAX_SUGGESTIONS,
        options: SearchRequestOptions = {}
    ): Promise<ContactSuggestion[]> {
        if (!query || query.trim().length < 1) {
            return [];
        }

        // Use mock data in demo mode
        if (this.isDemoMode) {
            try {
                const suggestionStrings = await mockDataService.getContactSuggestions(query);
                return suggestionStrings.slice(0, limit).map(text => ({
                    text,
                    type: 'person' as const,
                    confidence: 0.8,
                }));
            } catch (error) {
                console.warn('Mock suggestions failed, returning empty array:', error);
                return [];
            }
        }

        try {
            return await this.executeWithRetry(async () => {
                const endpoint = API_ENDPOINTS.CONTACT_SEARCH.SUGGESTIONS.replace('{query}', encodeURIComponent(query));
                const response = await apiClient.get<ApiResponse<{ suggestions: ContactSuggestion[] }>>(
                    endpoint,
                    {
                        params: { limit: Math.min(limit, SEARCH_CONFIG.MAX_SUGGESTIONS) },
                        timeout: options.timeout || 5000,
                        signal: options.signal,
                    }
                );

                return response.data.data.suggestions || [];
            }, { ...options, retries: 1 }); // Fewer retries for suggestions
        } catch (error) {
            console.warn('Search suggestions failed, returning empty array:', error);
            return []; // Graceful fallback for suggestions
        }
    }

    /**
     * Check contact search service health
     */
    async checkHealth(options: SearchRequestOptions = {}): Promise<{ status: string; timestamp: string; version?: string }> {
        return this.executeWithRetry(async () => {
            const response = await apiClient.get<ApiResponse<{ status: string; timestamp: string; version?: string }>>(
                API_ENDPOINTS.CONTACT_SEARCH.HEALTH,
                {
                    timeout: options.timeout || 5000,
                    signal: options.signal,
                }
            );

            return response.data.data;
        }, { ...options, retries: 1 });
    }

    /**
     * Get example natural language queries for testing
     */
    async getExampleQueries(options: SearchRequestOptions = {}): Promise<{ examples: string[]; supported_intents: string[] }> {
        try {
            return await this.executeWithRetry(async () => {
                const response = await apiClient.get<ApiResponse<{ examples: string[]; supported_intents: string[] }>>(
                    API_ENDPOINTS.CONTACT_SEARCH.EXAMPLES,
                    {
                        timeout: options.timeout || 5000,
                        signal: options.signal,
                    }
                );

                return response.data.data;
            }, { ...options, retries: 1 });
        } catch (error) {
            console.warn('Failed to get example queries, returning defaults:', error);
            return {
                examples: [
                    'messages with John',
                    'files from Sarah',
                    'calls with team',
                    'emails last week'
                ],
                supported_intents: ['person_search', 'content_search', 'temporal_search']
            };
        }
    }

    // Mock data integration methods for demo mode

    /**
     * Search contacts using mock data service
     */
    private async searchContactsWithMockData(
        query: string,
        limit: number,
        includeSuggestions: boolean
    ): Promise<ContactSearchResult> {
        const contacts = await mockDataService.searchContacts(query);
        const limitedContacts = contacts.slice(0, limit);

        let suggestions: ContactSuggestion[] = [];
        if (includeSuggestions) {
            const suggestionStrings = await mockDataService.getContactSuggestions(query);
            suggestions = suggestionStrings.map(text => ({
                text,
                type: 'person' as const,
                confidence: 0.8,
            }));
        }

        return {
            contacts: limitedContacts,
            suggestions,
            query: query.trim(),
            normalized_query: query.trim().toLowerCase(),
            total_results: contacts.length,
            has_more: contacts.length > limit,
            processing_time_ms: 150 + Math.random() * 100, // Simulate processing time
        };
    }

    /**
     * Process natural language query using mock data
     */
    private async processNaturalLanguageWithMockData(query: string): Promise<NaturalLanguageQueryResult> {
        // Simple intent detection for demo
        const lowerQuery = query.toLowerCase();
        let intent = 'general_search';
        let contacts: UnifiedContact[] = [];

        if (lowerQuery.includes('messages with') || lowerQuery.includes('conversation with')) {
            intent = 'person_messages';
            const nameMatch = query.match(/(?:messages with|conversation with)\s+([^,]+)/i);
            if (nameMatch) {
                contacts = await mockDataService.searchContacts(nameMatch[1].trim());
            }
        } else if (lowerQuery.includes('files from') || lowerQuery.includes('documents from')) {
            intent = 'person_files';
            const nameMatch = query.match(/(?:files from|documents from)\s+([^,]+)/i);
            if (nameMatch) {
                contacts = await mockDataService.searchContacts(nameMatch[1].trim());
            }
        } else if (lowerQuery.includes('calls with') || lowerQuery.includes('meetings with')) {
            intent = 'person_calls';
            const nameMatch = query.match(/(?:calls with|meetings with)\s+([^,]+)/i);
            if (nameMatch) {
                contacts = await mockDataService.searchContacts(nameMatch[1].trim());
            }
        }

        return {
            intent,
            processed_text: query.trim(),
            contacts: contacts.slice(0, 5),
            filters: {},
            temporal_constraints: {},
            entities: [],
            confidence: 0.85,
        };
    }

    /**
     * Search messages by contact using mock data
     */
    private async searchMessagesByContactWithMockData(
        contactId: string,
        query?: string,
        limit: number = 50,
        offset: number = 0,
        groupByThread: boolean = true
    ): Promise<ContactMessageSearchResult> {
        const contact = await mockDataService.getContact(contactId);
        if (!contact) {
            throw this.createError(ERROR_CODES.NOT_FOUND, 'Contact not found', false);
        }

        const messages = await mockDataService.searchMessages(query || '', contactId);
        const threads = await mockDataService.getThreadsForContact(contactId);

        const limitedMessages = messages.slice(offset, offset + limit);

        return {
            messages: limitedMessages.map(result => ({
                id: result.id,
                content: result.content || '',
                sender: result.contact || contact,
                timestamp: result.timestamp,
                platform: result.platform || 'gmail',
            })),
            threads: threads.slice(0, 5),
            contact,
            total_messages: messages.length,
            total_threads: threads.length,
            query: query || '',
            has_more: messages.length > offset + limit,
        };
    }

    /**
     * Get shared content using mock data
     */
    private async getSharedContentWithMockData(
        contactId: string,
        contentType?: 'files' | 'links' | 'media',
        limit: number = 50,
        offset: number = 0
    ): Promise<SharedContentResult> {
        const contact = await mockDataService.getContact(contactId);
        if (!contact) {
            throw this.createError(ERROR_CODES.NOT_FOUND, 'Contact not found', false);
        }

        let shared_files = contact.sharedFiles || [];
        let shared_links = contact.sharedLinks || [];
        let shared_media: MediaFile[] = [];

        // Filter by content type if specified
        if (contentType === 'files') {
            shared_links = [];
            shared_media = [];
        } else if (contentType === 'links') {
            shared_files = [];
            shared_media = [];
        } else if (contentType === 'media') {
            shared_files = [];
            shared_links = [];
            // Generate some mock media files
            shared_media = [
                {
                    id: 'media-1',
                    name: 'screenshot.png',
                    type: 'image',
                    url: 'https://example.com/screenshot.png',
                    thumbnail_url: 'https://example.com/screenshot_thumb.png',
                    size: 1024000,
                    shared_at: new Date(),
                    platform: 'slack',
                },
            ];
        }

        const total_items = shared_files.length + shared_links.length + shared_media.length;

        return {
            contact,
            shared_files: shared_files.slice(offset, offset + limit),
            shared_links: shared_links.slice(offset, offset + limit),
            shared_media: shared_media.slice(offset, offset + limit),
            total_items,
            has_more: total_items > offset + limit,
        };
    }

    // Private helper methods for error handling and retry logic

    /**
     * Execute a function with retry logic and exponential backoff
     */
    private async executeWithRetry<T>(
        fn: () => Promise<T>,
        options: SearchRequestOptions = {}
    ): Promise<T> {
        const maxRetries = options.retries ?? this.maxRetries;
        let lastError: any;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await fn();
            } catch (error: any) {
                lastError = error;

                // Don't retry on validation errors or non-retryable errors
                if (this.isNonRetryableError(error) || attempt === maxRetries) {
                    throw this.transformError(error);
                }

                // Calculate delay with exponential backoff and jitter
                const delay = this.calculateRetryDelay(attempt, options.retryDelay);
                await this.sleep(delay);

                console.warn(`Contact search attempt ${attempt + 1} failed, retrying in ${delay}ms:`, error.message);
            }
        }

        throw this.transformError(lastError);
    }

    /**
     * Check if an error should not be retried
     */
    private isNonRetryableError(error: any): boolean {
        if (apiClient.isNetworkError(error)) {
            return false; // Network errors are retryable
        }

        const status = error.response?.status;

        // Don't retry client errors (4xx) except for 408, 429
        if (status >= 400 && status < 500) {
            return ![408, 429].includes(status);
        }

        return false; // Retry server errors (5xx) and other errors
    }

    /**
     * Calculate retry delay with exponential backoff and jitter
     */
    private calculateRetryDelay(attempt: number, baseDelay?: number): number {
        const base = baseDelay ?? this.baseRetryDelay;
        const exponentialDelay = base * Math.pow(2, attempt);
        const jitter = Math.random() * 0.1 * exponentialDelay; // 10% jitter
        return Math.min(exponentialDelay + jitter, 10000); // Max 10 seconds
    }

    /**
     * Sleep for specified milliseconds
     */
    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Transform API errors into standardized ContactSearchError
     */
    private transformError(error: any): ContactSearchError {
        if (apiClient.isNetworkError(error)) {
            return this.createError(
                ERROR_CODES.NETWORK_ERROR,
                'Network connection failed. Please check your internet connection.',
                true
            );
        }

        const status = error.response?.status;
        const message = apiClient.getErrorMessage(error);

        switch (status) {
            case 400:
                return this.createError(ERROR_CODES.VALIDATION_ERROR, message, false);
            case 401:
                return this.createError(ERROR_CODES.AUTH_ERROR, 'Authentication required', false);
            case 404:
                return this.createError(ERROR_CODES.NOT_FOUND, 'Resource not found', false);
            case 408:
                return this.createError(ERROR_CODES.TIMEOUT_ERROR, 'Request timed out', true);
            case 429:
                return this.createError(ERROR_CODES.RATE_LIMITED, 'Too many requests. Please try again later.', true);
            case 500:
            case 502:
            case 503:
            case 504:
                return this.createError(ERROR_CODES.SERVER_ERROR, 'Server error. Please try again.', true);
            default:
                return this.createError(ERROR_CODES.SERVER_ERROR, message || 'An unexpected error occurred', true);
        }
    }

    /**
     * Create a standardized error object
     */
    private createError(code: string, message: string, retryable: boolean): ContactSearchError {
        return {
            code,
            message,
            retryable,
            details: { timestamp: new Date().toISOString() }
        };
    }

    /**
     * Validate and transform API response
     */
    private validateAndTransformResponse(response: any): ContactSearchResult {
        if (!response || typeof response !== 'object') {
            throw this.createError(
                ERROR_CODES.SERVER_ERROR,
                'Invalid response format from server',
                false
            );
        }

        // Ensure required fields exist with defaults
        return {
            contacts: Array.isArray(response.contacts) ? response.contacts : [],
            suggestions: Array.isArray(response.suggestions) ? response.suggestions : [],
            query: response.query || '',
            normalized_query: response.normalized_query || response.query || '',
            total_results: typeof response.total_results === 'number' ? response.total_results : 0,
            has_more: Boolean(response.has_more),
            processing_time_ms: response.processing_time_ms
        };
    }
}

export const contactSearchService = new ContactSearchService();