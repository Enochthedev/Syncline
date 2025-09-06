/**
 * React Query hooks for Contact Search functionality
 * 
 * Provides state management, caching, and error handling for contact search operations
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import {
    contactSearchService,
    ContactSearchResult,
    NaturalLanguageQueryResult,
    ContactMessageSearchResult,
    SharedContentResult,
    ContactSuggestion,
    SearchRequestOptions,
    ContactSearchError
} from '../services/contactSearchService';
import { SEARCH_CONFIG, CACHE_CONFIG } from '../constants/api';
import { UnifiedContact } from '../types';

// Query Keys for React Query
export const CONTACT_SEARCH_QUERY_KEYS = {
    all: ['contactSearch'] as const,
    realtime: (query: string) => [...CONTACT_SEARCH_QUERY_KEYS.all, 'realtime', query] as const,
    naturalLanguage: (query: string) => [...CONTACT_SEARCH_QUERY_KEYS.all, 'naturalLanguage', query] as const,
    messages: (contactId: string, query?: string) => [...CONTACT_SEARCH_QUERY_KEYS.all, 'messages', contactId, query] as const,
    sharedContent: (contactId: string, contentType?: string) => [...CONTACT_SEARCH_QUERY_KEYS.all, 'sharedContent', contactId, contentType] as const,
    suggestions: (query: string) => [...CONTACT_SEARCH_QUERY_KEYS.all, 'suggestions', query] as const,
    health: () => [...CONTACT_SEARCH_QUERY_KEYS.all, 'health'] as const,
    examples: () => [...CONTACT_SEARCH_QUERY_KEYS.all, 'examples'] as const,
} as const;

// Hook Options
interface UseContactSearchOptions extends SearchRequestOptions {
    enabled?: boolean;
    staleTime?: number;
    cacheTime?: number;
    refetchOnWindowFocus?: boolean;
}

/**
 * Real-time contact search with debouncing and caching
 */
export const useContactSearchRealtime = (
    query: string,
    limit?: number,
    includeSuggestions?: boolean,
    options: UseContactSearchOptions = {}
) => {
    const {
        enabled = true,
        staleTime = CACHE_CONFIG.SEARCH_TTL,
        cacheTime = CACHE_CONFIG.SEARCH_TTL * 2,
        refetchOnWindowFocus = false,
        ...requestOptions
    } = options;

    // Only search if query meets minimum length requirement
    const shouldSearch = query.length >= SEARCH_CONFIG.MIN_QUERY_LENGTH;

    return useQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.realtime(query),
        queryFn: ({ signal }) =>
            contactSearchService.searchContactsRealtime(
                query,
                limit,
                includeSuggestions,
                { ...requestOptions, signal }
            ),
        enabled: enabled && shouldSearch,
        staleTime,
        cacheTime,
        refetchOnWindowFocus,
        retry: (failureCount, error) => {
            const searchError = error as ContactSearchError;
            return searchError.retryable && failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
    });
};

/**
 * Natural language query processing
 */
export const useNaturalLanguageQuery = (
    query: string,
    options: UseContactSearchOptions = {}
) => {
    const {
        enabled = true,
        staleTime = CACHE_CONFIG.SEARCH_TTL,
        cacheTime = CACHE_CONFIG.SEARCH_TTL * 2,
        ...requestOptions
    } = options;

    const shouldProcess = query.trim().length > 0;

    return useQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.naturalLanguage(query),
        queryFn: ({ signal }) =>
            contactSearchService.processNaturalLanguageQuery(
                query,
                { ...requestOptions, signal }
            ),
        enabled: enabled && shouldProcess,
        staleTime,
        cacheTime,
        retry: (failureCount, error) => {
            const searchError = error as ContactSearchError;
            return searchError.retryable && failureCount < 2;
        },
    });
};

/**
 * Search messages by contact with infinite scrolling
 */
export const useContactMessages = (
    contactId: string,
    query?: string,
    groupByThread: boolean = true,
    options: UseContactSearchOptions = {}
) => {
    const {
        enabled = true,
        staleTime = CACHE_CONFIG.MESSAGE_TTL,
        cacheTime = CACHE_CONFIG.MESSAGE_TTL * 2,
        ...requestOptions
    } = options;

    return useInfiniteQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.messages(contactId, query),
        queryFn: ({ pageParam = 0, signal }) =>
            contactSearchService.searchMessagesByContact(
                contactId,
                query,
                SEARCH_CONFIG.DEFAULT_LIMIT,
                pageParam,
                groupByThread,
                { ...requestOptions, signal }
            ),
        enabled: enabled && !!contactId,
        staleTime,
        cacheTime,
        getNextPageParam: (lastPage, allPages) => {
            if (!lastPage.has_more) return undefined;
            return allPages.length * SEARCH_CONFIG.DEFAULT_LIMIT;
        },
        retry: (failureCount, error) => {
            const searchError = error as ContactSearchError;
            return searchError.retryable && failureCount < 2;
        },
    });
};

/**
 * Get shared content with a contact
 */
export const useSharedContent = (
    contactId: string,
    contentType?: 'files' | 'links' | 'media',
    options: UseContactSearchOptions = {}
) => {
    const {
        enabled = true,
        staleTime = CACHE_CONFIG.CONTACT_TTL,
        cacheTime = CACHE_CONFIG.CONTACT_TTL * 2,
        ...requestOptions
    } = options;

    return useInfiniteQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.sharedContent(contactId, contentType),
        queryFn: ({ pageParam = 0, signal }) =>
            contactSearchService.getSharedContentWithContact(
                contactId,
                contentType,
                SEARCH_CONFIG.DEFAULT_LIMIT,
                pageParam,
                { ...requestOptions, signal }
            ),
        enabled: enabled && !!contactId,
        staleTime,
        cacheTime,
        getNextPageParam: (lastPage, allPages) => {
            if (!lastPage.has_more) return undefined;
            return allPages.length * SEARCH_CONFIG.DEFAULT_LIMIT;
        },
        retry: (failureCount, error) => {
            const searchError = error as ContactSearchError;
            return searchError.retryable && failureCount < 2;
        },
    });
};

/**
 * Get search suggestions with minimal caching
 */
export const useSearchSuggestions = (
    query: string,
    limit?: number,
    options: UseContactSearchOptions = {}
) => {
    const {
        enabled = true,
        staleTime = 30000, // 30 seconds for suggestions
        cacheTime = 60000, // 1 minute
        ...requestOptions
    } = options;

    const shouldFetch = query.length >= 1;

    return useQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.suggestions(query),
        queryFn: ({ signal }) =>
            contactSearchService.getSearchSuggestions(
                query,
                limit,
                { ...requestOptions, signal }
            ),
        enabled: enabled && shouldFetch,
        staleTime,
        cacheTime,
        retry: false, // Don't retry suggestions
    });
};

/**
 * Health check for contact search service
 */
export const useContactSearchHealth = (options: UseContactSearchOptions = {}) => {
    const {
        enabled = true,
        staleTime = 60000, // 1 minute
        cacheTime = 300000, // 5 minutes
        refetchOnWindowFocus = false,
        ...requestOptions
    } = options;

    return useQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.health(),
        queryFn: ({ signal }) =>
            contactSearchService.checkHealth({ ...requestOptions, signal }),
        enabled,
        staleTime,
        cacheTime,
        refetchOnWindowFocus,
        retry: 1,
    });
};

/**
 * Get example queries for natural language search
 */
export const useExampleQueries = (options: UseContactSearchOptions = {}) => {
    const {
        enabled = true,
        staleTime = 3600000, // 1 hour
        cacheTime = 7200000, // 2 hours
        ...requestOptions
    } = options;

    return useQuery({
        queryKey: CONTACT_SEARCH_QUERY_KEYS.examples(),
        queryFn: ({ signal }) =>
            contactSearchService.getExampleQueries({ ...requestOptions, signal }),
        enabled,
        staleTime,
        cacheTime,
        retry: false,
    });
};

// Mutation hooks for actions that modify state

/**
 * Mutation for processing natural language queries with optimistic updates
 */
export const useProcessNaturalLanguageMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ query, options }: { query: string; options?: SearchRequestOptions }) =>
            contactSearchService.processNaturalLanguageQuery(query, options),
        onSuccess: (data, variables) => {
            // Cache the result
            queryClient.setQueryData(
                CONTACT_SEARCH_QUERY_KEYS.naturalLanguage(variables.query),
                data
            );
        },
        retry: (failureCount, error) => {
            const searchError = error as ContactSearchError;
            return searchError.retryable && failureCount < 1;
        },
    });
};

// Utility hooks for common patterns

/**
 * Combined hook for contact search with suggestions
 */
export const useContactSearchWithSuggestions = (
    query: string,
    options: UseContactSearchOptions = {}
) => {
    const searchQuery = useContactSearchRealtime(query, undefined, true, options);
    const suggestionsQuery = useSearchSuggestions(query, undefined, {
        ...options,
        enabled: options.enabled && query.length >= 1 && query.length < SEARCH_CONFIG.MIN_QUERY_LENGTH,
    });

    return useMemo(() => ({
        // Search results
        contacts: searchQuery.data?.contacts || [],
        suggestions: searchQuery.data?.suggestions || suggestionsQuery.data || [],
        totalResults: searchQuery.data?.total_results || 0,
        hasMore: searchQuery.data?.has_more || false,

        // Loading states
        isSearching: searchQuery.isFetching,
        isLoadingSuggestions: suggestionsQuery.isFetching,
        isLoading: searchQuery.isLoading || suggestionsQuery.isLoading,

        // Error states
        searchError: searchQuery.error as ContactSearchError | null,
        suggestionsError: suggestionsQuery.error as ContactSearchError | null,
        hasError: searchQuery.isError || suggestionsQuery.isError,

        // Actions
        refetchSearch: searchQuery.refetch,
        refetchSuggestions: suggestionsQuery.refetch,

        // Query info
        query: searchQuery.data?.query || query,
        normalizedQuery: searchQuery.data?.normalized_query,
        processingTime: searchQuery.data?.processing_time_ms,
    }), [searchQuery, suggestionsQuery, query]);
};

/**
 * Hook for managing contact search state across the app
 */
export const useContactSearchManager = () => {
    const queryClient = useQueryClient();

    const clearSearchCache = useCallback(() => {
        queryClient.removeQueries({ queryKey: CONTACT_SEARCH_QUERY_KEYS.all });
    }, [queryClient]);

    const invalidateSearches = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: CONTACT_SEARCH_QUERY_KEYS.all });
    }, [queryClient]);

    const prefetchContact = useCallback((contactId: string) => {
        queryClient.prefetchQuery({
            queryKey: CONTACT_SEARCH_QUERY_KEYS.messages(contactId),
            queryFn: () => contactSearchService.searchMessagesByContact(contactId),
            staleTime: CACHE_CONFIG.MESSAGE_TTL,
        });
    }, [queryClient]);

    const getCachedContacts = useCallback((): UnifiedContact[] => {
        const queries = queryClient.getQueriesData({ queryKey: CONTACT_SEARCH_QUERY_KEYS.all });
        const contacts: UnifiedContact[] = [];

        queries.forEach(([, data]) => {
            if (data && typeof data === 'object' && 'contacts' in data) {
                const searchResult = data as ContactSearchResult;
                contacts.push(...searchResult.contacts);
            }
        });

        // Remove duplicates by ID
        const uniqueContacts = contacts.filter((contact, index, array) =>
            array.findIndex(c => c.id === contact.id) === index
        );

        return uniqueContacts;
    }, [queryClient]);

    return {
        clearSearchCache,
        invalidateSearches,
        prefetchContact,
        getCachedContacts,
    };
};

// Error handling utilities

/**
 * Hook for handling contact search errors consistently
 */
export const useContactSearchErrorHandler = () => {
    const handleError = useCallback((error: ContactSearchError | null): string | null => {
        if (!error) return null;

        switch (error.code) {
            case 'NETWORK_ERROR':
                return 'No internet connection. Please check your network and try again.';
            case 'TIMEOUT_ERROR':
                return 'Search is taking longer than expected. Please try again.';
            case 'RATE_LIMITED':
                return 'Too many searches. Please wait a moment and try again.';
            case 'AUTH_ERROR':
                return 'Please sign in to search contacts.';
            case 'VALIDATION_ERROR':
                return error.message;
            case 'NOT_FOUND':
                return 'Contact not found.';
            case 'SERVER_ERROR':
            default:
                return 'Search temporarily unavailable. Please try again.';
        }
    }, []);

    const isRetryableError = useCallback((error: ContactSearchError | null): boolean => {
        return error?.retryable || false;
    }, []);

    return {
        handleError,
        isRetryableError,
    };
};