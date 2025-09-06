import { Platform, AppState, AppStateStatus } from 'react-native';
import DeviceInfo from 'react-native-device-info';
import BackgroundJob from 'react-native-background-job';
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface BatteryConfig {
    lowBatteryThreshold: number;
    criticalBatteryThreshold: number;
    backgroundProcessingLimit: number;
    adaptivePollingEnabled: boolean;
    aggressiveOptimizationEnabled: boolean;
    backgroundSyncInterval: number;
    foregroundSyncInterval: number;
    enableBatteryMonitoring: boolean;
}

export interface BatteryStats {
    batteryLevel: number;
    isCharging: boolean;
    batteryState: 'unknown' | 'unplugged' | 'charging' | 'full';
    powerSaveMode: boolean;
    estimatedTimeRemaining?: number;
    timestamp: number;
}

export interface PowerSavingMode {
    level: 'none' | 'light' | 'moderate' | 'aggressive';
    syncInterval: number;
    backgroundProcessingEnabled: boolean;
    imageQuality: 'high' | 'medium' | 'low';
    animationsEnabled: boolean;
    locationUpdatesEnabled: boolean;
    pushNotificationsEnabled: boolean;
}

class BatteryOptimizer {
    private static instance: BatteryOptimizer;
    private config: BatteryConfig;
    private currentStats: BatteryStats | null = null;
    private powerSavingMode: PowerSavingMode;
    private backgroundJobId: string | null = null;
    private monitoringInterval: NodeJS.Timeout | null = null;
    private appState: AppStateStatus = AppState.currentState;
    private batteryCallbacks: Array<(stats: BatteryStats) => void> = [];
    private powerModeCallbacks: Array<(mode: PowerSavingMode) => void> = [];

    private constructor() {
        this.config = this.getDefaultConfig();
        this.powerSavingMode = this.getDefaultPowerSavingMode();
        this.initializeBatteryOptimization();
    }

    public static getInstance(): BatteryOptimizer {
        if (!BatteryOptimizer.instance) {
            BatteryOptimizer.instance = new BatteryOptimizer();
        }
        return BatteryOptimizer.instance;
    }

    private getDefaultConfig(): BatteryConfig {
        return {
            lowBatteryThreshold: 0.2, // 20%
            criticalBatteryThreshold: 0.1, // 10%
            backgroundProcessingLimit: 30 * 1000, // 30 seconds
            adaptivePollingEnabled: true,
            aggressiveOptimizationEnabled: true,
            backgroundSyncInterval: 5 * 60 * 1000, // 5 minutes
            foregroundSyncInterval: 30 * 1000, // 30 seconds
            enableBatteryMonitoring: true,
        };
    }

    private getDefaultPowerSavingMode(): PowerSavingMode {
        return {
            level: 'none',
            syncInterval: this.config.foregroundSyncInterval,
            backgroundProcessingEnabled: true,
            imageQuality: 'high',
            animationsEnabled: true,
            locationUpdatesEnabled: true,
            pushNotificationsEnabled: true,
        };
    }

    private async initializeBatteryOptimization(): Promise<void> {
        try {
            // Load saved configuration
            const savedConfig = await AsyncStorage.getItem('battery_config');
            if (savedConfig) {
                this.config = { ...this.config, ...JSON.parse(savedConfig) };
            }

            // Load saved power saving mode
            const savedMode = await AsyncStorage.getItem('power_saving_mode');
            if (savedMode) {
                this.powerSavingMode = { ...this.powerSavingMode, ...JSON.parse(savedMode) };
            }

            // Start monitoring if enabled
            if (this.config.enableBatteryMonitoring) {
                this.startBatteryMonitoring();
            }

            // Setup app state listener
            AppState.addEventListener('change', this.handleAppStateChange);

            // Setup network state listener for adaptive optimization
            NetInfo.addEventListener(this.handleNetworkStateChange);

            console.log('Battery optimization initialized');
        } catch (error) {
            console.error('Failed to initialize battery optimization:', error);
        }
    }

    private startBatteryMonitoring(): void {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }

        // Initial battery check
        this.updateBatteryStats();

        // Set up periodic monitoring
        this.monitoringInterval = setInterval(() => {
            this.updateBatteryStats();
        }, 60 * 1000); // Check every minute
    }

    private async updateBatteryStats(): Promise<void> {
        try {
            const batteryLevel = await DeviceInfo.getBatteryLevel();
            const isCharging = await DeviceInfo.isBatteryCharging();

            // Get battery state (platform specific)
            let batteryState: BatteryStats['batteryState'] = 'unknown';
            if (Platform.OS === 'ios') {
                // iOS specific battery state detection
                if (isCharging) {
                    batteryState = batteryLevel >= 1.0 ? 'full' : 'charging';
                } else {
                    batteryState = 'unplugged';
                }
            } else {
                // Android specific battery state detection
                batteryState = isCharging ? 'charging' : 'unplugged';
            }

            const stats: BatteryStats = {
                batteryLevel,
                isCharging,
                batteryState,
                powerSaveMode: this.powerSavingMode.level !== 'none',
                timestamp: Date.now(),
            };

            // Calculate estimated time remaining (rough estimation)
            if (!isCharging && this.currentStats) {
                const timeDiff = stats.timestamp - this.currentStats.timestamp;
                const batteryDiff = this.currentStats.batteryLevel - batteryLevel;

                if (batteryDiff > 0 && timeDiff > 0) {
                    const drainRate = batteryDiff / (timeDiff / (60 * 60 * 1000)); // per hour
                    stats.estimatedTimeRemaining = (batteryLevel / drainRate) * 60 * 60 * 1000; // in ms
                }
            }

            this.currentStats = stats;

            // Analyze battery state and adjust optimization
            this.analyzeBatteryState(stats);

            // Notify callbacks
            this.batteryCallbacks.forEach(callback => {
                try {
                    callback(stats);
                } catch (error) {
                    console.error('Battery callback error:', error);
                }
            });

        } catch (error) {
            console.error('Failed to update battery stats:', error);
        }
    }

    private analyzeBatteryState(stats: BatteryStats): void {
        const { batteryLevel, isCharging } = stats;

        // Don't optimize if charging
        if (isCharging) {
            if (this.powerSavingMode.level !== 'none') {
                this.setPowerSavingMode('none');
            }
            return;
        }

        // Determine appropriate power saving level
        let newLevel: PowerSavingMode['level'] = 'none';

        if (batteryLevel <= this.config.criticalBatteryThreshold) {
            newLevel = 'aggressive';
        } else if (batteryLevel <= this.config.lowBatteryThreshold) {
            newLevel = 'moderate';
        } else if (batteryLevel <= 0.5 && this.config.adaptivePollingEnabled) {
            newLevel = 'light';
        }

        // Update power saving mode if changed
        if (newLevel !== this.powerSavingMode.level) {
            this.setPowerSavingMode(newLevel);
        }
    }

    private setPowerSavingMode(level: PowerSavingMode['level']): void {
        const previousLevel = this.powerSavingMode.level;

        switch (level) {
            case 'none':
                this.powerSavingMode = {
                    level: 'none',
                    syncInterval: this.config.foregroundSyncInterval,
                    backgroundProcessingEnabled: true,
                    imageQuality: 'high',
                    animationsEnabled: true,
                    locationUpdatesEnabled: true,
                    pushNotificationsEnabled: true,
                };
                break;

            case 'light':
                this.powerSavingMode = {
                    level: 'light',
                    syncInterval: this.config.foregroundSyncInterval * 2,
                    backgroundProcessingEnabled: true,
                    imageQuality: 'medium',
                    animationsEnabled: true,
                    locationUpdatesEnabled: true,
                    pushNotificationsEnabled: true,
                };
                break;

            case 'moderate':
                this.powerSavingMode = {
                    level: 'moderate',
                    syncInterval: this.config.backgroundSyncInterval,
                    backgroundProcessingEnabled: true,
                    imageQuality: 'low',
                    animationsEnabled: false,
                    locationUpdatesEnabled: false,
                    pushNotificationsEnabled: true,
                };
                break;

            case 'aggressive':
                this.powerSavingMode = {
                    level: 'aggressive',
                    syncInterval: this.config.backgroundSyncInterval * 2,
                    backgroundProcessingEnabled: false,
                    imageQuality: 'low',
                    animationsEnabled: false,
                    locationUpdatesEnabled: false,
                    pushNotificationsEnabled: false,
                };
                break;
        }

        // Save the new mode
        AsyncStorage.setItem('power_saving_mode', JSON.stringify(this.powerSavingMode));

        // Apply optimizations
        this.applyPowerSavingOptimizations();

        // Notify callbacks
        this.powerModeCallbacks.forEach(callback => {
            try {
                callback(this.powerSavingMode);
            } catch (error) {
                console.error('Power mode callback error:', error);
            }
        });

        console.log(`Power saving mode changed: ${previousLevel} -> ${level}`);
    }

    private applyPowerSavingOptimizations(): void {
        // Adjust background job configuration
        this.configureBackgroundJobs();

        // Apply network optimizations
        this.optimizeNetworkUsage();

        // Apply UI optimizations
        this.optimizeUIPerformance();
    }

    private configureBackgroundJobs(): void {
        if (Platform.OS !== 'android') return;

        // Stop existing background job
        if (this.backgroundJobId) {
            BackgroundJob.stop();
            this.backgroundJobId = null;
        }

        // Configure new background job based on power saving mode
        if (this.powerSavingMode.backgroundProcessingEnabled) {
            const jobConfig = {
                jobKey: 'batteryOptimizedSync',
                period: this.powerSavingMode.syncInterval,
            };

            BackgroundJob.register(jobConfig);

            this.backgroundJobId = BackgroundJob.start({
                jobKey: 'batteryOptimizedSync',
                notificationTitle: 'R.E.M.I Background Sync',
                notificationText: 'Syncing data in power saving mode...',
            });
        }
    }

    private optimizeNetworkUsage(): void {
        // This would integrate with NetworkOptimizer
        // For now, we'll just log the optimization
        console.log('Network usage optimized for power saving mode:', this.powerSavingMode.level);
    }

    private optimizeUIPerformance(): void {
        // This would integrate with UI components to disable animations, reduce image quality, etc.
        console.log('UI performance optimized for power saving mode:', this.powerSavingMode.level);
    }

    private handleAppStateChange = (nextAppState: AppStateStatus): void => {
        const previousState = this.appState;
        this.appState = nextAppState;

        if (previousState === 'active' && nextAppState.match(/inactive|background/)) {
            // App went to background
            this.optimizeForBackground();
        } else if (previousState.match(/inactive|background/) && nextAppState === 'active') {
            // App came to foreground
            this.optimizeForForeground();
        }
    };

    private handleNetworkStateChange = (state: any): void => {
        // Adjust power saving based on network conditions
        if (!state.isConnected) {
            // No network - enable aggressive power saving
            if (this.powerSavingMode.level === 'none') {
                this.setPowerSavingMode('light');
            }
        } else if (state.type === 'cellular') {
            // On cellular - be more conservative
            if (this.powerSavingMode.level === 'none' && this.currentStats?.batteryLevel && this.currentStats.batteryLevel < 0.5) {
                this.setPowerSavingMode('light');
            }
        }
    };

    private optimizeForBackground(): void {
        // Reduce monitoring frequency
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = setInterval(() => {
                this.updateBatteryStats();
            }, 5 * 60 * 1000); // Check every 5 minutes in background
        }

        // Enable background processing limits
        this.configureBackgroundJobs();
    }

    private optimizeForForeground(): void {
        // Restore normal monitoring frequency
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = setInterval(() => {
                this.updateBatteryStats();
            }, 60 * 1000); // Check every minute in foreground
        }

        // Update battery stats immediately
        this.updateBatteryStats();
    }

    // Public API methods
    public updateConfig(newConfig: Partial<BatteryConfig>): void {
        this.config = { ...this.config, ...newConfig };
        AsyncStorage.setItem('battery_config', JSON.stringify(this.config));

        // Restart monitoring with new config
        if (this.config.enableBatteryMonitoring) {
            this.startBatteryMonitoring();
        } else {
            this.stopBatteryMonitoring();
        }
    }

    public getConfig(): BatteryConfig {
        return { ...this.config };
    }

    public getCurrentStats(): BatteryStats | null {
        return this.currentStats;
    }

    public getPowerSavingMode(): PowerSavingMode {
        return { ...this.powerSavingMode };
    }

    public forcePowerSavingMode(level: PowerSavingMode['level']): void {
        this.setPowerSavingMode(level);
    }

    public onBatteryChange(callback: (stats: BatteryStats) => void): () => void {
        this.batteryCallbacks.push(callback);

        // Return unsubscribe function
        return () => {
            const index = this.batteryCallbacks.indexOf(callback);
            if (index > -1) {
                this.batteryCallbacks.splice(index, 1);
            }
        };
    }

    public onPowerModeChange(callback: (mode: PowerSavingMode) => void): () => void {
        this.powerModeCallbacks.push(callback);

        // Return unsubscribe function
        return () => {
            const index = this.powerModeCallbacks.indexOf(callback);
            if (index > -1) {
                this.powerModeCallbacks.splice(index, 1);
            }
        };
    }

    public stopBatteryMonitoring(): void {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }

        if (this.backgroundJobId) {
            BackgroundJob.stop();
            this.backgroundJobId = null;
        }
    }

    public async getBatteryHealth(): Promise<{
        level: number;
        isCharging: boolean;
        estimatedTimeRemaining?: number;
        powerSavingActive: boolean;
        recommendations: string[];
    }> {
        const stats = this.currentStats || await this.updateBatteryStats().then(() => this.currentStats);

        if (!stats) {
            throw new Error('Unable to get battery stats');
        }

        const recommendations: string[] = [];

        if (stats.batteryLevel < 0.2) {
            recommendations.push('Enable power saving mode');
            recommendations.push('Reduce screen brightness');
            recommendations.push('Close unnecessary apps');
        }

        if (!stats.isCharging && stats.batteryLevel < 0.1) {
            recommendations.push('Connect charger immediately');
            recommendations.push('Enable airplane mode if not needed');
        }

        return {
            level: stats.batteryLevel,
            isCharging: stats.isCharging,
            estimatedTimeRemaining: stats.estimatedTimeRemaining,
            powerSavingActive: this.powerSavingMode.level !== 'none',
            recommendations,
        };
    }

    public destroy(): void {
        this.stopBatteryMonitoring();
        this.batteryCallbacks = [];
        this.powerModeCallbacks = [];
    }
}

export default BatteryOptimizer;