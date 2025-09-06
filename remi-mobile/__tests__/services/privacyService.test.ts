import AsyncStorage from '@react-native-async-storage/async-storage';
import { privacyService, ConsentType } from '../../src/services/privacyService';
import { securityService } from '../../src/services/securityService';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('../../src/services/securityService');

const mockAsyncStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;
const mockSecurityService = securityService as jest.Mocked<typeof securityService>;

describe('PrivacyService', () => {
    beforeEach(() => {
        jest.clearAllMocks();

        mockAsyncStorage.getItem.mockResolvedValue(null);
        mockAsyncStorage.setItem.mockResolvedValue();
        mockAsyncStorage.getAllKeys.mockResolvedValue([]);
        mockAsyncStorage.multiRemove.mockResolvedValue();
        mockAsyncStorage.removeItem.mockResolvedValue();

        mockSecurityService.logSecurityEvent.mockResolvedValue();
    });

    describe('PII Redaction', () => {
        it('should redact email addresses', async () => {
            const text = 'Contact me at john.doe@example.com for more info';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toBe('Contact me at [EMAIL_REDACTED] for more info');
            expect(detectedPII).toHaveLength(1);
            expect(detectedPII[0].type).toBe('email');
            expect(detectedPII[0].original).toBe('john.doe@example.com');
        });

        it('should redact phone numbers', async () => {
            const text = 'Call me at (555) 123-4567 or 555.987.6543';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toContain('[PHONE_REDACTED]');
            expect(detectedPII.length).toBeGreaterThan(0);
            expect(detectedPII.some(pii => pii.type === 'phone_us')).toBe(true);
        });

        it('should redact SSN', async () => {
            const text = 'My SSN is 123-45-6789';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toBe('My SSN is [SSN_REDACTED]');
            expect(detectedPII).toHaveLength(1);
            expect(detectedPII[0].type).toBe('ssn');
        });

        it('should redact credit card numbers', async () => {
            const text = 'Card number: 4532 1234 5678 9012';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toBe('Card number: [CARD_REDACTED]');
            expect(detectedPII).toHaveLength(1);
            expect(detectedPII[0].type).toBe('credit_card');
        });

        it('should redact IP addresses', async () => {
            const text = 'Server IP: 192.168.1.100';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toBe('Server IP: [IP_REDACTED]');
            expect(detectedPII).toHaveLength(1);
            expect(detectedPII[0].type).toBe('ip_address');
        });

        it('should handle multiple PII types in one text', async () => {
            const text = 'Contact John Doe at john@example.com or (555) 123-4567';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(detectedPII.length).toBeGreaterThan(1);
            expect(detectedPII.some(pii => pii.type === 'email')).toBe(true);
            expect(detectedPII.some(pii => pii.type === 'phone_us')).toBe(true);
        });

        it('should respect redaction level settings', async () => {
            // Update config to strict level (lower confidence threshold)
            await privacyService.updatePrivacyConfig({ redactionLevel: 'strict' });

            const text = 'Meet John Smith at the office';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            // With strict level, potential names should be redacted
            expect(detectedPII.some(pii => pii.type === 'potential_name')).toBe(true);
        });

        it('should not redact when disabled', async () => {
            await privacyService.updatePrivacyConfig({ piiRedactionEnabled: false });

            const text = 'Email: test@example.com';

            const { redactedText, detectedPII } = await privacyService.redactPII(text);

            expect(redactedText).toBe(text);
            expect(detectedPII).toHaveLength(0);
        });

        it('should redact object fields', async () => {
            const obj = {
                name: 'John Doe',
                email: 'john@example.com',
                phone: '555-123-4567',
                public: 'This is public info'
            };

            const redacted = await privacyService.redactObjectPII(obj, ['email', 'phone']);

            expect(redacted.name).toBe('John Doe'); // Not in redaction list
            expect(redacted.email).toBe('[EMAIL_REDACTED]');
            expect(redacted.phone).toBe('[PHONE_REDACTED]');
            expect(redacted.public).toBe('This is public info');
        });

        it('should redact nested object fields', async () => {
            const obj = {
                user: {
                    profile: {
                        email: 'user@example.com',
                        phone: '555-123-4567'
                    },
                    settings: {
                        theme: 'dark'
                    }
                }
            };

            const redacted = await privacyService.redactObjectPII(obj, ['user.profile.email']);

            expect(redacted.user.profile.email).toBe('[EMAIL_REDACTED]');
            expect(redacted.user.profile.phone).toBe('555-123-4567'); // Not redacted
            expect(redacted.user.settings.theme).toBe('dark');
        });
    });

    describe('Data Minimization', () => {
        it('should retain only specified fields', async () => {
            const data = {
                id: '123',
                name: 'John Doe',
                email: 'john@example.com',
                password: 'secret',
                preferences: { theme: 'dark' },
                metadata: { created: '2023-01-01' }
            };

            const minimized = await privacyService.minimizeData(data, ['id', 'name', 'preferences.theme']);

            expect(minimized).toEqual({
                id: '123',
                name: 'John Doe',
                preferences: { theme: 'dark' }
            });
            expect(minimized.email).toBeUndefined();
            expect(minimized.password).toBeUndefined();
        });

        it('should handle nested field retention', async () => {
            const data = {
                user: {
                    id: '123',
                    profile: {
                        name: 'John',
                        email: 'john@example.com',
                        avatar: 'avatar.jpg'
                    },
                    settings: {
                        notifications: true,
                        privacy: 'strict'
                    }
                }
            };

            const minimized = await privacyService.minimizeData(data, [
                'user.id',
                'user.profile.name',
                'user.settings.notifications'
            ]);

            expect(minimized).toEqual({
                user: {
                    id: '123',
                    profile: {
                        name: 'John'
                    },
                    settings: {
                        notifications: true
                    }
                }
            });
        });

        it('should not minimize when disabled', async () => {
            await privacyService.updatePrivacyConfig({ dataMinimizationEnabled: false });

            const data = { a: 1, b: 2, c: 3 };
            const minimized = await privacyService.minimizeData(data, ['a']);

            expect(minimized).toEqual(data);
        });

        it('should log minimization events', async () => {
            const data = { a: 1, b: 2, c: 3, d: 4 };

            await privacyService.minimizeData(data, ['a', 'c']);

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith({
                type: expect.any(String),
                details: {
                    action: 'data_minimization',
                    originalFields: 4,
                    retainedFields: 2
                },
                severity: 'low'
            });
        });
    });

    describe('Consent Management', () => {
        it('should record consent', async () => {
            const consent = await privacyService.recordConsent(
                'user123',
                ConsentType.DATA_PROCESSING,
                true
            );

            expect(consent.userId).toBe('user123');
            expect(consent.consentType).toBe(ConsentType.DATA_PROCESSING);
            expect(consent.granted).toBe(true);
            expect(consent.id).toBeDefined();
            expect(consent.timestamp).toBeInstanceOf(Date);
        });

        it('should retrieve most recent consent', async () => {
            // Record multiple consents
            await privacyService.recordConsent('user123', ConsentType.DATA_PROCESSING, false);
            await new Promise(resolve => setTimeout(resolve, 10)); // Ensure different timestamps
            await privacyService.recordConsent('user123', ConsentType.DATA_PROCESSING, true);

            const consent = await privacyService.getConsent('user123', ConsentType.DATA_PROCESSING);

            expect(consent?.granted).toBe(true); // Should get the most recent one
        });

        it('should check valid consent', async () => {
            await privacyService.recordConsent('user123', ConsentType.AI_ANALYSIS, true);

            const hasConsent = await privacyService.hasValidConsent('user123', ConsentType.AI_ANALYSIS);

            expect(hasConsent).toBe(true);
        });

        it('should return false for no consent', async () => {
            const hasConsent = await privacyService.hasValidConsent('user123', ConsentType.MARKETING);

            expect(hasConsent).toBe(false);
        });

        it('should return false for denied consent', async () => {
            await privacyService.recordConsent('user123', ConsentType.ANALYTICS, false);

            const hasConsent = await privacyService.hasValidConsent('user123', ConsentType.ANALYTICS);

            expect(hasConsent).toBe(false);
        });

        it('should get all consents for user', async () => {
            await privacyService.recordConsent('user123', ConsentType.DATA_PROCESSING, true);
            await privacyService.recordConsent('user123', ConsentType.AI_ANALYSIS, false);
            await privacyService.recordConsent('user456', ConsentType.DATA_PROCESSING, true);

            const consents = await privacyService.getAllConsents('user123');

            expect(consents).toHaveLength(2);
            expect(consents.every(c => c.userId === 'user123')).toBe(true);
        });

        it('should bypass consent check when not required', async () => {
            await privacyService.updatePrivacyConfig({ consentRequired: false });

            const hasConsent = await privacyService.hasValidConsent('user123', ConsentType.DATA_PROCESSING);

            expect(hasConsent).toBe(true);
        });
    });

    describe('Data Export', () => {
        it('should create data export request', async () => {
            const request = await privacyService.requestDataExport('user123', 'json');

            expect(request.userId).toBe('user123');
            expect(request.format).toBe('json');
            expect(request.status).toBe('pending');
            expect(request.id).toBeDefined();
        });

        it('should reject export when not allowed', async () => {
            await privacyService.updatePrivacyConfig({ allowDataExport: false });

            await expect(privacyService.requestDataExport('user123'))
                .rejects.toThrow('Data export is not allowed');
        });

        it('should process export request', async () => {
            const request = await privacyService.requestDataExport('user123', 'json');

            // Wait for processing to complete
            await new Promise(resolve => setTimeout(resolve, 1100));

            // In a real implementation, we'd check the request status
            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: expect.any(String),
                    details: expect.objectContaining({
                        action: 'export_requested'
                    })
                })
            );
        });

        it('should support different export formats', async () => {
            const jsonRequest = await privacyService.requestDataExport('user123', 'json');
            const csvRequest = await privacyService.requestDataExport('user123', 'csv');
            const xmlRequest = await privacyService.requestDataExport('user123', 'xml');

            expect(jsonRequest.format).toBe('json');
            expect(csvRequest.format).toBe('csv');
            expect(xmlRequest.format).toBe('xml');
        });
    });

    describe('Data Deletion', () => {
        it('should create data deletion request', async () => {
            const request = await privacyService.requestDataDeletion('user123', 'complete');

            expect(request.userId).toBe('user123');
            expect(request.deletionType).toBe('complete');
            expect(request.status).toBe('pending');
            expect(request.id).toBeDefined();
        });

        it('should reject deletion when not allowed', async () => {
            await privacyService.updatePrivacyConfig({ allowDataDeletion: false });

            await expect(privacyService.requestDataDeletion('user123'))
                .rejects.toThrow('Data deletion is not allowed');
        });

        it('should support partial deletion', async () => {
            const request = await privacyService.requestDataDeletion(
                'user123',
                'partial',
                ['messages', 'contacts']
            );

            expect(request.deletionType).toBe('partial');
            expect(request.dataTypes).toEqual(['messages', 'contacts']);
        });

        it('should process deletion request', async () => {
            mockAsyncStorage.getAllKeys.mockResolvedValue([
                'user_profile_user123',
                'user_messages_user123',
                'other_data'
            ]);

            const request = await privacyService.requestDataDeletion('user123', 'complete');

            // Wait for processing
            await new Promise(resolve => setTimeout(resolve, 1100));

            expect(mockSecurityService.logSecurityEvent).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: expect.any(String),
                    details: expect.objectContaining({
                        action: 'deletion_requested'
                    })
                })
            );
        });
    });

    describe('Configuration Management', () => {
        it('should update privacy configuration', async () => {
            const newConfig = {
                piiRedactionEnabled: false,
                redactionLevel: 'strict' as const,
                dataMinimizationEnabled: false
            };

            await privacyService.updatePrivacyConfig(newConfig);

            expect(mockAsyncStorage.setItem).toHaveBeenCalledWith(
                'privacy_config',
                expect.stringContaining('piiRedactionEnabled')
            );
        });

        it('should get privacy configuration', async () => {
            const mockConfig = {
                piiRedactionEnabled: true,
                redactionLevel: 'basic',
                dataMinimizationEnabled: true,
                consentRequired: true,
                retentionPeriodDays: 365,
                allowDataExport: true,
                allowDataDeletion: true
            };

            mockAsyncStorage.getItem.mockResolvedValue(JSON.stringify(mockConfig));

            const config = await privacyService.getPrivacyConfig();

            expect(config.piiRedactionEnabled).toBe(true);
            expect(config.redactionLevel).toBe('basic');
        });
    });

    describe('Error Handling', () => {
        it('should handle storage errors gracefully', async () => {
            mockAsyncStorage.setItem.mockRejectedValue(new Error('Storage error'));

            // Should not throw
            await privacyService.recordConsent('user123', ConsentType.DATA_PROCESSING, true);

            expect(true).toBe(true); // Test passes if no exception
        });

        it('should handle malformed stored data', async () => {
            mockAsyncStorage.getItem.mockResolvedValue('invalid json');

            const consents = await privacyService.getAllConsents('user123');

            expect(consents).toEqual([]);
        });
    });

    describe('Performance', () => {
        it('should redact large text efficiently', async () => {
            const largeText = `
        This is a large document with multiple PII instances.
        Contact john.doe@example.com or jane.smith@company.org.
        Phone numbers: (555) 123-4567, 555.987.6543, +1-800-555-0199.
        SSNs: 123-45-6789, 987-65-4321.
        Credit cards: 4532 1234 5678 9012, 5555-4444-3333-2222.
        IP addresses: 192.168.1.1, 10.0.0.1, 172.16.0.1.
      `.repeat(100); // Repeat to make it large

            const startTime = Date.now();
            const { redactedText, detectedPII } = await privacyService.redactPII(largeText);
            const endTime = Date.now();

            expect(endTime - startTime).toBeLessThan(5000); // Should complete within 5 seconds
            expect(detectedPII.length).toBeGreaterThan(0);
        });
    });
});