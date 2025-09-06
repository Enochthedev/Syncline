/**
 * Unified Business Logic Service - Web Implementation
 * Shared business logic between React Native and Web applications
 * Web-specific implementation with browser optimizations
 */

import { Contact, Message, SearchResult, ConversationThread, ProactiveInsight } from '@/types'
import { contactSearchService } from './contactSearchService'
import { apiClient } from './apiClient'

export interface UnifiedBusinessLogicConfig {
    apiBaseUrl: string
    enableOfflineMode: boolean
    enableRealTimeSync: boolean
    enableProactiveInsights: boolean
    maxCacheSize: number
    syncInterval: number
}

export interface SearchWorkflowResult {
    contacts: Contact[]
    messages: Message[]
    threads: ConversationThread[]
    insights: ProactiveInsight[]
    totalResults: number
    processingTime: number
}

export interface OnboardingFlowState {
    currentStep: number
    totalSteps: number
    completedSteps: string[]
    platformConnections: PlatformConnection[]
    userPreferences: UserPreferences
}

export interface PlatformConnection {
    id: string
    platform: string
    status: 'connected' | 'disconnected' | 'error' | 'pending'
    lastSync: Date | null
    errorMessage?: string
    capabilities: string[]
}

export interface UserPreferences {
    notifications: NotificationPreferences
    privacy: PrivacyPreferences
    sync: SyncPreferences
    ui: UIPreferences
}

export interface NotificationPreferences {
    enabled: boolean
    types: string[]
    quietHours: { start: string; end: string }
    channels: string[]
}

export interface PrivacyPreferences {
    dataProcessing: boolean
    aiAnalysis: boolean
    piiRedaction: boolean
    dataSharing: boolean
}

export interface SyncPreferences {
    autoSync: boolean
    syncInterval: number
    backgroundSync: boolean
    wifiOnly: boolean
}

export interface UIPreferences {
    theme: 'light' | 'dark' | 'auto'
    language: string
    accessibility: AccessibilityPreferences
}

export interface AccessibilityPreferences {
    screenReader: boolean
    highContrast: boolean
    largeText: boolean
    voiceControl: boolean
}

class UnifiedBusinessLogicService {
    private config: UnifiedBusinessLogicConfig
    private onboardingState: OnboardingFlowState | null = null
    private searchCache = new Map<string, SearchWorkflowResult>()
    private readonly CACHE_TTL = 5 * 60 * 1000 // 5 minutes
    private websocket: WebSocket | null = null
    private serviceWorker: ServiceWorkerRegistration | null = null

    constructor(config: UnifiedBusinessLogicConfig) {
        this.config = config
    }

    /**
     * Initialize the unified business logic service
     */
    async initialize(): Promise<void> {
        try {
            // Initialize API client
            await apiClient.initialize()

            // Initialize contact search service
            await contactSearchService.initialize()

            // Set up service worker for offline support
            if (this.config.enableOfflineMode && 'serviceWorker' in navigator) {
                await this.setupServiceWorker()
            }

            // Set up real-time sync if enabled
            if (this.config.enableRealTimeSync) {
                await this.setupRealTimeSync()
            }

            // Set up proactive insights if enabled
            if (this.config.enableProactiveInsights) {
                await this.setupProactiveInsights()
            }

            // Load onboarding state from localStorage
            await this.loadOnboardingState()

            console.log('Unified business logic service initialized successfully')
        } catch (error) {
            console.error('Failed to initialize unified business logic service:', error)
            throw error
        }
    }

    /**
     * Execute end-to-end contact-based search workflow
     */
    async executeContactSearchWorkflow(
        query: string,
        options: {
            includeNaturalLanguage?: boolean
            includeInsights?: boolean
            useCache?: boolean
            maxResults?: number
        } = {}
    ): Promise<SearchWorkflowResult> {
        const startTime = Date.now()
        const cacheKey = `${query}-${JSON.stringify(options)}`

        // Check cache first if enabled
        if (options.useCache !== false && this.searchCache.has(cacheKey)) {
            const cached = this.searchCache.get(cacheKey)!
            if (Date.now() - cached.processingTime < this.CACHE_TTL) {
                return cached
            }
        }

        try {
            // Step 1: Parse query and determine intent
            const parsedQuery = options.includeNaturalLanguage
                ? await this.parseNaturalLanguageQuery(query)
                : { text: query, intent: 'general', entities: [] }

            // Step 2: Search contacts based on query
            const contacts = await contactSearchService.searchContacts(query, {
                fuzzyMatch: true,
                includeMetadata: true,
                maxResults: options.maxResults || 50
            })

            // Step 3: Search messages and threads
            const [messages, threads] = await Promise.all([
                this.searchMessages(query, {
                    contactFilter: contacts.map(c => c.id),
                    includeContent: true,
                    maxResults: options.maxResults || 100
                }),
                this.searchThreads(query, {
                    contactFilter: contacts.map(c => c.id),
                    includePreview: true,
                    maxResults: options.maxResults || 50
                })
            ])

            // Step 4: Get proactive insights if enabled
            const insights = options.includeInsights
                ? await this.getProactiveInsights({
                    contacts: contacts.map(c => c.id),
                    query: parsedQuery.text,
                    intent: parsedQuery.intent
                })
                : []

            const result: SearchWorkflowResult = {
                contacts,
                messages,
                threads,
                insights,
                totalResults: contacts.length + messages.length + threads.length,
                processingTime: Date.now() - startTime
            }

            // Cache the result
            this.searchCache.set(cacheKey, result)

            // Clean up old cache entries
            this.cleanupCache()

            return result
        } catch (error) {
            console.error('Contact search workflow failed:', error)
            throw error
        }
    }

    /**
     * Initialize user onboarding flow
     */
    async initializeOnboardingFlow(): Promise<OnboardingFlowState> {
        const onboardingSteps = [
            'welcome',
            'permissions',
            'platform-connections',
            'preferences',
            'demo',
            'complete'
        ]

        this.onboardingState = {
            currentStep: 0,
            totalSteps: onboardingSteps.length,
            completedSteps: [],
            platformConnections: [],
            userPreferences: this.getDefaultUserPreferences()
        }

        await this.saveOnboardingState()
        return this.onboardingState
    }

    /**
     * Progress through onboarding flow
     */
    async progressOnboardingStep(
        stepId: string,
        data?: any
    ): Promise<OnboardingFlowState> {
        if (!this.onboardingState) {
            throw new Error('Onboarding flow not initialized')
        }

        // Process step-specific data
        switch (stepId) {
            case 'platform-connections':
                if (data?.connections) {
                    this.onboardingState.platformConnections = data.connections
                }
                break
            case 'preferences':
                if (data?.preferences) {
                    this.onboardingState.userPreferences = {
                        ...this.onboardingState.userPreferences,
                        ...data.preferences
                    }
                }
                break
        }

        // Mark step as completed
        if (!this.onboardingState.completedSteps.includes(stepId)) {
            this.onboardingState.completedSteps.push(stepId)
        }

        // Progress to next step
        this.onboardingState.currentStep = Math.min(
            this.onboardingState.currentStep + 1,
            this.onboardingState.totalSteps - 1
        )

        // Save onboarding state
        await this.saveOnboardingState()

        return this.onboardingState
    }

    /**
     * Connect to a platform during onboarding
     */
    async connectPlatform(
        platform: string,
        credentials: any
    ): Promise<PlatformConnection> {
        try {
            // Attempt platform connection via API
            const response = await apiClient.post('/api/platforms/connect', {
                platform,
                credentials
            })

            const connection: PlatformConnection = {
                id: response.data.id,
                platform,
                status: 'connected',
                lastSync: new Date(response.data.lastSync),
                capabilities: response.data.capabilities
            }

            // Update onboarding state
            if (this.onboardingState) {
                const existingIndex = this.onboardingState.platformConnections
                    .findIndex(c => c.platform === platform)

                if (existingIndex >= 0) {
                    this.onboardingState.platformConnections[existingIndex] = connection
                } else {
                    this.onboardingState.platformConnections.push(connection)
                }

                await this.saveOnboardingState()
            }

            // Trigger initial sync
            await this.performInitialSync(platform)

            return connection
        } catch (error) {
            console.error(`Failed to connect to ${platform}:`, error)

            const errorConnection: PlatformConnection = {
                id: `${platform}-${Date.now()}`,
                platform,
                status: 'error',
                lastSync: null,
                errorMessage: error instanceof Error ? error.message : 'Unknown error',
                capabilities: []
            }

            if (this.onboardingState) {
                this.onboardingState.platformConnections.push(errorConnection)
                await this.saveOnboardingState()
            }

            throw error
        }
    }

    /**
     * Perform comprehensive cross-platform synchronization
     */
    async performCrossPlatformSync(
        options: {
            forceSync?: boolean
            platforms?: string[]
            includeRealTime?: boolean
        } = {}
    ): Promise<{
        success: boolean
        syncedPlatforms: string[]
        errors: Array<{ platform: string; error: string }>
        totalItems: number
        syncTime: number
    }> {
        const startTime = Date.now()
        const syncedPlatforms: string[] = []
        const errors: Array<{ platform: string; error: string }> = []
        let totalItems = 0

        try {
            // Get platforms to sync
            const platforms = options.platforms || await this.getConnectedPlatforms()

            // Perform sync for each platform
            for (const platform of platforms) {
                try {
                    const response = await apiClient.post(`/api/platforms/${platform}/sync`, {
                        force: options.forceSync,
                        includeRealTime: options.includeRealTime
                    })

                    syncedPlatforms.push(platform)
                    totalItems += response.data.itemCount
                } catch (error) {
                    console.error(`Sync failed for platform ${platform}:`, error)
                    errors.push({
                        platform,
                        error: error instanceof Error ? error.message : 'Unknown error'
                    })
                }
            }

            // Update sync status in localStorage
            localStorage.setItem('lastSync', JSON.stringify({
                timestamp: new Date().toISOString(),
                syncedPlatforms,
                errors
            }))

            return {
                success: errors.length === 0,
                syncedPlatforms,
                errors,
                totalItems,
                syncTime: Date.now() - startTime
            }
        } catch (error) {
            console.error('Cross-platform sync failed:', error)
            throw error
        }
    }

    /**
     * Handle offline support and queue management
     */
    async handleOfflineOperations(): Promise<{
        queuedOperations: number
        processedOperations: number
        failedOperations: number
    }> {
        try {
            // Get queued offline operations from IndexedDB
            const queuedOps = await this.getOfflineQueue()

            // Process operations when online
            const results = await this.processOfflineQueue()

            return {
                queuedOperations: queuedOps.length,
                processedOperations: results.successful.length,
                failedOperations: results.failed.length
            }
        } catch (error) {
            console.error('Failed to handle offline operations:', error)
            throw error
        }
    }

    /**
     * Get comprehensive system status
     */
    async getSystemStatus(): Promise<{
        online: boolean
        syncStatus: 'active' | 'idle' | 'error'
        platformConnections: PlatformConnection[]
        cacheSize: number
        lastSync: Date | null
        insights: {
            total: number
            unread: number
            urgent: number
        }
    }> {
        try {
            const [
                networkStatus,
                platforms,
                insights
            ] = await Promise.all([
                this.getNetworkStatus(),
                this.getPlatformConnections(),
                this.getInsightsSummary()
            ])

            const lastSyncData = localStorage.getItem('lastSync')
            const lastSync = lastSyncData
                ? new Date(JSON.parse(lastSyncData).timestamp)
                : null

            return {
                online: networkStatus.online,
                syncStatus: this.websocket?.readyState === WebSocket.OPEN ? 'active' : 'idle',
                platformConnections: platforms,
                cacheSize: this.searchCache.size,
                lastSync,
                insights: {
                    total: insights.total,
                    unread: insights.unread,
                    urgent: insights.urgent
                }
            }
        } catch (error) {
            console.error('Failed to get system status:', error)
            throw error
        }
    }

    /**
     * Clean up resources and cache
     */
    async cleanup(): Promise<void> {
        try {
            // Clear search cache
            this.searchCache.clear()

            // Close WebSocket connection
            if (this.websocket) {
                this.websocket.close()
                this.websocket = null
            }

            // Unregister service worker if needed
            if (this.serviceWorker) {
                await this.serviceWorker.unregister()
                this.serviceWorker = null
            }

            console.log('Unified business logic service cleaned up successfully')
        } catch (error) {
            console.error('Failed to cleanup unified business logic service:', error)
        }
    }

    // Private helper methods

    private async setupServiceWorker(): Promise<void> {
        try {
            this.serviceWorker = await navigator.serviceWorker.register('/sw.js')
            console.log('Service worker registered successfully')
        } catch (error) {
            console.error('Failed to register service worker:', error)
        }
    }

    private async setupRealTimeSync(): Promise<void> {
        try {
            const wsUrl = this.config.apiBaseUrl.replace('http', 'ws') + '/ws'
            this.websocket = new WebSocket(wsUrl)

            this.websocket.onopen = () => {
                console.log('WebSocket connection established')
            }

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data)
                this.handleRealTimeUpdate(data)
            }

            this.websocket.onclose = () => {
                console.log('WebSocket connection closed, attempting to reconnect...')
                setTimeout(() => this.setupRealTimeSync(), 5000)
            }

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error)
            }
        } catch (error) {
            console.error('Failed to setup real-time sync:', error)
        }
    }

    private async setupProactiveInsights(): Promise<void> {
        // Set up periodic insight checking
        setInterval(async () => {
            try {
                const insights = await this.getProactiveInsights({})
                if (insights.length > 0) {
                    this.notifyProactiveInsights(insights)
                }
            } catch (error) {
                console.error('Failed to check proactive insights:', error)
            }
        }, this.config.syncInterval)
    }

    private handleRealTimeUpdate(data: any): void {
        // Handle real-time updates from WebSocket
        switch (data.type) {
            case 'contact_update':
                this.invalidateContactCache(data.contactId)
                break
            case 'message_received':
                this.invalidateSearchCache()
                break
            case 'sync_complete':
                this.handleSyncComplete(data)
                break
        }
    }

    private async parseNaturalLanguageQuery(query: string): Promise<any> {
        try {
            const response = await apiClient.post('/api/search/parse', { query })
            return response.data
        } catch (error) {
            console.error('Failed to parse natural language query:', error)
            return { text: query, intent: 'general', entities: [] }
        }
    }

    private async searchMessages(query: string, options: any): Promise<Message[]> {
        try {
            const response = await apiClient.get('/api/messages/search', {
                params: { q: query, ...options }
            })
            return response.data.messages
        } catch (error) {
            console.error('Failed to search messages:', error)
            return []
        }
    }

    private async searchThreads(query: string, options: any): Promise<ConversationThread[]> {
        try {
            const response = await apiClient.get('/api/threads/search', {
                params: { q: query, ...options }
            })
            return response.data.threads
        } catch (error) {
            console.error('Failed to search threads:', error)
            return []
        }
    }

    private async getProactiveInsights(options: any): Promise<ProactiveInsight[]> {
        try {
            const response = await apiClient.get('/api/insights/proactive', {
                params: options
            })
            return response.data.insights
        } catch (error) {
            console.error('Failed to get proactive insights:', error)
            return []
        }
    }

    private async performInitialSync(platform: string): Promise<void> {
        try {
            await apiClient.post(`/api/platforms/${platform}/sync/initial`)
        } catch (error) {
            console.error(`Failed to perform initial sync for ${platform}:`, error)
        }
    }

    private async getConnectedPlatforms(): Promise<string[]> {
        try {
            const response = await apiClient.get('/api/platforms')
            return response.data.platforms.map((p: any) => p.name)
        } catch (error) {
            console.error('Failed to get connected platforms:', error)
            return []
        }
    }

    private async getPlatformConnections(): Promise<PlatformConnection[]> {
        try {
            const response = await apiClient.get('/api/platforms')
            return response.data.platforms
        } catch (error) {
            console.error('Failed to get platform connections:', error)
            return []
        }
    }

    private async getInsightsSummary(): Promise<any> {
        try {
            const response = await apiClient.get('/api/insights/summary')
            return response.data
        } catch (error) {
            console.error('Failed to get insights summary:', error)
            return { total: 0, unread: 0, urgent: 0 }
        }
    }

    private async getNetworkStatus(): Promise<{ online: boolean }> {
        return { online: navigator.onLine }
    }

    private async getOfflineQueue(): Promise<any[]> {
        // Implementation would use IndexedDB
        return []
    }

    private async processOfflineQueue(): Promise<{ successful: any[]; failed: any[] }> {
        // Implementation would process queued operations
        return { successful: [], failed: [] }
    }

    private getDefaultUserPreferences(): UserPreferences {
        return {
            notifications: {
                enabled: true,
                types: ['message', 'insight', 'reminder'],
                quietHours: { start: '22:00', end: '08:00' },
                channels: ['browser', 'in-app']
            },
            privacy: {
                dataProcessing: true,
                aiAnalysis: true,
                piiRedaction: true,
                dataSharing: false
            },
            sync: {
                autoSync: true,
                syncInterval: 300000, // 5 minutes
                backgroundSync: true,
                wifiOnly: false
            },
            ui: {
                theme: 'auto',
                language: 'en',
                accessibility: {
                    screenReader: false,
                    highContrast: false,
                    largeText: false,
                    voiceControl: false
                }
            }
        }
    }

    private async loadOnboardingState(): Promise<void> {
        try {
            const saved = localStorage.getItem('onboardingState')
            if (saved) {
                this.onboardingState = JSON.parse(saved)
            }
        } catch (error) {
            console.error('Failed to load onboarding state:', error)
        }
    }

    private async saveOnboardingState(): Promise<void> {
        try {
            if (this.onboardingState) {
                localStorage.setItem('onboardingState', JSON.stringify(this.onboardingState))
            }
        } catch (error) {
            console.error('Failed to save onboarding state:', error)
        }
    }

    private cleanupCache(): void {
        const now = Date.now()
        for (const [key, result] of this.searchCache.entries()) {
            if (now - result.processingTime > this.CACHE_TTL) {
                this.searchCache.delete(key)
            }
        }

        // Limit cache size
        if (this.searchCache.size > this.config.maxCacheSize) {
            const entries = Array.from(this.searchCache.entries())
            entries.sort((a, b) => a[1].processingTime - b[1].processingTime)

            const toDelete = entries.slice(0, entries.length - this.config.maxCacheSize)
            toDelete.forEach(([key]) => this.searchCache.delete(key))
        }
    }

    private invalidateContactCache(contactId: string): void {
        // Remove cache entries related to specific contact
        for (const [key] of this.searchCache.entries()) {
            if (key.includes(contactId)) {
                this.searchCache.delete(key)
            }
        }
    }

    private invalidateSearchCache(): void {
        // Clear all search cache
        this.searchCache.clear()
    }

    private handleSyncComplete(data: any): void {
        // Handle sync completion
        console.log('Sync completed:', data)
    }

    private notifyProactiveInsights(insights: ProactiveInsight[]): void {
        // Show browser notifications for proactive insights
        if ('Notification' in window && Notification.permission === 'granted') {
            insights.forEach(insight => {
                new Notification(insight.title, {
                    body: insight.description,
                    icon: '/icons/icon-192x192.png'
                })
            })
        }
    }
}

// Export singleton instance
export const unifiedBusinessLogic = new UnifiedBusinessLogicService({
    apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    enableOfflineMode: true,
    enableRealTimeSync: true,
    enableProactiveInsights: true,
    maxCacheSize: 100,
    syncInterval: 300000 // 5 minutes
})

export default unifiedBusinessLogic