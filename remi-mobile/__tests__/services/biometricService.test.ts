import TouchID from 'react-native-touch-id';
import { Platform } from 'react-native';
import { biometricService, BiometryType } from '../../src/services/biometricService';
import { securityService } from '../../src/services/securityService';

// Mock dependencies
jest.mock('react-native-touch-id');
jest.mock('react-native', () => ({
    Platform: {
        OS: 'ios'
    }
}));
jest.mock('../../src/services/securityService');

const mockTouchID = TouchID as jest.Mocked<typeof TouchID>;
const mockSecurityService = securityService as jest.Mocked<typeof securityService>;

describe('BiometricService', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockSecurityService.logSecurityEvent.mockResolvedValue();
    });

    describe('Biometric Capabilities', () => {
        it('should detect TouchID availability', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            const capabilities = await biometricService.checkBiometricCapabilities();

            expect(capabilities.isAvailable).toBe(true);
            expect(capabilities.biometryType).toBe(BiometryType.TOUCH_ID);
            expect(capabilities.error).toBeUndefined();
        });

        it('should detect FaceID availability', async () => {
            mockTouchID.isSupported.mockResolvedValue('FaceID');

            const capabilities = await biometricService.checkBiometricCapabilities();

            expect(capabilities.isAvailable).toBe(true);
            expect(capabilities.biometryType).toBe(BiometryType.FACE_ID);
        });

        it('should detect Fingerprint availability on Android', async () => {
            (Platform as any).OS = 'android';
            mockTouchID.isSupported.mockResolvedValue('Fingerprint');

            const capabilities = await biometricService.checkBiometricCapabilities();

            expect(capabilities.isAvailable).toBe(true);
            expect(capabilities.biometryType).toBe(BiometryType.FINGERPRINT);
        });

        it('should handle biometric not available', async () => {
            mockTouchID.isSupported.mockRejectedValue(new Error('Biometry not available'));

            const capabilities = await biometricService.checkBiometricCapabilities();

            expect(capabilities.isAvailable).toBe(false);
            expect(capabilities.biometryType).toBeNull();
            expect(capabilities.error).toBe('Biometry not available');
        });

        it('should log capability check events', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            await biometricService.checkBiometricCapabilities();

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'capability_check',
                    biometryType: 'TouchID',
                    platform: 'ios'
                },
                severity: 'low'
            });
        });
    });

    describe('Authentication', () => {
        beforeEach(() => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');
        });

        it('should authenticate successfully', async () => {
            mockTouchID.authenticate.mockResolvedValue(true);

            const result = await biometricService.authenticate();

            expect(result.success).toBe(true);
            expect(result.biometryType).toBe(BiometryType.TOUCH_ID);
            expect(result.error).toBeUndefined();
        });

        it('should handle authentication failure', async () => {
            const authError = new Error('Authentication failed');
            (authError as any).code = 'LAErrorAuthenticationFailed';
            mockTouchID.authenticate.mockRejectedValue(authError);

            const result = await biometricService.authenticate();

            expect(result.success).toBe(false);
            expect(result.error).toBe('Authentication failed. Please try again.');
        });

        it('should handle user cancellation', async () => {
            const cancelError = new Error('User cancelled');
            (cancelError as any).code = 'UserCancel';
            mockTouchID.authenticate.mockRejectedValue(cancelError);

            const result = await biometricService.authenticate();

            expect(result.success).toBe(false);
            expect(result.error).toBe('Authentication was cancelled by user.');
        });

        it('should handle biometry not enrolled', async () => {
            const notEnrolledError = new Error('Biometry not enrolled');
            (notEnrolledError as any).code = 'BiometryNotEnrolled';
            mockTouchID.authenticate.mockRejectedValue(notEnrolledError);

            const result = await biometricService.authenticate();

            expect(result.success).toBe(false);
            expect(result.error).toBe('No biometric data is enrolled on device.');
        });

        it('should handle biometry lockout', async () => {
            const lockoutError = new Error('Biometry locked out');
            (lockoutError as any).code = 'BiometryLockout';
            mockTouchID.authenticate.mockRejectedValue(lockoutError);

            const result = await biometricService.authenticate();

            expect(result.success).toBe(false);
            expect(result.error).toBe('Biometric authentication is locked. Please use passcode.');
        });

        it('should use custom authentication config', async () => {
            mockTouchID.authenticate.mockResolvedValue(true);

            const customConfig = {
                title: 'Custom Auth',
                description: 'Custom description',
                fallbackLabel: 'Use PIN'
            };

            await biometricService.authenticate(customConfig);

            expect(mockTouchID.authenticate).toHaveBeenCalledWith(
                'Custom description',
                expect.objectContaining({
                    title: 'Custom Auth',
                    fallbackLabel: 'Use PIN'
                })
            );
        });

        it('should log successful authentication', async () => {
            mockTouchID.authenticate.mockResolvedValue(true);

            await biometricService.authenticate();

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'authentication_success',
                    biometryType: BiometryType.TOUCH_ID,
                    duration: expect.any(Number)
                },
                severity: 'low'
            });
        });

        it('should log failed authentication', async () => {
            const authError = new Error('Auth failed');
            (authError as any).code = 'LAErrorAuthenticationFailed';
            mockTouchID.authenticate.mockRejectedValue(authError);

            await biometricService.authenticate();

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'authentication_failed',
                    error: 'Auth failed',
                    errorCode: 'LAErrorAuthenticationFailed',
                    duration: expect.any(Number)
                },
                severity: 'medium'
            });
        });

        it('should log user cancellation with low severity', async () => {
            const cancelError = new Error('User cancelled');
            (cancelError as any).code = 'UserCancel';
            mockTouchID.authenticate.mockRejectedValue(cancelError);

            await biometricService.authenticate();

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: expect.objectContaining({
                    action: 'authentication_failed'
                }),
                severity: 'low'
            });
        });
    });

    describe('Quick Authentication', () => {
        it('should perform quick authentication successfully', async () => {
            mockTouchID.isSupported.mockResolvedValue('FaceID');
            mockTouchID.authenticate.mockResolvedValue(true);

            const result = await biometricService.quickAuthenticate();

            expect(result).toBe(true);
            expect(mockTouchID.authenticate).toHaveBeenCalledWith(
                'Authenticate to access your data',
                expect.objectContaining({
                    title: 'Unlock App',
                    passcodeFallback: true
                })
            );
        });

        it('should return false on authentication failure', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');
            mockTouchID.authenticate.mockRejectedValue(new Error('Failed'));

            const result = await biometricService.quickAuthenticate();

            expect(result).toBe(false);
        });
    });

    describe('Authentication with Retry', () => {
        beforeEach(() => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');
        });

        it('should succeed on first attempt', async () => {
            mockTouchID.authenticate.mockResolvedValue(true);

            const result = await biometricService.authenticateWithRetry(3);

            expect(result.success).toBe(true);
            expect(mockTouchID.authenticate).toHaveBeenCalledTimes(1);
        });

        it('should retry on authentication failure', async () => {
            mockTouchID.authenticate
                .mockRejectedValueOnce(new Error('Failed'))
                .mockResolvedValueOnce(true);

            const result = await biometricService.authenticateWithRetry(3);

            expect(result.success).toBe(true);
            expect(mockTouchID.authenticate).toHaveBeenCalledTimes(2);
        });

        it('should not retry on user cancellation', async () => {
            const cancelError = new Error('User cancelled');
            (cancelError as any).code = 'UserCancel';
            mockTouchID.authenticate.mockRejectedValue(cancelError);

            const result = await biometricService.authenticateWithRetry(3);

            expect(result.success).toBe(false);
            expect(mockTouchID.authenticate).toHaveBeenCalledTimes(1);
        });

        it('should stop after max retries', async () => {
            mockTouchID.authenticate.mockRejectedValue(new Error('Failed'));

            const result = await biometricService.authenticateWithRetry(2);

            expect(result.success).toBe(false);
            expect(mockTouchID.authenticate).toHaveBeenCalledTimes(2);
        });

        it('should log max retries exceeded', async () => {
            mockTouchID.authenticate.mockRejectedValue(new Error('Failed'));

            await biometricService.authenticateWithRetry(2);

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'authentication_max_retries_exceeded',
                    attempts: 2,
                    lastError: expect.any(String)
                },
                severity: 'medium'
            });
        });

        it('should update title with attempt number', async () => {
            mockTouchID.authenticate
                .mockRejectedValueOnce(new Error('Failed'))
                .mockResolvedValueOnce(true);

            await biometricService.authenticateWithRetry(3, { title: 'Custom Title' });

            expect(mockTouchID.authenticate).toHaveBeenNthCalledWith(
                2,
                expect.any(String),
                expect.objectContaining({
                    title: 'Authentication (Attempt 2/3)'
                })
            );
        });
    });

    describe('Biometric Enrollment Check', () => {
        it('should return true when biometrics are enrolled', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            const isEnrolled = await biometricService.isBiometricEnrolled();

            expect(isEnrolled).toBe(true);
        });

        it('should return false when not enrolled', async () => {
            const notEnrolledError = new Error('Not enrolled');
            (notEnrolledError as any).code = 'LAErrorBiometryNotEnrolled';
            mockTouchID.isSupported.mockRejectedValue(notEnrolledError);

            const isEnrolled = await biometricService.isBiometricEnrolled();

            expect(isEnrolled).toBe(false);
        });

        it('should return false for other errors', async () => {
            mockTouchID.isSupported.mockRejectedValue(new Error('Other error'));

            const isEnrolled = await biometricService.isBiometricEnrolled();

            expect(isEnrolled).toBe(false);
        });
    });

    describe('Biometry Type Names', () => {
        it('should return correct name for TouchID', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            const name = await biometricService.getBiometryTypeName();

            expect(name).toBe('Touch ID');
        });

        it('should return correct name for FaceID', async () => {
            mockTouchID.isSupported.mockResolvedValue('FaceID');

            const name = await biometricService.getBiometryTypeName();

            expect(name).toBe('Face ID');
        });

        it('should return correct name for Fingerprint', async () => {
            mockTouchID.isSupported.mockResolvedValue('Fingerprint');

            const name = await biometricService.getBiometryTypeName();

            expect(name).toBe('Fingerprint');
        });

        it('should return default name when not available', async () => {
            mockTouchID.isSupported.mockRejectedValue(new Error('Not available'));

            const name = await biometricService.getBiometryTypeName();

            expect(name).toBe('Biometric Authentication');
        });
    });

    describe('Optimal Configuration', () => {
        it('should create TouchID specific config', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            const config = await biometricService.createOptimalConfig('unlock the app');

            expect(config.title).toBe('Touch ID Authentication');
            expect(config.subtitle).toBe('unlock the app');
            expect(config.description).toContain('Place your finger');
            expect(config.sensorDescription).toBe('Place your finger on the sensor');
        });

        it('should create FaceID specific config', async () => {
            mockTouchID.isSupported.mockResolvedValue('FaceID');

            const config = await biometricService.createOptimalConfig('authenticate');

            expect(config.title).toBe('Face ID Authentication');
            expect(config.description).toContain('Look at the camera');
            expect(config.sensorDescription).toBe('Position your face in front of the camera');
        });

        it('should create generic config for unknown types', async () => {
            mockTouchID.isSupported.mockResolvedValue('Unknown');

            const config = await biometricService.createOptimalConfig('verify identity');

            expect(config.title).toBe('Biometric Authentication Authentication');
            expect(config.description).toContain('Use Biometric Authentication');
            expect(config.sensorDescription).toBe('Follow the on-screen instructions');
        });
    });

    describe('Secure Operations', () => {
        beforeEach(() => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');
            mockTouchID.authenticate.mockResolvedValue(true);
        });

        it('should execute operation after successful authentication', async () => {
            const mockOperation = jest.fn().mockResolvedValue('operation result');

            const result = await biometricService.secureOperation(mockOperation, 'test operation');

            expect(mockOperation).toHaveBeenCalled();
            expect(result).toBe('operation result');
        });

        it('should not execute operation if authentication fails', async () => {
            mockTouchID.authenticate.mockRejectedValue(new Error('Auth failed'));
            const mockOperation = jest.fn();

            await expect(biometricService.secureOperation(mockOperation, 'test operation'))
                .rejects.toThrow('Authentication required');

            expect(mockOperation).not.toHaveBeenCalled();
        });

        it('should log successful secure operation', async () => {
            const mockOperation = jest.fn().mockResolvedValue('result');

            await biometricService.secureOperation(mockOperation, 'sensitive action');

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'secure_operation_completed',
                    purpose: 'sensitive action',
                    biometryType: BiometryType.TOUCH_ID
                },
                severity: 'low'
            });
        });

        it('should log failed secure operation', async () => {
            const mockOperation = jest.fn().mockRejectedValue(new Error('Operation failed'));

            await expect(biometricService.secureOperation(mockOperation, 'test'))
                .rejects.toThrow('Operation failed');

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'secure_operation_failed',
                    purpose: 'test',
                    error: 'Operation failed'
                },
                severity: 'medium'
            });
        });
    });

    describe('Error Mapping', () => {
        const testCases = [
            {
                code: 'LAErrorAuthenticationFailed',
                expected: 'Authentication failed. Please try again.'
            },
            {
                code: 'LAErrorUserCancel',
                expected: 'Authentication was cancelled by user.'
            },
            {
                code: 'LAErrorPasscodeNotSet',
                expected: 'Passcode is not set on device.'
            },
            {
                code: 'LAErrorBiometryNotAvailable',
                expected: 'Biometric authentication is not available.'
            },
            {
                code: 'LAErrorBiometryLockout',
                expected: 'Biometric authentication is locked. Please use passcode.'
            }
        ];

        testCases.forEach(({ code, expected }) => {
            it(`should map ${code} to user-friendly message`, async () => {
                mockTouchID.isSupported.mockResolvedValue('TouchID');

                const error = new Error('System error');
                (error as any).code = code;
                mockTouchID.authenticate.mockRejectedValue(error);

                const result = await biometricService.authenticate();

                expect(result.error).toBe(expected);
            });
        });

        it('should use error message for unknown codes', async () => {
            mockTouchID.isSupported.mockResolvedValue('TouchID');

            const error = new Error('Custom error message');
            (error as any).code = 'UnknownError';
            mockTouchID.authenticate.mockRejectedValue(error);

            const result = await biometricService.authenticate();

            expect(result.error).toBe('Custom error message');
        });
    });
});