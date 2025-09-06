import { Platform } from 'react-native';
import DeviceInfo from 'react-native-device-info';

export interface DeviceCapabilities {
    isLowEndDevice: boolean;
    totalMemory: number;
    availableMemory: number;
    cpuCount: number;
    screenDensity: number;
    isTablet: boolean;
    hasNotch: boolean;
    supportsBiometrics: boolean;
}

export interface PerformanceProfile {
    name: string;
    imageQuality: 'low' | 'medium' | 'high';
    animationDuration: number;
    listPageSize: number;
    cacheSize: number;
    backgroundSyncInterval: number;
    enableVirtualization: boolean;
    enableImageOptimization: boolean;
    enableMemoryOptimization: boolean;
    enableBatteryOptimization: boolean;
}

export class PerformanceConfig {
    private static instance: PerformanceConfig;
    private deviceCapabilities: DeviceCapabilities | null = null;
    private currentProfile: PerformanceProfile | null = null;

    private constructor() { }

    public static getInstance(): PerformanceConfig {
        if (!PerformanceConfig.instance) {
            PerformanceConfig.instance = new PerformanceConfig();
        }
        return PerformanceConfig.instance;
    }

    public async initialize(): Promise<void> {
        this.deviceCapabilities = await this.detectDeviceCapabilities();
        this.currentProfile = this.selectOptimalProfile(this.deviceCapabilities);

        console.log('Performance configuration initialized:', {
            capabilities: this.deviceCapabilities,
            profile: this.currentProfile,
        });
    }

    private async detectDeviceCapabilities(): Promise<DeviceCapabilities> {
        try {
            const [
                totalMemory,
                isLowRamDevice,
                isTablet,
                hasNotch,
                supportsBiometrics,
            ] = await Promise.all([
                DeviceInfo.getTotalMemory(),
                DeviceInfo.isLowRamDevice(),
                DeviceInfo.isTablet(),
                DeviceInfo.hasNotch(),
                DeviceInfo.supportedAbis().then(abis => abis.length > 0),
            ]);

            // Estimate available memory (rough calculation)
            const availableMemory = totalMemory * 0.7; // Assume 70% available

            // Determine if this is a low-end device
            const isLowEndDevice = isLowRamDevice || totalMemory < 2 * 1024 * 1024 * 1024; // Less than 2GB

            // Get screen density
            const screenDensity = Platform.select({
                ios: 2, // Assume retina
                android: 2, // Default to high density
                default: 1,
            });

            // Estimate CPU count (not directly available)
            const cpuCount = Platform.select({
                ios: isLowEndDevice ? 2 : 4,
                android: isLowEndDevice ? 2 : 4,
                default: 2,
            });

            return {
                isLowEndDevice,
                totalMemory,
                availableMemory,
                cpuCount,
                screenDensity,
                isTablet,
                hasNotch,
                supportsBiometrics,
            };
        } catch (error) {
            console.error('Failed to detect device capabilities:', error);

            // Return conservative defaults
            return {
                isLowEndDevice: true,
                totalMemory: 1024 * 1024 * 1024, // 1GB
                availableMemory: 512 * 1024 * 1024, // 512MB
                cpuCount: 2,
                screenDensity: 2,
                isTablet: false,
                hasNotch: false,
                supportsBiometrics: false,
            };
        }
    }

    private selectOptimalProfile(capabilities: DeviceCapabilities): PerformanceProfile {
        if (capabilities.isLowEndDevice) {
            return this.getLowEndProfile();
        } else if (capabilities.totalMemory > 6 * 1024 * 1024 * 1024) { // More than 6GB
            return this.getHighEndProfile();
        } else {
            return this.getMidRangeProfile();
        }
    }

    private getLowEndProfile(): PerformanceProfile {
        return {
            name: 'Low-End Device',
            imageQuality: 'low',
            animationDuration: 150, // Shorter animations
            listPageSize: 10,
            cacheSize: 25 * 1024 * 1024, // 25MB
            backgroundSyncInterval: 10 * 60 * 1000, // 10 minutes
            enableVirtualization: true,
            enableImageOptimization: true,
            enableMemoryOptimization: true,
            enableBatteryOptimization: true,
        };
    }

    private getMidRangeProfile(): PerformanceProfile {
        return {
            name: 'Mid-Range Device',
            imageQuality: 'medium',
            animationDuration: 200,
            listPageSize: 20,
            cacheSize: 50 * 1024 * 1024, // 50MB
            backgroundSyncInterval: 5 * 60 * 1000, // 5 minutes
            enableVirtualization: true,
            enableImageOptimization: true,
            enableMemoryOptimization: true,
            enableBatteryOptimization: true,
        };
    }

    private getHighEndProfile(): PerformanceProfile {
        return {
            name: 'High-End Device',
            imageQuality: 'high',
            animationDuration: 300,
            listPageSize: 50,
            cacheSize: 100 * 1024 * 1024, // 100MB
            backgroundSyncInterval: 2 * 60 * 1000, // 2 minutes
            enableVirtualization: false, // High-end devices can handle more items
            enableImageOptimization: false,
            enableMemoryOptimization: false,
            enableBatteryOptimization: false,
        };
    }

    public getDeviceCapabilities(): DeviceCapabilities | null {
        return this.deviceCapabilities;
    }

    public getCurrentProfile(): PerformanceProfile | null {
        return this.currentProfile;
    }

    public setProfile(profile: PerformanceProfile): void {
        this.currentProfile = profile;
        console.log('Performance profile updated:', profile.name);
    }

    public getCustomProfile(overrides: Partial<PerformanceProfile>): PerformanceProfile {
        if (!this.currentProfile) {
            throw new Error('Performance config not initialized');
        }

        return {
            ...this.currentProfile,
            ...overrides,
        };
    }

    // Specific configuration getters
    public getImageConfig(): {
        quality: 'low' | 'medium' | 'high';
        enableOptimization: boolean;
        cacheSize: number;
    } {
        if (!this.currentProfile) {
            throw new Error('Performance config not initialized');
        }

        return {
            quality: this.currentProfile.imageQuality,
            enableOptimization: this.currentProfile.enableImageOptimization,
            cacheSize: this.currentProfile.cacheSize * 0.3, // 30% of total cache for images
        };
    }

    public getListConfig(): {
        pageSize: number;
        enableVirtualization: boolean;
        windowSize: number;
        maxToRenderPerBatch: number;
    } {
        if (!this.currentProfile) {
            throw new Error('Performance config not initialized');
        }

        const basePageSize = this.currentProfile.listPageSize;

        return {
            pageSize: basePageSize,
            enableVirtualization: this.currentProfile.enableVirtualization,
            windowSize: Math.max(5, Math.floor(basePageSize / 2)),
            maxToRenderPerBatch: Math.max(5, Math.floor(basePageSize / 4)),
        };
    }

    public getAnimationConfig(): {
        duration: number;
        enabled: boolean;
        useNativeDriver: boolean;
    } {
        if (!this.currentProfile) {
            throw new Error('Performance config not initialized');
        }

        return {
            duration: this.currentProfile.animationDuration,
            enabled: this.currentProfile.animationDuration > 0,
            useNativeDriver: true, // Always use native driver for better performance
        };
    }

    public getMemoryConfig(): {
        maxCacheSize: number;
        enableOptimization: boolean;
        cleanupThreshold: number;
    } {
        if (!this.currentProfile || !this.deviceCapabilities) {
            throw new Error('Performance config not initialized');
        }

        return {
            maxCacheSize: this.currentProfile.cacheSize,
            enableOptimization: this.currentProfile.enableMemoryOptimization,
            cleanupThreshold: this.deviceCapabilities.isLowEndDevice ? 0.7 : 0.8,
        };
    }

    public getNetworkConfig(): {
        batchSize: number;
        timeout: number;
        enableCompression: boolean;
        enableCaching: boolean;
    } {
        if (!this.currentProfile || !this.deviceCapabilities) {
            throw new Error('Performance config not initialized');
        }

        const isLowEnd = this.deviceCapabilities.isLowEndDevice;

        return {
            batchSize: isLowEnd ? 5 : 10,
            timeout: isLowEnd ? 45000 : 30000,
            enableCompression: true,
            enableCaching: true,
        };
    }

    public getBatteryConfig(): {
        enableOptimization: boolean;
        backgroundSyncInterval: number;
        adaptivePolling: boolean;
    } {
        if (!this.currentProfile) {
            throw new Error('Performance config not initialized');
        }

        return {
            enableOptimization: this.currentProfile.enableBatteryOptimization,
            backgroundSyncInterval: this.currentProfile.backgroundSyncInterval,
            adaptivePolling: true,
        };
    }

    // Dynamic configuration based on current conditions
    public async getAdaptiveConfig(): Promise<{
        shouldReduceQuality: boolean;
        shouldEnablePowerSaving: boolean;
        shouldReduceAnimations: boolean;
        recommendedProfile: PerformanceProfile;
    }> {
        if (!this.deviceCapabilities) {
            throw new Error('Performance config not initialized');
        }

        try {
            const [batteryLevel, memoryUsage, isCharging] = await Promise.all([
                DeviceInfo.getBatteryLevel(),
                this.getMemoryUsage(),
                DeviceInfo.isBatteryCharging(),
            ]);

            const shouldReduceQuality = memoryUsage > 0.8 || (batteryLevel < 0.2 && !isCharging);
            const shouldEnablePowerSaving = batteryLevel < 0.3 && !isCharging;
            const shouldReduceAnimations = memoryUsage > 0.9 || batteryLevel < 0.1;

            let recommendedProfile = this.currentProfile!;

            if (shouldReduceQuality) {
                recommendedProfile = this.getCustomProfile({
                    imageQuality: 'low',
                    enableImageOptimization: true,
                    enableMemoryOptimization: true,
                });
            }

            if (shouldEnablePowerSaving) {
                recommendedProfile = this.getCustomProfile({
                    ...recommendedProfile,
                    enableBatteryOptimization: true,
                    backgroundSyncInterval: 15 * 60 * 1000, // 15 minutes
                    animationDuration: 100,
                });
            }

            return {
                shouldReduceQuality,
                shouldEnablePowerSaving,
                shouldReduceAnimations,
                recommendedProfile,
            };
        } catch (error) {
            console.error('Failed to get adaptive config:', error);

            return {
                shouldReduceQuality: false,
                shouldEnablePowerSaving: false,
                shouldReduceAnimations: false,
                recommendedProfile: this.currentProfile!,
            };
        }
    }

    private async getMemoryUsage(): Promise<number> {
        try {
            const [totalMemory, usedMemory] = await Promise.all([
                DeviceInfo.getTotalMemory(),
                DeviceInfo.getUsedMemory(),
            ]);

            return usedMemory / totalMemory;
        } catch (error) {
            console.error('Failed to get memory usage:', error);
            return 0.5; // Conservative estimate
        }
    }

    // Performance recommendations
    public getPerformanceRecommendations(): string[] {
        if (!this.deviceCapabilities || !this.currentProfile) {
            return ['Initialize performance configuration first'];
        }

        const recommendations: string[] = [];

        if (this.deviceCapabilities.isLowEndDevice) {
            recommendations.push('Consider enabling all performance optimizations');
            recommendations.push('Use low image quality for better performance');
            recommendations.push('Enable memory cleanup and battery optimization');
        }

        if (this.deviceCapabilities.totalMemory < 3 * 1024 * 1024 * 1024) { // Less than 3GB
            recommendations.push('Enable memory optimization');
            recommendations.push('Reduce cache size if experiencing memory issues');
        }

        if (!this.currentProfile.enableVirtualization && this.currentProfile.listPageSize > 30) {
            recommendations.push('Consider enabling list virtualization for large datasets');
        }

        return recommendations;
    }
}

export default PerformanceConfig;