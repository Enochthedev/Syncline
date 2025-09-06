/**
 * Unit Tests for SearchService
 * Comprehensive testing of search functionality
 */

import { SearchService } from '@/services/SearchService';
import { SearchQuery, SearchResponse, SearchFilters } from '@/types/search';

// Mock dependencies
jest.mock('@/services/apiClient');
jest.mock('@/services/cacheService');
jest.mock('@/services/voiceService');

describe('SearchService', () => {
    let searchService: SearchService;
    let mockApiClient: any;
    let mockCacheService: any;
    let mockVoiceService: any;

    beforeEach(() => {
        jest.clearAllMocks();

        mockApiClient = {
            get: jest.fn(),
            post: jest.fn(),
        };

        mockCacheService = {
            get: jest.fn(),
            set: jest.fn(),
            invalidate: jest.fn(),
        };

        mockVoiceService = {
            transcribe: jest.fn(),
        };

        searchService = new SearchService(
            mockApiClient,
            mockCacheService,
            mockVoiceService
        );
    });

    describe('search', () => {
        it('should perform basic text search', async () => {
            const query: SearchQuery = {
                text: 'project update',
                limit: 10,
            };

            const mockResponse: SearchResponse = {
                results: [
                    {
                        id: 'result-1',
                        type: 'message',
                        title: 'Project Update Meeting',
                        snippet: 'Let\'s discuss the project update...',
                        relevanceScore: 0.95,
                        timestamp: new Date().toISOString(),
                    },
                ],
                totalCount: 1,
                processingTime: 150,
            };

            mockApiClient.post.mockResolvedValue({ data: mockResponse });

            const result = await searchService.search(query);

            expect(mockApiClient.post).toHaveBeenCalledWith('/search', query);
            expect(result).toEqual(mockResponse);
        });

        it('should use cached results when available', async () => {
            const query: SearchQuery = { text: 'cached query' };
            const cachedResponse: SearchResponse = {
                results: [],
                totalCount: 0,
                processingTime: 0,
            };

            mockCacheService.get.mockResolvedValue(cachedResponse);

            const result = await searchService.search(query);

            expect(mockCacheService.get).toHaveBeenCalledWith(
                expect.stringContaining('search:')
            );
            expect(mockApiClient.post).not.toHaveBeenCalled();
            expect(result).toEqual(cachedResponse);
        });

        it('should cache new search results', async () => {
            const query: SearchQuery = { text: 'new query' };
            const mockResponse: SearchResponse = {
                results: [],
                totalCount: 0,
                processingTime: 100,
            };

            mockCacheService.get.mockResolvedValue(null);
            mockApiClient.post.mockResolvedValue({ data: mockResponse });

            await searchService.search(query);

            expect(mockCacheService.set).toHaveBeenCalledWith(
                expect.stringContaining('search:'),
                mockResponse,
                expect.any(Number)
            );
        });

        it('should handle search with filters', async () => {
            const filters: SearchFilters = {
                platforms: ['email', 'slack'],
                dateRange: {
                    start: '2023-01-01',
                    end: '2023-12-31',
                },
                contentTypes: ['message', 'file'],
                participants: ['john@example.com'],
            };

            const query: SearchQuery = {
                text: 'filtered search',
                filters,
            };

            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            await searchService.search(query);

            expect(mockApiClient.post).toHaveBeenCalledWith('/search', query);
        });

        it('should handle search errors gracefully', async () => {
            const query: SearchQuery = { text: 'error query' };

            mockCacheService.get.mockResolvedValue(null);
            mockApiClient.post.mockRejectedValue(new Error('Search API error'));

            await expect(searchService.search(query)).rejects.toThrow('Search API error');
        });
    });

    describe('searchByContact', () => {
        it('should search messages for specific contact', async () => {
            const contactId = 'contact-123';
            const query = 'meeting notes';

            const mockResponse: SearchResponse = {
                results: [
                    {
                        id: 'message-1',
                        type: 'message',
                        title: 'Meeting Notes',
                        snippet: 'Notes from our meeting...',
                        relevanceScore: 0.9,
                        timestamp: new Date().toISOString(),
                        contact: global.testUtils.createMockContact({ id: contactId }),
                    },
                ],
                totalCount: 1,
                processingTime: 120,
            };

            mockApiClient.post.mockResolvedValue({ data: mockResponse });

            const result = await searchService.searchByContact(contactId, query);

            expect(mockApiClient.post).toHaveBeenCalledWith('/search/contact', {
                contactId,
                query,
            });
            expect(result).toEqual(mockResponse);
        });

        it('should search all messages for contact when no query provided', async () => {
            const contactId = 'contact-123';

            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            await searchService.searchByContact(contactId);

            expect(mockApiClient.post).toHaveBeenCalledWith('/search/contact', {
                contactId,
                query: undefined,
            });
        });
    });

    describe('voiceSearch', () => {
        it('should transcribe audio and perform search', async () => {
            const audioBlob = new Blob(['audio data'], { type: 'audio/wav' });
            const transcription = 'find messages from john about project';

            mockVoiceService.transcribe.mockResolvedValue(transcription);
            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            const result = await searchService.voiceSearch(audioBlob);

            expect(mockVoiceService.transcribe).toHaveBeenCalledWith(audioBlob);
            expect(mockApiClient.post).toHaveBeenCalledWith('/search', {
                text: transcription,
            });
        });

        it('should handle transcription errors', async () => {
            const audioBlob = new Blob(['audio data'], { type: 'audio/wav' });

            mockVoiceService.transcribe.mockRejectedValue(new Error('Transcription failed'));

            await expect(searchService.voiceSearch(audioBlob)).rejects.toThrow('Transcription failed');
        });

        it('should handle empty transcription', async () => {
            const audioBlob = new Blob(['audio data'], { type: 'audio/wav' });

            mockVoiceService.transcribe.mockResolvedValue('');

            const result = await searchService.voiceSearch(audioBlob);

            expect(result).toEqual({
                results: [],
                totalCount: 0,
                processingTime: 0,
                error: 'No speech detected',
            });
        });
    });

    describe('parseNaturalLanguage', () => {
        it('should parse person-based queries', async () => {
            const query = 'messages from john about project';

            const mockParsedQuery = {
                intent: 'person_search',
                entities: {
                    person: 'john',
                    topic: 'project',
                },
                filters: {
                    participants: ['john'],
                },
            };

            mockApiClient.post.mockResolvedValue({ data: mockParsedQuery });

            const result = await searchService.parseNaturalLanguage(query);

            expect(mockApiClient.post).toHaveBeenCalledWith('/search/parse', { query });
            expect(result).toEqual(mockParsedQuery);
        });

        it('should parse time-based queries', async () => {
            const query = 'files shared last week';

            const mockParsedQuery = {
                intent: 'file_search',
                entities: {
                    timeRange: 'last_week',
                },
                filters: {
                    contentTypes: ['file'],
                    dateRange: {
                        start: expect.any(String),
                        end: expect.any(String),
                    },
                },
            };

            mockApiClient.post.mockResolvedValue({ data: mockParsedQuery });

            const result = await searchService.parseNaturalLanguage(query);

            expect(result.intent).toBe('file_search');
            expect(result.filters?.contentTypes).toContain('file');
        });

        it('should handle complex queries', async () => {
            const query = 'show me emails from sarah about the budget meeting yesterday';

            const mockParsedQuery = {
                intent: 'complex_search',
                entities: {
                    person: 'sarah',
                    platform: 'email',
                    topic: 'budget meeting',
                    timeRange: 'yesterday',
                },
                filters: {
                    platforms: ['email'],
                    participants: ['sarah'],
                    dateRange: {
                        start: expect.any(String),
                        end: expect.any(String),
                    },
                },
            };

            mockApiClient.post.mockResolvedValue({ data: mockParsedQuery });

            const result = await searchService.parseNaturalLanguage(query);

            expect(result.entities?.person).toBe('sarah');
            expect(result.filters?.platforms).toContain('email');
        });
    });

    describe('getSuggestions', () => {
        it('should provide search suggestions', async () => {
            const partialQuery = 'proj';

            const mockSuggestions = [
                { text: 'project update', type: 'recent' },
                { text: 'project meeting', type: 'popular' },
                { text: 'project files', type: 'suggested' },
            ];

            mockApiClient.get.mockResolvedValue({ data: mockSuggestions });

            const result = await searchService.getSuggestions(partialQuery);

            expect(mockApiClient.get).toHaveBeenCalledWith('/search/suggestions', {
                params: { q: partialQuery },
            });
            expect(result).toEqual(mockSuggestions);
        });

        it('should return empty suggestions for empty query', async () => {
            const result = await searchService.getSuggestions('');

            expect(result).toEqual([]);
            expect(mockApiClient.get).not.toHaveBeenCalled();
        });
    });

    describe('getSearchHistory', () => {
        it('should retrieve search history', async () => {
            const mockHistory = [
                {
                    id: 'history-1',
                    query: 'project update',
                    timestamp: new Date().toISOString(),
                    resultCount: 5,
                },
                {
                    id: 'history-2',
                    query: 'meeting notes',
                    timestamp: new Date().toISOString(),
                    resultCount: 3,
                },
            ];

            mockApiClient.get.mockResolvedValue({ data: mockHistory });

            const result = await searchService.getSearchHistory(10);

            expect(mockApiClient.get).toHaveBeenCalledWith('/search/history', {
                params: { limit: 10 },
            });
            expect(result).toEqual(mockHistory);
        });

        it('should handle empty history', async () => {
            mockApiClient.get.mockResolvedValue({ data: [] });

            const result = await searchService.getSearchHistory();

            expect(result).toEqual([]);
        });
    });

    describe('Performance Tests', () => {
        it('should handle concurrent searches efficiently', async () => {
            const queries = Array.from({ length: 10 }, (_, i) => ({
                text: `query ${i}`,
            }));

            mockApiClient.post.mockImplementation(() =>
                Promise.resolve({ data: { results: [], totalCount: 0, processingTime: 100 } })
            );

            const startTime = performance.now();
            const results = await Promise.all(
                queries.map(query => searchService.search(query))
            );
            const endTime = performance.now();

            expect(results).toHaveLength(10);
            expect(endTime - startTime).toBeLessThan(2000); // Should complete within 2 seconds
        });

        it('should debounce rapid search requests', async () => {
            const query = { text: 'rapid search' };

            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            // Simulate rapid successive calls
            const promises = Array.from({ length: 5 }, () =>
                searchService.search(query)
            );

            await Promise.all(promises);

            // Should only make one API call due to debouncing
            expect(mockApiClient.post).toHaveBeenCalledTimes(1);
        });
    });

    describe('Edge Cases', () => {
        it('should handle very long search queries', async () => {
            const longQuery = 'a'.repeat(1000);

            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            await expect(searchService.search({ text: longQuery })).resolves.toBeDefined();
        });

        it('should handle special characters in queries', async () => {
            const specialQuery = '!@#$%^&*()_+{}|:"<>?[];\'\\,./`~';

            mockApiClient.post.mockResolvedValue({ data: { results: [], totalCount: 0 } });

            await expect(searchService.search({ text: specialQuery })).resolves.toBeDefined();
        });

        it('should handle network timeouts', async () => {
            const query = { text: 'timeout test' };

            mockApiClient.post.mockImplementation(() =>
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Network timeout')), 100)
                )
            );

            await expect(searchService.search(query)).rejects.toThrow('Network timeout');
        });

        it('should handle malformed API responses', async () => {
            const query = { text: 'malformed response' };

            mockApiClient.post.mockResolvedValue({ data: null });

            await expect(searchService.search(query)).rejects.toThrow('Invalid search response');
        });
    });
});