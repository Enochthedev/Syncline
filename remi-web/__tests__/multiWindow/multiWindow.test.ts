import { renderHook, act } from '@testing-library/react';
import { multiWindowManager, useMultiWindow } from '@/utils/multiWindow';

// Mock BroadcastChannel
class MockBroadcastChannel {
    private listeners: Function[] = [];

    constructor(public name: string) { }

    postMessage(data: any) {
        // Simulate message to other windows
        setTimeout(() => {
            this.listeners.forEach(listener => listener({ data }));
        }, 0);
    }

    addEventListener(type: string, listener: Function) {
        if (type === 'message') {
            this.listeners.push(listener);
        }
    }

    close() {
        this.listeners = [];
    }
}

// Mock localStorage
const mockLocalStorage = {
    data: {} as Record<string, string>,
    getItem: jest.fn((key: string) => mockLocalStorage.data[key] || null),
    setItem: jest.fn((key: string, value: string) => {
        mockLocalStorage.data[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
        delete mockLocalStorage.data[key];
    }),
    clear: jest.fn(() => {
        mockLocalStorage.data = {};
    }),
};

describe('MultiWindowManager', () => {
    beforeEach(() => {
        // Reset localStorage mock
        mockLocalStorage.data = {};
        jest.clearAllMocks();

        // Mock BroadcastChannel
        (global as any).BroadcastChannel = MockBroadcastChannel;

        // Mock localStorage
        Object.defineProperty(window, 'localStorage', {
            value: mockLocalStorage,
            writable: true,
        });

        // Mock window properties
        Object.defineProperty(window, 'location', {
            value: { href: 'https://example.com' },
            writable: true,
        });

        Object.defineProperty(document, 'title', {
            value: 'Test Page',
            writable: true,
        });

        Object.defineProperty(document, 'hidden', {
            value: false,
            writable: true,
        });

        // Mock window.open
        Object.defineProperty(window, 'open', {
            value: jest.fn(() => ({
                focus: jest.fn(),
                close: jest.fn(),
            })),
            writable: true,
        });
    });

    describe('Window Registration', () => {
        it('should register current window on initialization', () => {
            const manager = new (multiWindowManager.constructor as any)();

            const windows = manager.getActiveWindows();
            expect(windows).toHaveLength(1);
            expect(windows[0]).toMatchObject({
                url: 'https://example.com',
                title: 'Test Page',
                isActive: true,
            });
        });

        it('should update localStorage with window list', () => {
            const manager = new (multiWindowManager.constructor as any)();

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-active-windows',
                expect.stringContaining('https://example.com')
            );
        });

        it('should detect available features', () => {
            // Mock feature detection
            Object.defineProperty(navigator, 'serviceWorker', {
                value: {},
                configurable: true,
            });

            Object.defineProperty(window, 'Notification', {
                value: class MockNotification { },
                configurable: true,
            });

            const manager = new (multiWindowManager.constructor as any)();
            const windows = manager.getActiveWindows();

            expect(windows[0].features).toContain('serviceWorker');
            expect(windows[0].features).toContain('notifications');
        });
    });

    describe('Cross-Window Communication', () => {
        it('should broadcast messages to other windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const testData = { test: 'data' };

            manager.syncContacts(testData);

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-window-message',
                expect.stringContaining('SYNC_CONTACTS')
            );
        });

        it('should handle incoming messages from other windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const mockHandler = jest.fn();

            manager.onMessage('TEST_MESSAGE', mockHandler);

            // Simulate message from another window
            const message = {
                type: 'TEST_MESSAGE',
                payload: { data: 'test' },
                timestamp: Date.now(),
                windowId: 'other-window',
                source: 'remi-web',
            };

            manager['processMessage'](message);

            expect(mockHandler).toHaveBeenCalledWith({ data: 'test' }, 'other-window');
        });

        it('should ignore messages from same window', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const mockHandler = jest.fn();

            manager.onMessage('TEST_MESSAGE', mockHandler);

            // Simulate message from same window
            const message = {
                type: 'TEST_MESSAGE',
                payload: { data: 'test' },
                timestamp: Date.now(),
                windowId: manager.getCurrentWindowId(),
                source: 'remi-web',
            };

            manager['processMessage'](message);

            expect(mockHandler).not.toHaveBeenCalled();
        });
    });

    describe('Data Synchronization', () => {
        it('should sync contacts across windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const contacts = [{ id: '1', name: 'John Doe' }];

            manager.syncContacts(contacts);

            const syncData = manager.getSyncData();
            expect(syncData.contacts).toEqual(contacts);
        });

        it('should sync search results across windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const results = [{ id: '1', title: 'Result 1' }];

            manager.syncSearchResults(results);

            const syncData = manager.getSyncData();
            expect(syncData.searchResults).toEqual(results);
        });

        it('should sync user preferences across windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const preferences = { theme: 'dark', language: 'en' };

            manager.syncUserPreferences(preferences);

            const syncData = manager.getSyncData();
            expect(syncData.userPreferences).toEqual(preferences);
        });

        it('should sync authentication state across windows', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const authState = { isAuthenticated: true, user: { id: '1' } };

            manager.syncAuthState(authState);

            const syncData = manager.getSyncData();
            expect(syncData.authState).toEqual(authState);
        });
    });

    describe('Window Management', () => {
        it('should open new window', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const mockWindow = { focus: jest.fn(), close: jest.fn() };

            (window.open as jest.Mock).mockReturnValue(mockWindow);

            const result = manager.openNewWindow('https://example.com/new');

            expect(window.open).toHaveBeenCalledWith('https://example.com/new', '_blank', undefined);
            expect(result).toBe(mockWindow);
        });

        it('should focus specific window', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const targetWindowId = 'target-window';

            manager.focusWindow(targetWindowId);

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-window-message',
                expect.stringContaining('FOCUS_WINDOW')
            );
        });

        it('should navigate specific window', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const targetWindowId = 'target-window';
            const url = 'https://example.com/new-page';

            manager.navigateWindow(targetWindowId, url);

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-window-message',
                expect.stringContaining('NAVIGATE_WINDOW')
            );
        });

        it('should close specific window', () => {
            const manager = new (multiWindowManager.constructor as any)();
            const targetWindowId = 'target-window';

            manager.closeWindow(targetWindowId);

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-window-message',
                expect.stringContaining('CLOSE_WINDOW')
            );
        });
    });

    describe('Feature Locking', () => {
        it('should grant feature lock when available', async () => {
            const manager = new (multiWindowManager.constructor as any)();

            const result = await manager.requestFeatureLock('background-sync');

            expect(result).toBe(true);
            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'feature-lock-background-sync',
                expect.stringContaining(manager.getCurrentWindowId())
            );
        });

        it('should deny feature lock when already taken', async () => {
            const manager = new (multiWindowManager.constructor as any)();

            // Set existing lock
            mockLocalStorage.data['feature-lock-background-sync'] = JSON.stringify({
                windowId: 'other-window',
                timestamp: Date.now(),
                requestId: 'existing-request',
            });

            const result = await manager.requestFeatureLock('background-sync');

            expect(result).toBe(false);
        });

        it('should release feature lock', () => {
            const manager = new (multiWindowManager.constructor as any)();

            // Set lock first
            mockLocalStorage.data['feature-lock-test'] = JSON.stringify({
                windowId: manager.getCurrentWindowId(),
                timestamp: Date.now(),
            });

            manager.releaseFeatureLock('test');

            expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('feature-lock-test');
        });
    });

    describe('Cleanup and Lifecycle', () => {
        it('should cleanup inactive windows', () => {
            const manager = new (multiWindowManager.constructor as any)();

            // Add an old window
            const oldTimestamp = Date.now() - (10 * 60 * 1000); // 10 minutes ago
            manager['windows'].set('old-window', {
                id: 'old-window',
                url: 'https://example.com',
                title: 'Old Window',
                isActive: false,
                lastActivity: oldTimestamp,
                features: [],
            });

            manager['cleanupInactiveWindows']();

            const windows = manager.getActiveWindows();
            expect(windows.find(w => w.id === 'old-window')).toBeUndefined();
        });

        it('should handle window close event', () => {
            const manager = new (multiWindowManager.constructor as any)();

            manager['handleWindowClose']();

            expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
                'remi-window-message',
                expect.stringContaining('WINDOW_CLOSED')
            );
        });

        it('should handle visibility change', () => {
            const manager = new (multiWindowManager.constructor as any)();

            // Mock document.hidden
            Object.defineProperty(document, 'hidden', {
                value: true,
                configurable: true,
            });

            manager['handleVisibilityChange']();

            const windows = manager.getActiveWindows();
            expect(windows[0].isActive).toBe(false);
        });
    });
});

describe('useMultiWindow Hook', () => {
    beforeEach(() => {
        // Mock React
        jest.mock('react', () => ({
            useState: jest.fn((initial) => [initial, jest.fn()]),
            useEffect: jest.fn((fn) => fn()),
            useCallback: jest.fn((fn) => fn),
        }));
    });

    it('should provide multi-window functionality', () => {
        const { result } = renderHook(() => useMultiWindow());

        expect(result.current).toHaveProperty('activeWindows');
        expect(result.current).toHaveProperty('syncData');
        expect(result.current).toHaveProperty('currentWindowId');
        expect(result.current).toHaveProperty('openWindow');
        expect(result.current).toHaveProperty('focusWindow');
        expect(result.current).toHaveProperty('closeWindow');
        expect(result.current).toHaveProperty('syncContacts');
        expect(result.current).toHaveProperty('syncSearchResults');
    });

    it('should open new window through hook', () => {
        const { result } = renderHook(() => useMultiWindow());

        const mockWindow = { focus: jest.fn() };
        (window.open as jest.Mock).mockReturnValue(mockWindow);

        act(() => {
            result.current.openWindow('https://example.com/new');
        });

        expect(window.open).toHaveBeenCalledWith('https://example.com/new', undefined);
    });

    it('should sync data through hook', () => {
        const { result } = renderHook(() => useMultiWindow());
        const contacts = [{ id: '1', name: 'John' }];

        act(() => {
            result.current.syncContacts(contacts);
        });

        expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
            'remi-window-message',
            expect.stringContaining('SYNC_CONTACTS')
        );
    });
});