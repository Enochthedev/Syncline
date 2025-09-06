/**
 * Natural Language Search Service Tests
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { naturalLanguageSearchService } from '@/services/naturalLanguageSearchService';
import { apiClient } from '@/services/apiClient';

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
}));

// Mock API client
jest.mock('@/services/apiClient', () => ({
    apiClient: {
        post: jest.fn(),
    },
}));

describe('NaturalLanguageSearchService', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('processNaturalLanguageQuery', () => {
        it('should process natural language query successfully', async () => {
            const mockResponse = {
                data: {
                    intent: 'person_messages',
                    processed_text: 'messages with John',
                    contacts: [{ id: '1', displayName: 'John Smith' }],
                    filters: {},
                    temporal_constraints: {},
                    entities: [{ text: 'John', type: 'PERSON' }],
                },
            };

            (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);

            const result = await naturalLanguageSearchService.processNaturalLanguageQuery('messages with John');

            expect(apiClient.post).toHaveBeenCalledWith('/contacts/search/natural-language', {
                query: 'messages with John',
            });
            expect(result).toEqual(mockResponse.data);
        });

        it('should handle API errors', async () => {
            (apiClient.post as jest.Mock).mockRejectedValue(new Error('API Error'));

            await expect(
                naturalLanguageSearchService.processNaturalLanguageQuery('test query')
            ).rejects.toThrow('API Error');
        });
    });

    describe('getSearchSuggestions', () => {
        it('should return template suggestions for partial queries', async () => {
            const suggestions = await naturalLanguageSearchService.getSearchSuggestions('messages', 5);

            expect(suggestions).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        text: 'messages with [contact name]',
                        type: 'template',
                    }),
                ])
            );
        });

        it('should return history-based suggestions', async () => {
            const mockHistory = [
                {
                    query: 'messages with John',
                    timestamp: new Date(),
                    intent: 'person_messages',
                    resultCount: 5,
                },
            ];

            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            const suggestions = await naturalLanguageSearchService.getSearchSuggestions('messages', 5);

            expect(suggestions).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        text: 'messages with John',
                        type: 'history',
                    }),
                ])
            );
        });

        it('should limit suggestions to specified count', async () => {
            const suggestions = await naturalLanguageSearchService.getSearchSuggestions('test', 3);

            expect(suggestions.length).toBeLessThanOrEqual(3);
        });
    });

    describe('search history management', () => {
        it('should save search query to history', async () => {
            const mockHistory = [];
            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            await naturalLanguageSearchService.saveToHistory('test query', 'general_search', 10);

            expect(AsyncStorage.setItem).toHaveBeenCalledWith(
                'nl_search_history',
                expect.stringContaining('test query')
            );
        });

        it('should retrieve search history', async () => {
            const mockHistory = [
                {
                    query: 'test query',
                    timestamp: new Date().toISOString(),
                    intent: 'general_search',
                    resultCount: 10,
                },
            ];

            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            const history = await naturalLanguageSearchService.getSearchHistory();

            expect(history).toHaveLength(1);
            expect(history[0].query).toBe('test query');
            expect(history[0].timestamp).toBeInstanceOf(Date);
        });

        it('should clear search history', async () => {
            await naturalLanguageSearchService.clearHistory();

            expect(AsyncStorage.removeItem).toHaveBeenCalledWith('nl_search_history');
        });

        it('should remove specific item from history', async () => {
            const mockHistory = [
                {
                    query: 'query 1',
                    timestamp: new Date().toISOString(),
                },
                {
                    query: 'query 2',
                    timestamp: new Date().toISOString(),
                },
            ];

            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            await naturalLanguageSearchService.removeFromHistory('query 1');

            expect(AsyncStorage.setItem).toHaveBeenCalledWith(
                'nl_search_history',
                expect.not.stringContaining('query 1')
            );
        });

        it('should limit history to maximum items', async () => {
            const mockHistory = Array.from({ length: 60 }, (_, i) => ({
                query: `query ${i}`,
                timestamp: new Date().toISOString(),
            }));

            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            await naturalLanguageSearchService.saveToHistory('new query');

            const savedData = (AsyncStorage.setItem as jest.Mock).mock.calls[0][1];
            const savedHistory = JSON.parse(savedData);

            expect(savedHistory.length).toBe(50); // MAX_HISTORY_ITEMS
            expect(savedHistory[0].query).toBe('new query'); // New item should be first
        });
    });

    describe('searchCommitments', () => {
        it('should search for commitments', async () => {
            const mockResponse = {
                data: {
                    results: [
                        {
                            id: '1',
                            type: 'commitment',
                            title: 'Complete project',
                            snippet: 'Due next week',
                            timestamp: new Date().toISOString(),
                        },
                    ],
                },
            };

            (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);

            const results = await naturalLanguageSearchService.searchCommitments('John', 'project', 'next week');

            expect(apiClient.post).toHaveBeenCalledWith('/search/commitments', {
                person: 'John',
                topic: 'project',
                timeframe: 'next week',
                limit: 20,
            });

            expect(results).toHaveLength(1);
            expect(results[0].type).toBe('commitment');
        });
    });

    describe('searchFiles', () => {
        it('should search for files', async () => {
            const mockResponse = {
                data: {
                    results: [
                        {
                            id: '1',
                            type: 'file',
                            title: 'document.pdf',
                            snippet: 'PDF • 1.2 MB',
                            timestamp: new Date().toISOString(),
                        },
                    ],
                },
            };

            (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);

            const results = await naturalLanguageSearchService.searchFiles('Sarah', 'pdf');

            expect(apiClient.post).toHaveBeenCalledWith('/search/files', {
                contact: 'Sarah',
                file_type: 'pdf',
                limit: 20,
            });

            expect(results).toHaveLength(1);
            expect(results[0].type).toBe('file');
        });
    });

    describe('performGeneralSearch', () => {
        it('should perform general search', async () => {
            const mockResponse = {
                data: {
                    results: [
                        {
                            id: '1',
                            type: 'message',
                            title: 'Meeting notes',
                            snippet: 'Discussion about project',
                            timestamp: new Date().toISOString(),
                        },
                    ],
                },
            };

            (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);

            const results = await naturalLanguageSearchService.performGeneralSearch('meeting notes');

            expect(apiClient.post).toHaveBeenCalledWith('/search/', {
                query: 'meeting notes',
                limit: 50,
                include_suggestions: true,
                include_facets: false,
            });

            expect(results).toHaveLength(1);
            expect(results[0].type).toBe('message');
        });
    });

    describe('getPopularPatterns', () => {
        it('should return popular search patterns', async () => {
            const mockHistory = [
                { query: 'query 1', intent: 'person_messages' },
                { query: 'query 2', intent: 'person_messages' },
                { query: 'query 3', intent: 'file_search' },
            ];

            (AsyncStorage.getItem as jest.Mock).mockResolvedValue(JSON.stringify(mockHistory));

            const patterns = await naturalLanguageSearchService.getPopularPatterns();

            expect(patterns).toEqual([
                { pattern: 'person_messages', count: 2 },
                { pattern: 'file_search', count: 1 },
            ]);
        });
    });

    describe('validateQuery', () => {
        it('should validate valid queries', () => {
            const result = naturalLanguageSearchService.validateQuery('messages with John');

            expect(result.isValid).toBe(true);
            expect(result.error).toBeUndefined();
        });

        it('should reject empty queries', () => {
            const result = naturalLanguageSearchService.validateQuery('');

            expect(result.isValid).toBe(false);
            expect(result.error).toBe('Query cannot be empty');
        });

        it('should reject too long queries', () => {
            const longQuery = 'a'.repeat(501);
            const result = naturalLanguageSearchService.validateQuery(longQuery);

            expect(result.isValid).toBe(false);
            expect(result.error).toBe('Query is too long (max 500 characters)');
        });

        it('should reject too short queries', () => {
            const result = naturalLanguageSearchService.validateQuery('a');

            expect(result.isValid).toBe(false);
            expect(result.error).toBe('Query is too short (min 2 characters)');
        });
    });

    describe('getExampleQueries', () => {
        it('should return example queries', () => {
            const examples = naturalLanguageSearchService.getExampleQueries();

            expect(examples).toBeInstanceOf(Array);
            expect(examples.length).toBeGreaterThan(0);
            expect(examples).toContain('messages with John Smith');
        });
    });
});