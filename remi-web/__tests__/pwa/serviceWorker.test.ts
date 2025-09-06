import { serviceWorkerManager } from '@/utils/serviceWorker';

// Mock IndexedDB
const mockIDB = {
    open: jest.fn(),
    put: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
    getAll: jest.fn(),
};

// Mock navigator.serviceWorker
Object.defineProperty(navigator, 'serviceWorker', {
    value: {
        register: jest.fn(),
        addEventListener: jest.fn(),
        controller: null,
        getRegistration: jest.fn(),
    },
    writable: true,
});

// Mock window.addEventListener
const mockAddEventListener = jest.fn();
Object.defineProperty(window, 'addEventListener', {
    value: mockAddEventListener,
    writable: true,
});

describe('ServiceWorkerManager', () => {
    beforeEach(() => {
        jest.clearAllMocks();

        // Mock online status
        Object.defineProperty(navigator, 'onLine', {
            value: true,
            writable: true,
        });
    });

    describe('Initialization', () => {
        it('should initialize service worker manager', async () => {
            const registerSpy = jest.spyOn(navigator.serviceWorker, 'register');
            registerSpy.mockResolvedValue({
                installing: null,
                waiting: null,
                active: null,
                addEventListener: jest.fn(),
            } as any);

            await serviceWorkerManager.init();

            expect(registerSpy).toHaveBeenCalledWith('/sw.js');
            expect(mockAddEventListener).toHaveBeenCalledWith('online', expect.any(Function));
            expect(mockAddEventListener).toHaveBeenCalledWith('offline', expect.any(Function));
        });

        it('should handle service worker registration failure', async () => {
            const registerSpy = jest.spyOn(navigator.serviceWorker, 'register');
            const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

            registerSpy.mockRejectedValue(new Error('Registration failed'));

            await serviceWorkerManager.init();

            expect(consoleSpy).toHaveBeenCalledWith('Service Worker registration failed:', expect.any(Error));

            consoleSpy.mockRestore();
        });
    });

    describe('Offline Data Management', () => {
        beforeEach(() => {
            // Mock successful IndexedDB operations
            mockIDB.put.mockResolvedValue(undefined);
            mockIDB.get.mockResolvedValue(null);
            mockIDB.delete.mockResolvedValue(undefined);
            mockIDB.getAll.mockResolvedValue([]);
        });

        it('should cache contact data', async () => {
            const contact = {
                id: 'contact-1',
                name: 'John Doe',
                email: 'john@example.com',
                version: 1,
            };

            await serviceWorkerManager.cacheContact(contact);

            expect(mockIDB.put).toHaveBeenCalledWith('contacts', {
                id: contact.id,
                data: contact,
                timestamp: expect.any(Number),
                version: contact.version,
            });
        });

        it('should retrieve cached contact data', async () => {
            const cachedContact = {
                id: 'contact-1',
                data: { name: 'John Doe' },
                timestamp: Date.now(),
                version: 1,
            };

            mockIDB.get.mockResolvedValue(cachedContact);

            const result = await serviceWorkerManager.getCachedContact('contact-1');

            expect(mockIDB.get).toHaveBeenCalledWith('contacts', 'contact-1');
            expect(result).toEqual(cachedContact.data);
        });

        it('should cache search results with expiration', async () => {
            const query = 'test query';
            const results = [{ id: '1', title: 'Result 1' }];

            await serviceWorkerManager.cacheSearchResults(query, results);

            expect(mockIDB.put).toHaveBeenCalledWith('searchCache', {
                query,
                results,
                timestamp: expect.any(Number),
                expiresAt: expect.any(Number),
            });
        });

        it('should return null for expired search results', async () => {
            const expiredCache = {
                query: 'test',
                results: [],
                timestamp: Date.now() - 1000,
                expiresAt: Date.now() - 500, // Expired
            };

            mockIDB.get.mockResolvedValue(expiredCache);

            const result = await serviceWorkerManager.getCachedSearchResults('test');

            expect(result).toBeNull();
        });
    });

    describe('Sync Queue Management', () => {
        it('should queue actions for offline sync', async () => {
            const action = 'create';
            const resource = 'contacts';
            const data = { name: 'New Contact' };

            await serviceWorkerManager.queueAction(action, resource, data);

            expect(mockIDB.put).toHaveBeenCalledWith('syncQueue', {
                id: expect.stringMatching(/^contacts_\d+_[a-z0-9]+$/),
                action,
                resource,
                data,
                timestamp: expect.any(Number),
                retryCount: 0,
            });
        });

        it('should process sync queue when online', async () => {
            const queuedItems = [
                {
                    id: 'item-1',
                    action: 'create',
                    resource: 'contacts',
                    data: { name: 'Test' },
                    timestamp: Date.now(),
                    retryCount: 0,
                },
            ];

            mockIDB.getAll.mockResolvedValue(queuedItems);

            // Mock successful API call
            global.fetch = jest.fn().mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({}),
            });

            await serviceWorkerManager['processSyncQueue']();

            expect(fetch).toHaveBeenCalledWith('/api/contacts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer null', // localStorage.getItem returns null in tests
                },
                body: JSON.stringify(queuedItems[0].data),
            });

            expect(mockIDB.delete).toHaveBeenCalledWith('syncQueue', 'item-1');
        });

        it('should handle sync failures with retry logic', async () => {
            const queuedItems = [
                {
                    id: 'item-1',
                    action: 'create',
                    resource: 'contacts',
                    data: { name: 'Test' },
                    timestamp: Date.now(),
                    retryCount: 0,
                },
            ];

            mockIDB.getAll.mockResolvedValue(queuedItems);

            // Mock failed API call
            global.fetch = jest.fn().mockResolvedValue({
                ok: false,
                statusText: 'Server Error',
            });

            await serviceWorkerManager['processSyncQueue']();

            expect(mockIDB.put).toHaveBeenCalledWith('syncQueue', {
                ...queuedItems[0],
                retryCount: 1,
            });
        });

        it('should remove items after max retries', async () => {
            const queuedItems = [
                {
                    id: 'item-1',
                    action: 'create',
                    resource: 'contacts',
                    data: { name: 'Test' },
                    timestamp: Date.now(),
                    retryCount: 3, // Already at max retries
                },
            ];

            mockIDB.getAll.mockResolvedValue(queuedItems);

            // Mock failed API call
            global.fetch = jest.fn().mockResolvedValue({
                ok: false,
                statusText: 'Server Error',
            });

            await serviceWorkerManager['processSyncQueue']();

            expect(mockIDB.delete).toHaveBeenCalledWith('syncQueue', 'item-1');
        });
    });

    describe('PWA Installation', () => {
        it('should check for install prompt availability', async () => {
            Object.defineProperty(window, 'beforeinstallprompt', {
                value: true,
                writable: true,
            });

            const canInstall = await serviceWorkerManager.checkInstallPrompt();

            expect(canInstall).toBe(true);
        });

        it('should show install prompt when available', async () => {
            const mockPrompt = {
                prompt: jest.fn(),
                userChoice: Promise.resolve({ outcome: 'accepted' }),
            };

            (window as any).deferredPrompt = mockPrompt;

            const result = await serviceWorkerManager.showInstallPrompt();

            expect(mockPrompt.prompt).toHaveBeenCalled();
            expect(result).toBe(true);
            expect((window as any).deferredPrompt).toBeNull();
        });

        it('should return false when no prompt available', async () => {
            (window as any).deferredPrompt = null;

            const result = await serviceWorkerManager.showInstallPrompt();

            expect(result).toBe(false);
        });
    });

    describe('Update Management', () => {
        it('should apply updates when available', async () => {
            const mockRegistration = {
                waiting: {
                    postMessage: jest.fn(),
                },
            };

            jest.spyOn(navigator.serviceWorker, 'getRegistration').mockResolvedValue(mockRegistration as any);

            // Mock window.location.reload
            Object.defineProperty(window, 'location', {
                value: { reload: jest.fn() },
                writable: true,
            });

            await serviceWorkerManager.applyUpdate();

            expect(mockRegistration.waiting.postMessage).toHaveBeenCalledWith({ type: 'SKIP_WAITING' });
            expect(window.location.reload).toHaveBeenCalled();
        });
    });

    describe('Connection Status', () => {
        it('should handle online event', () => {
            const onlineHandler = mockAddEventListener.mock.calls.find(
                call => call[0] === 'online'
            )?.[1];

            expect(onlineHandler).toBeDefined();

            // Simulate going online
            if (onlineHandler) {
                onlineHandler();
            }

            // Should broadcast connection status
            expect(window.dispatchEvent).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: 'sw-message',
                    detail: {
                        type: 'CONNECTION_STATUS',
                        payload: { isOnline: true },
                    },
                })
            );
        });

        it('should handle offline event', () => {
            const offlineHandler = mockAddEventListener.mock.calls.find(
                call => call[0] === 'offline'
            )?.[1];

            expect(offlineHandler).toBeDefined();

            // Simulate going offline
            if (offlineHandler) {
                offlineHandler();
            }

            // Should broadcast connection status
            expect(window.dispatchEvent).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: 'sw-message',
                    detail: {
                        type: 'CONNECTION_STATUS',
                        payload: { isOnline: false },
                    },
                })
            );
        });
    });

    describe('Cleanup', () => {
        it('should clean up old cache entries', async () => {
            const oldTimestamp = Date.now() - (8 * 24 * 60 * 60 * 1000); // 8 days ago
            const mockTransaction = {
                store: {
                    index: () => ({
                        iterate: async function* () {
                            yield {
                                value: { timestamp: oldTimestamp },
                                delete: jest.fn(),
                            };
                        },
                    }),
                },
                done: Promise.resolve(),
            };

            // Mock IndexedDB transaction
            mockIDB.open.mockResolvedValue({
                transaction: () => mockTransaction,
            });

            await serviceWorkerManager.cleanup();

            // Should have attempted to delete old entries
            expect(mockTransaction.store.index).toHaveBeenCalledWith('timestamp');
        });
    });
});