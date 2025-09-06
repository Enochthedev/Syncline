import { Platform, AppState, AppStateStatus } from 'react-native';
import DeviceInfo from 'react-native-device-info';
import NetInfo from '@react-native-community/netinfo';
import BackgroundJob from 'react-native-background-job';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface PerformanceMetrics {
    // App performance
    appLaunchTime: number;
    screenTransitionTime: number;
    searchResponseTime: number;

    // Resource usage
    memoryUsage: number;
    cpuUsage: number;
    batteryLevel: number;
    networkUsage: number;

    // User experience
    frameRate: number;
    inputLatency: number;
    scrollPerformance: number;

    // Timestamps
    timestamp: number;
    sessionId: string;
}

export interface PerformanceConfig {
    // Memory management
    maxCacheSize: number;
    cacheCleanupInterval: number;
    memoryWarningThreshold: number;

    // Battery optimization
    backgroundProcessingLimit: number;
    adaptivePollingEnabled: boolean;
    batteryOptimizationThreshold: number;

    // Network optimization
    requestBatchSize: number;
    compressionEnabled: boolean;
    connectionPoolSize: number;

    // Monitoring
    metricsCollectionEnabled: boolean;
    performanceLoggingEnabled: boolean;
    crashReportingEnabled: boolean;
}

class PerformanceManager {
    private static instance: PerformanceManager;
    private config: PerformanceConfig;
    private metrics: PerformanceMetrics[] = [];
    private sessionId: string;
    private appLaunchTime: number;
    private isMonitoring: boolean = false;
    private backgroundJobId: string | null = null;

    private constructor() {
        this.sessionId = this.generateSessionId();
        this.appLaunchTime = Date.now();
        this.config = this.getDefaultConfig();
        this.initializePerformanceMonitoring();
    }

    public static getInstance(): PerformanceManager {
        if (!PerformanceManager.instance) {
            PerformanceManager.instance = new PerformanceManager();
        }
        return PerformanceManager.instance;
    }

    private getDefaultConfig(): PerformanceConfig {
        return {
            maxCacheSize: 100 * 1024 * 1024, // 100MB
            cacheCleanupInterval: 30 * 60 * 1000, // 30 minutes
            memoryWarningThreshold: 0.8, // 80% of available memory

            backgroundProcessingLimit: 30 * 1000, // 30 seconds
            adaptivePollingEnabled: true,
            batteryOptimizationThreshold: 0.2, // 20% battery

            requestBatchSize: 10,
            compressionEnabled: true,
            connectionPoolSize: 5,

            metricsCollectionEnabled: true,
            performanceLoggingEnabled: __DEV__,
            crashReportingEnabled: true,
        };
    }

    private generateSessionId(): string {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private async initializePerformanceMonitoring(): Promise<void> {
        try {
            // Load saved configuration
            const savedConfig = await AsyncStorage.getItem('performance_config');
            if (savedConfig) {
                this.config = { ...this.config, ...JSON.parse(savedConfig) };
            }

            // Start monitoring
            this.startMonitoring();

            // Setup app state change listener
            AppState.addEventListener('change', this.handleAppStateChange);

            // Setup memory warning listener
            if (Platform.OS === 'ios') {
                // iOS memory warning handling
                this.setupMemoryWarningListener();
            }

            console.log('Performance monitoring initialized');
        } catch (error) {
            console.error('Failed to initialize performance monitoring:', error);
        }
    }

    private setupMemoryWarningListener(): void {
        // This would typically use a native module for iOS memory warnings
        // For now, we'll simulate with periodic memory checks
        setInterval(() => {
            this.checkMemoryUsage();
        }, 30000); // Check every 30 seconds
    }

    private handleAppStateChange = (nextAppState: AppStateStatus): void => {
        if (nextAppState === 'background') {
            this.optimizeForBackground();
        } else if (nextAppState === 'active') {
            this.optimizeForForeground();
        }
    };

    public startMonitoring(): void {
        if (this.isMonitoring) return;

        this.isMonitoring = true;

        // Collect metrics periodically
        setInterval(() => {
            this.collectMetrics();
        }, 60000); // Every minute

        // Setup background job for performance optimization
        this.setupBackgroundOptimization();
    }

    public stopMonitoring(): void {
        this.isMonitoring = false;

        if (this.backgroundJobId) {
            BackgroundJob.stop();
            this.backgroundJobId = null;
        }
    }

    private setupBackgroundOptimization(): void {
        if (Platform.OS === 'android') {
            BackgroundJob.register({
                jobKey: 'performanceOptimization',
                period: this.config.cacheCleanupInterval,
            });

            this.backgroundJobId = BackgroundJob.start({
                jobKey: 'performanceOptimization',
                notificationTitle: 'R.E.M.I Performance Optimization',
                notificationText: 'Optimizing app performance...',
            });
        }
    }

    private async collectMetrics(): Promise<void> {
        if (!this.config.metricsCollectionEnabled) return;

        try {
            const batteryLevel = await DeviceInfo.getBatteryLevel();
            const totalMemory = await DeviceInfo.getTotalMemory();
            const usedMemory = await DeviceInfo.getUsedMemory();
            const networkState = await NetInfo.fetch();

            const metrics: PerformanceMetrics = {
                appLaunchTime: Date.now() - this.appLaunchTime,
                screenTransitionTime: 0, // Will be updated by navigation
                searchResponseTime: 0, // Will be updated by search operations

                memoryUsage: usedMemory / totalMemory,
                cpuUsage: 0, // Would need native module for accurate CPU usage
                batteryLevel: batteryLevel,
                networkUsage: 0, // Would need to track network requests

                frameRate: 60, // Assume 60fps, would need native monitoring
                inputLatency: 0, // Would need gesture tracking
                scrollPerformance: 0, // Would need scroll event monitoring

                timestamp: Date.now(),
                sessionId: this.sessionId,
            };

            this.metrics.push(metrics);

            // Keep only last 100 metrics to prevent memory bloat
            if (this.metrics.length > 100) {
                this.metrics = this.metrics.slice(-100);
            }

            // Check for performance issues
            this.analyzePerformance(metrics);

        } catch (error) {
            console.error('Failed to collect performance metrics:', error);
        }
    }

    private analyzePerformance(metrics: PerformanceMetrics): void {
        // Memory usage warning
        if (metrics.memoryUsage > this.config.memoryWarningThreshold) {
            console.warn('High memory usage detected:', metrics.memoryUsage);
            this.triggerMemoryCleanup();
        }

        // Battery optimization
        if (metrics.batteryLevel < this.config.batteryOptimizationThreshold) {
            console.log('Low battery detected, enabling power saving mode');
            this.enableBatteryOptimization();
        }

        // Performance logging
        if (this.config.performanceLoggingEnabled) {
            console.log('Performance metrics:', metrics);
        }
    }

    private async triggerMemoryCleanup(): Promise<void> {
        try {
            // Clear old cache entries
            await this.clearOldCache();

            // Force garbage collection (if available)
            if (global.gc) {
                global.gc();
            }

            console.log('Memory cleanup completed');
        } catch (error) {
            console.error('Memory cleanup failed:', error);
        }
    }

    private async clearOldCache(): Promise<void> {
        try {
            const keys = await AsyncStorage.getAllKeys();
            const cacheKeys = keys.filter(key =>
                key.startsWith('cache_') ||
                key.startsWith('image_cache_') ||
                key.startsWith('search_cache_')
            );

            // Remove cache entries older than 24 hours
            const cutoffTime = Date.now() - (24 * 60 * 60 * 1000);

            for (const key of cacheKeys) {
                try {
                    const item = await AsyncStorage.getItem(key);
                    if (item) {
                        const parsed = JSON.parse(item);
                        if (parsed.timestamp && parsed.timestamp < cutoffTime) {
                            await AsyncStorage.removeItem(key);
                        }
                    }
                } catch (error) {
                    // If we can't parse the item, remove it
                    await AsyncStorage.removeItem(key);
                }
            }
        } catch (error) {
            console.error('Failed to clear old cache:', error);
        }
    }

    private enableBatteryOptimization(): void {
        // Reduce background processing
        this.config.backgroundProcessingLimit = 10 * 1000; // 10 seconds

        // Enable adaptive polling
        this.config.adaptivePollingEnabled = true;

        // Reduce cache cleanup frequency
        this.config.cacheCleanupInterval = 60 * 60 * 1000; // 1 hour

        console.log('Battery optimization enabled');
    }

    private optimizeForBackground(): void {
        // Pause non-essential operations
        this.stopMonitoring();

        // Clear sensitive data from memory
        this.clearSensitiveMemoryData();

        console.log('Optimized for background mode');
    }

    private optimizeForForeground(): void {
        // Resume monitoring
        this.startMonitoring();

        // Refresh data if needed
        this.refreshCriticalData();

        console.log('Optimized for foreground mode');
    }

    private clearSensitiveMemoryData(): void {
        // Clear any sensitive data from memory when app goes to background
        // This is a security measure to prevent data exposure in app switcher
    }

    private refreshCriticalData(): void {
        // Refresh critical data when app comes to foreground
        // This ensures users see up-to-date information
    }

    private async checkMemoryUsage(): Promise<void> {
        try {
            const totalMemory = await DeviceInfo.getTotalMemory();
            const usedMemory = await DeviceInfo.getUsedMemory();
            const memoryUsage = usedMemory / totalMemory;

            if (memoryUsage > this.config.memoryWarningThreshold) {
                await this.triggerMemoryCleanup();
            }
        } catch (error) {
            console.error('Failed to check memory usage:', error);
        }
    }

    // Public API methods
    public updateConfig(newConfig: Partial<PerformanceConfig>): void {
        this.config = { ...this.config, ...newConfig };
        AsyncStorage.setItem('performance_config', JSON.stringify(this.config));
    }

    public getMetrics(): PerformanceMetrics[] {
        return [...this.metrics];
    }

    public getLatestMetrics(): PerformanceMetrics | null {
        return this.metrics.length > 0 ? this.metrics[this.metrics.length - 1] : null;
    }

    public recordScreenTransition(duration: number): void {
        if (this.metrics.length > 0) {
            this.metrics[this.metrics.length - 1].screenTransitionTime = duration;
        }
    }

    public recordSearchResponse(duration: number): void {
        if (this.metrics.length > 0) {
            this.metrics[this.metrics.length - 1].searchResponseTime = duration;
        }
    }

    public async exportMetrics(): Promise<string> {
        return JSON.stringify({
            sessionId: this.sessionId,
            config: this.config,
            metrics: this.metrics,
            exportTime: Date.now(),
        }, null, 2);
    }

    public clearMetrics(): void {
        this.metrics = [];
    }
}

export default PerformanceManager;