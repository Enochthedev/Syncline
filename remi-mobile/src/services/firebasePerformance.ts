import perf from '@react-native-firebase/perf';
import { Platform } from 'react-native';

export interface PerformanceTrace {
    name: string;
    startTime: number;
    attributes?: Record<string, string>;
}

export interface NetworkTrace {
    url: string;
    method: string;
    startTime: number;
    responseCode?: number;
    responseSize?: number;
    requestSize?: number;
}

class FirebasePerformanceMonitor {
    private static instance: FirebasePerformanceMonitor;
    private activeTraces: Map<string, any> = new Map();
    private activeHttpTraces: Map<string, any> = new Map();
    private isEnabled: boolean = true;

    private constructor() {
        this.initializePerformanceMonitoring();
    }

    public static getInstance(): FirebasePerformanceMonitor {
        if (!FirebasePerformanceMonitor.instance) {
            FirebasePerformanceMonitor.instance = new FirebasePerformanceMonitor();
        }
        return FirebasePerformanceMonitor.instance;
    }

    private async initializePerformanceMonitoring(): Promise<void> {
        try {
            // Check if Firebase Performance is available
            this.isEnabled = await perf().isPerformanceCollectionEnabled();

            if (this.isEnabled) {
                console.log('Firebase Performance monitoring initialized');
            } else {
                console.log('Firebase Performance monitoring is disabled');
            }
        } catch (error) {
            console.error('Failed to initialize Firebase Performance:', error);
            this.isEnabled = false;
        }
    }

    // Screen performance tracking
    public startScreenTrace(screenName: string): string {
        if (!this.isEnabled) return '';

        try {
            const traceId = `screen_${screenName}_${Date.now()}`;
            const trace = perf().newTrace(`screen_${screenName}`);

            trace.start();
            this.activeTraces.set(traceId, trace);

            console.log(`Started screen trace: ${screenName}`);
            return traceId;
        } catch (error) {
            console.error('Failed to start screen trace:', error);
            return '';
        }
    }

    public stopScreenTrace(traceId: string, attributes?: Record<string, string>): void {
        if (!this.isEnabled || !traceId) return;

        try {
            const trace = this.activeTraces.get(traceId);
            if (trace) {
                // Add custom attributes
                if (attributes) {
                    Object.entries(attributes).forEach(([key, value]) => {
                        trace.putAttribute(key, value);
                    });
                }

                // Add platform information
                trace.putAttribute('platform', Platform.OS);
                trace.putAttribute('platform_version', Platform.Version.toString());

                trace.stop();
                this.activeTraces.delete(traceId);

                console.log(`Stopped screen trace: ${traceId}`);
            }
        } catch (error) {
            console.error('Failed to stop screen trace:', error);
        }
    }

    // API call performance tracking
    public startHttpTrace(url: string, method: string): string {
        if (!this.isEnabled) return '';

        try {
            const traceId = `http_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            const httpTrace = perf().newHttpMetric(url, method.toUpperCase());

            httpTrace.start();
            this.activeHttpTraces.set(traceId, httpTrace);

            console.log(`Started HTTP trace: ${method} ${url}`);
            return traceId;
        } catch (error) {
            console.error('Failed to start HTTP trace:', error);
            return '';
        }
    }

    public stopHttpTrace(
        traceId: string,
        responseCode: number,
        responseSize?: number,
        requestSize?: number
    ): void {
        if (!this.isEnabled || !traceId) return;

        try {
            const httpTrace = this.activeHttpTraces.get(traceId);
            if (httpTrace) {
                httpTrace.setHttpResponseCode(responseCode);

                if (responseSize !== undefined) {
                    httpTrace.setResponseContentType('application/json');
                    httpTrace.setResponsePayloadSize(responseSize);
                }

                if (requestSize !== undefined) {
                    httpTrace.setRequestPayloadSize(requestSize);
                }

                httpTrace.stop();
                this.activeHttpTraces.delete(traceId);

                console.log(`Stopped HTTP trace: ${traceId} (${responseCode})`);
            }
        } catch (error) {
            console.error('Failed to stop HTTP trace:', error);
        }
    }

    // Custom performance traces
    public startCustomTrace(traceName: string, attributes?: Record<string, string>): string {
        if (!this.isEnabled) return '';

        try {
            const traceId = `custom_${traceName}_${Date.now()}`;
            const trace = perf().newTrace(traceName);

            // Add initial attributes
            if (attributes) {
                Object.entries(attributes).forEach(([key, value]) => {
                    trace.putAttribute(key, value);
                });
            }

            trace.start();
            this.activeTraces.set(traceId, trace);

            console.log(`Started custom trace: ${traceName}`);
            return traceId;
        } catch (error) {
            console.error('Failed to start custom trace:', error);
            return '';
        }
    }

    public stopCustomTrace(traceId: string, attributes?: Record<string, string>): void {
        if (!this.isEnabled || !traceId) return;

        try {
            const trace = this.activeTraces.get(traceId);
            if (trace) {
                // Add final attributes
                if (attributes) {
                    Object.entries(attributes).forEach(([key, value]) => {
                        trace.putAttribute(key, value);
                    });
                }

                trace.stop();
                this.activeTraces.delete(traceId);

                console.log(`Stopped custom trace: ${traceId}`);
            }
        } catch (error) {
            console.error('Failed to stop custom trace:', error);
        }
    }

    // Increment metric counters
    public incrementMetric(traceId: string, metricName: string, value: number = 1): void {
        if (!this.isEnabled || !traceId) return;

        try {
            const trace = this.activeTraces.get(traceId);
            if (trace) {
                trace.incrementMetric(metricName, value);
                console.log(`Incremented metric ${metricName} by ${value} for trace ${traceId}`);
            }
        } catch (error) {
            console.error('Failed to increment metric:', error);
        }
    }

    // Set metric values
    public setMetric(traceId: string, metricName: string, value: number): void {
        if (!this.isEnabled || !traceId) return;

        try {
            const trace = this.activeTraces.get(traceId);
            if (trace) {
                trace.putMetric(metricName, value);
                console.log(`Set metric ${metricName} to ${value} for trace ${traceId}`);
            }
        } catch (error) {
            console.error('Failed to set metric:', error);
        }
    }

    // Convenience methods for common operations
    public measureScreenLoad(screenName: string): {
        finish: (attributes?: Record<string, string>) => void;
    } {
        const traceId = this.startScreenTrace(screenName);

        return {
            finish: (attributes?: Record<string, string>) => {
                this.stopScreenTrace(traceId, attributes);
            },
        };
    }

    public measureApiCall(url: string, method: string): {
        finish: (responseCode: number, responseSize?: number, requestSize?: number) => void;
    } {
        const traceId = this.startHttpTrace(url, method);

        return {
            finish: (responseCode: number, responseSize?: number, requestSize?: number) => {
                this.stopHttpTrace(traceId, responseCode, responseSize, requestSize);
            },
        };
    }

    public measureCustomOperation(operationName: string, attributes?: Record<string, string>): {
        finish: (finalAttributes?: Record<string, string>) => void;
        incrementMetric: (metricName: string, value?: number) => void;
        setMetric: (metricName: string, value: number) => void;
    } {
        const traceId = this.startCustomTrace(operationName, attributes);

        return {
            finish: (finalAttributes?: Record<string, string>) => {
                this.stopCustomTrace(traceId, finalAttributes);
            },
            incrementMetric: (metricName: string, value: number = 1) => {
                this.incrementMetric(traceId, metricName, value);
            },
            setMetric: (metricName: string, value: number) => {
                this.setMetric(traceId, metricName, value);
            },
        };
    }

    // Search performance tracking
    public measureSearchOperation(query: string, resultCount?: number): {
        finish: (success: boolean, resultCount?: number) => void;
    } {
        const trace = this.measureCustomOperation('search_operation', {
            query_length: query.length.toString(),
            query_type: this.getQueryType(query),
        });

        return {
            finish: (success: boolean, finalResultCount?: number) => {
                const resultCount = finalResultCount || 0;

                trace.setMetric('result_count', resultCount);
                trace.setMetric('success', success ? 1 : 0);

                trace.finish({
                    success: success.toString(),
                    result_count: resultCount.toString(),
                });
            },
        };
    }

    // Contact loading performance
    public measureContactLoad(contactCount: number): {
        finish: (loadedCount: number, fromCache: boolean) => void;
    } {
        const trace = this.measureCustomOperation('contact_load', {
            expected_count: contactCount.toString(),
        });

        return {
            finish: (loadedCount: number, fromCache: boolean) => {
                trace.setMetric('loaded_count', loadedCount);
                trace.setMetric('from_cache', fromCache ? 1 : 0);

                trace.finish({
                    loaded_count: loadedCount.toString(),
                    from_cache: fromCache.toString(),
                    cache_hit_rate: fromCache ? '1.0' : '0.0',
                });
            },
        };
    }

    // Memory performance tracking
    public measureMemoryOperation(operationType: string): {
        finish: (memoryUsed: number, memoryFreed: number) => void;
    } {
        const trace = this.measureCustomOperation(`memory_${operationType}`);

        return {
            finish: (memoryUsed: number, memoryFreed: number) => {
                trace.setMetric('memory_used_mb', Math.round(memoryUsed / (1024 * 1024)));
                trace.setMetric('memory_freed_mb', Math.round(memoryFreed / (1024 * 1024)));

                trace.finish({
                    memory_used_mb: Math.round(memoryUsed / (1024 * 1024)).toString(),
                    memory_freed_mb: Math.round(memoryFreed / (1024 * 1024)).toString(),
                });
            },
        };
    }

    // Helper methods
    private getQueryType(query: string): string {
        if (query.includes('@')) return 'email';
        if (query.match(/^\+?\d+/)) return 'phone';
        if (query.includes(' ')) return 'full_name';
        return 'partial_name';
    }

    // Configuration methods
    public async setPerformanceCollectionEnabled(enabled: boolean): Promise<void> {
        try {
            await perf().setPerformanceCollectionEnabled(enabled);
            this.isEnabled = enabled;
            console.log('Firebase Performance collection', enabled ? 'enabled' : 'disabled');
        } catch (error) {
            console.error('Failed to set performance collection enabled:', error);
        }
    }

    public async isPerformanceCollectionEnabled(): Promise<boolean> {
        try {
            return await perf().isPerformanceCollectionEnabled();
        } catch (error) {
            console.error('Failed to check performance collection status:', error);
            return false;
        }
    }

    // Cleanup methods
    public stopAllTraces(): void {
        try {
            // Stop all active traces
            this.activeTraces.forEach((trace, traceId) => {
                try {
                    trace.stop();
                    console.log(`Force stopped trace: ${traceId}`);
                } catch (error) {
                    console.error(`Failed to stop trace ${traceId}:`, error);
                }
            });

            // Stop all active HTTP traces
            this.activeHttpTraces.forEach((httpTrace, traceId) => {
                try {
                    httpTrace.stop();
                    console.log(`Force stopped HTTP trace: ${traceId}`);
                } catch (error) {
                    console.error(`Failed to stop HTTP trace ${traceId}:`, error);
                }
            });

            this.activeTraces.clear();
            this.activeHttpTraces.clear();
        } catch (error) {
            console.error('Failed to stop all traces:', error);
        }
    }

    public getActiveTraceCount(): number {
        return this.activeTraces.size + this.activeHttpTraces.size;
    }

    public isEnabled(): boolean {
        return this.isEnabled;
    }
}

export default FirebasePerformanceMonitor;