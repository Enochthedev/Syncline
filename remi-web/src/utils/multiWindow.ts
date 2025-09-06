// Multi-window support and cross-tab communication
interface WindowMessage {
    type: string;
    payload: any;
    timestamp: number;
    windowId: string;
    source: 'remi-web';
}

interface WindowState {
    id: string;
    url: string;
    title: string;
    isActive: boolean;
    lastActivity: number;
    features: string[];
}

interface SyncData {
    contacts: any[];
    searchResults: any[];
    userPreferences: any;
    authState: any;
    notifications: any[];
}

class MultiWindowManager {
    private windowId: string;
    private windows = new Map<string, WindowState>();
    private messageHandlers = new Map<string, (payload: any, source: string) => void>();
    private syncData: Partial<SyncData> = {};
    private broadcastChannel: BroadcastChannel | null = null;
    private storageListener: ((e: StorageEvent) => void) | null = null;

    constructor() {
        this.windowId = `window_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        this.init();
    }

    private init(): void {
        if (typeof window === 'undefined') return;

        // Initialize BroadcastChannel for modern browsers
        if ('BroadcastChannel' in window) {
            this.broadcastChannel = new BroadcastChannel('remi-windows');
            this.broadcastChannel.addEventListener('message', this.handleBroadcastMessage.bind(this));
        }

        // Fallback to localStorage events for older browsers
        this.storageListener = this.handleStorageEvent.bind(this);
        window.addEventListener('storage', this.storageListener);

        // Register this window
        this.registerWindow();

        // Set up periodic cleanup
        setInterval(this.cleanupInactiveWindows.bind(this), 30000); // 30 seconds

        // Handle window close
        window.addEventListener('beforeunload', this.handleWindowClose.bind(this));

        // Handle visibility change
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));

        // Register default message handlers
        this.registerDefaultHandlers();

        console.log(`Multi-window manager initialized for window: ${this.windowId}`);
    }

    private registerWindow(): void {
        const windowState: WindowState = {
            id: this.windowId,
            url: window.location.href,
            title: document.title,
            isActive: !document.hidden,
            lastActivity: Date.now(),
            features: this.detectFeatures(),
        };

        this.windows.set(this.windowId, windowState);
        this.broadcastToOtherWindows('WINDOW_REGISTERED', windowState);
        this.updateStorageWindowList();
    }

    private detectFeatures(): string[] {
        const features: string[] = [];

        if ('serviceWorker' in navigator) features.push('serviceWorker');
        if ('Notification' in window) features.push('notifications');
        if ('BroadcastChannel' in window) features.push('broadcastChannel');
        if ('indexedDB' in window) features.push('indexedDB');
        if ('WebSocket' in window) features.push('webSocket');

        return features;
    }

    private handleBroadcastMessage(event: MessageEvent): void {
        const message: WindowMessage = event.data;
        if (message.source !== 'remi-web' || message.windowId === this.windowId) {
            return;
        }

        this.processMessage(message);
    }

    private handleStorageEvent(event: StorageEvent): void {
        if (event.key === 'remi-window-message' && event.newValue) {
            try {
                const message: WindowMessage = JSON.parse(event.newValue);
                if (message.windowId !== this.windowId) {
                    this.processMessage(message);
                }
            } catch (error) {
                console.error('Failed to parse storage message:', error);
            }
        }
    }

    private processMessage(message: WindowMessage): void {
        const { type, payload, windowId } = message;

        // Update window state if it's a window-related message
        if (type === 'WINDOW_REGISTERED' || type === 'WINDOW_UPDATED') {
            this.windows.set(windowId, payload);
        } else if (type === 'WINDOW_CLOSED') {
            this.windows.delete(windowId);
        }

        // Handle the message
        const handler = this.messageHandlers.get(type);
        if (handler) {
            handler(payload, windowId);
        }

        // Emit custom event for React components
        window.dispatchEvent(new CustomEvent('multi-window-message', {
            detail: { type, payload, windowId }
        }));
    }

    private registerDefaultHandlers(): void {
        // Sync data handlers
        this.messageHandlers.set('SYNC_CONTACTS', (contacts) => {
            this.syncData.contacts = contacts;
            this.notifyComponents('contacts-synced', contacts);
        });

        this.messageHandlers.set('SYNC_SEARCH_RESULTS', (results) => {
            this.syncData.searchResults = results;
            this.notifyComponents('search-results-synced', results);
        });

        this.messageHandlers.set('SYNC_USER_PREFERENCES', (preferences) => {
            this.syncData.userPreferences = preferences;
            this.notifyComponents('preferences-synced', preferences);
        });

        this.messageHandlers.set('SYNC_AUTH_STATE', (authState) => {
            this.syncData.authState = authState;
            this.notifyComponents('auth-state-synced', authState);
        });

        this.messageHandlers.set('SYNC_NOTIFICATIONS', (notifications) => {
            this.syncData.notifications = notifications;
            this.notifyComponents('notifications-synced', notifications);
        });

        // Window management handlers
        this.messageHandlers.set('FOCUS_WINDOW', (payload, sourceWindowId) => {
            if (payload.targetWindowId === this.windowId) {
                window.focus();
            }
        });

        this.messageHandlers.set('NAVIGATE_WINDOW', (payload, sourceWindowId) => {
            if (payload.targetWindowId === this.windowId) {
                window.location.href = payload.url;
            }
        });

        this.messageHandlers.set('CLOSE_WINDOW', (payload, sourceWindowId) => {
            if (payload.targetWindowId === this.windowId) {
                window.close();
            }
        });

        // Feature coordination
        this.messageHandlers.set('REQUEST_FEATURE_LOCK', (payload, sourceWindowId) => {
            this.handleFeatureLockRequest(payload, sourceWindowId);
        });

        this.messageHandlers.set('RELEASE_FEATURE_LOCK', (payload, sourceWindowId) => {
            this.handleFeatureLockRelease(payload, sourceWindowId);
        });
    }

    private handleFeatureLockRequest(payload: { feature: string; requestId: string }, sourceWindowId: string): void {
        // Simple feature locking mechanism (e.g., for background sync)
        const lockKey = `feature-lock-${payload.feature}`;
        const existingLock = localStorage.getItem(lockKey);

        if (!existingLock || JSON.parse(existingLock).windowId === this.windowId) {
            const lock = {
                windowId: sourceWindowId,
                timestamp: Date.now(),
                requestId: payload.requestId,
            };

            localStorage.setItem(lockKey, JSON.stringify(lock));

            this.sendToWindow(sourceWindowId, 'FEATURE_LOCK_GRANTED', {
                feature: payload.feature,
                requestId: payload.requestId,
            });
        } else {
            this.sendToWindow(sourceWindowId, 'FEATURE_LOCK_DENIED', {
                feature: payload.feature,
                requestId: payload.requestId,
                currentOwner: JSON.parse(existingLock).windowId,
            });
        }
    }

    private handleFeatureLockRelease(payload: { feature: string }, sourceWindowId: string): void {
        const lockKey = `feature-lock-${payload.feature}`;
        const existingLock = localStorage.getItem(lockKey);

        if (existingLock) {
            const lock = JSON.parse(existingLock);
            if (lock.windowId === sourceWindowId) {
                localStorage.removeItem(lockKey);
            }
        }
    }

    private handleWindowClose(): void {
        this.broadcastToOtherWindows('WINDOW_CLOSED', { windowId: this.windowId });
        this.windows.delete(this.windowId);
        this.updateStorageWindowList();

        // Clean up resources
        if (this.broadcastChannel) {
            this.broadcastChannel.close();
        }

        if (this.storageListener) {
            window.removeEventListener('storage', this.storageListener);
        }
    }

    private handleVisibilityChange(): void {
        const windowState = this.windows.get(this.windowId);
        if (windowState) {
            windowState.isActive = !document.hidden;
            windowState.lastActivity = Date.now();
            this.windows.set(this.windowId, windowState);
            this.broadcastToOtherWindows('WINDOW_UPDATED', windowState);
        }
    }

    private cleanupInactiveWindows(): void {
        const now = Date.now();
        const timeout = 5 * 60 * 1000; // 5 minutes

        for (const [windowId, windowState] of this.windows.entries()) {
            if (windowId !== this.windowId && now - windowState.lastActivity > timeout) {
                this.windows.delete(windowId);
            }
        }

        this.updateStorageWindowList();
    }

    private updateStorageWindowList(): void {
        const windowList = Array.from(this.windows.values());
        localStorage.setItem('remi-active-windows', JSON.stringify(windowList));
    }

    private broadcastToOtherWindows(type: string, payload: any): void {
        const message: WindowMessage = {
            type,
            payload,
            timestamp: Date.now(),
            windowId: this.windowId,
            source: 'remi-web',
        };

        // Use BroadcastChannel if available
        if (this.broadcastChannel) {
            this.broadcastChannel.postMessage(message);
        }

        // Fallback to localStorage
        localStorage.setItem('remi-window-message', JSON.stringify(message));
        // Clear immediately to trigger storage event
        setTimeout(() => {
            localStorage.removeItem('remi-window-message');
        }, 100);
    }

    private sendToWindow(targetWindowId: string, type: string, payload: any): void {
        this.broadcastToOtherWindows(type, { ...payload, targetWindowId });
    }

    private notifyComponents(event: string, data: any): void {
        window.dispatchEvent(new CustomEvent(`multi-window-${event}`, {
            detail: data
        }));
    }

    // Public API
    public getActiveWindows(): WindowState[] {
        return Array.from(this.windows.values());
    }

    public getCurrentWindowId(): string {
        return this.windowId;
    }

    public syncContacts(contacts: any[]): void {
        this.syncData.contacts = contacts;
        this.broadcastToOtherWindows('SYNC_CONTACTS', contacts);
    }

    public syncSearchResults(results: any[]): void {
        this.syncData.searchResults = results;
        this.broadcastToOtherWindows('SYNC_SEARCH_RESULTS', results);
    }

    public syncUserPreferences(preferences: any): void {
        this.syncData.userPreferences = preferences;
        this.broadcastToOtherWindows('SYNC_USER_PREFERENCES', preferences);
    }

    public syncAuthState(authState: any): void {
        this.syncData.authState = authState;
        this.broadcastToOtherWindows('SYNC_AUTH_STATE', authState);
    }

    public syncNotifications(notifications: any[]): void {
        this.syncData.notifications = notifications;
        this.broadcastToOtherWindows('SYNC_NOTIFICATIONS', notifications);
    }

    public openNewWindow(url: string, features?: string): Window | null {
        const newWindow = window.open(url, '_blank', features);

        if (newWindow) {
            // Wait for the new window to register itself
            setTimeout(() => {
                const windows = this.getActiveWindows();
                const newestWindow = windows.find(w => w.url === url && w.id !== this.windowId);
                if (newestWindow) {
                    this.notifyComponents('window-opened', newestWindow);
                }
            }, 1000);
        }

        return newWindow;
    }

    public focusWindow(windowId: string): void {
        this.sendToWindow(windowId, 'FOCUS_WINDOW', { targetWindowId: windowId });
    }

    public navigateWindow(windowId: string, url: string): void {
        this.sendToWindow(windowId, 'NAVIGATE_WINDOW', { targetWindowId: windowId, url });
    }

    public closeWindow(windowId: string): void {
        this.sendToWindow(windowId, 'CLOSE_WINDOW', { targetWindowId: windowId });
    }

    public requestFeatureLock(feature: string): Promise<boolean> {
        return new Promise((resolve) => {
            const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

            const handleResponse = (event: CustomEvent) => {
                const { type, payload } = event.detail;
                if (payload.requestId === requestId) {
                    window.removeEventListener('multi-window-message', handleResponse as EventListener);
                    resolve(type === 'FEATURE_LOCK_GRANTED');
                }
            };

            window.addEventListener('multi-window-message', handleResponse as EventListener);

            this.broadcastToOtherWindows('REQUEST_FEATURE_LOCK', { feature, requestId });

            // Timeout after 5 seconds
            setTimeout(() => {
                window.removeEventListener('multi-window-message', handleResponse as EventListener);
                resolve(false);
            }, 5000);
        });
    }

    public releaseFeatureLock(feature: string): void {
        this.broadcastToOtherWindows('RELEASE_FEATURE_LOCK', { feature });
    }

    public onMessage(type: string, handler: (payload: any, sourceWindowId: string) => void): void {
        this.messageHandlers.set(type, handler);
    }

    public offMessage(type: string): void {
        this.messageHandlers.delete(type);
    }

    public getSyncData(): Partial<SyncData> {
        return { ...this.syncData };
    }
}

// Create singleton instance
export const multiWindowManager = new MultiWindowManager();

// React hook for multi-window functionality
export function useMultiWindow() {
    const [activeWindows, setActiveWindows] = React.useState<WindowState[]>([]);
    const [syncData, setSyncData] = React.useState<Partial<SyncData>>({});

    React.useEffect(() => {
        // Update active windows list
        const updateWindows = () => {
            setActiveWindows(multiWindowManager.getActiveWindows());
        };

        // Update sync data
        const updateSyncData = () => {
            setSyncData(multiWindowManager.getSyncData());
        };

        // Listen for window changes
        const handleWindowMessage = (event: CustomEvent) => {
            const { type } = event.detail;
            if (type.includes('WINDOW_')) {
                updateWindows();
            }
            if (type.includes('SYNC_')) {
                updateSyncData();
            }
        };

        window.addEventListener('multi-window-message', handleWindowMessage as EventListener);

        // Initial update
        updateWindows();
        updateSyncData();

        return () => {
            window.removeEventListener('multi-window-message', handleWindowMessage as EventListener);
        };
    }, []);

    const openWindow = React.useCallback((url: string, features?: string) => {
        return multiWindowManager.openNewWindow(url, features);
    }, []);

    const focusWindow = React.useCallback((windowId: string) => {
        multiWindowManager.focusWindow(windowId);
    }, []);

    const closeWindow = React.useCallback((windowId: string) => {
        multiWindowManager.closeWindow(windowId);
    }, []);

    const syncContacts = React.useCallback((contacts: any[]) => {
        multiWindowManager.syncContacts(contacts);
    }, []);

    const syncSearchResults = React.useCallback((results: any[]) => {
        multiWindowManager.syncSearchResults(results);
    }, []);

    return {
        activeWindows,
        syncData,
        currentWindowId: multiWindowManager.getCurrentWindowId(),
        openWindow,
        focusWindow,
        closeWindow,
        syncContacts,
        syncSearchResults,
        multiWindowManager,
    };
}

// Import React for the hook
import React from 'react';