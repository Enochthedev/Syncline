/**
 * Platform Connection Management Service
 * 
 * Handles OAuth flows, connection health monitoring, and platform-specific settings
 * for all supported communication platforms.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiClient } from './apiClient';
import { authService } from './authService';

export interface PlatformConnection {
    id: string;
    platform: string;
    displayName: string;
    isConnected: boolean;
    isEnabled: boolean;
    connectionStatus: 'healthy' | 'degraded' | 'unhealthy' | 'disconnected' | 'authenticating';
    lastSyncTime?: Date;
    lastErrorTime?: Date;
    lastError?: string;
    syncPreferences: PlatformSyncPreferences;
    platformSpecificSettings: Record<string, any>;
    connectionHistory: ConnectionHistoryEntry[];
    oauthConfig?: OAuthConfig;
    healthMetrics: HealthMetrics;
}

export interface PlatformSyncPreferences {
    enabled: boolean;
    syncMessages: boolean;
    syncContacts: boolean;
    syncFiles: boolean;
    syncFrequency: 'realtime' | 'hourly' | 'daily' | 'manual';
    dataFilters: {
        dateRange?: {
            start?: Date;
            end?: Date;
        };
        messageTypes?: string[];
        excludeKeywords?: string[];
        includeKeywords?: string[];
    };
    privacySettings: {
        enablePIIRedaction: boolean;
        enableAIAnalysis: boolean;
        dataRetentionDays?: number;
    };
}

export interface ConnectionHistoryEntry {
    id: string;
    timestamp: Date;
    action: 'connected' | 'disconnected' | 'error' | 'sync_started' | 'sync_completed' | 'settings_changed';
    details?: string;
    errorCode?: string;
    metadata?: Record<string, any>;
}

export interface OAuthConfig {
    clientId: string;
    redirectUri: string;
    scopes: string[];
    authUrl: string;
    tokenUrl: string;
    revokeUrl?: string;
}

export interface HealthMetrics {
    uptime: number;
    errorCount: number;
    successfulSyncs: number;
    failedSyncs: number;
    averageResponseTime: number;
    lastHealthCheck: Date;
    rateLimitStatus?: {
        remaining: number;
        resetTime: Date;
    };
}

export interface ConnectionTroubleshootingInfo {
    platform: string;
    issues: TroubleshootingIssue[];
    suggestedActions: SuggestedAction[];
    diagnosticData: Record<string, any>;
}

export interface TroubleshootingIssue {
    id: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    description: string;
    possibleCauses: string[];
    lastOccurred: Date;
}

export interface SuggestedAction {
    id: string;
    title: string;
    description: string;
    actionType: 'reconnect' | 'refresh_token' | 'check_permissions' | 'contact_support' | 'retry_sync';
    automated: boolean;
    estimatedTime?: string;
}

export interface BulkOperationResult {
    successful: string[];
    failed: Array<{
        platform: string;
        error: string;
    }>;
    totalProcessed: number;
}

class PlatformConnectionService {
    private connections: Map<string, PlatformConnection> = new Map();
    private healthCheckInterval?: NodeJS.Timeout;
    private readonly STORAGE_KEY = 'platform_connections';
    private readonly HEALTH_CHECK_INTERVAL = 60000; // 1 minute

    constructor() {
        this.initializeService();
    }

    private async initializeService(): Promise<void> {
        await this.loadConnectionsFromStorage();
        this.startHealthMonitoring();
    }

    /**
     * Get all platform connections
     */
    async getAllConnections(): Promise<PlatformConnection[]> {
        return Array.from(this.connections.values());
    }

    /**
     * Get a specific platform connection
     */
    async getConnection(platform: string): Promise<PlatformConnection | null> {
        return this.connections.get(platform) || null;
    }

    /**
     * Get available platforms for connection
     */
    async getAvailablePlatforms(): Promise<Array<{
        platform: string;
        displayName: string;
        description: string;
        icon: string;
        isSupported: boolean;
        oauthConfig?: OAuthConfig;
    }>> {
        try {
            const response = await apiClient.get('/api/platforms/available');
            return response.data;
        } catch (error) {
            console.error('Failed to fetch available platforms:', error);
            return this.getDefaultPlatforms();
        }
    }

    /**
     * Initiate OAuth flow for platform connection
     */
    async initiateOAuthFlow(platform: string): Promise<{
        authUrl: string;
        state: string;
    }> {
        try {
            const response = await apiClient.post(`/api/platforms/${platform}/oauth/initiate`);

            // Store OAuth state for verification
            await AsyncStorage.setItem(`oauth_state_${platform}`, response.data.state);

            return response.data;
        } catch (error) {
            console.error(`Failed to initiate OAuth for ${platform}:`, error);
            throw new Error(`Failed to start connection process for ${platform}`);
        }
    }

    /**
     * Complete OAuth flow with authorization code
     */
    async completeOAuthFlow(platform: string, authCode: string, state: string): Promise<PlatformConnection> {
        try {
            // Verify state parameter
            const storedState = await AsyncStorage.getItem(`oauth_state_${platform}`);
            if (storedState !== state) {
                throw new Error('Invalid OAuth state parameter');
            }

            const response = await apiClient.post(`/api/platforms/${platform}/oauth/complete`, {
                code: authCode,
                state: state,
            });

            const connection = this.createConnectionFromResponse(platform, response.data);
            this.connections.set(platform, connection);

            await this.saveConnectionsToStorage();
            await this.addConnectionHistoryEntry(platform, 'connected', 'OAuth flow completed successfully');

            // Clean up OAuth state
            await AsyncStorage.removeItem(`oauth_state_${platform}`);

            return connection;
        } catch (error) {
            console.error(`Failed to complete OAuth for ${platform}:`, error);
            await this.addConnectionHistoryEntry(platform, 'error', `OAuth completion failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Disconnect a platform
     */
    async disconnectPlatform(platform: string): Promise<void> {
        try {
            await apiClient.delete(`/api/platforms/${platform}/connection`);

            const connection = this.connections.get(platform);
            if (connection) {
                connection.isConnected = false;
                connection.connectionStatus = 'disconnected';
                connection.lastSyncTime = undefined;

                await this.addConnectionHistoryEntry(platform, 'disconnected', 'Platform disconnected by user');
                await this.saveConnectionsToStorage();
            }
        } catch (error) {
            console.error(`Failed to disconnect ${platform}:`, error);
            throw error;
        }
    }

    /**
     * Update platform sync preferences
     */
    async updateSyncPreferences(platform: string, preferences: Partial<PlatformSyncPreferences>): Promise<void> {
        try {
            const connection = this.connections.get(platform);
            if (!connection) {
                throw new Error(`Platform ${platform} not found`);
            }

            const updatedPreferences = { ...connection.syncPreferences, ...preferences };

            await apiClient.put(`/api/platforms/${platform}/sync-preferences`, updatedPreferences);

            connection.syncPreferences = updatedPreferences;
            await this.saveConnectionsToStorage();
            await this.addConnectionHistoryEntry(platform, 'settings_changed', 'Sync preferences updated');
        } catch (error) {
            console.error(`Failed to update sync preferences for ${platform}:`, error);
            throw error;
        }
    }

    /**
     * Update platform-specific settings
     */
    async updatePlatformSettings(platform: string, settings: Record<string, any>): Promise<void> {
        try {
            const connection = this.connections.get(platform);
            if (!connection) {
                throw new Error(`Platform ${platform} not found`);
            }

            await apiClient.put(`/api/platforms/${platform}/settings`, settings);

            connection.platformSpecificSettings = { ...connection.platformSpecificSettings, ...settings };
            await this.saveConnectionsToStorage();
            await this.addConnectionHistoryEntry(platform, 'settings_changed', 'Platform settings updated');
        } catch (error) {
            console.error(`Failed to update platform settings for ${platform}:`, error);
            throw error;
        }
    }

    /**
     * Perform health check for a specific platform
     */
    async performHealthCheck(platform: string): Promise<HealthMetrics> {
        try {
            const response = await apiClient.get(`/api/platforms/${platform}/health`);
            const healthMetrics = response.data;

            const connection = this.connections.get(platform);
            if (connection) {
                connection.healthMetrics = healthMetrics;
                connection.connectionStatus = this.determineConnectionStatus(healthMetrics);
                await this.saveConnectionsToStorage();
            }

            return healthMetrics;
        } catch (error) {
            console.error(`Health check failed for ${platform}:`, error);

            const connection = this.connections.get(platform);
            if (connection) {
                connection.connectionStatus = 'unhealthy';
                connection.lastError = error.message;
                connection.lastErrorTime = new Date();
                connection.healthMetrics.errorCount++;
            }

            throw error;
        }
    }

    /**
     * Get troubleshooting information for a platform
     */
    async getTroubleshootingInfo(platform: string): Promise<ConnectionTroubleshootingInfo> {
        try {
            const response = await apiClient.get(`/api/platforms/${platform}/troubleshoot`);
            return response.data;
        } catch (error) {
            console.error(`Failed to get troubleshooting info for ${platform}:`, error);

            // Return basic troubleshooting info based on connection state
            const connection = this.connections.get(platform);
            return this.generateBasicTroubleshootingInfo(platform, connection);
        }
    }

    /**
     * Execute a suggested troubleshooting action
     */
    async executeTroubleshootingAction(platform: string, actionId: string): Promise<boolean> {
        try {
            const response = await apiClient.post(`/api/platforms/${platform}/troubleshoot/execute`, {
                actionId,
            });

            if (response.data.success) {
                await this.addConnectionHistoryEntry(platform, 'sync_completed', `Troubleshooting action ${actionId} executed successfully`);
                // Refresh connection status
                await this.performHealthCheck(platform);
            }

            return response.data.success;
        } catch (error) {
            console.error(`Failed to execute troubleshooting action for ${platform}:`, error);
            await this.addConnectionHistoryEntry(platform, 'error', `Troubleshooting action ${actionId} failed: ${error.message}`);
            return false;
        }
    }

    /**
     * Perform bulk operations on multiple platforms
     */
    async bulkEnablePlatforms(platforms: string[]): Promise<BulkOperationResult> {
        const result: BulkOperationResult = {
            successful: [],
            failed: [],
            totalProcessed: platforms.length,
        };

        for (const platform of platforms) {
            try {
                await this.enablePlatform(platform);
                result.successful.push(platform);
            } catch (error) {
                result.failed.push({
                    platform,
                    error: error.message,
                });
            }
        }

        return result;
    }

    /**
     * Perform bulk operations on multiple platforms
     */
    async bulkDisablePlatforms(platforms: string[]): Promise<BulkOperationResult> {
        const result: BulkOperationResult = {
            successful: [],
            failed: [],
            totalProcessed: platforms.length,
        };

        for (const platform of platforms) {
            try {
                await this.disablePlatform(platform);
                result.successful.push(platform);
            } catch (error) {
                result.failed.push({
                    platform,
                    error: error.message,
                });
            }
        }

        return result;
    }

    /**
     * Sync all enabled platforms
     */
    async syncAllPlatforms(): Promise<BulkOperationResult> {
        const enabledConnections = Array.from(this.connections.values())
            .filter(conn => conn.isEnabled && conn.isConnected);

        const result: BulkOperationResult = {
            successful: [],
            failed: [],
            totalProcessed: enabledConnections.length,
        };

        for (const connection of enabledConnections) {
            try {
                await this.syncPlatform(connection.platform);
                result.successful.push(connection.platform);
            } catch (error) {
                result.failed.push({
                    platform: connection.platform,
                    error: error.message,
                });
            }
        }

        return result;
    }

    /**
     * Enable a platform
     */
    async enablePlatform(platform: string): Promise<void> {
        const connection = this.connections.get(platform);
        if (!connection) {
            throw new Error(`Platform ${platform} not found`);
        }

        connection.isEnabled = true;
        await this.saveConnectionsToStorage();
        await this.addConnectionHistoryEntry(platform, 'settings_changed', 'Platform enabled');
    }

    /**
     * Disable a platform
     */
    async disablePlatform(platform: string): Promise<void> {
        const connection = this.connections.get(platform);
        if (!connection) {
            throw new Error(`Platform ${platform} not found`);
        }

        connection.isEnabled = false;
        await this.saveConnectionsToStorage();
        await this.addConnectionHistoryEntry(platform, 'settings_changed', 'Platform disabled');
    }

    /**
     * Sync a specific platform
     */
    async syncPlatform(platform: string): Promise<void> {
        try {
            const connection = this.connections.get(platform);
            if (!connection || !connection.isEnabled || !connection.isConnected) {
                throw new Error(`Platform ${platform} is not available for sync`);
            }

            await this.addConnectionHistoryEntry(platform, 'sync_started', 'Manual sync initiated');

            const response = await apiClient.post(`/api/platforms/${platform}/sync`);

            connection.lastSyncTime = new Date();
            connection.healthMetrics.successfulSyncs++;

            await this.saveConnectionsToStorage();
            await this.addConnectionHistoryEntry(platform, 'sync_completed', 'Manual sync completed successfully');
        } catch (error) {
            console.error(`Failed to sync ${platform}:`, error);

            const connection = this.connections.get(platform);
            if (connection) {
                connection.healthMetrics.failedSyncs++;
                connection.lastError = error.message;
                connection.lastErrorTime = new Date();
            }

            await this.addConnectionHistoryEntry(platform, 'error', `Sync failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Get connection history for a platform
     */
    async getConnectionHistory(platform: string, limit: number = 50): Promise<ConnectionHistoryEntry[]> {
        const connection = this.connections.get(platform);
        if (!connection) {
            return [];
        }

        return connection.connectionHistory
            .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
            .slice(0, limit);
    }

    /**
     * Export platform connection data
     */
    async exportConnectionData(platforms?: string[]): Promise<any> {
        const connectionsToExport = platforms
            ? Array.from(this.connections.values()).filter(conn => platforms.includes(conn.platform))
            : Array.from(this.connections.values());

        return {
            exportedAt: new Date().toISOString(),
            connections: connectionsToExport.map(conn => ({
                platform: conn.platform,
                displayName: conn.displayName,
                isConnected: conn.isConnected,
                isEnabled: conn.isEnabled,
                connectionStatus: conn.connectionStatus,
                lastSyncTime: conn.lastSyncTime?.toISOString(),
                syncPreferences: conn.syncPreferences,
                platformSpecificSettings: conn.platformSpecificSettings,
                healthMetrics: conn.healthMetrics,
                connectionHistory: conn.connectionHistory.slice(-10), // Last 10 entries
            })),
        };
    }

    // Private helper methods

    private async loadConnectionsFromStorage(): Promise<void> {
        try {
            const stored = await AsyncStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const connections = JSON.parse(stored);
                for (const conn of connections) {
                    // Convert date strings back to Date objects
                    if (conn.lastSyncTime) conn.lastSyncTime = new Date(conn.lastSyncTime);
                    if (conn.lastErrorTime) conn.lastErrorTime = new Date(conn.lastErrorTime);
                    if (conn.healthMetrics?.lastHealthCheck) {
                        conn.healthMetrics.lastHealthCheck = new Date(conn.healthMetrics.lastHealthCheck);
                    }

                    conn.connectionHistory = conn.connectionHistory.map((entry: any) => ({
                        ...entry,
                        timestamp: new Date(entry.timestamp),
                    }));

                    this.connections.set(conn.platform, conn);
                }
            }
        } catch (error) {
            console.error('Failed to load connections from storage:', error);
        }
    }

    private async saveConnectionsToStorage(): Promise<void> {
        try {
            const connections = Array.from(this.connections.values());
            await AsyncStorage.setItem(this.STORAGE_KEY, JSON.stringify(connections));
        } catch (error) {
            console.error('Failed to save connections to storage:', error);
        }
    }

    private createConnectionFromResponse(platform: string, data: any): PlatformConnection {
        return {
            id: data.id || platform,
            platform,
            displayName: data.displayName || platform,
            isConnected: true,
            isEnabled: true,
            connectionStatus: 'healthy',
            lastSyncTime: data.lastSyncTime ? new Date(data.lastSyncTime) : new Date(),
            syncPreferences: data.syncPreferences || this.getDefaultSyncPreferences(),
            platformSpecificSettings: data.platformSpecificSettings || {},
            connectionHistory: [],
            oauthConfig: data.oauthConfig,
            healthMetrics: data.healthMetrics || this.getDefaultHealthMetrics(),
        };
    }

    private getDefaultSyncPreferences(): PlatformSyncPreferences {
        return {
            enabled: true,
            syncMessages: true,
            syncContacts: true,
            syncFiles: true,
            syncFrequency: 'realtime',
            dataFilters: {},
            privacySettings: {
                enablePIIRedaction: true,
                enableAIAnalysis: true,
                dataRetentionDays: 365,
            },
        };
    }

    private getDefaultHealthMetrics(): HealthMetrics {
        return {
            uptime: 0,
            errorCount: 0,
            successfulSyncs: 0,
            failedSyncs: 0,
            averageResponseTime: 0,
            lastHealthCheck: new Date(),
        };
    }

    private getDefaultPlatforms() {
        return [
            {
                platform: 'gmail',
                displayName: 'Gmail',
                description: 'Connect your Gmail account to sync emails',
                icon: 'gmail',
                isSupported: true,
            },
            {
                platform: 'slack',
                displayName: 'Slack',
                description: 'Connect your Slack workspace',
                icon: 'slack',
                isSupported: true,
            },
            {
                platform: 'discord',
                displayName: 'Discord',
                description: 'Connect your Discord account',
                icon: 'discord',
                isSupported: true,
            },
            {
                platform: 'whatsapp',
                displayName: 'WhatsApp',
                description: 'Connect your WhatsApp account',
                icon: 'whatsapp',
                isSupported: false,
            },
        ];
    }

    private determineConnectionStatus(healthMetrics: HealthMetrics): PlatformConnection['connectionStatus'] {
        const errorRate = healthMetrics.failedSyncs / (healthMetrics.successfulSyncs + healthMetrics.failedSyncs);

        if (errorRate > 0.5) return 'unhealthy';
        if (errorRate > 0.2) return 'degraded';
        if (healthMetrics.averageResponseTime > 5000) return 'degraded';

        return 'healthy';
    }

    private generateBasicTroubleshootingInfo(platform: string, connection?: PlatformConnection): ConnectionTroubleshootingInfo {
        const issues: TroubleshootingIssue[] = [];
        const suggestedActions: SuggestedAction[] = [];

        if (!connection?.isConnected) {
            issues.push({
                id: 'not_connected',
                severity: 'high',
                title: 'Platform Not Connected',
                description: `${platform} is not currently connected`,
                possibleCauses: ['OAuth token expired', 'Manual disconnection', 'Authentication failure'],
                lastOccurred: new Date(),
            });

            suggestedActions.push({
                id: 'reconnect',
                title: 'Reconnect Platform',
                description: 'Initiate a new connection to the platform',
                actionType: 'reconnect',
                automated: false,
                estimatedTime: '2-3 minutes',
            });
        }

        if (connection?.connectionStatus === 'unhealthy') {
            issues.push({
                id: 'unhealthy_connection',
                severity: 'medium',
                title: 'Connection Issues',
                description: 'The platform connection is experiencing issues',
                possibleCauses: ['Network connectivity', 'API rate limits', 'Service outage'],
                lastOccurred: connection.lastErrorTime || new Date(),
            });

            suggestedActions.push({
                id: 'retry_sync',
                title: 'Retry Synchronization',
                description: 'Attempt to sync data again',
                actionType: 'retry_sync',
                automated: true,
                estimatedTime: '30 seconds',
            });
        }

        return {
            platform,
            issues,
            suggestedActions,
            diagnosticData: {
                connectionStatus: connection?.connectionStatus || 'unknown',
                lastError: connection?.lastError,
                lastSyncTime: connection?.lastSyncTime?.toISOString(),
                healthMetrics: connection?.healthMetrics,
            },
        };
    }

    private async addConnectionHistoryEntry(
        platform: string,
        action: ConnectionHistoryEntry['action'],
        details?: string,
        errorCode?: string,
        metadata?: Record<string, any>
    ): Promise<void> {
        const connection = this.connections.get(platform);
        if (!connection) return;

        const entry: ConnectionHistoryEntry = {
            id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date(),
            action,
            details,
            errorCode,
            metadata,
        };

        connection.connectionHistory.push(entry);

        // Keep only last 100 entries
        if (connection.connectionHistory.length > 100) {
            connection.connectionHistory = connection.connectionHistory.slice(-100);
        }

        await this.saveConnectionsToStorage();
    }

    private startHealthMonitoring(): void {
        this.healthCheckInterval = setInterval(async () => {
            const connections = Array.from(this.connections.values())
                .filter(conn => conn.isConnected && conn.isEnabled);

            for (const connection of connections) {
                try {
                    await this.performHealthCheck(connection.platform);
                } catch (error) {
                    // Health check errors are already handled in performHealthCheck
                }
            }
        }, this.HEALTH_CHECK_INTERVAL);
    }

    /**
     * Clean up resources
     */
    destroy(): void {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = undefined;
        }
    }
}

export const platformConnectionService = new PlatformConnectionService();