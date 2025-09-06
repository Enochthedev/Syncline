// Browser Extension API for third-party integrations
export interface ExtensionMessage {
    type: string;
    payload: any;
    requestId?: string;
    source: 'remi-web' | 'extension';
}

export interface ExtensionAPI {
    // Contact operations
    searchContacts(query: string): Promise<any[]>;
    getContact(id: string): Promise<any>;
    createContact(contact: any): Promise<any>;
    updateContact(id: string, updates: any): Promise<any>;

    // Message operations
    searchMessages(query: string, filters?: any): Promise<any[]>;
    getMessage(id: string): Promise<any>;
    sendMessage(message: any): Promise<any>;

    // Search operations
    performSearch(query: string, options?: any): Promise<any>;
    saveSearch(query: string, name: string): Promise<any>;

    // Analytics operations
    getAnalytics(type: string, filters?: any): Promise<any>;
    exportData(type: string, format: string): Promise<Blob>;

    // Notification operations
    showNotification(notification: any): Promise<void>;
    requestPermissions(permissions: string[]): Promise<boolean>;

    // UI operations
    openModal(component: string, props?: any): Promise<void>;
    navigateTo(path: string): Promise<void>;
    focusSearch(): Promise<void>;
}

class ExtensionAPIManager implements ExtensionAPI {
    private messageHandlers = new Map<string, (payload: any) => Promise<any>>();
    private pendingRequests = new Map<string, { resolve: Function; reject: Function }>();
    private isInitialized = false;

    constructor() {
        this.init();
    }

    private init(): void {
        if (typeof window === 'undefined') return;

        // Listen for messages from extensions
        window.addEventListener('message', this.handleMessage.bind(this));

        // Register default handlers
        this.registerHandlers();

        // Expose API to window for extensions
        (window as any).remiAPI = this.createPublicAPI();

        this.isInitialized = true;
        console.log('Extension API initialized');
    }

    private handleMessage(event: MessageEvent): void {
        if (event.origin !== window.location.origin && !this.isTrustedOrigin(event.origin)) {
            return;
        }

        const message: ExtensionMessage = event.data;
        if (!message || message.source !== 'extension') {
            return;
        }

        this.processMessage(message);
    }

    private isTrustedOrigin(origin: string): boolean {
        // Add trusted extension origins here
        const trustedOrigins = [
            'chrome-extension://',
            'moz-extension://',
            'safari-web-extension://',
        ];

        return trustedOrigins.some(trusted => origin.startsWith(trusted));
    }

    private async processMessage(message: ExtensionMessage): Promise<void> {
        const { type, payload, requestId } = message;

        try {
            const handler = this.messageHandlers.get(type);
            if (!handler) {
                throw new Error(`Unknown message type: ${type}`);
            }

            const result = await handler(payload);

            if (requestId) {
                this.sendResponse(requestId, result);
            }
        } catch (error) {
            console.error('Extension API error:', error);
            if (requestId) {
                this.sendError(requestId, error);
            }
        }
    }

    private sendResponse(requestId: string, result: any): void {
        const response: ExtensionMessage = {
            type: 'response',
            payload: { requestId, result },
            source: 'remi-web',
        };

        window.postMessage(response, window.location.origin);
    }

    private sendError(requestId: string, error: any): void {
        const response: ExtensionMessage = {
            type: 'error',
            payload: {
                requestId,
                error: error.message || 'Unknown error',
                stack: error.stack
            },
            source: 'remi-web',
        };

        window.postMessage(response, window.location.origin);
    }

    private registerHandlers(): void {
        // Contact handlers
        this.messageHandlers.set('searchContacts', this.searchContacts.bind(this));
        this.messageHandlers.set('getContact', this.getContact.bind(this));
        this.messageHandlers.set('createContact', this.createContact.bind(this));
        this.messageHandlers.set('updateContact', this.updateContact.bind(this));

        // Message handlers
        this.messageHandlers.set('searchMessages', this.searchMessages.bind(this));
        this.messageHandlers.set('getMessage', this.getMessage.bind(this));
        this.messageHandlers.set('sendMessage', this.sendMessage.bind(this));

        // Search handlers
        this.messageHandlers.set('performSearch', this.performSearch.bind(this));
        this.messageHandlers.set('saveSearch', this.saveSearch.bind(this));

        // Analytics handlers
        this.messageHandlers.set('getAnalytics', this.getAnalytics.bind(this));
        this.messageHandlers.set('exportData', this.exportData.bind(this));

        // Notification handlers
        this.messageHandlers.set('showNotification', this.showNotification.bind(this));
        this.messageHandlers.set('requestPermissions', this.requestPermissions.bind(this));

        // UI handlers
        this.messageHandlers.set('openModal', this.openModal.bind(this));
        this.messageHandlers.set('navigateTo', this.navigateTo.bind(this));
        this.messageHandlers.set('focusSearch', this.focusSearch.bind(this));
    }

    private createPublicAPI(): any {
        return {
            version: '1.0.0',

            // Contact operations
            contacts: {
                search: (query: string) => this.makeRequest('searchContacts', { query }),
                get: (id: string) => this.makeRequest('getContact', { id }),
                create: (contact: any) => this.makeRequest('createContact', { contact }),
                update: (id: string, updates: any) => this.makeRequest('updateContact', { id, updates }),
            },

            // Message operations
            messages: {
                search: (query: string, filters?: any) => this.makeRequest('searchMessages', { query, filters }),
                get: (id: string) => this.makeRequest('getMessage', { id }),
                send: (message: any) => this.makeRequest('sendMessage', { message }),
            },

            // Search operations
            search: {
                perform: (query: string, options?: any) => this.makeRequest('performSearch', { query, options }),
                save: (query: string, name: string) => this.makeRequest('saveSearch', { query, name }),
            },

            // Analytics operations
            analytics: {
                get: (type: string, filters?: any) => this.makeRequest('getAnalytics', { type, filters }),
                export: (type: string, format: string) => this.makeRequest('exportData', { type, format }),
            },

            // Notification operations
            notifications: {
                show: (notification: any) => this.makeRequest('showNotification', { notification }),
                requestPermissions: (permissions: string[]) => this.makeRequest('requestPermissions', { permissions }),
            },

            // UI operations
            ui: {
                openModal: (component: string, props?: any) => this.makeRequest('openModal', { component, props }),
                navigateTo: (path: string) => this.makeRequest('navigateTo', { path }),
                focusSearch: () => this.makeRequest('focusSearch', {}),
            },

            // Event system
            on: (event: string, callback: Function) => this.addEventListener(event, callback),
            off: (event: string, callback: Function) => this.removeEventListener(event, callback),
            emit: (event: string, data: any) => this.emitEvent(event, data),
        };
    }

    private makeRequest(type: string, payload: any): Promise<any> {
        return new Promise((resolve, reject) => {
            const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

            this.pendingRequests.set(requestId, { resolve, reject });

            const message: ExtensionMessage = {
                type,
                payload,
                requestId,
                source: 'extension',
            };

            // Simulate extension message
            setTimeout(() => {
                this.processMessage(message);
            }, 0);

            // Timeout after 30 seconds
            setTimeout(() => {
                if (this.pendingRequests.has(requestId)) {
                    this.pendingRequests.delete(requestId);
                    reject(new Error('Request timeout'));
                }
            }, 30000);
        });
    }

    // API Implementation
    async searchContacts(payload: { query: string }): Promise<any[]> {
        // This would integrate with your contact search service
        const response = await fetch(`/api/contacts/search?q=${encodeURIComponent(payload.query)}`);
        return response.json();
    }

    async getContact(payload: { id: string }): Promise<any> {
        const response = await fetch(`/api/contacts/${payload.id}`);
        return response.json();
    }

    async createContact(payload: { contact: any }): Promise<any> {
        const response = await fetch('/api/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload.contact),
        });
        return response.json();
    }

    async updateContact(payload: { id: string; updates: any }): Promise<any> {
        const response = await fetch(`/api/contacts/${payload.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload.updates),
        });
        return response.json();
    }

    async searchMessages(payload: { query: string; filters?: any }): Promise<any[]> {
        const params = new URLSearchParams({ q: payload.query });
        if (payload.filters) {
            Object.entries(payload.filters).forEach(([key, value]) => {
                params.append(key, String(value));
            });
        }

        const response = await fetch(`/api/messages/search?${params}`);
        return response.json();
    }

    async getMessage(payload: { id: string }): Promise<any> {
        const response = await fetch(`/api/messages/${payload.id}`);
        return response.json();
    }

    async sendMessage(payload: { message: any }): Promise<any> {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload.message),
        });
        return response.json();
    }

    async performSearch(payload: { query: string; options?: any }): Promise<any> {
        const params = new URLSearchParams({ q: payload.query });
        if (payload.options) {
            Object.entries(payload.options).forEach(([key, value]) => {
                params.append(key, String(value));
            });
        }

        const response = await fetch(`/api/search?${params}`);
        return response.json();
    }

    async saveSearch(payload: { query: string; name: string }): Promise<any> {
        const response = await fetch('/api/searches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: payload.query, name: payload.name }),
        });
        return response.json();
    }

    async getAnalytics(payload: { type: string; filters?: any }): Promise<any> {
        const params = new URLSearchParams({ type: payload.type });
        if (payload.filters) {
            Object.entries(payload.filters).forEach(([key, value]) => {
                params.append(key, String(value));
            });
        }

        const response = await fetch(`/api/analytics?${params}`);
        return response.json();
    }

    async exportData(payload: { type: string; format: string }): Promise<Blob> {
        const response = await fetch(`/api/export/${payload.type}?format=${payload.format}`);
        return response.blob();
    }

    async showNotification(payload: { notification: any }): Promise<void> {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(payload.notification.title, {
                body: payload.notification.body,
                icon: payload.notification.icon,
                tag: payload.notification.tag,
            });
        }
    }

    async requestPermissions(payload: { permissions: string[] }): Promise<boolean> {
        const results = await Promise.all(
            payload.permissions.map(async (permission) => {
                switch (permission) {
                    case 'notifications':
                        if ('Notification' in window) {
                            const result = await Notification.requestPermission();
                            return result === 'granted';
                        }
                        return false;
                    default:
                        return false;
                }
            })
        );

        return results.every(Boolean);
    }

    async openModal(payload: { component: string; props?: any }): Promise<void> {
        // This would integrate with your modal system
        window.dispatchEvent(new CustomEvent('remi:openModal', {
            detail: { component: payload.component, props: payload.props }
        }));
    }

    async navigateTo(payload: { path: string }): Promise<void> {
        window.location.href = payload.path;
    }

    async focusSearch(): Promise<void> {
        const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement;
        if (searchInput) {
            searchInput.focus();
        }
    }

    // Event system for extensions
    private eventListeners = new Map<string, Set<Function>>();

    private addEventListener(event: string, callback: Function): void {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, new Set());
        }
        this.eventListeners.get(event)!.add(callback);
    }

    private removeEventListener(event: string, callback: Function): void {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.delete(callback);
        }
    }

    private emitEvent(event: string, data: any): void {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Extension event listener error:', error);
                }
            });
        }
    }

    // Public methods for the app to emit events to extensions
    public notifyExtensions(event: string, data: any): void {
        this.emitEvent(event, data);

        // Also send as window message for extensions listening that way
        const message: ExtensionMessage = {
            type: 'event',
            payload: { event, data },
            source: 'remi-web',
        };

        window.postMessage(message, window.location.origin);
    }
}

// Create singleton instance
export const extensionAPI = new ExtensionAPIManager();

// Hook for React components to interact with extensions
export function useExtensionAPI() {
    const notifyExtensions = (event: string, data: any) => {
        extensionAPI.notifyExtensions(event, data);
    };

    return {
        notifyExtensions,
    };
}