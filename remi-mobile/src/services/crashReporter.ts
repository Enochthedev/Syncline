/**
 * Crash reporting and automatic error collection service
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';
import NetInfo from '@react-native-community/netinfo';
import { AppError, ErrorReport, DeviceInfo as ErrorDeviceInfo } from '../types/errors';

interface CrashReport {
    id: string;
    timestamp: Date;
    error: AppError;
    deviceInfo: ErrorDeviceInfo;
    appState: AppState;
    breadcrumbs: Breadcrumb[];
    userActions: UserAction[];
    performanceMetrics: PerformanceMetrics;
}

interface Breadcrumb {
    timestamp: Date;
    category: 'navigation' | 'user_action' | 'network' | 'state_change';
    message: string;
    level: 'info' | 'warning' | 'error';
    data?: Record<string, any>;
}

interface UserAction {
    timestamp: Date;
    action: string;
    screen: string;
    element?: string;
    data?: Record<string, any>;
}

interface PerformanceMetrics {
    memoryUsage: number;
    cpuUsage?: number;
    batteryLevel: number;
    networkLatency?: number;
    renderTime?: number;
    jsHeapSize?: number;
}

interface AppState {
    currentScreen: string;
    navigationStack: string[];
    userAuthenticated: boolean;
    connectedPlatforms: string[];
    lastSyncTime?: Date;
    cacheSize: number;
    backgroundTasksActive: number;
}

class CrashReporter {
    private static instance: CrashReporter;
    private breadcrumbs: Breadcrumb[] = [];
    private userActions: UserAction[] = [];
    private maxBreadcrumbs = 50;
    private maxUserActions = 20;
    private isEnabled = true;
    private reportQueue: CrashReport[] = [];

    private constructor() {
        this.initializeGlobalErrorHandlers();
        this.loadStoredReports();
    }

    public static getInstance(): CrashReporter {
        if (!CrashReporter.instance) {
            CrashReporter.instance = new CrashReporter();
        }
        return CrashReporter.instance;
    }

    /**
     * Initialize global error handlers for automatic crash detection
     */
    private initializeGlobalErrorHandlers(): void {
        // Handle unhandled promise rejections
        const originalHandler = global.Promise.prototype.catch;
        global.Promise.prototype.catch = function (onRejected) {
            return originalHandler.call(this, (error) => {
                CrashReporter.getInstance().recordUnhandledError(error, 'unhandled_promise_rejection');
                if (onRejected) {
                    return onRejected(error);
                }
                throw error;
            });
        };

        // Handle JavaScript errors
        const originalConsoleError = console.error;
        console.error = (...args) => {
            const error = args[0];
            if (error instanceof Error) {
                CrashReporter.getInstance().recordUnhandledError(error, 'console_error');
            }
            originalConsoleError.apply(console, args);
        };

        // Set up periodic reporting
        setInterval(() => {
            this.processReportQueue();
        }, 30000); // Process every 30 seconds
    }

    /**
     * Record an unhandled error for crash reporting
     */
    public async recordUnhandledError(error: Error, source: string): Promise<void> {
        if (!this.isEnabled) return;

        try {
            const crashReport = await this.createCrashReport(error, source);
            await this.storeCrashReport(crashReport);
            this.reportQueue.push(crashReport);

            console.error('Unhandled error recorded:', {
                id: crashReport.id,
                source,
                message: error.message
            });
        } catch (reportingError) {
            console.error('Failed to record crash report:', reportingError);
        }
    }

    /**
     * Record a handled error for analysis
     */
    public async recordHandledError(appError: AppError): Promise<void> {
        if (!this.isEnabled) return;

        try {
            const crashReport = await this.createCrashReportFromAppError(appError);
            await this.storeCrashReport(crashReport);

            // Only queue critical errors for immediate reporting
            if (appError.severity === 'critical') {
                this.reportQueue.push(crashReport);
            }
        } catch (reportingError) {
            console.error('Failed to record handled error:', reportingError);
        }
    }

    /**
     * Add breadcrumb for debugging context
     */
    public addBreadcrumb(
        category: Breadcrumb['category'],
        message: string,
        level: Breadcrumb['level'] = 'info',
        data?: Record<string, any>
    ): void {
        if (!this.isEnabled) return;

        const breadcrumb: Breadcrumb = {
            timestamp: new Date(),
            category,
            message,
            level,
            data
        };

        this.breadcrumbs.push(breadcrumb);

        // Keep only the most recent breadcrumbs
        if (this.breadcrumbs.length > this.maxBreadcrumbs) {
            this.breadcrumbs = this.breadcrumbs.slice(-this.maxBreadcrumbs);
        }
    }

    /**
     * Record user action for debugging context
     */
    public recordUserAction(
        action: string,
        screen: string,
        element?: string,
        data?: Record<string, any>
    ): void {
        if (!this.isEnabled) return;

        const userAction: UserAction = {
            timestamp: new Date(),
            action,
            screen,
            element,
            data
        };

        this.userActions.push(userAction);

        // Keep only the most recent actions
        if (this.userActions.length > this.maxUserActions) {
            this.userActions = this.userActions.slice(-this.maxUserActions);
        }
    }

    /**
     * Create comprehensive crash report
     */
    private async createCrashReport(error: Error, source: string): Promise<CrashReport> {
        const deviceInfo = await this.collectDeviceInfo();
        const appState = await this.collectAppState();
        const performanceMetrics = await this.collectPerformanceMetrics();

        // Create AppError from raw error
        const appError: AppError = {
            id: this.generateReportId(),
            type: 'unknown_error' as any,
            severity: 'critical' as any,
            message: error.message,
            userMessage: 'An unexpected error occurred',
            context: {
                deviceId: deviceInfo.model,
                platform: 'ios' as any,
                appVersion: deviceInfo.appVersion,
                timestamp: new Date(),
                additionalData: { source }
            },
            recoveryActions: [],
            suggestedActions: [],
            retryable: false,
            reportable: true,
            timestamp: new Date(),
            stackTrace: error.stack,
            originalError: error
        };

        return {
            id: this.generateReportId(),
            timestamp: new Date(),
            error: appError,
            deviceInfo,
            appState,
            breadcrumbs: [...this.breadcrumbs],
            userActions: [...this.userActions],
            performanceMetrics
        };
    }

    /**
     * Create crash report from existing AppError
     */
    private async createCrashReportFromAppError(appError: AppError): Promise<CrashReport> {
        const deviceInfo = await this.collectDeviceInfo();
        const appState = await this.collectAppState();
        const performanceMetrics = await this.collectPerformanceMetrics();

        return {
            id: this.generateReportId(),
            timestamp: new Date(),
            error: appError,
            deviceInfo,
            appState,
            breadcrumbs: [...this.breadcrumbs],
            userActions: [...this.userActions],
            performanceMetrics
        };
    }

    /**
     * Collect comprehensive device information
     */
    private async collectDeviceInfo(): Promise<ErrorDeviceInfo> {
        const netInfo = await NetInfo.fetch();

        return {
            model: await DeviceInfo.getModel(),
            osVersion: await DeviceInfo.getSystemVersion(),
            appVersion: await DeviceInfo.getVersion(),
            buildNumber: await DeviceInfo.getBuildNumber(),
            isEmulator: await DeviceInfo.isEmulator(),
            availableMemory: await DeviceInfo.getFreeDiskStorage(),
            totalMemory: await DeviceInfo.getTotalDiskCapacity(),
            batteryLevel: await DeviceInfo.getBatteryLevel(),
            networkType: netInfo.type || 'unknown'
        };
    }

    /**
     * Collect current app state
     */
    private async collectAppState(): Promise<AppState> {
        // This would integrate with your app's state management
        return {
            currentScreen: 'unknown',
            navigationStack: [],
            userAuthenticated: false,
            connectedPlatforms: [],
            lastSyncTime: undefined,
            cacheSize: 0,
            backgroundTasksActive: 0
        };
    }

    /**
     * Collect performance metrics
     */
    private async collectPerformanceMetrics(): Promise<PerformanceMetrics> {
        const batteryLevel = await DeviceInfo.getBatteryLevel();
        const availableMemory = await DeviceInfo.getFreeDiskStorage();
        const totalMemory = await DeviceInfo.getTotalDiskCapacity();

        return {
            memoryUsage: ((totalMemory - availableMemory) / totalMemory) * 100,
            batteryLevel,
            jsHeapSize: (global as any).performance?.memory?.usedJSHeapSize
        };
    }

    /**
     * Store crash report locally
     */
    private async storeCrashReport(report: CrashReport): Promise<void> {
        try {
            const stored = await this.getStoredReports();
            stored.push(report);

            // Keep only the most recent 50 reports
            const recentReports = stored.slice(-50);

            await AsyncStorage.setItem('crash_reports', JSON.stringify(recentReports));
        } catch (error) {
            console.error('Failed to store crash report:', error);
        }
    }

    /**
     * Load stored crash reports
     */
    private async loadStoredReports(): Promise<void> {
        try {
            const stored = await AsyncStorage.getItem('crash_reports');
            if (stored) {
                const reports: CrashReport[] = JSON.parse(stored);
                this.reportQueue.push(...reports.filter(r => !r.error.reportable));
            }
        } catch (error) {
            console.error('Failed to load stored reports:', error);
        }
    }

    /**
     * Get stored crash reports
     */
    private async getStoredReports(): Promise<CrashReport[]> {
        try {
            const stored = await AsyncStorage.getItem('crash_reports');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }

    /**
     * Process report queue and send to backend
     */
    private async processReportQueue(): Promise<void> {
        if (this.reportQueue.length === 0) return;

        const netInfo = await NetInfo.fetch();
        if (!netInfo.isConnected) return;

        const reportsToSend = [...this.reportQueue];
        this.reportQueue = [];

        try {
            await this.sendReportsToBackend(reportsToSend);
            console.log(`Sent ${reportsToSend.length} crash reports to backend`);
        } catch (error) {
            console.error('Failed to send crash reports:', error);
            // Re-queue reports for later
            this.reportQueue.unshift(...reportsToSend);
        }
    }

    /**
     * Send reports to backend service
     */
    private async sendReportsToBackend(reports: CrashReport[]): Promise<void> {
        // This would integrate with your backend API
        // For now, just log the reports
        console.log('Would send crash reports to backend:', {
            count: reports.length,
            reports: reports.map(r => ({
                id: r.id,
                timestamp: r.timestamp,
                errorType: r.error.type,
                severity: r.error.severity
            }))
        });

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    /**
     * Generate unique report ID
     */
    private generateReportId(): string {
        return `crash_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Public API methods
     */
    public setEnabled(enabled: boolean): void {
        this.isEnabled = enabled;
    }

    public isReportingEnabled(): boolean {
        return this.isEnabled;
    }

    public async getCrashReports(): Promise<CrashReport[]> {
        return this.getStoredReports();
    }

    public async clearCrashReports(): Promise<void> {
        await AsyncStorage.removeItem('crash_reports');
        this.reportQueue = [];
    }

    public getBreadcrumbs(): Breadcrumb[] {
        return [...this.breadcrumbs];
    }

    public getUserActions(): UserAction[] {
        return [...this.userActions];
    }

    public clearBreadcrumbs(): void {
        this.breadcrumbs = [];
    }

    public clearUserActions(): void {
        this.userActions = [];
    }

    /**
     * Force send all queued reports
     */
    public async forceSendReports(): Promise<void> {
        await this.processReportQueue();
    }
}

export default CrashReporter;