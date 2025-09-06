/**
 * Unit Tests for ContactManager
 * Comprehensive testing of contact management functionality
 */

import { ContactManager } from '@/services/ContactManager';
import { Contact, ContactSearchOptions } from '@/types/contact';

// Mock dependencies
jest.mock('@/services/apiClient');
jest.mock('@/services/storageService');
jest.mock('@/services/syncService');

describe('ContactManager', () => {
    let contactManager: ContactManager;
    let mockApiClient: any;
    let mockStorageService: any;
    let mockSyncService: any;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();

        // Create mock instances
        mockApiClient = {
            get: jest.fn(),
            post: jest.fn(),
            put: jest.fn(),
            delete: jest.fn(),
        };

        mockStorageService = {
            getContacts: jest.fn(),
            saveContact: jest.fn(),
            deleteContact: jest.fn(),
            searchContacts: jest.fn(),
        };

        mockSyncService = {
            syncContact: jest.fn(),
            queueSync: jest.fn(),
        };

        contactManager = new ContactManager(
            mockApiClient,
            mockStorageService,
            mockSyncService
        );
    });

    describe('searchContacts', () => {
        it('should search contacts with fuzzy matching', async () => {
            const mockContacts: Contact[] = [
                global.testUtils.createMockContact({ name: 'John Smith' }),
                global.testUtils.createMockContact({ name: 'Jane Doe', id: 'test-contact-2' }),
            ];

            mockStorageService.searchContacts.mockResolvedValue(mockContacts);

            const results = await contactManager.searchContacts('jon smith');

            expect(mockStorageService.searchContacts).toHaveBeenCalledWith('jon smith', undefined);
            expect(results).toHaveLength(2);
            expect(results[0].name).toBe('John Smith');
        });

        it('should handle search with options', async () => {
            const options: ContactSearchOptions = {
                platforms: ['email', 'slack'],
                limit: 10,
                includeInactive: false,
            };

            mockStorageService.searchContacts.mockResolvedValue([]);

            await contactManager.searchContacts('test', options);

            expect(mockStorageService.searchContacts).toHaveBeenCalledWith('test', options);
        });

        it('should handle search errors gracefully', async () => {
            mockStorageService.searchContacts.mockRejectedValue(new Error('Search failed'));

            await expect(contactManager.searchContacts('test')).rejects.toThrow('Search failed');
        });

        it('should return empty array for empty query', async () => {
            const results = await contactManager.searchContacts('');

            expect(results).toEqual([]);
            expect(mockStorageService.searchContacts).not.toHaveBeenCalled();
        });
    });

    describe('getContact', () => {
        it('should retrieve contact by id', async () => {
            const mockContact = global.testUtils.createMockContact();
            mockStorageService.getContact = jest.fn().mockResolvedValue(mockContact);

            const result = await contactManager.getContact('test-contact-1');

            expect(mockStorageService.getContact).toHaveBeenCalledWith('test-contact-1');
            expect(result).toEqual(mockContact);
        });

        it('should handle non-existent contact', async () => {
            mockStorageService.getContact = jest.fn().mockResolvedValue(null);

            const result = await contactManager.getContact('non-existent');

            expect(result).toBeNull();
        });

        it('should handle retrieval errors', async () => {
            mockStorageService.getContact = jest.fn().mockRejectedValue(new Error('Database error'));

            await expect(contactManager.getContact('test-id')).rejects.toThrow('Database error');
        });
    });

    describe('mergeContacts', () => {
        it('should merge duplicate contacts correctly', async () => {
            const primaryContact = global.testUtils.createMockContact({
                id: 'primary',
                platforms: ['email'],
            });

            const duplicateContact = global.testUtils.createMockContact({
                id: 'duplicate',
                platforms: ['slack'],
                email: 'john.doe@company.com',
            });

            mockStorageService.getContact = jest.fn()
                .mockResolvedValueOnce(primaryContact)
                .mockResolvedValueOnce(duplicateContact);

            mockStorageService.saveContact = jest.fn().mockResolvedValue(undefined);
            mockStorageService.deleteContact = jest.fn().mockResolvedValue(undefined);

            await contactManager.mergeContacts('primary', ['duplicate']);

            expect(mockStorageService.saveContact).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 'primary',
                    platforms: ['email', 'slack'],
                })
            );
            expect(mockStorageService.deleteContact).toHaveBeenCalledWith('duplicate');
        });

        it('should handle merge conflicts', async () => {
            const primaryContact = global.testUtils.createMockContact({
                id: 'primary',
                name: 'John Smith',
            });

            const duplicateContact = global.testUtils.createMockContact({
                id: 'duplicate',
                name: 'John Doe',
            });

            mockStorageService.getContact = jest.fn()
                .mockResolvedValueOnce(primaryContact)
                .mockResolvedValueOnce(duplicateContact);

            mockStorageService.saveContact = jest.fn().mockResolvedValue(undefined);

            await contactManager.mergeContacts('primary', ['duplicate']);

            // Should keep primary contact's name
            expect(mockStorageService.saveContact).toHaveBeenCalledWith(
                expect.objectContaining({
                    name: 'John Smith',
                })
            );
        });
    });

    describe('updateContact', () => {
        it('should update contact and sync', async () => {
            const updates = { name: 'Updated Name' };
            mockStorageService.saveContact = jest.fn().mockResolvedValue(undefined);
            mockSyncService.queueSync = jest.fn().mockResolvedValue(undefined);

            await contactManager.updateContact('test-id', updates);

            expect(mockStorageService.saveContact).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 'test-id',
                    ...updates,
                    updatedAt: expect.any(String),
                })
            );
            expect(mockSyncService.queueSync).toHaveBeenCalledWith('contact', 'test-id');
        });

        it('should validate required fields', async () => {
            await expect(
                contactManager.updateContact('test-id', { name: '' })
            ).rejects.toThrow('Contact name cannot be empty');
        });
    });

    describe('deleteContact', () => {
        it('should delete contact and sync', async () => {
            mockStorageService.deleteContact = jest.fn().mockResolvedValue(undefined);
            mockSyncService.queueSync = jest.fn().mockResolvedValue(undefined);

            await contactManager.deleteContact('test-id');

            expect(mockStorageService.deleteContact).toHaveBeenCalledWith('test-id');
            expect(mockSyncService.queueSync).toHaveBeenCalledWith('contact_delete', 'test-id');
        });
    });

    describe('getContactInsights', () => {
        it('should retrieve contact insights', async () => {
            const mockInsights = {
                communicationFrequency: 'high',
                lastInteraction: new Date().toISOString(),
                relationshipStrength: 0.8,
                topTopics: ['work', 'project'],
            };

            mockApiClient.get.mockResolvedValue({ data: mockInsights });

            const result = await contactManager.getContactInsights('test-id');

            expect(mockApiClient.get).toHaveBeenCalledWith('/contacts/test-id/insights');
            expect(result).toEqual(mockInsights);
        });

        it('should handle insights API errors', async () => {
            mockApiClient.get.mockRejectedValue(new Error('API Error'));

            await expect(contactManager.getContactInsights('test-id')).rejects.toThrow('API Error');
        });
    });

    describe('getCommunicationHistory', () => {
        it('should retrieve communication history', async () => {
            const mockHistory = [
                global.testUtils.createMockMessage(),
                global.testUtils.createMockMessage({ id: 'test-message-2' }),
            ];

            mockApiClient.get.mockResolvedValue({ data: mockHistory });

            const result = await contactManager.getCommunicationHistory('test-id');

            expect(mockApiClient.get).toHaveBeenCalledWith('/contacts/test-id/messages');
            expect(result).toEqual(mockHistory);
        });

        it('should handle history with filters', async () => {
            const filters = {
                platforms: ['email'],
                dateRange: { start: '2023-01-01', end: '2023-12-31' },
            };

            mockApiClient.get.mockResolvedValue({ data: [] });

            await contactManager.getCommunicationHistory('test-id', filters);

            expect(mockApiClient.get).toHaveBeenCalledWith(
                '/contacts/test-id/messages',
                { params: filters }
            );
        });
    });

    describe('Performance Tests', () => {
        it('should handle large contact lists efficiently', async () => {
            const largeContactList = Array.from({ length: 1000 }, (_, i) =>
                global.testUtils.createMockContact({ id: `contact-${i}`, name: `Contact ${i}` })
            );

            mockStorageService.searchContacts.mockResolvedValue(largeContactList);

            const startTime = performance.now();
            const results = await contactManager.searchContacts('Contact');
            const endTime = performance.now();

            expect(results).toHaveLength(1000);
            expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second
        });

        it('should batch contact operations', async () => {
            const contactIds = Array.from({ length: 100 }, (_, i) => `contact-${i}`);

            mockStorageService.getContact = jest.fn().mockImplementation((id) =>
                Promise.resolve(global.testUtils.createMockContact({ id }))
            );

            const startTime = performance.now();
            const results = await contactManager.getMultipleContacts(contactIds);
            const endTime = performance.now();

            expect(results).toHaveLength(100);
            expect(endTime - startTime).toBeLessThan(2000); // Should complete within 2 seconds
        });
    });

    describe('Edge Cases', () => {
        it('should handle null/undefined inputs gracefully', async () => {
            await expect(contactManager.searchContacts(null as any)).resolves.toEqual([]);
            await expect(contactManager.searchContacts(undefined as any)).resolves.toEqual([]);
        });

        it('should handle special characters in search', async () => {
            const specialQuery = 'John@#$%^&*()_+{}|:"<>?[];\'\\,./`~';
            mockStorageService.searchContacts.mockResolvedValue([]);

            await expect(contactManager.searchContacts(specialQuery)).resolves.toEqual([]);
        });

        it('should handle concurrent operations', async () => {
            mockStorageService.searchContacts.mockImplementation(() =>
                new Promise(resolve => setTimeout(() => resolve([]), 100))
            );

            const promises = Array.from({ length: 10 }, () =>
                contactManager.searchContacts('test')
            );

            const results = await Promise.all(promises);

            expect(results).toHaveLength(10);
            results.forEach(result => expect(result).toEqual([]));
        });
    });
});