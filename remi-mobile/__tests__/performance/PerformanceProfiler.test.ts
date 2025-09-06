/**
 * Performance Testing with Flipper Integration
 * Memory analysis and battery usage monitoring
 */

import { PerformanceProfiler } from '@/utils/PerformanceProfiler';
import { MemoryAnalyzer } from '@/utils/MemoryAnalyzer';
import { BatteryMonitor } from '@/utils/BatteryMonitor';
import { ContactManager } from '@/services/ContactManager';
import { SearchService } from '@/services/SearchService';

// Mock React Native performance APIs
const mockPerformance = {
    now: jest.fn(() => Date.now()),
    mark: jest.fn(),
    measure: jest.fn(),
    getEntriesByType: jest.fn(() => []),
    getEntriesByName: jest.fn(() => []),
};

(global as any).performance = mockPerformance;

// Mock React Native DeviceInfo for battery monitoring
jest.mock('react-native-device-info', () => ({
    getBatteryLevel: jest.fn(() => Promise.resolve(0.85)),
    isBatteryCharging: jest.fn(() => Promise.resolve(false)),
    getPowerState: jest.fn(() => Promise.resolve({
        batteryLevel: 0.85,
        batteryState: 'unplugged',
        lowPowerMode: false,
    })),
}));

// Mock Flipper for performance profiling
const mockFlipper = {
    addPlugin: jest.fn(),
    send: jest.fn(),
    subscribe: jest.fn(),
};

jest.mock('react-native-flipper', () => ({
    logger: {
        info: jest.fn(),
        warn: jest.fn(),
        error: jest.fn(),
    },
    createConnection: jest.fn(() => mockFlipper),
}));

describe('Performance Profiling and Monitoring', () => {
    let performanceProfiler: PerformanceProfiler;
    let memoryAnalyzer: MemoryAnalyzer;
    let batteryMonitor: BatteryMonitor;
    let contactManager: ContactManager;
    let searchService: SearchService;

    beforeEach(() => {
        jest.clearAllMocks();

        performanceProfiler = new PerformanceProfiler();
        memoryAnalyzer = new MemoryAnalyzer();
        batteryMonitor = new BatteryMonitor();
        contactManager = new ContactManager();
        searchService = new SearchService();
    });

    describe('Performance Profiling', () => {
        it('should profile contact search performance', async () => {
            const profileId = 'contact-search-test';

            // Start profiling
            performanceProfiler.startProfile(profileId);

            // Perform contact search operations
            const contacts = Array.from({ length: 1000 }, (_, i) =>
                global.testUtils.createMockContact({ id: `contact-${i}`, name: `Contact ${i}` })
            );

            const startTime = performance.now();

            // Simulate search operations
            for (let i = 0; i < 100; i++) {
                await contactManager.searchContacts(`Contact ${i}`);
            }

            const endTime = performance.now();
            const duration = endTime - startTime;

            // Stop profiling
            const profile = performanceProfiler.stopProfile(profileId);

            // Verify performance metrics
            expect(profile.duration).toBeLessThan(5000); // Should complete within 5 seconds
            expect(profile.operations).toBe(100);
            expect(profile.averageOperationTime).toBeLessThan(50); // Average < 50ms per operation

            // Check memory usage during operations
            expect(profile.memoryUsage.peak).toBeLessThan(100 * 1024 * 1024); // < 100MB peak
            expect(profile.memoryUsage.average).toBeLessThan(50 * 1024 * 1024); // < 50MB average
        });

        it('should profile search service performance', async () => {
            const profileId = 'search-service-test';

            performanceProfiler.startProfile(profileId);

            // Perform various search operations
            const searchQueries = [
                'john',
                'project update',
                'meeting notes',
                'files from sarah',
                'messages last week',
            ];

            const startTime = performance.now();

            for (const query of searchQueries) {
                await searchService.search({ text: query });
                await searchService.getSuggestions(query);
                await searchService.parseNaturalLanguage(query);
            }

            const endTime = performance.now();

            const profile = performanceProfiler.stopProfile(profileId);

            // Verify search performance
            expect(profile.duration).toBeLessThan(3000); // Should complete within 3 seconds
            expect(profile.operations).toBe(15); // 5 queries × 3 operations each
            expect(profile.averageOperationTime).toBeLessThan(200); // Average < 200ms per operation
        });

        it('should profile UI rendering performance', async () => {
            const profileId = 'ui-rendering-test';

            performanceProfiler.startProfile(profileId);

            // Simulate UI rendering operations
            const renderOperations = [
                'ContactList',
                'ContactProfile',
                'MessageThread',
                'SearchResults',
                'ContactCard',
            ];

            for (const component of renderOperations) {
                // Simulate component rendering
                performanceProfiler.markRenderStart(component);

                // Simulate rendering time
                await new Promise(resolve => setTimeout(resolve, Math.random() * 100));

                performanceProfiler.markRenderEnd(component);
            }

            const profile = performanceProfiler.stopProfile(profileId);

            // Verify UI performance
            expect(profile.renderMetrics.averageRenderTime).toBeLessThan(100); // < 100ms average
            expect(profile.renderMetrics.maxRenderTime).toBeLessThan(200); // < 200ms max
            expect(profile.renderMetrics.frameDrops).toBe(0); // No frame drops
        });

        it('should detect performance bottlenecks', async () => {
            const profileId = 'bottleneck-detection';

            performanceProfiler.startProfile(profileId);

            // Simulate operations with varying performance
            const operations = [
                { name: 'fast-operation', duration: 10 },
                { name: 'slow-operation', duration: 500 }, // Bottleneck
                { name: 'medium-operation', duration: 100 },
                { name: 'another-slow-operation', duration: 400 }, // Another bottleneck
            ];

            for (const op of operations) {
                performanceProfiler.markOperationStart(op.name);
                await new Promise(resolve => setTimeout(resolve, op.duration));
                performanceProfiler.markOperationEnd(op.name);
            }

            const profile = performanceProfiler.stopProfile(profileId);
            const bottlenecks = performanceProfiler.detectBottlenecks(profile);

            // Should detect slow operations as bottlenecks
            expect(bottlenecks).toHaveLength(2);
            expect(bottlenecks[0].operation).toBe('slow-operation');
            expect(bottlenecks[1].operation).toBe('another-slow-operation');
            expect(bottlenecks[0].impact).toBeGreaterThan(0.3); // > 30% of total time
        });
    });

    describe('Memory Analysis', () => {
        it('should monitor memory usage during operations', async () => {
            memoryAnalyzer.startMonitoring();

            // Simulate memory-intensive operations
            const largeDataSets = [];

            for (let i = 0; i < 10; i++) {
                // Create large contact datasets
                const contacts = Array.from({ length: 1000 }, (_, j) =>
                    global.testUtils.createMockContact({ id: `contact-${i}-${j}` })
                );
                largeDataSets.push(contacts);

                // Monitor memory after each allocation
                const memorySnapshot = memoryAnalyzer.takeSnapshot();
                expect(memorySnapshot.usedJSHeapSize).toBeDefined();
                expect(memorySnapshot.totalJSHeapSize).toBeDefined();
            }

            const memoryReport = memoryAnalyzer.stopMonitoring();

            // Verify memory usage patterns
            expect(memoryReport.peakUsage).toBeGreaterThan(memoryReport.initialUsage);
            expect(memoryReport.memoryLeaks).toHaveLength(0); // No memory leaks detected
            expect(memoryReport.gcEvents).toBeGreaterThan(0); // Garbage collection occurred
        });

        it('should detect memory leaks', async () => {
            memoryAnalyzer.startMonitoring();

            // Simulate potential memory leak scenario
            const leakyObjects = [];

            for (let i = 0; i < 100; i++) {
                // Create objects that might not be properly cleaned up
                const leakyObject = {
                    id: i,
                    data: new Array(1000).fill(`data-${i}`),
                    circularRef: null as any,
                };

                // Create circular reference (potential leak)
                leakyObject.circularRef = leakyObject;

                leakyObjects.push(leakyObject);

                // Don't clean up references (simulating leak)
            }

            // Force garbage collection
            if (global.gc) {
                global.gc();
            }

            const memoryReport = memoryAnalyzer.stopMonitoring();

            // Should detect potential memory leaks
            expect(memoryReport.potentialLeaks).toBeGreaterThan(0);
            expect(memoryReport.retainedSize).toBeGreaterThan(1024 * 1024); // > 1MB retained
        });

        it('should analyze memory usage by component', async () => {
            memoryAnalyzer.startComponentTracking();

            // Simulate component lifecycle
            const components = ['ContactList', 'ContactProfile', 'MessageThread'];

            for (const component of components) {
                memoryAnalyzer.trackComponentMount(component);

                // Simulate component memory usage
                const componentData = new Array(1000).fill(`${component}-data`);

                // Simulate component operations
                await new Promise(resolve => setTimeout(resolve, 100));

                memoryAnalyzer.trackComponentUnmount(component);
            }

            const componentReport = memoryAnalyzer.getComponentReport();

            // Verify component memory tracking
            expect(componentReport.components).toHaveLength(3);

            componentReport.components.forEach(comp => {
                expect(comp.mountMemory).toBeDefined();
                expect(comp.unmountMemory).toBeDefined();
                expect(comp.memoryDelta).toBeLessThan(10 * 1024 * 1024); // < 10MB per component
            });
        });

        it('should optimize memory usage automatically', async () => {
            memoryAnalyzer.enableAutoOptimization();

            // Simulate high memory usage scenario
            const initialMemory = memoryAnalyzer.getCurrentUsage();

            // Create large amount of data
            const largeArrays = Array.from({ length: 50 }, () =>
                new Array(10000).fill('memory-intensive-data')
            );

            // Wait for auto-optimization to trigger
            await new Promise(resolve => setTimeout(resolve, 1000));

            const optimizedMemory = memoryAnalyzer.getCurrentUsage();

            // Should have triggered optimization
            expect(memoryAnalyzer.getOptimizationEvents()).toBeGreaterThan(0);

            // Memory usage should be controlled
            const memoryIncrease = optimizedMemory - initialMemory;
            expect(memoryIncrease).toBeLessThan(100 * 1024 * 1024); // < 100MB increase
        });
    });

    describe('Battery Usage Monitoring', () => {
        it('should monitor battery consumption during operations', async () => {
            await batteryMonitor.startMonitoring();

            const initialBattery = await batteryMonitor.getCurrentBatteryLevel();

            // Simulate battery-intensive operations
            const operations = [
                () => contactManager.syncContacts(),
                () => searchService.search({ text: 'intensive search' }),
                () => performanceProfiler.runBenchmark(),
            ];

            for (const operation of operations) {
                await batteryMonitor.trackOperation('test-operation', operation);
            }

            const batteryReport = await batteryMonitor.stopMonitoring();

            // Verify battery monitoring
            expect(batteryReport.initialLevel).toBe(initialBattery);
            expect(batteryReport.operations).toHaveLength(3);
            expect(batteryReport.totalConsumption).toBeGreaterThan(0);

            // Each operation should have battery impact data
            batteryReport.operations.forEach(op => {
                expect(op.batteryDelta).toBeDefined();
                expect(op.duration).toBeGreaterThan(0);
                expect(op.batteryEfficiency).toBeDefined(); // Battery per ms
            });
        });

        it('should detect battery-intensive operations', async () => {
            await batteryMonitor.startMonitoring();

            // Simulate operations with different battery impacts
            const lightOperation = async () => {
                await new Promise(resolve => setTimeout(resolve, 100));
            };

            const heavyOperation = async () => {
                // Simulate CPU-intensive work
                for (let i = 0; i < 1000000; i++) {
                    Math.random() * Math.random();
                }
            };

            await batteryMonitor.trackOperation('light-op', lightOperation);
            await batteryMonitor.trackOperation('heavy-op', heavyOperation);

            const batteryReport = await batteryMonitor.stopMonitoring();
            const intensiveOps = batteryMonitor.getIntensiveOperations(batteryReport);

            // Should identify heavy operation as battery-intensive
            expect(intensiveOps).toHaveLength(1);
            expect(intensiveOps[0].name).toBe('heavy-op');
            expect(intensiveOps[0].batteryImpact).toBeGreaterThan(0.5); // High impact score
        });

        it('should provide battery optimization recommendations', async () => {
            await batteryMonitor.startMonitoring();

            // Simulate various operation patterns
            const operations = [
                { name: 'frequent-sync', frequency: 'high', impact: 'medium' },
                { name: 'background-processing', frequency: 'medium', impact: 'high' },
                { name: 'ui-animations', frequency: 'high', impact: 'low' },
            ];

            for (const op of operations) {
                await batteryMonitor.trackOperation(op.name, async () => {
                    // Simulate operation based on characteristics
                    const duration = op.impact === 'high' ? 500 : op.impact === 'medium' ? 200 : 50;
                    await new Promise(resolve => setTimeout(resolve, duration));
                });
            }

            const batteryReport = await batteryMonitor.stopMonitoring();
            const recommendations = batteryMonitor.getOptimizationRecommendations(batteryReport);

            // Should provide relevant recommendations
            expect(recommendations).toHaveLength(2); // For high and medium impact operations

            const backgroundProcessingRec = recommendations.find(r =>
                r.operation === 'background-processing'
            );
            expect(backgroundProcessingRec?.recommendation).toContain('reduce frequency');
            expect(backgroundProcessingRec?.potentialSavings).toBeGreaterThan(0);
        });

        it('should adapt to battery level and charging state', async () => {
            // Mock low battery scenario
            const DeviceInfo = require('react-native-device-info');
            DeviceInfo.getBatteryLevel.mockResolvedValue(0.15); // 15% battery
            DeviceInfo.isBatteryCharging.mockResolvedValue(false);

            await batteryMonitor.startMonitoring();

            // Should enable battery saving mode
            expect(batteryMonitor.isBatterySavingMode()).toBe(true);

            // Should throttle operations
            const throttledOperation = await batteryMonitor.trackOperation('test-op', async () => {
                await new Promise(resolve => setTimeout(resolve, 100));
            });

            expect(throttledOperation.wasThrottled).toBe(true);
            expect(throttledOperation.throttleReason).toBe('low_battery');

            // Mock charging scenario
            DeviceInfo.isBatteryCharging.mockResolvedValue(true);

            await batteryMonitor.updateBatteryState();

            // Should disable battery saving mode when charging
            expect(batteryMonitor.isBatterySavingMode()).toBe(false);
        });
    });

    describe('Integrated Performance Testing', () => {
        it('should run comprehensive performance benchmark', async () => {
            const benchmark = await performanceProfiler.runComprehensiveBenchmark({
                includeMemoryAnalysis: true,
                includeBatteryMonitoring: true,
                testDuration: 30000, // 30 seconds
            });

            // Verify benchmark results
            expect(benchmark.performance.overallScore).toBeGreaterThan(70); // > 70/100
            expect(benchmark.memory.efficiency).toBeGreaterThan(0.8); // > 80% efficient
            expect(benchmark.battery.efficiency).toBeGreaterThan(0.7); // > 70% efficient

            // Should provide actionable insights
            expect(benchmark.recommendations).toBeDefined();
            expect(benchmark.recommendations.length).toBeGreaterThan(0);

            // Should identify top performance issues
            expect(benchmark.topIssues).toBeDefined();
            expect(benchmark.topIssues.length).toBeLessThanOrEqual(5);
        });

        it('should generate performance report for CI/CD', async () => {
            const report = await performanceProfiler.generateCIReport({
                includeMetrics: true,
                includeRecommendations: true,
                format: 'json',
            });

            // Verify CI report structure
            expect(report.version).toBeDefined();
            expect(report.timestamp).toBeDefined();
            expect(report.metrics).toBeDefined();
            expect(report.thresholds).toBeDefined();
            expect(report.passed).toBeDefined();

            // Should include key performance metrics
            expect(report.metrics.appLaunchTime).toBeLessThan(3000); // < 3s
            expect(report.metrics.searchResponseTime).toBeLessThan(1000); // < 1s
            expect(report.metrics.memoryUsage).toBeLessThan(200 * 1024 * 1024); // < 200MB
            expect(report.metrics.batteryEfficiency).toBeGreaterThan(0.7); // > 70%

            // Should pass performance thresholds
            expect(report.passed).toBe(true);
        });
    });
});