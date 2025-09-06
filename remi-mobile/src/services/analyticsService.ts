/**
 * Analytics and Monitoring Service
 * Integrates Firebase Analytics, Crashlytics, and Performance Monitoring
 */

import analytics from '@react-native-firebase/analytics';
import crashlytics from '@react-native-firebase/crashlytics';
import perf from '@react-native-firebase/perf';
import { Platform } from 'react-native';

// Event types for analytics
export enum AnalyticsEvent {
    // User actions
    USER_LOGIN = 'user_login',
    USER_LOGOUT = 'user_logout',
    USER_SIGNUP = 'user_signup',

    // Search events
    SEARCH_PERFORMED = 'search_performed',
    SEARCH_RESULT_CLICKED = 'search_result_clicked',
    CONTACT_SEARCHED = 'contact_searched',
    VOICE_SEARCH_USED = 'voice_search_used',

    // Contact events
    CONTACT_VIEWED = 'contact_viewed',
    CONTACT_CALLED = 'contact_called',
    CONTACT_MESSAGED = 'contact_messaged',
    CONTACT_SHARED = 'contact_shared',

    // App lifecycle
    APP_OPENED = 'app_opened',
    APP_BACKGROUNDED = 'app_backgrounded',
    SCREEN_VIEW = 'screen_view',

    // Feature usage
    FEATURE_USED = 'feature_used',
    BIOMETRIC_AUTH_USED = 'biometric_auth_used',
    OFFLINE_MODE_ENTERED = 'offline_mode_entered',

    // Performance
    API_CALL_COMPLETED = 'api_call_completed',
    SYNC_COMPLETED = 'sync_completed',
    ERROR_OCCURRED = 'error_occurred',
}

// User properties for segmentation
export enum UserProperty {
    USER_TYPE = 'user_type',
    PLATFORM_COUNT = 'platform_count',
    CONTACT_COUNT = 'contact_count',
    FEATURE_FLAGS = 'feature_flags',
    APP_VERSION = 'app_version',
    DEVICE_TYPE = 'device_type',
}

// Performance trace names
export enum PerformanceTrace {
    APP_START = 'app_start',
    SEARCH_PERFORMANCE = 'search_performance',
    CONTACT_LOAD = 'contact_load',
    API_RESPONSE = 'api_response',
    SYNC_PERFORMANCE = 'sync_performance',
    SCREEN_LOAD = 'screen_load',
}

interface AnalyticsEventParams {
    [key: string]: string | number | boolean;
}

interface PerformanceMetrics {
    duration: number;
    success: boolean;
    errorCode?: string;
    itemCount?: number;
}

class AnalyticsService {
    private isInitialized = false;
    private userId: string | null = null;
    private activeTraces = new Map<string, any>();

    async initialize(): Promise<void> {
        try {
            // Initialize Firebase Analytics
            await analytics().setAnalyticsCollectionEnabled(true);

            // Initialize Crashlytics
            await crashlytics().setCrashlyticsCollectionEnabled(true);

            // Set default user properties
            await this.setDefaultUserProperties();

            this.isInitialized = true;
            console.log('Analytics service initialized successfully');
        } catch (error) {
            console.error('Failed to initialize analytics service:', error);
            this.logError('analytics_init_failed', error);
        }
    }

    async setUserId(userId: string): Promise<void> {
        if (!this.isInitialized) return;

        try {
            this.userId = userId;
            await analytics().setUserId(userId);
            await crashlytics().setUserId(userId);

            console.log('User ID set for analytics:', userId);
        } catch (error) {
            console.error('Failed to set user ID:', error);
        }
    }

    async setUserProperty(property: UserProperty, value: string): Promise<void> {
        if (!this.isInitialized) return;

        try {
            await analytics().setUserProperty(property, value);
            console.log(`User property set: ${property} = ${value}`);
        } catch (error) {
            console.error('Failed to set user property:', error);
        }
    }

    async logEvent(
        event: AnalyticsEvent,
        params: AnalyticsEventParams = {}
    ): Promise<void> {
        if (!this.isInitialized) return;

        try {
            // Add common parameters
            const enrichedParams = {
                ...params,
                platform: Platform.OS,
                timestamp: Date.now(),
                user_id: this.userId,
            };

            await analytics().logEvent(event, enrichedParams);
            console.log(`Analytics event logged: ${event}`, enrichedParams);
        } catch (error) {
            console.error('Failed to log analytics event:', error);
        }
    }

    async logScreenView(screenName: string, screenClass?: string): Promise<void> {
        if (!this.isInitialized) return;

        try {
            await analytics().logScreenView({
                screen_name: screenName,
                screen_class: screenClass || screenName,
            });

            // Also log as custom event for additional tracking
            await this.logEvent(AnalyticsEvent.SCREEN_VIEW, {
                screen_name: screenName,
                screen_class: screenClass || screenName,
            });
        } catch (error) {
            console.error('Failed to log screen view:', error);
        }
    }

    async logError(
        errorName: string,
        error: Error | string,
        context?: Record<string, any>
    ): Promise<void> {
        if (!this.isInitialized) return;

        try {
            // Log to Crashlytics
            if (error instanceof Error) {
                if (context) {
                    Object.entries(context).forEach(([key, value]) => {
                        crashlytics().setAttribute(key, String(value));
                    });
                }
                crashlytics().recordError(error);
            } else {
                crashlytics().log(String(error));
            }

            // Log as analytics event
            await this.logEvent(AnalyticsEvent.ERROR_OCCURRED, {
                error_name: errorName,
                error_message: error instanceof Error ? error.message : String(error),
                ...context,
            });

            console.error(`Error logged: ${errorName}`, error, context);
        } catch (logError) {
            console.error('Failed to log error:', logError);
        }
    }

    async startPerformanceTrace(traceName: PerformanceTrace): Promise<void> {
        if (!this.isInitialized) return;

        try {
            const trace = perf().newTrace(traceName);
            await trace.start();
            this.activeTraces.set(traceName, trace);

            console.log(`Performance trace started: ${traceName}`);
        } catch (error) {
            console.error('Failed to start performance trace:', error);
        }
    }

    async stopPerformanceTrace(
        traceName: PerformanceTrace,
        metrics?: PerformanceMetrics
    ): Promise<void> {
        if (!this.isInitialized) return;

        try {
            const trace = this.activeTraces.get(traceName);
            if (!trace) {
                console.warn(`No active trace found for: ${traceName}`);
                return;
            }

            // Add custom metrics if provided
            if (metrics) {
                if (metrics.itemCount !== undefined) {
                    trace.putMetric('item_count', metrics.itemCount);
                }
                trace.putMetric('success', metrics.success ? 1 : 0);
                if (metrics.errorCode) {
                    trace.putAttribute('error_code', metrics.errorCode);
                }
            }

            await trace.stop();
            this.activeTraces.delete(traceName);

            console.log(`Performance trace stopped: ${traceName}`, metrics);
        } catch (error) {
            console.error('Failed to stop performance trace:', error);
        }
    }

    async logSearchPerformance(
        query: string,
        resultCount: number,
        duration: number,
        searchType: 'text' | 'voice' | 'contact'
    ): Promise<void> {
        await this.logEvent(AnalyticsEvent.SEARCH_PERFORMED, {
            search_type: searchType,
            query_length: query.length,
            result_count: resultCount,
            duration_ms: duration,
            has_results: resultCount > 0,
        });
    }

    async logAPICall(
        endpoint: string,
        method: string,
        statusCode: number,
        duration: number
    ): Promise<void> {
        await this.logEvent(AnalyticsEvent.API_CALL_COMPLETED, {
            endpoint,
            method,
            status_code: statusCode,
            duration_ms: duration,
            success: statusCode >= 200 && statusCode < 300,
        });
    }

    async logFeatureUsage(
        featureName: string,
        context?: Record<string, any>
    ): Promise<void> {
        await this.logEvent(AnalyticsEvent.FEATURE_USED, {
            feature_name: featureName,
            ...context,
        });
    }

    async logUserEngagement(
        action: string,
        category: string,
        value?: number
    ): Promise<void> {
        await this.logEvent('user_engagement', {
            engagement_action: action,
            engagement_category: category,
            engagement_value: value,
        });
    }

    async setCustomDimensions(dimensions: Record<string, string>): Promise<void> {
        if (!this.isInitialized) return;

        try {
            for (const [key, value] of Object.entries(dimensions)) {
                await analytics().setUserProperty(key, value);
            }
        } catch (error) {
            console.error('Failed to set custom dimensions:', error);
        }
    }

    private async setDefaultUserProperties(): Promise<void> {
        try {
            const DeviceInfo = require('react-native-device-info');

            await this.setUserProperty(UserProperty.PLATFORM_COUNT, '0');
            await this.setUserProperty(UserProperty.CONTACT_COUNT, '0');
            await this.setUserProperty(UserProperty.APP_VERSION, DeviceInfo.getVersion());
            await this.setUserProperty(UserProperty.DEVICE_TYPE, Platform.OS);
        } catch (error) {
            console.error('Failed to set default user properties:', error);
        }
    }

    // A/B Testing Analytics
    async logABTestExposure(
        testName: string,
        variant: string,
        context?: Record<string, any>
    ): Promise<void> {
        await this.logEvent('ab_test_exposure', {
            test_name: testName,
            variant,
            ...context,
        });
    }

    async logABTestConversion(
        testName: string,
        variant: string,
        conversionType: string,
        value?: number
    ): Promise<void> {
        await this.logEvent('ab_test_conversion', {
            test_name: testName,
            variant,
            conversion_type: conversionType,
            conversion_value: value,
        });
    }

    // Performance Monitoring Helpers
    async measureAsyncOperation<T>(
        traceName: PerformanceTrace,
        operation: () => Promise<T>
    ): Promise<T> {
        await this.startPerformanceTrace(traceName);

        try {
            const result = await operation();
            await this.stopPerformanceTrace(traceName, {
                duration: 0, // Will be calculated by Firebase
                success: true,
            });
            return result;
        } catch (error) {
            await this.stopPerformanceTrace(traceName, {
                duration: 0,
                success: false,
                errorCode: error instanceof Error ? error.name : 'unknown_error',
            });
            throw error;
        }
    }

    // Crash Reporting Helpers
    async setBreadcrumb(message: string, category?: string): Promise<void> {
        if (!this.isInitialized) return;

        try {
            crashlytics().log(`[${category || 'INFO'}] ${message}`);
        } catch (error) {
            console.error('Failed to set breadcrumb:', error);
        }
    }

    async setCustomKey(key: string, value: string | number | boolean): Promise<void> {
        if (!this.isInitialized) return;

        try {
            await crashlytics().setAttribute(key, String(value));
        } catch (error) {
            console.error('Failed to set custom key:', error);
        }
    }

    // Network Monitoring
    async logNetworkRequest(
        url: string,
        method: string,
        statusCode: number,
        responseTime: number,
        responseSize?: number
    ): Promise<void> {
        await this.logEvent('network_request', {
            url,
            method,
            status_code: statusCode,
            response_time_ms: responseTime,
            response_size_bytes: responseSize,
            success: statusCode >= 200 && statusCode < 300,
        });
    }
}

// Create singleton instance
export const analyticsService = new AnalyticsService();

// Export types and enums
export type { AnalyticsEventParams, PerformanceMetrics };