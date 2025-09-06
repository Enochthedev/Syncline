/**
 * CodePush Configuration for React Native
 * Handles over-the-air updates with feature flags and A/B testing
 */

import { Platform } from 'react-native';
import CodePush from 'react-native-code-push';

// CodePush deployment keys
const CODEPUSH_DEPLOYMENT_KEYS = {
    ios: {
        staging: 'YOUR_IOS_STAGING_DEPLOYMENT_KEY',
        production: 'YOUR_IOS_PRODUCTION_DEPLOYMENT_KEY',
    },
    android: {
        staging: 'YOUR_ANDROID_STAGING_DEPLOYMENT_KEY',
        production: 'YOUR_ANDROID_PRODUCTION_DEPLOYMENT_KEY',
    },
};

// Feature flags configuration
const FEATURE_FLAGS = {
    // Core features
    ENHANCED_SEARCH: 'enhanced_search',
    VOICE_COMMANDS: 'voice_commands',
    BIOMETRIC_AUTH: 'biometric_auth',
    DARK_MODE: 'dark_mode',

    // Experimental features
    AI_INSIGHTS: 'ai_insights',
    REAL_TIME_SYNC: 'real_time_sync',
    ADVANCED_FILTERS: 'advanced_filters',
    CONTACT_ANALYTICS: 'contact_analytics',

    // A/B testing features
    NEW_ONBOARDING: 'new_onboarding',
    REDESIGNED_SEARCH: 'redesigned_search',
    IMPROVED_NAVIGATION: 'improved_navigation',
};

// A/B testing configuration
const AB_TESTS = {
    SEARCH_ALGORITHM: {
        name: 'search_algorithm_test',
        variants: ['fuzzy_search', 'semantic_search', 'hybrid_search'],
        defaultVariant: 'fuzzy_search',
        rolloutPercentage: 50,
    },
    CONTACT_CARD_DESIGN: {
        name: 'contact_card_design_test',
        variants: ['compact', 'detailed', 'minimal'],
        defaultVariant: 'compact',
        rolloutPercentage: 30,
    },
    NOTIFICATION_STRATEGY: {
        name: 'notification_strategy_test',
        variants: ['immediate', 'batched', 'smart_timing'],
        defaultVariant: 'immediate',
        rolloutPercentage: 25,
    },
};

// CodePush update strategies
const UPDATE_STRATEGIES = {
    IMMEDIATE: 'immediate',
    ON_NEXT_RESTART: 'on_next_restart',
    ON_NEXT_RESUME: 'on_next_resume',
    MANUAL: 'manual',
};

// Environment-based configuration
const getEnvironment = () => {
    if (__DEV__) return 'development';
    return process.env.NODE_ENV === 'production' ? 'production' : 'staging';
};

// Get deployment key based on platform and environment
const getDeploymentKey = () => {
    const environment = getEnvironment();
    const platform = Platform.OS;

    if (environment === 'development') {
        return null; // No CodePush in development
    }

    return CODEPUSH_DEPLOYMENT_KEYS[platform][environment];
};

// CodePush options configuration
const getCodePushOptions = () => {
    const environment = getEnvironment();

    const baseOptions = {
        checkFrequency: CodePush.CheckFrequency.ON_APP_RESUME,
        installMode: CodePush.InstallMode.ON_NEXT_RESTART,
        minimumBackgroundDuration: 60000, // 1 minute
        deploymentKey: getDeploymentKey(),
    };

    // Environment-specific configurations
    switch (environment) {
        case 'staging':
            return {
                ...baseOptions,
                checkFrequency: CodePush.CheckFrequency.ON_APP_START,
                installMode: CodePush.InstallMode.IMMEDIATE,
            };

        case 'production':
            return {
                ...baseOptions,
                checkFrequency: CodePush.CheckFrequency.ON_APP_RESUME,
                installMode: CodePush.InstallMode.ON_NEXT_RESTART,
                minimumBackgroundDuration: 300000, // 5 minutes
            };

        default:
            return baseOptions;
    }
};

// Feature flag management
class FeatureFlagManager {
    constructor() {
        this.flags = new Map();
        this.abTests = new Map();
        this.userId = null;
    }

    async initialize(userId) {
        this.userId = userId;
        await this.loadFeatureFlags();
        await this.initializeABTests();
    }

    async loadFeatureFlags() {
        try {
            // Load feature flags from remote config or local storage
            const remoteFlags = await this.fetchRemoteFlags();
            const localFlags = await this.getLocalFlags();

            // Merge remote and local flags (remote takes precedence)
            const mergedFlags = { ...localFlags, ...remoteFlags };

            Object.entries(mergedFlags).forEach(([key, value]) => {
                this.flags.set(key, value);
            });
        } catch (error) {
            console.warn('Failed to load feature flags:', error);
            // Use default flags if remote loading fails
            this.loadDefaultFlags();
        }
    }

    async fetchRemoteFlags() {
        // Implement remote feature flag fetching
        // This could be from Firebase Remote Config, LaunchDarkly, etc.
        const response = await fetch('/api/feature-flags', {
            headers: {
                'Authorization': `Bearer ${await this.getAuthToken()}`,
                'User-ID': this.userId,
            },
        });

        if (response.ok) {
            return await response.json();
        }

        throw new Error('Failed to fetch remote flags');
    }

    async getLocalFlags() {
        // Load cached flags from AsyncStorage
        const AsyncStorage = require('@react-native-async-storage/async-storage');
        const cachedFlags = await AsyncStorage.getItem('feature_flags');
        return cachedFlags ? JSON.parse(cachedFlags) : {};
    }

    loadDefaultFlags() {
        // Set default feature flag values
        Object.values(FEATURE_FLAGS).forEach(flag => {
            this.flags.set(flag, false);
        });
    }

    async initializeABTests() {
        for (const [testKey, testConfig] of Object.entries(AB_TESTS)) {
            const variant = await this.getABTestVariant(testKey, testConfig);
            this.abTests.set(testKey, variant);
        }
    }

    async getABTestVariant(testKey, testConfig) {
        // Check if user already has a variant assigned
        const AsyncStorage = require('@react-native-async-storage/async-storage');
        const existingVariant = await AsyncStorage.getItem(`ab_test_${testKey}`);

        if (existingVariant) {
            return existingVariant;
        }

        // Determine if user should be included in the test
        const userHash = this.hashUserId(this.userId);
        const rolloutThreshold = testConfig.rolloutPercentage / 100;

        if (userHash > rolloutThreshold) {
            // User not in test, return default variant
            return testConfig.defaultVariant;
        }

        // Assign variant based on user hash
        const variantIndex = Math.floor(userHash * testConfig.variants.length / rolloutThreshold);
        const assignedVariant = testConfig.variants[variantIndex] || testConfig.defaultVariant;

        // Cache the variant assignment
        await AsyncStorage.setItem(`ab_test_${testKey}`, assignedVariant);

        // Track the assignment
        this.trackABTestAssignment(testKey, assignedVariant);

        return assignedVariant;
    }

    hashUserId(userId) {
        // Simple hash function for consistent variant assignment
        let hash = 0;
        for (let i = 0; i < userId.length; i++) {
            const char = userId.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash) / Math.pow(2, 31);
    }

    isFeatureEnabled(flagName) {
        return this.flags.get(flagName) || false;
    }

    getABTestVariant(testName) {
        return this.abTests.get(testName);
    }

    async trackABTestAssignment(testName, variant) {
        // Track A/B test assignment for analytics
        const analytics = require('@react-native-firebase/analytics').default;

        await analytics().logEvent('ab_test_assignment', {
            test_name: testName,
            variant: variant,
            user_id: this.userId,
            timestamp: Date.now(),
        });
    }

    async getAuthToken() {
        // Get authentication token for API calls
        const AsyncStorage = require('@react-native-async-storage/async-storage');
        return await AsyncStorage.getItem('auth_token');
    }
}

// CodePush update manager
class CodePushManager {
    constructor() {
        this.updateAvailable = false;
        this.downloadProgress = 0;
        this.updateStrategy = UPDATE_STRATEGIES.ON_NEXT_RESTART;
    }

    async checkForUpdate() {
        try {
            const update = await CodePush.checkForUpdate(getDeploymentKey());

            if (update) {
                this.updateAvailable = true;
                await this.handleUpdateAvailable(update);
            }

            return update;
        } catch (error) {
            console.warn('CodePush check failed:', error);
            return null;
        }
    }

    async handleUpdateAvailable(update) {
        // Check if update should be applied based on strategy
        const shouldDownload = await this.shouldDownloadUpdate(update);

        if (shouldDownload) {
            await this.downloadUpdate(update);
        }
    }

    async shouldDownloadUpdate(update) {
        // Implement logic to determine if update should be downloaded
        // Consider factors like:
        // - Update strategy
        // - Network conditions
        // - Battery level
        // - User preferences

        const NetInfo = require('@react-native-community/netinfo');
        const DeviceInfo = require('react-native-device-info');

        const networkState = await NetInfo.fetch();
        const batteryLevel = await DeviceInfo.getBatteryLevel();

        // Don't download on cellular if update is large
        if (!networkState.isWiFiEnabled && update.packageSize > 5 * 1024 * 1024) {
            return false;
        }

        // Don't download if battery is low
        if (batteryLevel < 0.2) {
            return false;
        }

        return true;
    }

    async downloadUpdate(update) {
        try {
            await CodePush.sync(
                {
                    ...getCodePushOptions(),
                    updateDialog: {
                        title: 'Update Available',
                        optionalUpdateMessage: 'An update is available. Would you like to install it?',
                        optionalIgnoreButtonLabel: 'Later',
                        optionalInstallButtonLabel: 'Install',
                    },
                },
                this.onSyncStatusChanged.bind(this),
                this.onDownloadProgress.bind(this)
            );
        } catch (error) {
            console.error('CodePush sync failed:', error);
        }
    }

    onSyncStatusChanged(status) {
        switch (status) {
            case CodePush.SyncStatus.CHECKING_FOR_UPDATE:
                console.log('Checking for CodePush update...');
                break;
            case CodePush.SyncStatus.DOWNLOADING_PACKAGE:
                console.log('Downloading CodePush update...');
                break;
            case CodePush.SyncStatus.INSTALLING_UPDATE:
                console.log('Installing CodePush update...');
                break;
            case CodePush.SyncStatus.UP_TO_DATE:
                console.log('App is up to date');
                break;
            case CodePush.SyncStatus.UPDATE_INSTALLED:
                console.log('CodePush update installed');
                break;
        }
    }

    onDownloadProgress(progress) {
        this.downloadProgress = progress.receivedBytes / progress.totalBytes;
        console.log(`Download progress: ${Math.round(this.downloadProgress * 100)}%`);
    }
}

// Export configuration and managers
export {
    FEATURE_FLAGS,
    AB_TESTS,
    UPDATE_STRATEGIES,
    getCodePushOptions,
    FeatureFlagManager,
    CodePushManager,
};