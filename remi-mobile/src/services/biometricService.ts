import TouchID from 'react-native-touch-id';
import { Platform } from 'react-native';
import { securityService, SecurityEventType } from './securityService';

export interface BiometricConfig {
    title: string;
    subtitle?: string;
    description?: string;
    fallbackLabel?: string;
    cancelLabel?: string;
    color?: string;
    imageColor?: string;
    imageErrorColor?: string;
    sensorDescription?: string;
    sensorErrorDescription?: string;
    passcodeFallback?: boolean;
    showFallbackButton?: boolean;
    unifiedErrors?: boolean;
}

export interface BiometricCapabilities {
    isAvailable: boolean;
    biometryType: BiometryType | null;
    error?: string;
}

export enum BiometryType {
    TOUCH_ID = 'TouchID',
    FACE_ID = 'FaceID',
    FINGERPRINT = 'Fingerprint',
    FACE = 'Face',
    IRIS = 'Iris'
}

export interface BiometricAuthResult {
    success: boolean;
    error?: string;
    biometryType?: BiometryType;
    timestamp: Date;
}

class BiometricService {
    private defaultConfig: BiometricConfig = {
        title: 'Authenticate',
        subtitle: 'Use your biometric to authenticate',
        description: 'Place your finger on the sensor or look at the camera',
        fallbackLabel: 'Use Passcode',
        cancelLabel: 'Cancel',
        passcodeFallback: true,
        showFallbackButton: true,
        unifiedErrors: false
    };

    // Check biometric availability
    async checkBiometricCapabilities(): Promise<BiometricCapabilities> {
        try {
            const biometryType = await TouchID.isSupported();

            await securityService.logSecurityEvent({
                type: SecurityEventType.BIOMETRIC_AUTH,
                details: {
                    action: 'capability_check',
                    biometryType,
                    platform: Platform.OS
                },
                severity: 'low'
            });

            return {
                isAvailable: true,
                biometryType: this.mapBiometryType(biometryType)
            };
        } catch (error) {
            await securityService.logSecurityEvent({
                type: SecurityEventType.BIOMETRIC_AUTH,
                details: {
                    action: 'capability_check_failed',
                    error: error.message,
                    platform: Platform.OS
                },
                severity: 'low'
            });

            return {
                isAvailable: false,
                biometryType: null,
                error: error.message
            };
        }
    }

    private mapBiometryType(touchIdType: any): BiometryType | null {
        if (typeof touchIdType === 'string') {
            switch (touchIdType) {
                case 'TouchID':
                    return BiometryType.TOUCH_ID;
                case 'FaceID':
                    return BiometryType.FACE_ID;
                case 'Fingerprint':
                    return BiometryType.FINGERPRINT;
                case 'Face':
                    return BiometryType.FACE;
                case 'Iris':
                    return BiometryType.IRIS;
                default:
                    return null;
            }
        }
        return null;
    }

    // Authenticate with biometrics
    async authenticate(config?: Partial<BiometricConfig>): Promise<BiometricAuthResult> {
        const authConfig = { ...this.defaultConfig, ...config };
        const startTime = new Date();

        try {
            // Check if biometrics are available
            const capabilities = await this.checkBiometricCapabilities();
            if (!capabilities.isAvailable) {
                throw new Error(capabilities.error || 'Biometric authentication not available');
            }

            // Perform authentication
            const success = await TouchID.authenticate(
                authConfig.description || 'Authenticate to continue',
                {
                    title: authConfig.title,
                    subtitle: authConfig.subtitle,
                    fallbackLabel: authConfig.fallbackLabel,
                    cancelLabel: authConfig.cancelLabel,
                    color: authConfig.color,
                    imageColor: authConfig.imageColor,
                    imageErrorColor: authConfig.imageErrorColor,
                    sensorDescription: authConfig.sensorDescription,
                    sensorErrorDescription: authConfig.sensorErrorDescription,
                    passcodeFallback: authConfig.passcodeFallback,
                    showFallbackButton: authConfig.showFallbackButton,
                    unifiedErrors: authConfig.unifiedErrors
                }
            );

            const result: BiometricAuthResult = {
                success: true,
                biometryType: capabilities.biometryType || undefined,
                timestamp: startTime
            };

            await securityService.logSecurityEvent({
                type: SecurityEventType.BIOMETRIC_AUTH,
                details: {
                    action: 'authentication_success',
                    biometryType: capabilities.biometryType,
                    duration: Date.now() - startTime.getTime()
                },
                severity: 'low'
            });

            return result;
        } catch (error) {
            const result: BiometricAuthResult = {
                success: false,
                error: this.mapAuthError(error),
                timestamp: startTime
            };

            await securityService.logSecurityEvent({
                type: SecurityEventType.BIOMETRIC_AUTH,
                details: {
                    action: 'authentication_failed',
                    error: error.message,
                    errorCode: error.code,
                    duration: Date.now() - startTime.getTime()
                },
                severity: error.code === 'UserCancel' ? 'low' : 'medium'
            });

            return result;
        }
    }

    private mapAuthError(error: any): string {
        // Map TouchID error codes to user-friendly messages
        switch (error.code) {
            case 'LAErrorAuthenticationFailed':
                return 'Authentication failed. Please try again.';
            case 'LAErrorUserCancel':
            case 'UserCancel':
                return 'Authentication was cancelled by user.';
            case 'LAErrorUserFallback':
            case 'UserFallback':
                return 'User chose to use passcode instead.';
            case 'LAErrorSystemCancel':
            case 'SystemCancel':
                return 'Authentication was cancelled by system.';
            case 'LAErrorPasscodeNotSet':
            case 'PasscodeNotSet':
                return 'Passcode is not set on device.';
            case 'LAErrorBiometryNotAvailable':
            case 'BiometryNotAvailable':
                return 'Biometric authentication is not available.';
            case 'LAErrorBiometryNotEnrolled':
            case 'BiometryNotEnrolled':
                return 'No biometric data is enrolled on device.';
            case 'LAErrorBiometryLockout':
            case 'BiometryLockout':
                return 'Biometric authentication is locked. Please use passcode.';
            default:
                return error.message || 'Biometric authentication failed.';
        }
    }

    // Quick authentication check (for app unlock scenarios)
    async quickAuthenticate(): Promise<boolean> {
        try {
            const result = await this.authenticate({
                title: 'Unlock App',
                description: 'Authenticate to access your data',
                passcodeFallback: true
            });
            return result.success;
        } catch (error) {
            return false;
        }
    }

    // Authentication with retry logic
    async authenticateWithRetry(
        maxRetries: number = 3,
        config?: Partial<BiometricConfig>
    ): Promise<BiometricAuthResult> {
        let lastResult: BiometricAuthResult | null = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            const result = await this.authenticate({
                ...config,
                title: attempt > 1 ? `Authentication (Attempt ${attempt}/${maxRetries})` : config?.title
            });

            if (result.success) {
                return result;
            }

            lastResult = result;

            // Don't retry if user cancelled or chose fallback
            if (result.error?.includes('cancelled') || result.error?.includes('fallback')) {
                break;
            }

            // Add delay between retries
            if (attempt < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }

        await securityService.logSecurityEvent({
            type: SecurityEventType.BIOMETRIC_AUTH,
            details: {
                action: 'authentication_max_retries_exceeded',
                attempts: maxRetries,
                lastError: lastResult?.error
            },
            severity: 'medium'
        });

        return lastResult || {
            success: false,
            error: 'Maximum authentication attempts exceeded',
            timestamp: new Date()
        };
    }

    // Check if user has biometrics enrolled
    async isBiometricEnrolled(): Promise<boolean> {
        try {
            await TouchID.isSupported();
            return true;
        } catch (error) {
            // Check specific error codes that indicate no enrollment
            if (error.code === 'LAErrorBiometryNotEnrolled' ||
                error.code === 'BiometryNotEnrolled') {
                return false;
            }
            // For other errors, assume not enrolled
            return false;
        }
    }

    // Get user-friendly biometry type name
    async getBiometryTypeName(): Promise<string> {
        const capabilities = await this.checkBiometricCapabilities();

        if (!capabilities.isAvailable || !capabilities.biometryType) {
            return 'Biometric Authentication';
        }

        switch (capabilities.biometryType) {
            case BiometryType.TOUCH_ID:
                return 'Touch ID';
            case BiometryType.FACE_ID:
                return 'Face ID';
            case BiometryType.FINGERPRINT:
                return 'Fingerprint';
            case BiometryType.FACE:
                return 'Face Recognition';
            case BiometryType.IRIS:
                return 'Iris Recognition';
            default:
                return 'Biometric Authentication';
        }
    }

    // Create authentication config based on biometry type
    async createOptimalConfig(purpose: string): Promise<BiometricConfig> {
        const capabilities = await this.checkBiometricCapabilities();
        const biometryName = await this.getBiometryTypeName();

        let description: string;
        let sensorDescription: string;

        switch (capabilities.biometryType) {
            case BiometryType.TOUCH_ID:
            case BiometryType.FINGERPRINT:
                description = `Place your finger on the ${biometryName} sensor to ${purpose}`;
                sensorDescription = 'Place your finger on the sensor';
                break;
            case BiometryType.FACE_ID:
            case BiometryType.FACE:
                description = `Look at the camera to ${purpose} with ${biometryName}`;
                sensorDescription = 'Position your face in front of the camera';
                break;
            case BiometryType.IRIS:
                description = `Look at the camera to ${purpose} with ${biometryName}`;
                sensorDescription = 'Position your eyes in front of the camera';
                break;
            default:
                description = `Use ${biometryName} to ${purpose}`;
                sensorDescription = 'Follow the on-screen instructions';
        }

        return {
            title: `${biometryName} Authentication`,
            subtitle: purpose,
            description,
            sensorDescription,
            sensorErrorDescription: `${biometryName} authentication failed`,
            fallbackLabel: 'Use Passcode',
            cancelLabel: 'Cancel',
            passcodeFallback: true,
            showFallbackButton: true,
            unifiedErrors: false
        };
    }

    // Secure operation with biometric authentication
    async secureOperation<T>(
        operation: () => Promise<T>,
        purpose: string = 'perform this action'
    ): Promise<T> {
        const config = await this.createOptimalConfig(purpose);
        const authResult = await this.authenticate(config);

        if (!authResult.success) {
            throw new Error(authResult.error || 'Authentication required');
        }

        try {
            const result = await operation();

            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: {
                    action: 'secure_operation_completed',
                    purpose,
                    biometryType: authResult.biometryType
                },
                severity: 'low'
            });

            return result;
        } catch (error) {
            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: {
                    action: 'secure_operation_failed',
                    purpose,
                    error: error.message
                },
                severity: 'medium'
            });
            throw error;
        }
    }
}

export const biometricService = new BiometricService();