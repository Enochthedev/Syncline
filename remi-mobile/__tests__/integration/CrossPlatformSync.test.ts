/**
 * Integration Tests for Cross-Platform Synchronization
 * Tests real-time sync between mobile and web platforms
 */

import { SyncManager } from '@/services/SyncManager';
import { ContactManager } from '@/services/ContactManager';
import { MessageManager } from '@/services/MessageManager';
import { WebSocketService } from '@/services/WebSocketService';
import { StorageService } from '@/services/StorageService';

// Mock WebSocket for testing
class MockWebSocket {
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;

    readyState = WebSocket.CONNECTING;

    send = jest.fn();
    close = jest.fn();

    // Test utilities
    simulateOpen() {
        this.readyState = WebSocket.OPEN;
        if (this.onopen) {
            this.onopen(new Event('open'));
        }
    }

    simulateMessage(data: any) {
        if (this.onmessage) {
            this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
        }
    }

    simulateClose() {
        this.readyState = WebSocket.CLOSED;
        if (this.onclose) {
            this.onclose(new CloseEvent('close'));
        }
    }
}

// Mock global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('Cross-Platform Synchronization', () => {
    let syncManager: SyncManager;
    let contactManager: ContactManager;
    let messageManager: MessageManager;
    let webSocketService: WebSocketService;
    let storageService: StorageService;
    let mockWebSocket: MockWebSocket;

    beforeEach(async () => {
        // Reset all mocks
        jest.clearAllMocks();

        // Create service instances
        storageService = new StorageService();
        webSocketService = new WebSocketService();
        contactManager = new ContactManager();
        messageManager = new MessageManager();
        syncManager = new SyncManager(
            webSocketService,
            contactManager,
            messageManager,
            storageService
        );

        // Initialize services
        await storageService.initialize();

        // Get WebSocket mock instance
        mockWebSocket = new MockWebSocket();
        (webSocketService as any).ws = mockWebSocket;
    });

    afterEach(async () => {
        await syncManager.disconnect();
        await storageService.cleanup();
    });

    describe('Real-time Contact Synchronization', () => {
        it('should sync contact updates across devices', async () => {
            // Connect to sync service
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Create a contact on "mobile"
            const contact = global.testUtils.createMockContact({
                name: 'John Doe',
                email: 'john@example.com',
            });

            await contactManager.createContact(contact);

            // Simulate receiving update from "web" platform
            const webUpdate = {
                type: 'contact_update',
                action: 'update',
                data: {
                    ...contact,
                    name: 'John Smith', // Name changed on web
                    phone: '+1234567890', // Phone added on web
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(webUpdate);

            // Wait for sync to complete
            await global.testUtils.waitFor(() =>
                contactManager.getContact(contact.id).then(c => c?.name === 'John Smith')
            );

            // Verify contact was updated locally
            const updatedContact = await contactManager.getContact(contact.id);
            expect(updatedContact?.name).toBe('John Smith');
            expect(updatedContact?.phone).toBe('+1234567890');
        });

        it('should handle contact merge conflicts', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const contact = global.testUtils.createMockContact({
                name: 'Original Name',
                lastModified: new Date('2023-01-01').toISOString(),
            });

            await contactManager.createContact(contact);

            // Simulate concurrent updates
            const mobileUpdate = {
                ...contact,
                name: 'Mobile Update',
                lastModified: new Date('2023-01-02T10:00:00Z').toISOString(),
            };

            const webUpdate = {
                type: 'contact_update',
                action: 'update',
                data: {
                    ...contact,
                    name: 'Web Update',
                    lastModified: new Date('2023-01-02T11:00:00Z').toISOString(), // Later timestamp
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            // Update locally first
            await contactManager.updateContact(contact.id, mobileUpdate);

            // Then receive web update
            mockWebSocket.simulateMessage(webUpdate);

            await global.testUtils.waitFor(() =>
                contactManager.getContact(contact.id).then(c => c?.name === 'Web Update')
            );

            // Web update should win due to later timestamp
            const finalContact = await contactManager.getContact(contact.id);
            expect(finalContact?.name).toBe('Web Update');
        });

        it('should batch multiple contact updates', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const contacts = Array.from({ length: 10 }, (_, i) =>
                global.testUtils.createMockContact({ id: `contact-${i}`, name: `Contact ${i}` })
            );

            // Create contacts locally
            await Promise.all(contacts.map(c => contactManager.createContact(c)));

            // Simulate batch update from web
            const batchUpdate = {
                type: 'batch_update',
                action: 'update',
                data: contacts.map(c => ({
                    ...c,
                    name: `${c.name} Updated`,
                })),
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(batchUpdate);

            // Wait for all updates to complete
            await global.testUtils.waitFor(async () => {
                const updatedContacts = await Promise.all(
                    contacts.map(c => contactManager.getContact(c.id))
                );
                return updatedContacts.every(c => c?.name.includes('Updated'));
            });

            // Verify all contacts were updated
            const updatedContacts = await Promise.all(
                contacts.map(c => contactManager.getContact(c.id))
            );

            updatedContacts.forEach((contact, i) => {
                expect(contact?.name).toBe(`Contact ${i} Updated`);
            });
        });
    });

    describe('Message Synchronization', () => {
        it('should sync new messages in real-time', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const newMessage = {
                type: 'message_received',
                action: 'create',
                data: global.testUtils.createMockMessage({
                    content: 'New message from web',
                    platform: 'slack',
                }),
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(newMessage);

            await global.testUtils.waitFor(() =>
                messageManager.getMessage(newMessage.data.id).then(m => m !== null)
            );

            const syncedMessage = await messageManager.getMessage(newMessage.data.id);
            expect(syncedMessage?.content).toBe('New message from web');
            expect(syncedMessage?.platform).toBe('slack');
        });

        it('should sync message read status', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const message = global.testUtils.createMockMessage({ isRead: false });
            await messageManager.createMessage(message);

            // Simulate message read on web
            const readUpdate = {
                type: 'message_update',
                action: 'mark_read',
                data: {
                    messageId: message.id,
                    isRead: true,
                    readAt: new Date().toISOString(),
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(readUpdate);

            await global.testUtils.waitFor(() =>
                messageManager.getMessage(message.id).then(m => m?.isRead === true)
            );

            const updatedMessage = await messageManager.getMessage(message.id);
            expect(updatedMessage?.isRead).toBe(true);
        });

        it('should handle message thread synchronization', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const threadId = 'thread-123';
            const messages = Array.from({ length: 5 }, (_, i) =>
                global.testUtils.createMockMessage({
                    id: `message-${i}`,
                    threadId,
                    content: `Message ${i}`,
                })
            );

            // Simulate thread sync from web
            const threadSync = {
                type: 'thread_sync',
                action: 'sync',
                data: {
                    threadId,
                    messages,
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(threadSync);

            await global.testUtils.waitFor(async () => {
                const threadMessages = await messageManager.getThreadMessages(threadId);
                return threadMessages.length === 5;
            });

            const syncedMessages = await messageManager.getThreadMessages(threadId);
            expect(syncedMessages).toHaveLength(5);
            syncedMessages.forEach((msg, i) => {
                expect(msg.content).toBe(`Message ${i}`);
            });
        });
    });

    describe('Offline Synchronization', () => {
        it('should queue operations when offline', async () => {
            // Start offline
            await syncManager.connect();

            const contact = global.testUtils.createMockContact();

            // Perform operations while offline
            await contactManager.createContact(contact);
            await contactManager.updateContact(contact.id, { name: 'Updated Offline' });

            // Verify operations are queued
            const queuedOps = await syncManager.getQueuedOperations();
            expect(queuedOps).toHaveLength(2);
            expect(queuedOps[0].type).toBe('contact_create');
            expect(queuedOps[1].type).toBe('contact_update');
        });

        it('should sync queued operations when coming online', async () => {
            // Start offline and queue operations
            const contact = global.testUtils.createMockContact();
            await contactManager.createContact(contact);
            await contactManager.updateContact(contact.id, { name: 'Updated Offline' });

            // Come online
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Wait for queue to process
            await global.testUtils.waitFor(async () => {
                const queuedOps = await syncManager.getQueuedOperations();
                return queuedOps.length === 0;
            });

            // Verify operations were sent
            expect(mockWebSocket.send).toHaveBeenCalledTimes(2);

            const sentOps = (mockWebSocket.send as jest.Mock).mock.calls.map(
                call => JSON.parse(call[0])
            );

            expect(sentOps[0].type).toBe('contact_create');
            expect(sentOps[1].type).toBe('contact_update');
        });

        it('should handle sync conflicts after reconnection', async () => {
            const contact = global.testUtils.createMockContact({
                name: 'Original',
                lastModified: new Date('2023-01-01').toISOString(),
            });

            await contactManager.createContact(contact);

            // Go offline and make local changes
            await syncManager.disconnect();
            await contactManager.updateContact(contact.id, {
                name: 'Local Update',
                lastModified: new Date('2023-01-02T10:00:00Z').toISOString(),
            });

            // Come back online
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Simulate server has newer version
            const serverUpdate = {
                type: 'sync_conflict',
                action: 'resolve',
                data: {
                    localVersion: {
                        ...contact,
                        name: 'Local Update',
                        lastModified: new Date('2023-01-02T10:00:00Z').toISOString(),
                    },
                    serverVersion: {
                        ...contact,
                        name: 'Server Update',
                        lastModified: new Date('2023-01-02T11:00:00Z').toISOString(),
                    },
                },
                timestamp: new Date().toISOString(),
                source: 'server',
            };

            mockWebSocket.simulateMessage(serverUpdate);

            await global.testUtils.waitFor(() =>
                contactManager.getContact(contact.id).then(c => c?.name === 'Server Update')
            );

            // Server version should win
            const resolvedContact = await contactManager.getContact(contact.id);
            expect(resolvedContact?.name).toBe('Server Update');
        });
    });

    describe('Performance and Reliability', () => {
        it('should handle high-frequency updates efficiently', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const startTime = performance.now();

            // Simulate 100 rapid updates
            for (let i = 0; i < 100; i++) {
                const update = {
                    type: 'contact_update',
                    action: 'update',
                    data: global.testUtils.createMockContact({
                        id: `contact-${i}`,
                        name: `Contact ${i}`,
                    }),
                    timestamp: new Date().toISOString(),
                    source: 'web',
                };

                mockWebSocket.simulateMessage(update);
            }

            // Wait for all updates to process
            await global.testUtils.waitFor(async () => {
                const contact99 = await contactManager.getContact('contact-99');
                return contact99 !== null;
            });

            const endTime = performance.now();

            // Should process all updates within reasonable time
            expect(endTime - startTime).toBeLessThan(5000);

            // Verify all contacts were created
            const finalContact = await contactManager.getContact('contact-99');
            expect(finalContact?.name).toBe('Contact 99');
        });

        it('should recover from connection failures', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Simulate connection loss
            mockWebSocket.simulateClose();

            // Verify reconnection attempt
            await global.testUtils.waitFor(() =>
                syncManager.getConnectionStatus() === 'reconnecting'
            );

            // Simulate successful reconnection
            mockWebSocket.simulateOpen();

            await global.testUtils.waitFor(() =>
                syncManager.getConnectionStatus() === 'connected'
            );

            expect(syncManager.getConnectionStatus()).toBe('connected');
        });

        it('should handle malformed sync messages gracefully', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Send malformed messages
            const malformedMessages = [
                null,
                undefined,
                '',
                '{"invalid": json}',
                '{"type": "unknown_type"}',
                '{"type": "contact_update"}', // Missing data
            ];

            malformedMessages.forEach(msg => {
                if (mockWebSocket.onmessage) {
                    mockWebSocket.onmessage(new MessageEvent('message', {
                        data: typeof msg === 'string' ? msg : JSON.stringify(msg)
                    }));
                }
            });

            // Should remain connected and functional
            expect(syncManager.getConnectionStatus()).toBe('connected');

            // Should still process valid messages
            const validUpdate = {
                type: 'contact_update',
                action: 'update',
                data: global.testUtils.createMockContact(),
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(validUpdate);

            await global.testUtils.waitFor(() =>
                contactManager.getContact(validUpdate.data.id).then(c => c !== null)
            );

            const contact = await contactManager.getContact(validUpdate.data.id);
            expect(contact).toBeDefined();
        });
    });

    describe('Data Consistency', () => {
        it('should maintain data integrity during sync', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            const contact = global.testUtils.createMockContact({
                platforms: ['email'],
                messageCount: 5,
            });

            await contactManager.createContact(contact);

            // Simulate partial update that could cause inconsistency
            const partialUpdate = {
                type: 'contact_update',
                action: 'update',
                data: {
                    id: contact.id,
                    platforms: ['email', 'slack'], // Added platform
                    // messageCount intentionally omitted
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(partialUpdate);

            await global.testUtils.waitFor(() =>
                contactManager.getContact(contact.id).then(c =>
                    c?.platforms.includes('slack')
                )
            );

            const updatedContact = await contactManager.getContact(contact.id);

            // Should have new platform but preserve existing data
            expect(updatedContact?.platforms).toContain('slack');
            expect(updatedContact?.messageCount).toBe(5); // Should be preserved
        });

        it('should validate sync data before applying', async () => {
            await syncManager.connect();
            mockWebSocket.simulateOpen();

            // Send invalid contact data
            const invalidUpdate = {
                type: 'contact_update',
                action: 'update',
                data: {
                    id: 'invalid-contact',
                    name: '', // Invalid: empty name
                    email: 'not-an-email', // Invalid: malformed email
                    platforms: 'not-an-array', // Invalid: should be array
                },
                timestamp: new Date().toISOString(),
                source: 'web',
            };

            mockWebSocket.simulateMessage(invalidUpdate);

            // Should not create invalid contact
            await new Promise(resolve => setTimeout(resolve, 500));

            const contact = await contactManager.getContact('invalid-contact');
            expect(contact).toBeNull();
        });
    });
});