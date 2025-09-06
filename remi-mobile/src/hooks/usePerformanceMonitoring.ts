import { useEffect, useRef, useState, useCallback } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import PerformanceManager from '../services/performanceManager';
import MemoryManager from '../services/memoryManager';
import type { PerformanceMetrics, MemoryStats } from '../services/performanceManager';

export interface PerformanceHookOptions {
    enableMemoryMonitoring?: boolean;
    enablePerformanceTracking?: boolean;
    enableBatteryOptimization?: boolean;
    monitoringInterval?: number;
}

export interface PerformanceHookResult {
    metrics: PerformanceMetrics | null;
    memoryStats: MemoryStats | null;
    isMonitoring: boolean;
    startMonitoring: () => void;
    stopMonitoring: () => void;
    recordScreenTransition: (duration: number) => void;
    recordSearchResponse: (duration: number) => void;
    forceMemoryCleanup: () => Promise<void>;
    exportMetrics: () => Promise<string>;
}

export const usePerformanceMonitoring = (
    options: PerformanceHookOptions = {}
): PerformanceHookResult => {
    const {
        enableMemoryMonitoring = true,
        enablePerformanceTracking = true,
        enableBatteryOptimization = true,
        monitoringInterval = 60000, // 1 minute
    } = options;

    const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
    const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
    const [isMonitoring, setIsMonitoring] = useState(false);

    const performanceManager = useRef(PerformanceManager.getInstance());
    const memoryManager = useRef(MemoryManager.getInstance());
    const monitoringInterval = useRef<NodeJS.Timeout | null>(null);
    const appStateRef = useRef<AppStateStatus>(AppState.currentState);

    // Update metrics periodically
    const updateMetrics = useCallback(async () => {
        if (!isMonitoring) return;

        try {
            if (enablePerformanceTracking) {
                const latestMetrics = performanceManager.current.getLatestMetrics();
                setMetrics(latestMetrics);
            }

            if (enableMemoryMonitoring) {
                const latestMemoryStats = await memoryManager.current.getMemoryStats();
                setMemoryStats(latestMemoryStats);
            }
        } catch (error) {
            console.error('Failed to update performance metrics:', error);
        }
    }, [isMonitoring, enablePerformanceTracking, enableMemoryMonitoring]);

    // Start monitoring
    const startMonitoring = useCallback(() => {
        if (isMonitoring) return;

        setIsMonitoring(true);

        if (enablePerformanceTracking) {
            performanceManager.current.startMonitoring();
        }

        // Set up periodic updates
        monitoringInterval.current = setInterval(updateMetrics, monitoringInterval);

        // Initial update
        updateMetrics();

        console.log('Performance monitoring started');
    }, [isMonitoring, enablePerformanceTracking, updateMetrics, monitoringInterval]);

    // Stop monitoring
    const stopMonitoring = useCallback(() => {
        if (!isMonitoring) return;

        setIsMonitoring(false);

        if (enablePerformanceTracking) {
            performanceManager.current.stopMonitoring();
        }

        if (monitoringInterval.current) {
            clearInterval(monitoringInterval.current);
            monitoringInterval.current = null;
        }

        console.log('Performance monitoring stopped');
    }, [isMonitoring, enablePerformanceTracking]);

    // Record screen transition time
    const recordScreenTransition = useCallback((duration: number) => {
        if (enablePerformanceTracking) {
            performanceManager.current.recordScreenTransition(duration);
        }
    }, [enablePerformanceTracking]);

    // Record search response time
    const recordSearchResponse = useCallback((duration: number) => {
        if (enablePerformanceTracking) {
            performanceManager.current.recordSearchResponse(duration);
        }
    }, [enablePerformanceTracking]);

    // Force memory cleanup
    const forceMemoryCleanup = useCallback(async () => {
        if (enableMemoryMonitoring) {
            await memoryManager.current.forceCleanup();
            // Update memory stats after cleanup
            const updatedStats = await memoryManager.current.getMemoryStats();
            setMemoryStats(updatedStats);
        }
    }, [enableMemoryMonitoring]);

    // Export metrics
    const exportMetrics = useCallback(async () => {
        return await performanceManager.current.exportMetrics();
    }, []);

    // Handle app state changes for battery optimization
    useEffect(() => {
        if (!enableBatteryOptimization) return;

        const handleAppStateChange = (nextAppState: AppStateStatus) => {
            const previousState = appStateRef.current;
            appStateRef.current = nextAppState;

            if (previousState === 'active' && nextAppState.match(/inactive|background/)) {
                // App went to background - reduce monitoring frequency
                if (monitoringInterval.current) {
                    clearInterval(monitoringInterval.current);
                    monitoringInterval.current = setInterval(updateMetrics, monitoringInterval * 5); // 5x slower
                }
            } else if (previousState.match(/inactive|background/) && nextAppState === 'active') {
                // App came to foreground - restore normal monitoring
                if (monitoringInterval.current) {
                    clearInterval(monitoringInterval.current);
                    monitoringInterval.current = setInterval(updateMetrics, monitoringInterval);
                }
                // Immediate update when returning to foreground
                updateMetrics();
            }
        };

        const subscription = AppState.addEventListener('change', handleAppStateChange);

        return () => {
            subscription?.remove();
        };
    }, [enableBatteryOptimization, updateMetrics, monitoringInterval]);

    // Memory warning handler
    useEffect(() => {
        if (!enableMemoryMonitoring) return;

        const unsubscribe = memoryManager.current.onMemoryWarning((stats) => {
            console.warn('Memory warning received:', stats);
            setMemoryStats(stats);

            // Optionally trigger automatic cleanup
            memoryManager.current.forceCleanup().catch(error => {
                console.error('Failed to cleanup memory after warning:', error);
            });
        });

        return unsubscribe;
    }, [enableMemoryMonitoring]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (monitoringInterval.current) {
                clearInterval(monitoringInterval.current);
            }
        };
    }, []);

    return {
        metrics,
        memoryStats,
        isMonitoring,
        startMonitoring,
        stopMonitoring,
        recordScreenTransition,
        recordSearchResponse,
        forceMemoryCleanup,
        exportMetrics,
    };
};

// Hook for measuring component render performance
export const useRenderPerformance = (componentName: string) => {
    const renderStartTime = useRef<number>(Date.now());
    const renderCount = useRef<number>(0);
    const { recordScreenTransition } = usePerformanceMonitoring();

    useEffect(() => {
        renderCount.current++;
        const renderTime = Date.now() - renderStartTime.current;

        if (renderTime > 16) { // More than one frame at 60fps
            console.warn(`Slow render detected in ${componentName}: ${renderTime}ms`);
        }

        // Record transition time for navigation components
        if (componentName.includes('Screen') || componentName.includes('Navigator')) {
            recordScreenTransition(renderTime);
        }

        renderStartTime.current = Date.now();
    });

    return {
        renderCount: renderCount.current,
        componentName,
    };
};

// Hook for measuring async operation performance
export const useAsyncPerformance = () => {
    const { recordSearchResponse } = usePerformanceMonitoring();

    const measureAsync = useCallback(async <T>(
        operation: () => Promise<T>,
        operationType: 'search' | 'api' | 'database' | 'other' = 'other'
    ): Promise<T> => {
        const startTime = Date.now();

        try {
            const result = await operation();
            const duration = Date.now() - startTime;

            // Record specific operation types
            if (operationType === 'search') {
                recordSearchResponse(duration);
            }

            // Log slow operations
            if (duration > 1000) { // More than 1 second
                console.warn(`Slow ${operationType} operation: ${duration}ms`);
            }

            return result;
        } catch (error) {
            const duration = Date.now() - startTime;
            console.error(`Failed ${operationType} operation after ${duration}ms:`, error);
            throw error;
        }
    }, [recordSearchResponse]);

    return { measureAsync };
};

export default usePerformanceMonitoring;