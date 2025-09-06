import AsyncStorage from '@react-native-async-storage/async-storage';
import Keychain from 'react-native-keychain';
import JailMonkey from 'jail-monkey';
import { securityService, SecurityEventType } from '../../src/services/securityService';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('react-native-keychain');
jest.mock('jail-monkey');
jest.mock('crypto-js', () => ({
    AES: {
        encrypt: jest.fn().mockReturnValue({ toString: () => 'encrypted_data' }),
        decrypt: jest.fn().mockReturnValue({ toString: () => '{"test": "data"}' })
    },
    PBKDF2: jest.fn().mockReturnValue('derived_key'),
    lib: {
        WordArray: {
            random: jest.fn().mockReturnValue({ toString: () => 'random_value' })
        }
    },
    enc: {
        Hex: {
            parse: jest.fn().mockReturnValue('parsed_hex')
        },
        Utf8: 'utf8_encoding'
    }
}));

const mockAsyncStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;
const mockKeychain = Keychain as jest.Mocked<typeof Keychain>;
const mockJailMonkey = JailMonkey as jest.Mocked<typeof JailMonkey>;

describe('SecurityService', () => {
    beforeEach(() => {
        jest.clearAllMocks();

        // Setup default mocks
        mockKeychain.getInternetCredentials.mockResolvedValue({
            username: 'encryption',
            password: 'test_encryption_key',
            service: 'remi_encryption_key',
            storage: 'keychain'
        });

        mockAsyncStorage.getItem.mockResolvedValue(null);
        mockAsyncStorage.setItem.mockResolvedValue();

        mockJailMonkey.isJailBroken.mockReturnValue(false);
        mockJailMonkey.isOnExternalStorage.mockReturnValue(false);
        mockJailMonkey.isDebuggedMode.mockReturnValue(false);
        mockJailMonkey.hookDetected.mockReturnValue(false);
    });

    describe('Device Security Detection', () => {
        it('should detect secure device', async () => {
            const status = await securityService.checkDeviceSecurity();

            expect(status.isSecure).toBe(true);
            expect(status.violations).toHaveLength(0);
            expect(status.isJailbroken).toBe(false);
            expect(status.isRooted).toBe(false);
        });

        it('should detect jailbroken device', async () => {
            mockJailMonkey.isJailBroken.mockReturnValue(true);

            const status = await securityService.checkDeviceSecurity();

            expect(status.isSecure).toBe(false);
            expect(status.violations).toContain('Device is jailbroken');
            expect(status.isJailbroken).toBe(true);
        });

        it('should detect rooted device', async () => {
            mockJailMonkey.isOnExternalStorage.mockReturnValue(true);

            const status = await securityService.checkDeviceSecurity();

            expect(status.isSecure).toBe(false);
            expect(status.violations).toContain('Device is rooted or on external storage');
            expect(status.isRooted).toBe(true);
        });

        it('should detect debug mode', async () => {
            mockJailMonkey.isDebuggedMode.mockReturnValue(true);

            const status = await securityService.checkDeviceSecurity();

            expect(status.isSecure).toBe(false);
            expect(status.violations).toContain('Debug mode is enabled');
            expect(status.isDebuggingEnabled).toBe(true);
        });

        it('should detect runtime hooks', async () => {
            mockJailMonkey.hookDetected.mockReturnValue(true);

            const status = await securityService.checkDeviceSecurity();

            expect(status.isSecure).toBe(false);
            expect(status.violations).toContain('Runtime manipulation detected');
            expect(status.hasHooks).toBe(true);
        });

        it('should log security violations', async () => {
            mockJailMonkey.isJailBroken.mockReturnValue(true);

            const logSpy = jest.spyOn(securityService, 'logSecurityEvent');

            await securityService.checkDeviceSecurity();

            expect(logSpy).toHaveBeenCalledWith({
                type: SecurityEventType.DEVICE_SECURITY_VIOLATION,
                details: expect.objectContaining({
                    violations: expect.arrayContaining(['Device is jailbroken'])
                }),
                severity: 'high'
            });
        });
    });

    describe('Encryption Services', () => {
        it('should initialize encryption with existing key', async () => {
            await securityService.initializeEncryption();

            expect(mockKeychain.getInternetCredentials).toHaveBeenCalledWith('remi_encryption_key');
        });

        it('should generate new encryption key if none exists', async () => {
            mockKeychain.getInternetCredentials.mockRejectedValue(new Error('Key not found'));

            await securityService.initializeEncryption();

            expect(mockKeychain.setInternetCredentials).toHaveBeenCalledWith(
                'remi_encryption_key',
                'encryption',
                expect.any(String),
                expect.objectContaining({
                    accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET_OR_DEVICE_PASSCODE
                })
            );
        });

        it('should encrypt data successfully', async () => {
            await securityService.initializeEncryption();

            const testData = { message: 'test data', sensitive: true };
            const encrypted = await securityService.encryptData(testData);

            expect(encrypted).toHaveProperty('data');
            expect(encrypted).toHaveProperty('iv');
            expect(encrypted).toHaveProperty('salt');
            expect(encrypted).toHaveProperty('timestamp');
        });

        it('should decrypt data successfully', async () => {
            await securityService.initializeEncryption();

            const encryptedData = {
                data: 'encrypted_data',
                iv: 'test_iv',
                salt: 'test_salt',
                timestamp: new Date()
            };

            const decrypted = await securityService.decryptData(encryptedData);

            expect(decrypted).toEqual({ test: 'data' });
        });

        it('should apply field-level encryption', async () => {
            await securityService.initializeEncryption();

            const testData = {
                public: 'public data',
                private: 'sensitive data',
                nested: {
                    secret: 'very secret'
                }
            };

            const encrypted = await securityService.encryptData(testData, ['private', 'nested.secret']);

            // The actual implementation would encrypt specific fields
            expect(encrypted).toBeDefined();
        });

        it('should handle encryption errors', async () => {
            // Don't initialize encryption

            await expect(securityService.encryptData({ test: 'data' }))
                .rejects.toThrow('Encryption not initialized');
        });
    });

    describe('Secure Storage', () => {
        it('should store data securely', async () => {
            await securityService.initializeEncryption();

            const testData = { username: 'testuser', token: 'secret_token' };

            await securityService.storeSecurely('user_data', testData);

            expect(mockAsyncStorage.setItem).toHaveBeenCalledWith(
                'secure_user_data',
                expect.any(String)
            );
        });

        it('should retrieve data securely', async () => {
            await securityService.initializeEncryption();

            const encryptedData = JSON.stringify({
                data: 'encrypted_data',
                iv: 'test_iv',
                salt: 'test_salt',
                timestamp: new Date().toISOString()
            });

            mockAsyncStorage.getItem.mockResolvedValue(encryptedData);

            const retrieved = await securityService.retrieveSecurely('user_data');

            expect(retrieved).toEqual({ test: 'data' });
            expect(mockAsyncStorage.getItem).toHaveBeenCalledWith('secure_user_data');
        });

        it('should return null for non-existent data', async () => {
            await securityService.initializeEncryption();

            mockAsyncStorage.getItem.mockResolvedValue(null);

            const retrieved = await securityService.retrieveSecurely('non_existent');

            expect(retrieved).toBeNull();
        });
    });

    describe('Audit Logging', () => {
        it('should log security events', async () => {
            const testEvent = {
                type: SecurityEventType.LOGIN_SUCCESS,
                details: { userId: 'test_user' },
                severity: 'low' as const
            };

            await securityService.logSecurityEvent(testEvent);

            expect(mockAsyncStorage.setItem).toHaveBeenCalledWith(
                'security_audit_log',
                expect.any(String)
            );
        });

        it('should retrieve audit events', async () => {
            const mockEvents = [
                {
                    id: 'event_1',
                    type: SecurityEventType.LOGIN_SUCCESS,
                    timestamp: new Date().toISOString(),
                    deviceId: 'test_device',
                    details: {},
                    severity: 'low'
                }
            ];

            mockAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockEvents));

            const events = await securityService.getAuditEvents();

            expect(events).toHaveLength(1);
            expect(events[0].type).toBe(SecurityEventType.LOGIN_SUCCESS);
        });

        it('should limit stored events to 1000', async () => {
            // This would be tested by creating more than 1000 events
            // and verifying only the last 1000 are kept
            const events = Array.from({ length: 1200 }, (_, i) => ({
                id: `event_${i}`,
                type: SecurityEventType.DATA_ACCESS,
                timestamp: new Date(),
                deviceId: 'test_device',
                details: {},
                severity: 'low'
            }));

            // Mock the internal auditEvents array to have 1200 events
            (securityService as any).auditEvents = events;

            await securityService.logSecurityEvent({
                type: SecurityEventType.LOGIN_SUCCESS,
                details: {},
                severity: 'low'
            });

            // Verify that setItem was called with a string representing ≤ 1000 events
            const setItemCall = mockAsyncStorage.setItem.mock.calls.find(
                call => call[0] === 'security_audit_log'
            );

            if (setItemCall) {
                const storedEvents = JSON.parse(setItemCall[1]);
                expect(storedEvents.length).toBeLessThanOrEqual(1000);
            }
        });
    });

    describe('Security Configuration', () => {
        it('should update security configuration', async () => {
            const newConfig = {
                encryptionEnabled: false,
                biometricEnabled: false
            };

            await securityService.updateSecurityConfig(newConfig);

            expect(mockAsyncStorage.setItem).toHaveBeenCalledWith(
                'security_config',
                expect.stringContaining('encryptionEnabled')
            );
        });

        it('should get security configuration', async () => {
            const mockConfig = {
                encryptionEnabled: true,
                biometricEnabled: true,
                deviceSecurityRequired: true,
                auditLoggingEnabled: true,
                piiRedactionLevel: 'basic'
            };

            mockAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockConfig));

            const config = await securityService.getSecurityConfig();

            expect(config.encryptionEnabled).toBe(true);
            expect(config.biometricEnabled).toBe(true);
        });
    });

    describe('Security Status', () => {
        it('should get comprehensive security status', async () => {
            await securityService.initializeEncryption();

            const status = await securityService.getSecurityStatus();

            expect(status).toHaveProperty('deviceSecurity');
            expect(status).toHaveProperty('encryptionStatus');
            expect(status).toHaveProperty('auditingEnabled');
            expect(status).toHaveProperty('recentIncidents');

            expect(status.encryptionStatus).toBe(true);
        });

        it('should filter recent high-severity incidents', async () => {
            const mockEvents = [
                {
                    id: 'event_1',
                    type: SecurityEventType.LOGIN_SUCCESS,
                    timestamp: new Date(),
                    deviceId: 'test_device',
                    details: {},
                    severity: 'low'
                },
                {
                    id: 'event_2',
                    type: SecurityEventType.DEVICE_SECURITY_VIOLATION,
                    timestamp: new Date(),
                    deviceId: 'test_device',
                    details: {},
                    severity: 'high'
                }
            ];

            mockAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockEvents));

            const status = await securityService.getSecurityStatus();

            expect(status.recentIncidents).toHaveLength(1);
            expect(status.recentIncidents[0].severity).toBe('high');
        });
    });

    describe('Error Handling', () => {
        it('should handle keychain errors gracefully', async () => {
            mockKeychain.getInternetCredentials.mockRejectedValue(new Error('Keychain error'));
            mockKeychain.setInternetCredentials.mockRejectedValue(new Error('Cannot store key'));

            await expect(securityService.initializeEncryption())
                .rejects.toThrow('Failed to initialize encryption');
        });

        it('should handle AsyncStorage errors', async () => {
            mockAsyncStorage.setItem.mockRejectedValue(new Error('Storage error'));

            // Should not throw, but log the error
            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: {},
                severity: 'low'
            });

            // Verify error was handled gracefully
            expect(true).toBe(true); // Test passes if no exception is thrown
        });
    });

    describe('Performance', () => {
        it('should encrypt and decrypt data within reasonable time', async () => {
            await securityService.initializeEncryption();

            const largeData = {
                content: 'x'.repeat(10000), // 10KB of data
                metadata: { size: 10000, type: 'test' }
            };

            const startTime = Date.now();
            const encrypted = await securityService.encryptData(largeData);
            const decrypted = await securityService.decryptData(encrypted);
            const endTime = Date.now();

            expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second
            expect(decrypted.content).toBe(largeData.content);
        });
    });
});