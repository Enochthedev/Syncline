/**
 * Integration tests for Contact Search Service
 */

import { contactSearchService } from '../../src/services/contactSearchService';
import { apiClient } from '../../src/services/apiClient';

// Mock the API client
jest.mock('../../src/services/apiClient');
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Test data
const mockContactSearchResult = {
    contacts: [
        {
            id: 'contact-1',
            primaryName: 'John Doe',
            displayName: 'John Doe',
            emails: ['john@example.com'],
            phoneNumbers: ['+1234567890'],
            platforms: ['gmail', 'slack'],
            totalMessages: 150,
            lastInteraction: new Date('2024-01-15'),
            relationshipStrength: 0.8,
            communicationFrequency: 'high' as const,
            identities: [],
            socialProfiles: [],
            responsePattern: {
                averageResponseTime: 30,
                responseRate: 0.9,
                preferredTimes: ['9-17'],
                communicationStyle: 'professional' as const,
            },
            topicAffinity: [],
            sharedFiles: [],
            sharedLinks: [],
            commonContacts: [],
            createdAt: new Date('2024-01-01'),
            updatedAt: new Date('2024-01-15'),
            lastSyncAt: new Date('2024-01-15'),
        }
    ],
    suggestions: [
        {
            text: 'John Doe',
            type: 'person' as const,
            contact_id: 'contact-1',
            confidence: 0.95,
        }
    ],
    query: 'john',
    normalized_query: 'john',
    total_results: 1,
    has_more: false,
    processing_time_ms: 45,
};

const mockNaturalLanguageResult = {
    intent: 'person_search',
    processed_text: 'messages with john',
    contacts: mockContactSearchResult.contacts,
    filters: {
        participants: ['john'],
    },
    temporal_constraints: {},
    entities: [
        {
            type: 'person',
            text: 'john',
            confidence: 0.9,
            start_offset: 14,
            end_offset: 18,
        }
    ],
    confidence: 0.9,
};

describe('ContactSearchService', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('searchContactsRealtime', () => {
        it('should search contacts successfully', async () => {
            mockApiClient.get.mockResolvedValueOnce({
                data: { data: mockContactSearchResult }
            });

            const result = await contactSearchService.searchContactsRealtime('john');

            expect(mockApiClient.get).toHaveBeenCalledWith(
                '/api/v1/contacts/search/realtime',
                expect.objectContaining({
                    params: {
                        q: 'john',
                        limit: 20,
                        suggestions: true,
                    },
                })
            );

            expect(result).toEqual(mockContactSearchResult);
        });

        it('should handle validation errors', async () => {
            await expect(
                contactSearchService.searchContactsRealtime('j') // Too short
            ).rejects.toMatchObject({
                code: 'VALIDATION_ERROR',
                message: expect.stringContaining('at least 2 characters'),
                retryable: false,
            });
        });

        it('should retry on network errors', async () => {
            const networkError = new Error('Network Error');
            (networkError as any).request = {};

            mockApiClient.get
                .mockRejectedValueOnce(networkError)
                .mockResolvedValueOnce({
                    data: { data: mockContactSearchResult }
                });

            const result = await contactSearchService.searchContactsRealtime('john');

            expect(mockApiClient.get).toHaveBeenCalledTimes(2);
            expect(result).toEqual(mockContactSearchResult);
        });

        it('should not retry on validation errors', async () => {
            const validationError = {
                response: { status: 400, data: { detail: 'Invalid query' } }
            };

            mockApiClient.get.mockRejectedValueOnce(validationError);

            await expect(
                contactSearchService.searchContactsRealtime('john')
            ).rejects.toMatchObject({
                code: 'VALIDATION_ERROR',
                retryable: false,
            });

            expect(mockApiClient.get).toHaveBeenCalledTimes(1);
        });
    });

    describe('processNaturalLanguageQuery', () => {
        it('should process natural language queries', async () => {
            mockApiClient.post.mockResolvedValueOnce({
                data: { data: mockNaturalLanguageResult }
            });

            const result = await contactSearchService.processNaturalLanguageQuery('messages with john');

            expect(mockApiClient.post).toHaveBeenCalledWith(
                '/api/v1/contacts/search/natural-language',
                { query: 'messages with john' },
                expect.any(Object)
            );

            expect(result).toEqual(mockNaturalLanguageResult);
        });

        it('should handle empty queries', async () => {
            await expect(
                contactSearchService.processNaturalLanguageQuery('')
            ).rejects.toMatchObject({
                code: 'VALIDATION_ERROR',
                message: 'Query cannot be empty',
                retryable: false,
            });
        });
    });

    describe('searchMessagesByContact', () => {
        it('should search messages by contact', async () => {
            const mockContactMessages = {
                messages: [
                    {
                        id: 'msg-1',
                        content: 'Hello John, how are you?',
                        sender: mockContactSearchResult.contacts[0],
                        timestamp: new Date('2024-01-15T10:00:00Z'),
                        platform: 'gmail',
                    }
                ],
                threads: [],
                contact: mockContactSearchResult.contacts[0],
                total_messages: 1,
                total_threads: 0,
                query: 'hello',
                has_more: false,
            };

            mockApiClient.get.mockResolvedValueOnce({
                data: { data: mockContactMessages }
            });

            const result = await contactSearchService.searchMessagesByContact('contact-1', 'hello');

            expect(mockApiClient.get).toHaveBeenCalledWith(
                '/api/v1/contacts/search/contact-1/messages',
                expect.objectContaining({
                    params: {
                        q: 'hello',
                        limit: 50,
                        offset: 0,
                        group_by_thread: true,
                    },
                })
            );

            expect(result).toEqual(mockContactMessages);
        });

        it('should validate contact ID', async () => {
            await expect(
                contactSearchService.searchMessagesByContact('')
            ).rejects.toMatchObject({
                code: 'VALIDATION_ERROR',
                message: 'Contact ID is required',
                retryable: false,
            });
        });
    });

    describe('getSearchSuggestions', () => {
        it('should get search suggestions', async () => {
            const suggestions = [
                { text: 'John Doe', type: 'person' as const, contact_id: 'contact-1' }
            ];

            mockApiClient.get.mockResolvedValueOnce({
                data: { data: { suggestions } }
            });

            const result = await contactSearchService.getSearchSuggestions('jo');

            expect(result).toEqual(suggestions);
        });

        it('should return empty array for empty query', async () => {
            const result = await contactSearchService.getSearchSuggestions('');
            expect(result).toEqual([]);
        });

        it('should gracefully handle suggestion errors', async () => {
            mockApiClient.get.mockRejectedValueOnce(new Error('Network error'));

            const result = await contactSearchService.getSearchSuggestions('jo');
            expect(result).toEqual([]);
        });
    });

    describe('checkHealth', () => {
        it('should check service health', async () => {
            const healthData = { status: 'healthy', timestamp: '2024-01-15T10:00:00Z' };

            mockApiClient.get.mockResolvedValueOnce({
                data: { data: healthData }
            });

            const result = await contactSearchService.checkHealth();

            expect(mockApiClient.get).toHaveBeenCalledWith(
                '/api/v1/contacts/search/health',
                expect.any(Object)
            );

            expect(result).toEqual(healthData);
        });
    });
});

describe('API Client Integration', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('Error Handling', () => {
        it('should handle network errors', () => {
            const networkError = { request: {}, message: 'Network Error' };
            expect(apiClient.isNetworkError(networkError)).toBe(true);
            expect(apiClient.getErrorMessage(networkError)).toContain('Network error');
        });

        it('should handle timeout errors', () => {
            const timeoutError = { code: 'ECONNABORTED', message: 'timeout of 5000ms exceeded' };
            expect(apiClient.isTimeoutError(timeoutError)).toBe(true);
            expect(apiClient.getErrorMessage(timeoutError)).toContain('timed out');
        });

        it('should identify retryable errors', () => {
            const networkError = { request: {} };
            const serverError = { response: { status: 500 } };
            const validationError = { response: { status: 400 } };

            expect(apiClient.isRetryableError(networkError)).toBe(true);
            expect(apiClient.isRetryableError(serverError)).toBe(true);
            expect(apiClient.isRetryableError(validationError)).toBe(false);
        });
    });

    describe('Request Retry Logic', () => {
        it('should retry failed requests', async () => {
            const mockRequest = jest.fn()
                .mockRejectedValueOnce({ response: { status: 500 } })
                .mockResolvedValueOnce({ data: 'success' });

            const result = await apiClient.requestWithRetry(mockRequest, 2, 100);

            expect(mockRequest).toHaveBeenCalledTimes(2);
            expect(result.data).toBe('success');
        });

        it('should not retry non-retryable errors', async () => {
            const mockRequest = jest.fn()
                .mockRejectedValue({ response: { status: 400 } });

            await expect(
                apiClient.requestWithRetry(mockRequest, 2, 100)
            ).rejects.toMatchObject({ response: { status: 400 } });

            expect(mockRequest).toHaveBeenCalledTimes(1);
        });
    });
});