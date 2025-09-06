/**
 * Unified Business Logic Service
 * Shared business logic between React Native and Web applications
 * Provides consistent data processing and state management
 */

import { Contact, Message, SearchResult, ConversationThread, ProactiveInsight } from '@/types'
import { contactSearchService } from './contactSearchService'
import { naturalLanguageSearchService } from './naturalLanguageSearchService'
import { syncService } from './syncService'
import { insightsService } from './insightsService'
import { notificationService } from './notificationService'

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

    constructor(config: UnifiedBusinessLogicConfig) {
        this.config = config
    }

    /**
     * Initialize the unified business logic service
     */
    async initialize(): Promise<void> {
        try {
            // Initialize all dependent services
            await Promise.all([
                contactSearchService.initialize(),
                naturalLanguageSearchService.initialize(),
                syncService.initialize(),
                insightsService.initialize(),
                notificationService.initialize()
            ])

            // Set up real-time sync if enabled
            if (this.config.enableRealTimeSync) {
                await this.setupRealTimeSync()
            }

            // Set up proactive insights if enabled
            if (this.config.enableProactiveInsights) {
                await this.setupProactiveInsights()
            }

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
                ? await naturalLanguageSearchService.parseQuery(query)
                : { text: query, intent: 'general', entities: [] }

            // Step 2: Search contacts based on query
            const contacts = await contactSearchService.searchContacts(query, {
                fuzzyMatch: true,
                includeMetadata: true,
                maxResults: options.maxResults || 50
            })

            // Step 3: Search messages and threads
            const [messages, threads] = await Promise.all([
                contactSearchService.searchMessages(query, {
                    contactFilter: contacts.map(c => c.id),
                    includeContent: true,
                    maxResults: options.maxResults || 100
                }),
                contactSearchService.searchThreads(query, {
                    contactFilter: contacts.map(c => c.id),
                    includePreview: true,
                    maxResults: options.maxResults || 50
                })
            ])

            // Step 4: Get proactive insights if enabled
            const insights = options.includeInsights
                ? await insightsService.getProactiveInsights({
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
            // Attempt platform connection
            const connection = await syncService.connectPlatform(platform, credentials)

            // Update onboarding state
            if (this.onboardingState) {
                const existingIndex = this.onboardingState.platformConnections
                    .findIndex(c => c.platform === platform)

                if (existingIndex >= 0) {
                    this.onboardingState.platformConnections[existingIndex] = connection
                } else {
                    this.onboardingState.platformConnections.push(connection)
                }
            }

            // Trigger initial sync
            await syncService.performInitialSync(platform)

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
            const platforms = options.platforms || await syncService.getConnectedPlatforms()

            // Perform sync for each platform
            for (const platform of platforms) {
                try {
                    const result = await syncService.syncPlatform(platform, {
                        force: options.forceSync,
                        includeRealTime: options.includeRealTime
                    })

                    syncedPlatforms.push(platform)
                    totalItems += result.itemCount
                } catch (error) {
                    console.error(`Sync failed for platform ${platform}:`, error)
                    errors.push({
                        platform,
                        error: error instanceof Error ? error.message : 'Unknown error'
                    })
                }
            }

            // Update sync status
            await syncService.updateSyncStatus({
                lastSync: new Date(),
                syncedPlatforms,
                errors
            })

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
            // Get queued offline operations
            const queuedOps = await syncService.getOfflineQueue()

            // Process operations when online
            const results = await syncService.processOfflineQueue()

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
                syncStatus,
                platforms,
                insights
            ] = await Promise.all([
                syncService.getNetworkStatus(),
                syncService.getSyncStatus(),
                syncService.getPlatformConnections(),
                insightsService.getInsightsSummary()
            ])

            return {
                online: networkStatus.online,
                syncStatus: syncStatus.status,
                platformConnections: platforms,
                cacheSize: this.searchCache.size,
                lastSync: syncStatus.lastSync,
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

            // Cleanup dependent services
            await Promise.all([
                contactSearchService.cleanup(),
                naturalLanguageSearchService.cleanup(),
                syncService.cleanup(),
                insightsService.cleanup(),
                notificationService.cleanup()
            ])

            console.log('Unified business logic service cleaned up successfully')
        } catch (error) {
            console.error('Failed to cleanup unified business logic service:', error)
        }
    }

    // Private helper methods

    private async setupRealTimeSync(): Promise<void> {
        await syncService.enableRealTimeSync({
            interval: this.config.syncInterval,
            backgroundSync: true,
            conflictResolution: 'timestamp'
        })
    }

    private async setupProactiveInsights(): Promise<void> {
        await insightsService.enableProactiveInsights({
            types: ['follow_up', 'commitment', 'relationship'],
            frequency: 'hourly',
            notifications: true
        })
    }

    private getDefaultUserPreferences(): UserPreferences {
        return {
            notifications: {
                enabled: true,
                types: ['message', 'insight', 'reminder'],
                quietHours: { start: '22:00', end: '08:00' },
                channels: ['push', 'in-app']
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

    private async saveOnboardingState(): Promise<void> {
        if (this.onboardingState) {
            // Save to local storage or secure storage
            // Implementation depends on platform (AsyncStorage for RN, localStorage for web)
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
}

// Export singleton instance
export const unifiedBusinessLogic = new UnifiedBusinessLogicService({
    apiBaseUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
    enableOfflineMode: true,
    enableRealTimeSync: true,
    enableProactiveInsights: true,
    maxCacheSize: 100,
    syncInterval: 300000 // 5 minutes
})

export default unifiedBusinessLogic