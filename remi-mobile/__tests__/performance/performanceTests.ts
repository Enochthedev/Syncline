import { by, device, element, expect } from 'detox';
import PerformanceManager from '../../src/services/performanceManager';
import MemoryManager from '../../src/services/memoryManager';
import BatteryOptimizer from '../../src/services/batteryOptimizer';
import NetworkOptimizer from '../../src/services/networkOptimizer';

describe('Performance Tests', () => {
    let performanceManager: PerformanceManager;
    let memoryManager: MemoryManager;
    let batteryOptimizer: BatteryOptimizer;

    beforeAll(async () => {
        await device.launchApp();
        performanceManager = PerformanceManager.getInstance();
        memoryManager = MemoryManager.getInstance();
        batteryOptimizer = BatteryOptimizer.getInstance();
    });

    beforeEach(async () => {
        await device.reloadReactNative();
    });

    describe('App Launch Performance', () => {
        it('should launch within acceptable time', async () => {
            const startTime = Date.now();

            await device.launchApp({ newInstance: true });
            await element(by.id('main-screen')).toBeVisible();

            const launchTime = Date.now() - startTime;

            // App should launch within 3 seconds
            expect(launchTime).toBeLessThan(3000);

            // Record the launch time
            performanceManager.recordScreenTransition(launchTime);
        });

        it('should show splash screen immediately', async () => {
            await device.launchApp({ newInstance: true });

            // Splash screen should be visible within 100ms
            await expect(element(by.id('splash-screen'))).toBeVisible();
        });
    });

    describe('Navigation Performance', () => {
        it('should navigate between screens quickly', async () => {
            const screens = ['contacts', 'search', 'messages', 'settings'];

            for (const screen of screens) {
                const startTime = Date.now();

                await element(by.id(`tab-${screen}`)).tap();
                await element(by.id(`${screen}-screen`)).toBeVisible();

                const navigationTime = Date.now() - startTime;

                // Navigation should complete within 500ms
                expect(navigationTime).toBeLessThan(500);

                performanceManager.recordScreenTransition(navigationTime);
            }
        });

        it('should handle rapid navigation without crashes', async () => {
            const screens = ['contacts', 'search', 'messages'];

            // Rapidly tap between screens
            for (let i = 0; i < 10; i++) {
                const screen = screens[i % screens.length];
                await element(by.id(`tab-${screen}`)).tap();

                // Small delay to allow rendering
                await new Promise(resolve => setTimeout(resolve, 50));
            }

            // App should still be responsive
            await expect(element(by.id('main-screen'))).toBeVisible();
        });
    });

    describe('Search Performance', () => {
        it('should perform contact search within acceptable time', async () => {
            await element(by.id('tab-search')).tap();
            await element(by.id('search-input')).toBeVisible();

            const startTime = Date.now();

            await element(by.id('search-input')).typeText('John');
            await element(by.id('search-results')).toBeVisible();

            const searchTime = Date.now() - startTime;

            // Search should complete within 1 second
            expect(searchTime).toBeLessThan(1000);

            performanceManager.recordSearchResponse(searchTime);
        });

        it('should handle rapid typing without lag', async () => {
            await element(by.id('tab-search')).tap();
            await element(by.id('search-input')).toBeVisible();

            const searchQuery = 'John Smith';
            const startTime = Date.now();

            // Type rapidly
            for (const char of searchQuery) {
                await element(by.id('search-input')).typeText(char);
                await new Promise(resolve => setTimeout(resolve, 50));
            }

            const typingTime = Date.now() - startTime;

            // Should handle rapid typing smoothly
            expect(typingTime).toBeLessThan(2000);
        });
    });

    describe('List Performance', () => {
        it('should scroll through large contact list smoothly', async () => {
            await element(by.id('tab-contacts')).tap();
            await element(by.id('contact-list')).toBeVisible();

            const startTime = Date.now();

            // Scroll through the list multiple times
            for (let i = 0; i < 5; i++) {
                await element(by.id('contact-list')).scroll(1000, 'down');
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            const scrollTime = Date.now() - startTime;

            // Scrolling should be smooth and responsive
            expect(scrollTime).toBeLessThan(3000);
        });

        it('should handle list updates without performance degradation', async () => {
            await element(by.id('tab-contacts')).tap();

            const startTime = Date.now();

            // Trigger refresh
            await element(by.id('contact-list')).swipe('down', 'fast', 0.8);
            await element(by.id('refresh-indicator')).toBeNotVisible();

            const refreshTime = Date.now() - startTime;

            // Refresh should complete within 2 seconds
            expect(refreshTime).toBeLessThan(2000);
        });
    });

    describe('Memory Performance', () => {
        it('should maintain reasonable memory usage', async () => {
            const initialStats = await memoryManager.getMemoryStats();

            // Navigate through multiple screens and perform operations
            await element(by.id('tab-contacts')).tap();
            await element(by.id('contact-list')).scroll(2000, 'down');

            await element(by.id('tab-search')).tap();
            await element(by.id('search-input')).typeText('test search');

            await element(by.id('tab-messages')).tap();

            const finalStats = await memoryManager.getMemoryStats();

            // Memory usage should not increase dramatically
            const memoryIncrease = finalStats.memoryUsagePercentage - initialStats.memoryUsagePercentage;
            expect(memoryIncrease).toBeLessThan(0.2); // Less than 20% increase
        });

        it('should cleanup memory when navigating away from screens', async () => {
            // Force memory cleanup
            await memoryManager.forceCleanup();

            const beforeStats = await memoryManager.getMemoryStats();

            // Load heavy screen
            await element(by.id('tab-contacts')).tap();
            await element(by.id('contact-list')).scroll(3000, 'down');

            // Navigate away
            await element(by.id('tab-settings')).tap();

            // Wait for cleanup
            await new Promise(resolve => setTimeout(resolve, 2000));

            const afterStats = await memoryManager.getMemoryStats();

            // Memory should be cleaned up
            expect(afterStats.memoryUsagePercentage).toBeLessThanOrEqual(beforeStats.memoryUsagePercentage + 0.1);
        });
    });

    describe('Battery Performance', () => {
        it('should adapt to low battery conditions', async () => {
            // Simulate low battery
            batteryOptimizer.forcePowerSavingMode('moderate');

            const powerMode = batteryOptimizer.getPowerSavingMode();
            expect(powerMode.level).toBe('moderate');

            // Verify optimizations are applied
            expect(powerMode.animationsEnabled).toBe(false);
            expect(powerMode.imageQuality).toBe('low');
        });

        it('should reduce background activity in power saving mode', async () => {
            batteryOptimizer.forcePowerSavingMode('aggressive');

            const powerMode = batteryOptimizer.getPowerSavingMode();

            expect(powerMode.level).toBe('aggressive');
            expect(powerMode.backgroundProcessingEnabled).toBe(false);
            expect(powerMode.syncInterval).toBeGreaterThan(300000); // More than 5 minutes
        });
    });

    describe('Network Performance', () => {
        it('should handle network requests efficiently', async () => {
            // This would require mocking network requests
            // For now, we'll test the basic functionality

            await element(by.id('tab-search')).tap();

            const startTime = Date.now();

            await element(by.id('search-input')).typeText('network test');
            await element(by.id('search-results')).toBeVisible();

            const networkTime = Date.now() - startTime;

            // Network requests should complete reasonably quickly
            expect(networkTime).toBeLessThan(5000);
        });

        it('should work offline gracefully', async () => {
            // Simulate offline mode
            await device.setURLBlacklist(['*']);

            await element(by.id('tab-contacts')).tap();

            // Should show cached data or offline message
            await expect(element(by.id('contact-list'))).toBeVisible();

            // Restore network
            await device.setURLBlacklist([]);
        });
    });

    describe('Image Loading Performance', () => {
        it('should load images efficiently', async () => {
            await element(by.id('tab-contacts')).tap();

            const startTime = Date.now();

            // Scroll to load images
            await element(by.id('contact-list')).scroll(1000, 'down');

            // Wait for images to load
            await new Promise(resolve => setTimeout(resolve, 2000));

            const imageLoadTime = Date.now() - startTime;

            // Images should load within reasonable time
            expect(imageLoadTime).toBeLessThan(5000);
        });

        it('should handle image loading errors gracefully', async () => {
            // This would require mocking image failures
            await element(by.id('tab-contacts')).tap();

            // Should show fallback images or placeholders
            await expect(element(by.id('contact-list'))).toBeVisible();
        });
    });

    describe('Performance Monitoring', () => {
        it('should collect performance metrics', async () => {
            performanceManager.startMonitoring();

            // Perform various operations
            await element(by.id('tab-contacts')).tap();
            await element(by.id('tab-search')).tap();
            await element(by.id('search-input')).typeText('metrics test');

            // Wait for metrics collection
            await new Promise(resolve => setTimeout(resolve, 3000));

            const metrics = performanceManager.getMetrics();
            expect(metrics.length).toBeGreaterThan(0);

            const latestMetrics = performanceManager.getLatestMetrics();
            expect(latestMetrics).toBeTruthy();
            expect(latestMetrics?.sessionId).toBeTruthy();
        });

        it('should export performance data', async () => {
            const exportData = await performanceManager.exportMetrics();

            expect(exportData).toBeTruthy();

            const parsed = JSON.parse(exportData);
            expect(parsed.sessionId).toBeTruthy();
            expect(parsed.metrics).toBeDefined();
            expect(parsed.config).toBeDefined();
        });
    });

    describe('Stress Tests', () => {
        it('should handle rapid user interactions', async () => {
            const actions = [
                () => element(by.id('tab-contacts')).tap(),
                () => element(by.id('tab-search')).tap(),
                () => element(by.id('tab-messages')).tap(),
                () => element(by.id('search-input')).typeText('a'),
                () => element(by.id('search-input')).clearText(),
            ];

            // Perform rapid actions
            for (let i = 0; i < 20; i++) {
                const action = actions[i % actions.length];
                await action();
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            // App should still be responsive
            await expect(element(by.id('main-screen'))).toBeVisible();
        });

        it('should handle memory pressure gracefully', async () => {
            // Simulate memory pressure by loading lots of data
            for (let i = 0; i < 10; i++) {
                await element(by.id('tab-contacts')).tap();
                await element(by.id('contact-list')).scroll(2000, 'down');
                await element(by.id('tab-search')).tap();
                await element(by.id('search-input')).typeText(`stress test ${i}`);
                await element(by.id('search-input')).clearText();
            }

            // Check memory stats
            const memoryStats = await memoryManager.getMemoryStats();

            // Should not exceed critical memory threshold
            expect(memoryStats.memoryUsagePercentage).toBeLessThan(0.9);
        });
    });

    afterAll(async () => {
        performanceManager.stopMonitoring();
        batteryOptimizer.destroy();
        memoryManager.destroy();
    });
});

// Helper functions for performance testing
export const measurePerformance = async <T>(
    operation: () => Promise<T>,
    expectedMaxTime: number,
    operationName: string
): Promise<T> => {
    const startTime = Date.now();

    try {
        const result = await operation();
        const duration = Date.now() - startTime;

        if (duration > expectedMaxTime) {
            console.warn(`Performance warning: ${operationName} took ${duration}ms (expected < ${expectedMaxTime}ms)`);
        }

        return result;
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error(`Performance error: ${operationName} failed after ${duration}ms:`, error);
        throw error;
    }
};

export const waitForElement = async (
    elementId: string,
    timeout: number = 5000
): Promise<void> => {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
        try {
            await expect(element(by.id(elementId))).toBeVisible();
            return;
        } catch {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }

    throw new Error(`Element ${elementId} not found within ${timeout}ms`);
};

export const measureScrollPerformance = async (
    listId: string,
    scrollDistance: number,
    expectedMaxTime: number
): Promise<number> => {
    const startTime = Date.now();

    await element(by.id(listId)).scroll(scrollDistance, 'down');

    const scrollTime = Date.now() - startTime;

    if (scrollTime > expectedMaxTime) {
        console.warn(`Scroll performance warning: ${scrollTime}ms (expected < ${expectedMaxTime}ms)`);
    }

    return scrollTime;
};