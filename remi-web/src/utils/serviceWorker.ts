// Enhanced Service Worker utilities for PWA functionality
import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface OfflineDB extends DBSchema {
    contacts: {
        key: string;
        value: {
            id: string;
            data: any;
            timestamp: number;
            version: number;
        };
    };
    messages: {
        key: string;
        value: {
            id: string;
            threadId: string;
            data: any;
            timestamp: number;
        };
    };
    searchCache: {
        key: string;
        value: {
            query: string;
            results: any[];
            timestamp: number;
            expiresAt: number;
        };
    };
    syncQueue: {
        key: string;
        value: {
            id: string;
            action: 'create' | 'update' | 'delete';
            resource: string;
            data: any;
            timestamp: number;
            retryCount: number;
        };
    };
}

class ServiceWorkerManager {
    private db: IDBPDatabase<OfflineDB> | null = null;
    private isOnline = navigator.onLine;
    private syncInProgress = false;

    async init(): Promise<void> {
        // Initialize IndexedDB
        this.db = await openDB<OfflineDB>('remi-offline', 1, {
            upgrade(db) {
                // Contacts store
                if (!db.objectStoreNames.contains('contacts')) {
                    const contactsStore = db.createObjectStore('contacts', { keyPath: 'id' });
                    contactsStore.createIndex('timestamp', 'timestamp');
                }

                // Messages store
                if (!db.objectStoreNames.contains('messages')) {
                    const messagesStore = db.createObjectStore('messages', { keyPath: 'id' });
                    messagesStore.createIndex('threadId', 'threadId');
                    messagesStore.createIndex('timestamp', 'timestamp');
                }

                // Search cache store
                if (!db.objectStoreNames.contains('searchCache')) {
                    const searchStore = db.createObjectStore('searchCache', { keyPath: 'query' });
                    searchStore.createIndex('timestamp', 'timestamp');
                }

                // Sync queue store
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id' });
                    syncStore.createIndex('timestamp', 'timestamp');
                    syncStore.createIndex('resource', 'resource');
                }
            },
        });

        // Listen for online/offline events
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));

        // Register service worker
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker registered:', registration);

                // Listen for service worker messages
                navigator.serviceWorker.addEventListener('message', this.handleSWMessage.bind(this));

                // Check for updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    if (newWorker) {
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                this.showUpdateAvailable();
                            }
                        });
                    }
                });
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }

        // Start periodic sync if online
        if (this.isOnline) {
            this.startPeriodicSync();
        }
    }

    private handleOnline(): void {
        this.isOnline = true;
        console.log('App is online');
        this.processSyncQueue();
        this.startPeriodicSync();
        this.broadcastConnectionStatus(true);
    }

    private handleOffline(): void {
        this.isOnline = false;
        console.log('App is offline');
        this.broadcastConnectionStatus(false);
    }

    private handleSWMessage(event: MessageEvent): void {
        const { type, payload } = event.data;

        switch (type) {
            case 'CACHE_UPDATED':
                this.broadcastCacheUpdate(payload);
                break;
            case 'BACKGROUND_SYNC':
                this.processSyncQueue();
                break;
            case 'PUSH_NOTIFICATION':
                this.handlePushNotification(payload);
                break;
        }
    }

    // Offline data management
    async cacheContact(contact: any): Promise<void> {
        if (!this.db) return;

        await this.db.put('contacts', {
            id: contact.id,
            data: contact,
            timestamp: Date.now(),
            version: contact.version || 1,
        });
    }

    async getCachedContact(id: string): Promise<any | null> {
        if (!this.db) return null;

        const cached = await this.db.get('contacts', id);
        return cached?.data || null;
    }

    async cacheSearchResults(query: string, results: any[]): Promise<void> {
        if (!this.db) return;

        await this.db.put('searchCache', {
            query,
            results,
            timestamp: Date.now(),
            expiresAt: Date.now() + (24 * 60 * 60 * 1000), // 24 hours
        });
    }

    async getCachedSearchResults(query: string): Promise<any[] | null> {
        if (!this.db) return null;

        const cached = await this.db.get('searchCache', query);
        if (!cached || cached.expiresAt < Date.now()) {
            return null;
        }

        return cached.results;
    }

    // Sync queue management
    async queueAction(action: string, resource: string, data: any): Promise<void> {
        if (!this.db) return;

        const id = `${resource}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        await this.db.put('syncQueue', {
            id,
            action: action as any,
            resource,
            data,
            timestamp: Date.now(),
            retryCount: 0,
        });

        // Try to sync immediately if online
        if (this.isOnline) {
            this.processSyncQueue();
        }
    }

    private async processSyncQueue(): Promise<void> {
        if (!this.db || this.syncInProgress || !this.isOnline) return;

        this.syncInProgress = true;

        try {
            const queuedItems = await this.db.getAll('syncQueue');

            for (const item of queuedItems) {
                try {
                    await this.syncItem(item);
                    await this.db.delete('syncQueue', item.id);
                } catch (error) {
                    console.error('Sync failed for item:', item.id, error);

                    // Increment retry count
                    item.retryCount++;

                    // Remove item if too many retries
                    if (item.retryCount > 3) {
                        await this.db.delete('syncQueue', item.id);
                    } else {
                        await this.db.put('syncQueue', item);
                    }
                }
            }
        } finally {
            this.syncInProgress = false;
        }
    }

    private async syncItem(item: any): Promise<void> {
        const { action, resource, data } = item;

        // This would integrate with your API client
        const response = await fetch(`/api/${resource}`, {
            method: action === 'create' ? 'POST' : action === 'update' ? 'PUT' : 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
            },
            body: action !== 'delete' ? JSON.stringify(data) : undefined,
        });

        if (!response.ok) {
            throw new Error(`Sync failed: ${response.statusText}`);
        }
    }

    private startPeriodicSync(): void {
        // Background sync every 5 minutes
        setInterval(() => {
            if (this.isOnline) {
                this.processSyncQueue();
            }
        }, 5 * 60 * 1000);
    }

    // PWA installation
    async checkInstallPrompt(): Promise<boolean> {
        return 'beforeinstallprompt' in window;
    }

    async showInstallPrompt(): Promise<boolean> {
        const deferredPrompt = (window as any).deferredPrompt;

        if (!deferredPrompt) {
            return false;
        }

        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;

        (window as any).deferredPrompt = null;

        return outcome === 'accepted';
    }

    // Update management
    private showUpdateAvailable(): void {
        this.broadcastMessage('UPDATE_AVAILABLE', {
            message: 'A new version is available. Refresh to update.',
        });
    }

    async applyUpdate(): Promise<void> {
        if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.getRegistration();
            if (registration?.waiting) {
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                window.location.reload();
            }
        }
    }

    // Communication
    private broadcastMessage(type: string, payload: any): void {
        window.dispatchEvent(new CustomEvent('sw-message', {
            detail: { type, payload }
        }));
    }

    private broadcastConnectionStatus(isOnline: boolean): void {
        this.broadcastMessage('CONNECTION_STATUS', { isOnline });
    }

    private broadcastCacheUpdate(payload: any): void {
        this.broadcastMessage('CACHE_UPDATED', payload);
    }

    private handlePushNotification(payload: any): void {
        this.broadcastMessage('PUSH_NOTIFICATION', payload);
    }

    // Cleanup
    async cleanup(): Promise<void> {
        if (!this.db) return;

        const now = Date.now();
        const oneWeekAgo = now - (7 * 24 * 60 * 60 * 1000);

        // Clean old search cache
        const tx = this.db.transaction('searchCache', 'readwrite');
        const index = tx.store.index('timestamp');

        for await (const cursor of index.iterate()) {
            if (cursor.value.timestamp < oneWeekAgo) {
                cursor.delete();
            }
        }

        await tx.done;
    }
}

export const serviceWorkerManager = new ServiceWorkerManager();

// Initialize on load
if (typeof window !== 'undefined') {
    serviceWorkerManager.init().catch(console.error);
}