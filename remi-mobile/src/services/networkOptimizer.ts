import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import { QueryClient } from '@tanstack/react-query';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface NetworkRequest {
    id: string;
    url: string;
    method: string;
    data?: any;
    headers?: Record<string, string>;
    priority: 'low' | 'medium' | 'high' | 'critical';
    timestamp: number;
    retryCount: number;
    maxRetries: number;
}

export interface NetworkConfig {
    batchSize: number;
    batchTimeout: number;
    compressionEnabled: boolean;
    connectionPoolSize: number;
    retryDelayBase: number;
    maxRetryDelay: number;
    requestTimeout: number;
    enableOfflineQueue: boolean;
    enableRequestDeduplication: boolean;
}

export interface NetworkStats {
    totalRequests: number;
    successfulRequests: number;
    failedRequests: number;
    averageResponseTime: number;
    bytesTransferred: number;
    compressionRatio: number;
    cacheHitRate: number;
    timestamp: number;
}

class NetworkOptimizer {
    private static instance: NetworkOptimizer;
    private config: NetworkConfig;
    private requestQueue: NetworkRequest[] = [];
    private batchTimer: NodeJS.Timeout | null = null;
    private connectionPool: Map<string, any> = new Map();
    private requestCache: Map<string, any> = new Map();
    private stats: NetworkStats;
    private isOnline: boolean = true;
    private networkState: NetInfoState | null = null;
    private queryClient: QueryClient;

    private constructor(queryClient: QueryClient) {
        this.queryClient = queryClient;
        this.config = this.getDefaultConfig();
        this.stats = this.initializeStats();
        this.initializeNetworkOptimization();
    }

    public static getInstance(queryClient?: QueryClient): NetworkOptimizer {
        if (!NetworkOptimizer.instance) {
            if (!queryClient) {
                throw new Error('QueryClient is required for first initialization');
            }
            NetworkOptimizer.instance = new NetworkOptimizer(queryClient);
        }
        return NetworkOptimizer.instance;
    }

    private getDefaultConfig(): NetworkConfig {
        return {
            batchSize: 10,
            batchTimeout: 100, // 100ms
            compressionEnabled: true,
            connectionPoolSize: 5,
            retryDelayBase: 1000, // 1 second
            maxRetryDelay: 30000, // 30 seconds
            requestTimeout: 30000, // 30 seconds
            enableOfflineQueue: true,
            enableRequestDeduplication: true,
        };
    }

    private initializeStats(): NetworkStats {
        return {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            averageResponseTime: 0,
            bytesTransferred: 0,
            compressionRatio: 1.0,
            cacheHitRate: 0,
            timestamp: Date.now(),
        };
    }

    private async initializeNetworkOptimization(): Promise<void> {
        try {
            // Load saved configuration
            const savedConfig = await AsyncStorage.getItem('network_config');
            if (savedConfig) {
                this.config = { ...this.config, ...JSON.parse(savedConfig) };
            }

            // Setup network state monitoring
            this.setupNetworkMonitoring();

            // Configure React Query for network optimization
            this.configureReactQuery();

            console.log('Network optimization initialized');
        } catch (error) {
            console.error('Failed to initialize network optimization:', error);
        }
    }

    private setupNetworkMonitoring(): void {
        NetInfo.addEventListener(state => {
            this.networkState = state;
            this.isOnline = state.isConnected ?? false;

            if (this.isOnline) {
                this.processOfflineQueue();
            }

            this.adaptToNetworkConditions(state);
        });
    }

    private configureReactQuery(): void {
        // Configure React Query with network-aware settings
        this.queryClient.setDefaultOptions({
            queries: {
                staleTime: this.getStaleTimeForNetwork(),
                cacheTime: 10 * 60 * 1000, // 10 minutes
                retry: (failureCount, error) => {
                    return this.shouldRetryRequest(failureCount, error);
                },
                retryDelay: (attemptIndex) => {
                    return this.calculateRetryDelay(attemptIndex);
                },
                networkMode: 'offlineFirst',
            },
            mutations: {
                retry: (failureCount, error) => {
                    return this.shouldRetryRequest(failureCount, error);
                },
                retryDelay: (attemptIndex) => {
                    return this.calculateRetryDelay(attemptIndex);
                },
                networkMode: 'offlineFirst',
            },
        });
    }

    private getStaleTimeForNetwork(): number {
        if (!this.networkState) return 5 * 60 * 1000; // 5 minutes default

        // Adjust stale time based on network conditions
        if (this.networkState.type === 'wifi') {
            return 2 * 60 * 1000; // 2 minutes on WiFi
        } else if (this.networkState.type === 'cellular') {
            const effectiveType = (this.networkState.details as any)?.effectiveType;
            switch (effectiveType) {
                case '4g':
                    return 3 * 60 * 1000; // 3 minutes on 4G
                case '3g':
                    return 5 * 60 * 1000; // 5 minutes on 3G
                case '2g':
                    return 10 * 60 * 1000; // 10 minutes on 2G
                default:
                    return 5 * 60 * 1000;
            }
        }

        return 5 * 60 * 1000;
    }

    private adaptToNetworkConditions(state: NetInfoState): void {
        if (!state.isConnected) {
            // Offline mode
            this.config.enableOfflineQueue = true;
            return;
        }

        // Adapt configuration based on network type and quality
        if (state.type === 'wifi') {
            this.config.batchSize = 15;
            this.config.batchTimeout = 50;
            this.config.requestTimeout = 30000;
        } else if (state.type === 'cellular') {
            const effectiveType = (state.details as any)?.effectiveType;
            switch (effectiveType) {
                case '4g':
                    this.config.batchSize = 10;
                    this.config.batchTimeout = 100;
                    this.config.requestTimeout = 30000;
                    break;
                case '3g':
                    this.config.batchSize = 5;
                    this.config.batchTimeout = 200;
                    this.config.requestTimeout = 45000;
                    break;
                case '2g':
                    this.config.batchSize = 3;
                    this.config.batchTimeout = 500;
                    this.config.requestTimeout = 60000;
                    break;
                default:
                    this.config.batchSize = 5;
                    this.config.batchTimeout = 200;
                    this.config.requestTimeout = 45000;
            }
        }

        console.log('Network configuration adapted:', {
            type: state.type,
            effectiveType: (state.details as any)?.effectiveType,
            config: this.config,
        });
    }

    public async queueRequest(request: Omit<NetworkRequest, 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
        const requestId = this.generateRequestId();

        const networkRequest: NetworkRequest = {
            ...request,
            id: requestId,
            timestamp: Date.now(),
            retryCount: 0,
        };

        // Check for duplicate requests if deduplication is enabled
        if (this.config.enableRequestDeduplication) {
            const duplicateId = this.findDuplicateRequest(networkRequest);
            if (duplicateId) {
                return duplicateId;
            }
        }

        this.requestQueue.push(networkRequest);
        this.scheduleRequestBatch();

        return requestId;
    }

    private generateRequestId(): string {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private findDuplicateRequest(request: NetworkRequest): string | null {
        const existing = this.requestQueue.find(req =>
            req.url === request.url &&
            req.method === request.method &&
            JSON.stringify(req.data) === JSON.stringify(request.data)
        );

        return existing ? existing.id : null;
    }

    private scheduleRequestBatch(): void {
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
        }

        this.batchTimer = setTimeout(() => {
            this.processBatch();
        }, this.config.batchTimeout);

        // Process immediately if batch is full
        if (this.requestQueue.length >= this.config.batchSize) {
            if (this.batchTimer) {
                clearTimeout(this.batchTimer);
                this.batchTimer = null;
            }
            this.processBatch();
        }
    }

    private async processBatch(): Promise<void> {
        if (this.requestQueue.length === 0) return;

        const batch = this.requestQueue.splice(0, this.config.batchSize);

        if (!this.isOnline && this.config.enableOfflineQueue) {
            await this.saveToOfflineQueue(batch);
            return;
        }

        // Group requests by priority
        const criticalRequests = batch.filter(req => req.priority === 'critical');
        const highRequests = batch.filter(req => req.priority === 'high');
        const mediumRequests = batch.filter(req => req.priority === 'medium');
        const lowRequests = batch.filter(req => req.priority === 'low');

        // Process in priority order
        await this.processRequestGroup(criticalRequests);
        await this.processRequestGroup(highRequests);
        await this.processRequestGroup(mediumRequests);
        await this.processRequestGroup(lowRequests);
    }

    private async processRequestGroup(requests: NetworkRequest[]): Promise<void> {
        const promises = requests.map(request => this.executeRequest(request));

        try {
            await Promise.allSettled(promises);
        } catch (error) {
            console.error('Batch processing error:', error);
        }
    }

    private async executeRequest(request: NetworkRequest): Promise<any> {
        const startTime = Date.now();

        try {
            // Check cache first
            const cacheKey = this.getCacheKey(request);
            const cachedResponse = this.requestCache.get(cacheKey);

            if (cachedResponse && this.isCacheValid(cachedResponse)) {
                this.updateStats('cache_hit', Date.now() - startTime);
                return cachedResponse.data;
            }

            // Execute the actual request
            const response = await this.performHttpRequest(request);

            // Cache the response
            this.cacheResponse(cacheKey, response);

            // Update statistics
            this.updateStats('success', Date.now() - startTime, this.estimateResponseSize(response));

            return response;

        } catch (error) {
            console.error('Request failed:', error);

            // Handle retry logic
            if (request.retryCount < request.maxRetries) {
                request.retryCount++;
                const delay = this.calculateRetryDelay(request.retryCount);

                setTimeout(() => {
                    this.requestQueue.unshift(request);
                    this.scheduleRequestBatch();
                }, delay);
            } else {
                this.updateStats('failure', Date.now() - startTime);
            }

            throw error;
        }
    }

    private async performHttpRequest(request: NetworkRequest): Promise<any> {
        // This would integrate with your actual HTTP client (axios, fetch, etc.)
        // For now, we'll simulate the request structure

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.requestTimeout);

        try {
            const response = await fetch(request.url, {
                method: request.method,
                headers: {
                    'Content-Type': 'application/json',
                    ...request.headers,
                },
                body: request.data ? JSON.stringify(request.data) : undefined,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    private getCacheKey(request: NetworkRequest): string {
        return `${request.method}:${request.url}:${JSON.stringify(request.data)}`;
    }

    private isCacheValid(cachedResponse: any): boolean {
        const maxAge = 5 * 60 * 1000; // 5 minutes
        return Date.now() - cachedResponse.timestamp < maxAge;
    }

    private cacheResponse(key: string, data: any): void {
        this.requestCache.set(key, {
            data,
            timestamp: Date.now(),
        });

        // Limit cache size
        if (this.requestCache.size > 100) {
            const oldestKey = this.requestCache.keys().next().value;
            this.requestCache.delete(oldestKey);
        }
    }

    private shouldRetryRequest(failureCount: number, error: any): boolean {
        if (failureCount >= 3) return false;

        // Don't retry on client errors (4xx)
        if (error?.status >= 400 && error?.status < 500) {
            return false;
        }

        return true;
    }

    private calculateRetryDelay(attemptIndex: number): number {
        const delay = Math.min(
            this.config.retryDelayBase * Math.pow(2, attemptIndex - 1),
            this.config.maxRetryDelay
        );

        // Add jitter to prevent thundering herd
        return delay + Math.random() * 1000;
    }

    private async saveToOfflineQueue(requests: NetworkRequest[]): Promise<void> {
        try {
            const existingQueue = await AsyncStorage.getItem('offline_request_queue');
            const queue = existingQueue ? JSON.parse(existingQueue) : [];

            queue.push(...requests);

            await AsyncStorage.setItem('offline_request_queue', JSON.stringify(queue));
        } catch (error) {
            console.error('Failed to save offline queue:', error);
        }
    }

    private async processOfflineQueue(): Promise<void> {
        try {
            const queueData = await AsyncStorage.getItem('offline_request_queue');
            if (!queueData) return;

            const queue: NetworkRequest[] = JSON.parse(queueData);

            if (queue.length > 0) {
                console.log(`Processing ${queue.length} offline requests`);

                // Add to current queue
                this.requestQueue.unshift(...queue);

                // Clear offline queue
                await AsyncStorage.removeItem('offline_request_queue');

                // Process the queue
                this.scheduleRequestBatch();
            }
        } catch (error) {
            console.error('Failed to process offline queue:', error);
        }
    }

    private updateStats(type: 'success' | 'failure' | 'cache_hit', responseTime: number, bytes?: number): void {
        this.stats.totalRequests++;

        if (type === 'success') {
            this.stats.successfulRequests++;
            this.stats.averageResponseTime =
                (this.stats.averageResponseTime * (this.stats.successfulRequests - 1) + responseTime) /
                this.stats.successfulRequests;

            if (bytes) {
                this.stats.bytesTransferred += bytes;
            }
        } else if (type === 'failure') {
            this.stats.failedRequests++;
        }

        // Update cache hit rate
        const cacheHits = this.stats.totalRequests - this.stats.successfulRequests - this.stats.failedRequests;
        this.stats.cacheHitRate = cacheHits / this.stats.totalRequests;

        this.stats.timestamp = Date.now();
    }

    private estimateResponseSize(response: any): number {
        try {
            return new Blob([JSON.stringify(response)]).size;
        } catch {
            return 0;
        }
    }

    // Public API methods
    public updateConfig(newConfig: Partial<NetworkConfig>): void {
        this.config = { ...this.config, ...newConfig };
        AsyncStorage.setItem('network_config', JSON.stringify(this.config));

        // Reconfigure React Query if needed
        this.configureReactQuery();
    }

    public getConfig(): NetworkConfig {
        return { ...this.config };
    }

    public getStats(): NetworkStats {
        return { ...this.stats };
    }

    public clearCache(): void {
        this.requestCache.clear();
    }

    public getNetworkState(): NetInfoState | null {
        return this.networkState;
    }

    public isNetworkAvailable(): boolean {
        return this.isOnline;
    }

    public async clearOfflineQueue(): Promise<void> {
        await AsyncStorage.removeItem('offline_request_queue');
    }

    public getQueueSize(): number {
        return this.requestQueue.length;
    }
}

export default NetworkOptimizer;