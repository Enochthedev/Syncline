/**
 * Browser Compatibility Tests
 * Tests for cross-browser functionality and feature detection
 */

// Add empty export to make this a module
export { };

describe('Browser Compatibility', () => {
    // Store original values to restore after tests
    const originalNavigator = global.navigator;
    const originalWindow = global.window;

    afterEach(() => {
        // Restore original values
        global.navigator = originalNavigator;
        global.window = originalWindow;
    });

    describe('Feature Detection', () => {
        it('should detect service worker support', () => {
            // Mock modern browser with service worker support
            Object.defineProperty(global.navigator, 'serviceWorker', {
                value: {
                    register: jest.fn(),
                    addEventListener: jest.fn(),
                },
                configurable: true,
            });

            const hasServiceWorker = 'serviceWorker' in navigator;
            expect(hasServiceWorker).toBe(true);
        });

        it('should detect IndexedDB support', () => {
            // Mock IndexedDB support
            Object.defineProperty(global.window, 'indexedDB', {
                value: {
                    open: jest.fn(),
                    deleteDatabase: jest.fn(),
                },
                configurable: true,
            });

            const hasIndexedDB = 'indexedDB' in window;
            expect(hasIndexedDB).toBe(true);
        });

        it('should detect BroadcastChannel support', () => {
            // Mock BroadcastChannel support
            Object.defineProperty(global.window, 'BroadcastChannel', {
                value: class MockBroadcastChannel {
                    constructor(name: string) { }
                    postMessage(data: any) { }
                    addEventListener(type: string, listener: Function) { }
                    close() { }
                },
                configurable: true,
            });

            const hasBroadcastChannel = 'BroadcastChannel' in window;
            expect(hasBroadcastChannel).toBe(true);
        });

        it('should detect Notification API support', () => {
            // Mock Notification API
            Object.defineProperty(global.window, 'Notification', {
                value: class MockNotification {
                    static permission = 'default';
                    static requestPermission = jest.fn();
                    constructor(title: string, options?: any) { }
                },
                configurable: true,
            });

            const hasNotifications = 'Notification' in window;
            expect(hasNotifications).toBe(true);
        });
    });

    describe('Browser-Specific Behavior', () => {
        it('should handle Chrome-specific features', () => {
            // Mock Chrome user agent
            Object.defineProperty(global.navigator, 'userAgent', {
                value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                configurable: true,
            });

            const isChrome = /Chrome/.test(navigator.userAgent);
            expect(isChrome).toBe(true);
        });

        it('should handle Safari-specific features', () => {
            // Mock Safari user agent
            Object.defineProperty(global.navigator, 'userAgent', {
                value: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                configurable: true,
            });

            const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);
            expect(isSafari).toBe(true);
        });
    });

    describe('Storage Compatibility', () => {
        it('should handle localStorage availability', () => {
            // Mock localStorage
            Object.defineProperty(global.window, 'localStorage', {
                value: {
                    getItem: jest.fn(),
                    setItem: jest.fn(),
                    removeItem: jest.fn(),
                    clear: jest.fn(),
                },
                configurable: true,
            });

            const hasLocalStorage = 'localStorage' in window;
            expect(hasLocalStorage).toBe(true);
        });
    });
});