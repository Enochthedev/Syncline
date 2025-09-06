/**
 * Comprehensive error handling types and classifications
 * for the mobile app integration system
 */

export enum ErrorType {
    // Network errors
    NETWORK_UNAVAILABLE = 'network_unavailable',
    API_TIMEOUT = 'api_timeout',
    SERVER_ERROR = 'server_error',
    CONNECTION_FAILED = 'connection_failed',

    // Authentication errors
    AUTH_EXPIRED = 'auth_expired',
    AUTH_INVALID = 'auth_invalid',
    PERMISSION_DENIED = 'permission_denied',
    BIOMETRIC_FAILED = 'biometric_failed',

    // Data errors
    DATA_CORRUPTION = 'data_corruption',
    SYNC_CONFLICT = 'sync_conflict',
    STORAGE_FULL = 'storage_full',
    CACHE_ERROR = 'cache_error',

    // Search errors
    SEARCH_TIMEOUT = 'search_timeout',
    SEARCH_INVALID_QUERY = 'search_invalid_query',
    SEARCH_SERVICE_UNAVAILABLE = 'search_service_unavailable',

    // Contact errors
    CONTACT_NOT_FOUND = 'contact_not_found',
    CONTACT_MERGE_FAILED = 'contact_merge_failed',
    CONTACT_SYNC_FAILED = 'contact_sync_failed',

    // Platform errors
    PLATFORM_DISCONNECTED = 'platform_disconnected',
    PLATFORM_RATE_LIMITED = 'platform_rate_limited',
    PLATFORM_AUTH_FAILED = 'platform_auth_failed',

    // UI/UX errors
    COMPONENT_RENDER_ERROR = 'component_render_error',
    NAVIGATION_ERROR = 'navigation_error',

    // System errors
    MEMORY_ERROR = 'memory_error',
    DEVICE_STORAGE_ERROR = 'device_storage_error',
    BACKGROUND_TASK_FAILED = 'background_task_failed',

    // Unknown/Generic
    UNKNOWN_ERROR = 'unknown_error'
}

export enum ErrorSeverity {
    LOW = 'low',
    MEDIUM = 'medium',
    HIGH = 'high',
    CRITICAL = 'critical'
}

export enum RecoveryAction {
    RETRY = 'retry',
    FALLBACK = 'fallback',
    USER_ACTION = 'user_action',
    IGNORE = 'ignore',
    RESTART_APP = 'restart_app',
    CONTACT_SUPPORT = 'contact_support'
}

export interface ErrorContext {
    userId?: string;
    deviceId: string;
    platform: 'ios' | 'android';
    appVersion: string;
    timestamp: Date;
    screenName?: string;
    actionAttempted?: string;
    networkStatus?: 'online' | 'offline' | 'poor';
    batteryLevel?: number;
    memoryUsage?: number;
    additionalData?: Record<string, any>;
}

export interface AppError {
    id: string;
    type: ErrorType;
    severity: ErrorSeverity;
    message: string;
    userMessage: string;
    technicalDetails?: string;
    context: ErrorContext;
    recoveryActions: RecoveryAction[];
    suggestedActions: SuggestedAction[];
    retryable: boolean;
    reportable: boolean;
    timestamp: Date;
    stackTrace?: string;
    originalError?: Error;
}

export interface SuggestedAction {
    id: string;
    title: string;
    description: string;
    actionType: 'button' | 'link' | 'navigation' | 'setting';
    actionData?: any;
    priority: number;
}

export interface ErrorResolution {
    resolved: boolean;
    action: RecoveryAction;
    message?: string;
    fallbackData?: any;
    retryAfter?: number;
}

export interface RetryConfig {
    maxRetries: number;
    baseDelay: number;
    maxDelay: number;
    backoffMultiplier: number;
    retryableErrors: ErrorType[];
}

export interface ErrorReport {
    errorId: string;
    error: AppError;
    userFeedback?: string;
    reproductionSteps?: string[];
    deviceInfo: DeviceInfo;
    appState: AppState;
    reportedAt: Date;
}

export interface DeviceInfo {
    model: string;
    osVersion: string;
    appVersion: string;
    buildNumber: string;
    isEmulator: boolean;
    availableMemory: number;
    totalMemory: number;
    batteryLevel: number;
    networkType: string;
}

export interface AppState {
    currentScreen: string;
    navigationStack: string[];
    userAuthenticated: boolean;
    connectedPlatforms: string[];
    lastSyncTime?: Date;
    cacheSize: number;
    backgroundTasksActive: number;
}

export interface FailureScenario {
    id: string;
    name: string;
    description: string;
    triggerConditions: string[];
    expectedBehavior: string;
    gracefulDegradation: GracefulDegradation;
}

export interface GracefulDegradation {
    fallbackStrategy: 'cached_data' | 'offline_mode' | 'limited_functionality' | 'error_state';
    fallbackMessage: string;
    availableActions: string[];
    dataSource?: 'cache' | 'local_storage' | 'mock_data';
}

export interface ErrorMetrics {
    errorType: ErrorType;
    count: number;
    lastOccurrence: Date;
    averageResolutionTime: number;
    userImpact: 'low' | 'medium' | 'high';
    resolutionRate: number;
}