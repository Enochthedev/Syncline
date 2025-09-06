/**
 * Comprehensive error handling service with classification,
 * retry logic, and user feedback systems
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';
import NetInfo from '@react-native-community/netinfo';
import {
    AppError,
    ErrorType,
    ErrorSeverity,
    ErrorContext,
    ErrorResolution,
    RecoveryAction,
    RetryConfig,
    ErrorReport,
    SuggestedAction,
    FailureScenario,
    GracefulDegradation,
    ErrorMetrics
} from '../types/errors';

class ErrorHandler {
    private static instance: ErrorHandler;
    private errorQueue: AppError[] = [];
    private retryConfigs: Map<ErrorType, RetryConfig> = new Map();
    private errorMetrics: Map<ErrorType, ErrorMetrics> = new Map();
    private failureScenarios: Map<string, FailureScenario> = new Map();

    private constructor() {
        this.initializeRetryConfigs();
        this.initializeFailureScenarios();
        this.loadErrorMetrics();
    }

    public static getInstance(): ErrorHandler {
        if (!ErrorHandler.instance) {
            ErrorHandler.instance = new ErrorHandler();
        }
        return ErrorHandler.instance;
    }

    /**
     * Main error handling method with classification and resolution
     */
    public async handleError(error: Error | AppError, context?: Partial<ErrorContext>): Promise<ErrorResolution> {
        try {
            const appError = await this.classifyError(error, context);
            await this.logError(appError);

            // Update metrics
            this.updateErrorMetrics(appError);

            // Determine resolution strategy
            const resolution = await this.resolveError(appError);

            // Queue for reporting if needed
            if (appError.reportable) {
                await this.queueErrorReport(appError);
            }

            return resolution;
        } catch (handlingError) {
            console.error('Error in error handler:', handlingError);
            return {
                resolved: false,
                action: RecoveryAction.CONTACT_SUPPORT,
                message: 'An unexpected error occurred. Please contact support.'
            };
        }
    }

    /**
     * Classify error into AppError with appropriate metadata
     */
    private async classifyError(error: Error | AppError, context?: Partial<ErrorContext>): Promise<AppError> {
        if (this.isAppError(error)) {
            return error;
        }

        const errorContext = await this.buildErrorContext(context);
        const classification = this.classifyErrorType(error);

        return {
            id: this.generateErrorId(),
            type: classification.type,
            severity: classification.severity,
            message: error.message,
            userMessage: this.generateUserMessage(classification.type, error),
            technicalDetails: error.stack,
            context: errorContext,
            recoveryActions: this.getRecoveryActions(classification.type),
            suggestedActions: this.getSuggestedActions(classification.type),
            retryable: this.isRetryable(classification.type),
            reportable: this.isReportable(classification.type, classification.severity),
            timestamp: new Date(),
            stackTrace: error.stack,
            originalError: error
        };
    }

    /**
     * Retry operation with exponential backoff
     */
    public async retryOperation<T>(
        operation: () => Promise<T>,
        errorType: ErrorType,
        customConfig?: Partial<RetryConfig>
    ): Promise<T> {
        const config = { ...this.retryConfigs.get(errorType), ...customConfig };
        if (!config) {
            throw new Error(`No retry configuration found for error type: ${errorType}`);
        }

        let lastError: Error;
        let delay = config.baseDelay;

        for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error as Error;

                const appError = await this.classifyError(error);

                // Check if error is retryable
                if (!config.retryableErrors.includes(appError.type) || attempt === config.maxRetries) {
                    throw error;
                }

                // Wait before retry with exponential backoff
                await this.delay(Math.min(delay, config.maxDelay));
                delay *= config.backoffMultiplier;

                console.log(`Retry attempt ${attempt + 1}/${config.maxRetries} for ${errorType} after ${delay}ms`);
            }
        }

        throw lastError!;
    }

    /**
     * Resolve error with appropriate recovery action
     */
    private async resolveError(error: AppError): Promise<ErrorResolution> {
        // Check for graceful degradation scenarios
        const degradation = await this.checkGracefulDegradation(error);
        if (degradation) {
            return {
                resolved: true,
                action: RecoveryAction.FALLBACK,
                message: degradation.fallbackMessage,
                fallbackData: await this.getFallbackData(degradation)
            };
        }

        // Determine primary recovery action
        const primaryAction = error.recoveryActions[0];

        switch (primaryAction) {
            case RecoveryAction.RETRY:
                return {
                    resolved: false,
                    action: RecoveryAction.RETRY,
                    retryAfter: this.calculateRetryDelay(error.type)
                };

            case RecoveryAction.FALLBACK:
                const fallbackData = await this.getFallbackData();
                return {
                    resolved: true,
                    action: RecoveryAction.FALLBACK,
                    message: 'Using cached data while service is unavailable',
                    fallbackData
                };

            case RecoveryAction.USER_ACTION:
                return {
                    resolved: false,
                    action: RecoveryAction.USER_ACTION,
                    message: error.userMessage
                };

            default:
                return {
                    resolved: false,
                    action: primaryAction,
                    message: error.userMessage
                };
        }
    }

    /**
     * Generate user-friendly error messages
     */
    private generateUserMessage(errorType: ErrorType, error: Error): string {
        const userMessages: Record<ErrorType, string> = {
            [ErrorType.NETWORK_UNAVAILABLE]: 'No internet connection. Please check your network and try again.',
            [ErrorType.API_TIMEOUT]: 'The request is taking longer than expected. Please try again.',
            [ErrorType.SERVER_ERROR]: 'Our servers are experiencing issues. Please try again in a few minutes.',
            [ErrorType.AUTH_EXPIRED]: 'Your session has expired. Please log in again.',
            [ErrorType.AUTH_INVALID]: 'Authentication failed. Please check your credentials.',
            [ErrorType.PERMISSION_DENIED]: 'You don\'t have permission to perform this action.',
            [ErrorType.CONTACT_NOT_FOUND]: 'The contact you\'re looking for could not be found.',
            [ErrorType.SEARCH_TIMEOUT]: 'Search is taking too long. Please try a simpler query.',
            [ErrorType.PLATFORM_DISCONNECTED]: 'Platform connection lost. Please reconnect in settings.',
            [ErrorType.STORAGE_FULL]: 'Device storage is full. Please free up space and try again.',
            [ErrorType.SYNC_CONFLICT]: 'Data conflict detected. Your changes will be merged automatically.',
            [ErrorType.BIOMETRIC_FAILED]: 'Biometric authentication failed. Please try again or use your password.',
            [ErrorType.UNKNOWN_ERROR]: 'An unexpected error occurred. Please try again or contact support.'
        };

        return userMessages[errorType] || 'An error occurred. Please try again.';
    }

    /**
     * Get suggested actions for error recovery
     */
    private getSuggestedActions(errorType: ErrorType): SuggestedAction[] {
        const actionMap: Record<ErrorType, SuggestedAction[]> = {
            [ErrorType.NETWORK_UNAVAILABLE]: [
                {
                    id: 'check_wifi',
                    title: 'Check Wi-Fi',
                    description: 'Verify your Wi-Fi connection is working',
                    actionType: 'setting',
                    actionData: { setting: 'wifi' },
                    priority: 1
                },
                {
                    id: 'use_cellular',
                    title: 'Use Cellular Data',
                    description: 'Switch to cellular data if available',
                    actionType: 'setting',
                    actionData: { setting: 'cellular' },
                    priority: 2
                }
            ],
            [ErrorType.AUTH_EXPIRED]: [
                {
                    id: 'login_again',
                    title: 'Log In Again',
                    description: 'Re-authenticate to continue using the app',
                    actionType: 'navigation',
                    actionData: { screen: 'Login' },
                    priority: 1
                }
            ],
            [ErrorType.PLATFORM_DISCONNECTED]: [
                {
                    id: 'reconnect_platform',
                    title: 'Reconnect Platform',
                    description: 'Go to settings to reconnect your platform',
                    actionType: 'navigation',
                    actionData: { screen: 'PlatformSettings' },
                    priority: 1
                }
            ],
            [ErrorType.STORAGE_FULL]: [
                {
                    id: 'clear_cache',
                    title: 'Clear Cache',
                    description: 'Free up space by clearing app cache',
                    actionType: 'button',
                    actionData: { action: 'clearCache' },
                    priority: 1
                },
                {
                    id: 'manage_storage',
                    title: 'Manage Storage',
                    description: 'Go to device settings to free up space',
                    actionType: 'setting',
                    actionData: { setting: 'storage' },
                    priority: 2
                }
            ]
        };

        return actionMap[errorType] || [];
    }

    /**
     * Check for graceful degradation scenarios
     */
    private async checkGracefulDegradation(error: AppError): Promise<GracefulDegradation | null> {
        // Network unavailable - use cached data
        if (error.type === ErrorType.NETWORK_UNAVAILABLE) {
            const hasCachedData = await this.hasCachedData();
            if (hasCachedData) {
                return {
                    fallbackStrategy: 'cached_data',
                    fallbackMessage: 'Showing cached data. Some information may be outdated.',
                    availableActions: ['refresh_when_online', 'view_cached_contacts'],
                    dataSource: 'cache'
                };
            }
        }

        // Search service unavailable - use local search
        if (error.type === ErrorType.SEARCH_SERVICE_UNAVAILABLE) {
            return {
                fallbackStrategy: 'limited_functionality',
                fallbackMessage: 'Advanced search is unavailable. Using basic local search.',
                availableActions: ['basic_search', 'browse_contacts'],
                dataSource: 'local_storage'
            };
        }

        // Platform disconnected - show offline mode
        if (error.type === ErrorType.PLATFORM_DISCONNECTED) {
            return {
                fallbackStrategy: 'offline_mode',
                fallbackMessage: 'Platform disconnected. Showing local data only.',
                availableActions: ['view_local_data', 'reconnect_platform'],
                dataSource: 'local_storage'
            };
        }

        return null;
    }

    /**
     * Initialize retry configurations for different error types
     */
    private initializeRetryConfigs(): void {
        this.retryConfigs.set(ErrorType.API_TIMEOUT, {
            maxRetries: 3,
            baseDelay: 1000,
            maxDelay: 10000,
            backoffMultiplier: 2,
            retryableErrors: [ErrorType.API_TIMEOUT, ErrorType.SERVER_ERROR]
        });

        this.retryConfigs.set(ErrorType.NETWORK_UNAVAILABLE, {
            maxRetries: 5,
            baseDelay: 2000,
            maxDelay: 30000,
            backoffMultiplier: 1.5,
            retryableErrors: [ErrorType.NETWORK_UNAVAILABLE, ErrorType.CONNECTION_FAILED]
        });

        this.retryConfigs.set(ErrorType.SERVER_ERROR, {
            maxRetries: 2,
            baseDelay: 5000,
            maxDelay: 20000,
            backoffMultiplier: 2,
            retryableErrors: [ErrorType.SERVER_ERROR]
        });
    }

    /**
     * Initialize failure scenarios for testing
     */
    private initializeFailureScenarios(): void {
        this.failureScenarios.set('network_failure', {
            id: 'network_failure',
            name: 'Network Connection Lost',
            description: 'Complete loss of network connectivity',
            triggerConditions: ['no_internet', 'wifi_disconnected', 'cellular_unavailable'],
            expectedBehavior: 'Show cached data and offline indicators',
            gracefulDegradation: {
                fallbackStrategy: 'cached_data',
                fallbackMessage: 'You\'re offline. Showing cached data.',
                availableActions: ['view_cached_data', 'retry_connection'],
                dataSource: 'cache'
            }
        });

        this.failureScenarios.set('auth_service_down', {
            id: 'auth_service_down',
            name: 'Authentication Service Unavailable',
            description: 'Authentication service is not responding',
            triggerConditions: ['auth_server_down', 'auth_timeout'],
            expectedBehavior: 'Allow limited functionality with cached credentials',
            gracefulDegradation: {
                fallbackStrategy: 'limited_functionality',
                fallbackMessage: 'Authentication service unavailable. Limited functionality enabled.',
                availableActions: ['view_local_data', 'retry_auth'],
                dataSource: 'local_storage'
            }
        });
    }

    /**
     * Build comprehensive error context
     */
    private async buildErrorContext(context?: Partial<ErrorContext>): Promise<ErrorContext> {
        const netInfo = await NetInfo.fetch();
        const deviceInfo = {
            model: await DeviceInfo.getModel(),
            osVersion: await DeviceInfo.getSystemVersion(),
            appVersion: await DeviceInfo.getVersion(),
            buildNumber: await DeviceInfo.getBuildNumber(),
            isEmulator: await DeviceInfo.isEmulator(),
            batteryLevel: await DeviceInfo.getBatteryLevel()
        };

        return {
            deviceId: await DeviceInfo.getUniqueId(),
            platform: await DeviceInfo.getSystemName() === 'iOS' ? 'ios' : 'android',
            appVersion: deviceInfo.appVersion,
            timestamp: new Date(),
            networkStatus: netInfo.isConnected ? 'online' : 'offline',
            batteryLevel: deviceInfo.batteryLevel,
            ...context
        };
    }

    /**
     * Classify error type and severity
     */
    private classifyErrorType(error: Error): { type: ErrorType; severity: ErrorSeverity } {
        const message = error.message.toLowerCase();
        const stack = error.stack?.toLowerCase() || '';

        // Network errors
        if (message.includes('network') || message.includes('timeout') || message.includes('connection')) {
            if (message.includes('timeout')) {
                return { type: ErrorType.API_TIMEOUT, severity: ErrorSeverity.MEDIUM };
            }
            return { type: ErrorType.NETWORK_UNAVAILABLE, severity: ErrorSeverity.HIGH };
        }

        // Authentication errors
        if (message.includes('auth') || message.includes('unauthorized') || message.includes('forbidden')) {
            if (message.includes('expired')) {
                return { type: ErrorType.AUTH_EXPIRED, severity: ErrorSeverity.MEDIUM };
            }
            return { type: ErrorType.AUTH_INVALID, severity: ErrorSeverity.HIGH };
        }

        // Storage errors
        if (message.includes('storage') || message.includes('disk') || message.includes('space')) {
            return { type: ErrorType.STORAGE_FULL, severity: ErrorSeverity.HIGH };
        }

        // Search errors
        if (message.includes('search') || stack.includes('search')) {
            return { type: ErrorType.SEARCH_TIMEOUT, severity: ErrorSeverity.MEDIUM };
        }

        // Contact errors
        if (message.includes('contact') || stack.includes('contact')) {
            return { type: ErrorType.CONTACT_NOT_FOUND, severity: ErrorSeverity.LOW };
        }

        // Default to unknown error
        return { type: ErrorType.UNKNOWN_ERROR, severity: ErrorSeverity.MEDIUM };
    }

    /**
     * Utility methods
     */
    private isAppError(error: any): error is AppError {
        return error && typeof error === 'object' && 'type' in error && 'severity' in error;
    }

    private generateErrorId(): string {
        return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private getRecoveryActions(errorType: ErrorType): RecoveryAction[] {
        const actionMap: Record<ErrorType, RecoveryAction[]> = {
            [ErrorType.NETWORK_UNAVAILABLE]: [RecoveryAction.RETRY, RecoveryAction.FALLBACK],
            [ErrorType.API_TIMEOUT]: [RecoveryAction.RETRY],
            [ErrorType.AUTH_EXPIRED]: [RecoveryAction.USER_ACTION],
            [ErrorType.STORAGE_FULL]: [RecoveryAction.USER_ACTION],
            [ErrorType.CONTACT_NOT_FOUND]: [RecoveryAction.FALLBACK],
            [ErrorType.UNKNOWN_ERROR]: [RecoveryAction.RETRY, RecoveryAction.CONTACT_SUPPORT]
        };

        return actionMap[errorType] || [RecoveryAction.CONTACT_SUPPORT];
    }

    private isRetryable(errorType: ErrorType): boolean {
        const retryableTypes = [
            ErrorType.NETWORK_UNAVAILABLE,
            ErrorType.API_TIMEOUT,
            ErrorType.SERVER_ERROR,
            ErrorType.CONNECTION_FAILED
        ];
        return retryableTypes.includes(errorType);
    }

    private isReportable(errorType: ErrorType, severity: ErrorSeverity): boolean {
        return severity === ErrorSeverity.HIGH || severity === ErrorSeverity.CRITICAL ||
            errorType === ErrorType.UNKNOWN_ERROR;
    }

    private calculateRetryDelay(errorType: ErrorType): number {
        const config = this.retryConfigs.get(errorType);
        return config?.baseDelay || 1000;
    }

    private async delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    private async hasCachedData(): Promise<boolean> {
        try {
            const cachedContacts = await AsyncStorage.getItem('cached_contacts');
            return cachedContacts !== null;
        } catch {
            return false;
        }
    }

    private async getFallbackData(degradation?: GracefulDegradation): Promise<any> {
        if (!degradation || degradation.dataSource === 'cache') {
            try {
                const cachedData = await AsyncStorage.getItem('cached_contacts');
                return cachedData ? JSON.parse(cachedData) : null;
            } catch {
                return null;
            }
        }
        return null;
    }

    private async logError(error: AppError): Promise<void> {
        console.error('AppError:', {
            id: error.id,
            type: error.type,
            severity: error.severity,
            message: error.message,
            context: error.context
        });

        // Store error locally for reporting
        try {
            const errors = await this.getStoredErrors();
            errors.push(error);
            await AsyncStorage.setItem('stored_errors', JSON.stringify(errors.slice(-100))); // Keep last 100 errors
        } catch (storageError) {
            console.error('Failed to store error:', storageError);
        }
    }

    private async queueErrorReport(error: AppError): Promise<void> {
        this.errorQueue.push(error);
        // Process queue in background
        setTimeout(() => this.processErrorQueue(), 1000);
    }

    private async processErrorQueue(): Promise<void> {
        if (this.errorQueue.length === 0) return;

        const errors = [...this.errorQueue];
        this.errorQueue = [];

        // Send errors to reporting service (implement based on your backend)
        try {
            // await this.sendErrorReports(errors);
            console.log('Would send error reports:', errors.length);
        } catch (reportingError) {
            console.error('Failed to send error reports:', reportingError);
            // Re-queue errors for later
            this.errorQueue.unshift(...errors);
        }
    }

    private updateErrorMetrics(error: AppError): void {
        const existing = this.errorMetrics.get(error.type);
        if (existing) {
            existing.count++;
            existing.lastOccurrence = error.timestamp;
        } else {
            this.errorMetrics.set(error.type, {
                errorType: error.type,
                count: 1,
                lastOccurrence: error.timestamp,
                averageResolutionTime: 0,
                userImpact: error.severity === ErrorSeverity.CRITICAL ? 'high' : 'medium',
                resolutionRate: 0
            });
        }
    }

    private async loadErrorMetrics(): Promise<void> {
        try {
            const stored = await AsyncStorage.getItem('error_metrics');
            if (stored) {
                const metrics = JSON.parse(stored);
                Object.entries(metrics).forEach(([type, data]) => {
                    this.errorMetrics.set(type as ErrorType, data as ErrorMetrics);
                });
            }
        } catch {
            // Ignore loading errors
        }
    }

    private async getStoredErrors(): Promise<AppError[]> {
        try {
            const stored = await AsyncStorage.getItem('stored_errors');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }

    /**
     * Public methods for error reporting and feedback
     */
    public async reportError(errorId: string, userFeedback?: string): Promise<void> {
        const errors = await this.getStoredErrors();
        const error = errors.find(e => e.id === errorId);

        if (error) {
            const report: ErrorReport = {
                errorId,
                error,
                userFeedback,
                deviceInfo: await this.getDeviceInfo(),
                appState: await this.getAppState(),
                reportedAt: new Date()
            };

            // Queue for sending to backend
            await this.queueErrorReport(error);
        }
    }

    public getErrorMetrics(): Map<ErrorType, ErrorMetrics> {
        return new Map(this.errorMetrics);
    }

    public async clearErrorHistory(): Promise<void> {
        await AsyncStorage.removeItem('stored_errors');
        await AsyncStorage.removeItem('error_metrics');
        this.errorMetrics.clear();
    }

    private async getDeviceInfo(): Promise<any> {
        return {
            model: await DeviceInfo.getModel(),
            osVersion: await DeviceInfo.getSystemVersion(),
            appVersion: await DeviceInfo.getVersion(),
            buildNumber: await DeviceInfo.getBuildNumber(),
            isEmulator: await DeviceInfo.isEmulator(),
            availableMemory: await DeviceInfo.getFreeDiskStorage(),
            totalMemory: await DeviceInfo.getTotalDiskCapacity(),
            batteryLevel: await DeviceInfo.getBatteryLevel(),
            networkType: (await NetInfo.fetch()).type
        };
    }

    private async getAppState(): Promise<any> {
        return {
            currentScreen: 'unknown', // Would be set by navigation
            navigationStack: [],
            userAuthenticated: false, // Would be set by auth service
            connectedPlatforms: [],
            cacheSize: 0,
            backgroundTasksActive: 0
        };
    }
}

export default ErrorHandler;