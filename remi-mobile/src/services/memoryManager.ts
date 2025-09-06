import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';
import { Platform } from 'react-native';

export interface MemoryStats {
    totalMemory: number;
    usedMemory: number;
    availableMemory: number;
    memoryUsagePercentage: number;
    cacheSize: number;
    timestamp: number;
}

export interface CacheEntry {
    key: string;
    data: any;
    timestamp: number;
    size: number;
    accessCount: number;
    lastAccessed: number;
}

export interface MemoryConfig {
    maxCacheSize: number;
    maxCacheEntries: number;
    cacheExpirationTime: number;
    memoryWarningThreshold: number;
    aggressiveCleanupThreshold: number;
    enableAutoCleanup: boolean;
}

class MemoryManager {
    private static instance: MemoryManager;
    private cache: Map<string, CacheEntry> = new Map();
    private config: MemoryConfig;
    private cleanupInterval: NodeJS.Timeout | null = null;
    private memoryWarningCallbacks: Array<(stats: MemoryStats) => void> = [];

    private constructor() {
        this.config = this.getDefaultConfig();
        this.initializeMemoryManagement();
    }

    public static getInstance(): MemoryManager {
        if (!MemoryManager.instance) {
            MemoryManager.instance = new MemoryManager();
        }
        return MemoryManager.instance;
    }

    private getDefaultConfig(): MemoryConfig {
        return {
            maxCacheSize: 50 * 1024 * 1024, // 50MB
            maxCacheEntries: 1000,
            cacheExpirationTime: 30 * 60 * 1000, // 30 minutes
            memoryWarningThreshold: 0.8, // 80%
            aggressiveCleanupThreshold: 0.9, // 90%
            enableAutoCleanup: true,
        };
    }

    private async initializeMemoryManagement(): Promise<void> {
        try {
            // Load saved configuration
            const savedConfig = await AsyncStorage.getItem('memory_config');
            if (savedConfig) {
                this.config = { ...this.config, ...JSON.parse(savedConfig) };
            }

            // Start automatic cleanup if enabled
            if (this.config.enableAutoCleanup) {
                this.startAutoCleanup();
            }

            // Setup memory monitoring
            this.startMemoryMonitoring();

            console.log('Memory management initialized');
        } catch (error) {
            console.error('Failed to initialize memory management:', error);
        }
    }

    private startAutoCleanup(): void {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }

        this.cleanupInterval = setInterval(() => {
            this.performAutomaticCleanup();
        }, 5 * 60 * 1000); // Every 5 minutes
    }

    private startMemoryMonitoring(): void {
        setInterval(async () => {
            const stats = await this.getMemoryStats();

            if (stats.memoryUsagePercentage > this.config.memoryWarningThreshold) {
                this.handleMemoryWarning(stats);
            }

            if (stats.memoryUsagePercentage > this.config.aggressiveCleanupThreshold) {
                await this.performAggressiveCleanup();
            }
        }, 30 * 1000); // Every 30 seconds
    }

    private handleMemoryWarning(stats: MemoryStats): void {
        console.warn('Memory warning:', stats);

        // Notify registered callbacks
        this.memoryWarningCallbacks.forEach(callback => {
            try {
                callback(stats);
            } catch (error) {
                console.error('Memory warning callback error:', error);
            }
        });

        // Trigger cleanup
        this.performAutomaticCleanup();
    }

    public async getMemoryStats(): Promise<MemoryStats> {
        try {
            const totalMemory = await DeviceInfo.getTotalMemory();
            const usedMemory = await DeviceInfo.getUsedMemory();
            const availableMemory = totalMemory - usedMemory;
            const cacheSize = this.calculateCacheSize();

            return {
                totalMemory,
                usedMemory,
                availableMemory,
                memoryUsagePercentage: usedMemory / totalMemory,
                cacheSize,
                timestamp: Date.now(),
            };
        } catch (error) {
            console.error('Failed to get memory stats:', error);
            return {
                totalMemory: 0,
                usedMemory: 0,
                availableMemory: 0,
                memoryUsagePercentage: 0,
                cacheSize: 0,
                timestamp: Date.now(),
            };
        }
    }

    private calculateCacheSize(): number {
        let totalSize = 0;
        this.cache.forEach(entry => {
            totalSize += entry.size;
        });
        return totalSize;
    }

    public setItem(key: string, data: any, options?: { ttl?: number }): void {
        try {
            const serializedData = JSON.stringify(data);
            const size = this.estimateSize(serializedData);
            const now = Date.now();

            const entry: CacheEntry = {
                key,
                data,
                timestamp: now,
                size,
                accessCount: 1,
                lastAccessed: now,
            };

            // Check if adding this entry would exceed limits
            if (this.shouldEvictBeforeAdd(size)) {
                this.evictLeastRecentlyUsed();
            }

            this.cache.set(key, entry);

            // Check cache size limits
            this.enforceCacheLimits();
        } catch (error) {
            console.error('Failed to set cache item:', error);
        }
    }

    public getItem(key: string): any | null {
        const entry = this.cache.get(key);

        if (!entry) {
            return null;
        }

        // Check if entry has expired
        const now = Date.now();
        const ttl = this.config.cacheExpirationTime;

        if (now - entry.timestamp > ttl) {
            this.cache.delete(key);
            return null;
        }

        // Update access statistics
        entry.accessCount++;
        entry.lastAccessed = now;

        return entry.data;
    }

    public removeItem(key: string): void {
        this.cache.delete(key);
    }

    public clear(): void {
        this.cache.clear();
    }

    private shouldEvictBeforeAdd(newItemSize: number): boolean {
        const currentSize = this.calculateCacheSize();
        const wouldExceedSize = currentSize + newItemSize > this.config.maxCacheSize;
        const wouldExceedCount = this.cache.size >= this.config.maxCacheEntries;

        return wouldExceedSize || wouldExceedCount;
    }

    private evictLeastRecentlyUsed(): void {
        if (this.cache.size === 0) return;

        let lruKey: string | null = null;
        let oldestAccess = Date.now();

        this.cache.forEach((entry, key) => {
            if (entry.lastAccessed < oldestAccess) {
                oldestAccess = entry.lastAccessed;
                lruKey = key;
            }
        });

        if (lruKey) {
            this.cache.delete(lruKey);
        }
    }

    private enforceCacheLimits(): void {
        // Enforce size limit
        while (this.calculateCacheSize() > this.config.maxCacheSize && this.cache.size > 0) {
            this.evictLeastRecentlyUsed();
        }

        // Enforce count limit
        while (this.cache.size > this.config.maxCacheEntries) {
            this.evictLeastRecentlyUsed();
        }
    }

    private performAutomaticCleanup(): void {
        const now = Date.now();
        const expiredKeys: string[] = [];

        // Find expired entries
        this.cache.forEach((entry, key) => {
            if (now - entry.timestamp > this.config.cacheExpirationTime) {
                expiredKeys.push(key);
            }
        });

        // Remove expired entries
        expiredKeys.forEach(key => {
            this.cache.delete(key);
        });

        // If still over limits, evict least recently used
        this.enforceCacheLimits();

        if (expiredKeys.length > 0) {
            console.log(`Cleaned up ${expiredKeys.length} expired cache entries`);
        }
    }

    private async performAggressiveCleanup(): Promise<void> {
        console.log('Performing aggressive memory cleanup');

        // Clear half of the cache, starting with least recently used
        const targetSize = Math.floor(this.cache.size / 2);

        const entries = Array.from(this.cache.entries());
        entries.sort((a, b) => a[1].lastAccessed - b[1].lastAccessed);

        for (let i = 0; i < targetSize && entries.length > 0; i++) {
            this.cache.delete(entries[i][0]);
        }

        // Clear AsyncStorage cache
        await this.clearAsyncStorageCache();

        // Force garbage collection if available
        if (global.gc) {
            global.gc();
        }
    }

    private async clearAsyncStorageCache(): Promise<void> {
        try {
            const keys = await AsyncStorage.getAllKeys();
            const cacheKeys = keys.filter(key =>
                key.startsWith('cache_') ||
                key.startsWith('temp_') ||
                key.startsWith('image_cache_')
            );

            if (cacheKeys.length > 0) {
                await AsyncStorage.multiRemove(cacheKeys);
                console.log(`Cleared ${cacheKeys.length} AsyncStorage cache entries`);
            }
        } catch (error) {
            console.error('Failed to clear AsyncStorage cache:', error);
        }
    }

    private estimateSize(data: string): number {
        // Rough estimation of string size in bytes
        return new Blob([data]).size;
    }

    // Public API methods
    public updateConfig(newConfig: Partial<MemoryConfig>): void {
        this.config = { ...this.config, ...newConfig };
        AsyncStorage.setItem('memory_config', JSON.stringify(this.config));

        // Restart auto cleanup with new config
        if (this.config.enableAutoCleanup) {
            this.startAutoCleanup();
        } else if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }
    }

    public getConfig(): MemoryConfig {
        return { ...this.config };
    }

    public getCacheStats(): {
        size: number;
        count: number;
        hitRate: number;
        entries: Array<{ key: string; size: number; accessCount: number; age: number }>;
    } {
        const now = Date.now();
        const entries: Array<{ key: string; size: number; accessCount: number; age: number }> = [];
        let totalAccesses = 0;

        this.cache.forEach((entry, key) => {
            entries.push({
                key,
                size: entry.size,
                accessCount: entry.accessCount,
                age: now - entry.timestamp,
            });
            totalAccesses += entry.accessCount;
        });

        return {
            size: this.calculateCacheSize(),
            count: this.cache.size,
            hitRate: totalAccesses > 0 ? entries.length / totalAccesses : 0,
            entries: entries.sort((a, b) => b.accessCount - a.accessCount),
        };
    }

    public onMemoryWarning(callback: (stats: MemoryStats) => void): () => void {
        this.memoryWarningCallbacks.push(callback);

        // Return unsubscribe function
        return () => {
            const index = this.memoryWarningCallbacks.indexOf(callback);
            if (index > -1) {
                this.memoryWarningCallbacks.splice(index, 1);
            }
        };
    }

    public async forceCleanup(): Promise<void> {
        await this.performAggressiveCleanup();
    }

    public destroy(): void {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }

        this.cache.clear();
        this.memoryWarningCallbacks = [];
    }
}

export default MemoryManager;