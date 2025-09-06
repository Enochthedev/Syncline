import AsyncStorage from '@react-native-async-storage/async-storage';
import Keychain from 'react-native-keychain';
import JailMonkey from 'jail-monkey';
import CryptoJS from 'crypto-js';
import { Platform } from 'react-native';

export interface SecurityConfig {
    encryptionEnabled: boolean;
    biometricEnabled: boolean;
    deviceSecurityRequired: boolean;
    auditLoggingEnabled: boolean;
    piiRedactionLevel: 'none' | 'basic' | 'strict';
}

export interface SecurityEvent {
    id: string;
    type: SecurityEventType;
    timestamp: Date;
    userId?: string;
    deviceId: string;
    details: Record<string, any>;
    severity: 'low' | 'medium' | 'high' | 'critical';
}

export enum SecurityEventType {
    LOGIN_ATTEMPT = 'login_attempt',
    LOGIN_SUCCESS = 'login_success',
    LOGIN_FAILURE = 'login_failure',
    BIOMETRIC_AUTH = 'biometric_auth',
    DEVICE_SECURITY_VIOLATION = 'device_security_violation',
    DATA_ACCESS = 'data_access',
    DATA_EXPORT = 'data_export',
    DATA_DELETION = 'data_deletion',
    ENCRYPTION_ERROR = 'encryption_error',
    JAILBREAK_DETECTED = 'jailbreak_detected',
    ROOT_DETECTED = 'root_detected',
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
}

export interface EncryptedData {
    data: string;
    iv: string;
    salt: string;
    timestamp: Date;
}

export interface DeviceSecurityStatus {
    isJailbroken: boolean;
    isRooted: boolean;
    isDebuggingEnabled: boolean;
    hasHooks: boolean;
    isSecure: boolean;
    violations: string[];
}

class SecurityService {
    private encryptionKey: string | null = null;
    private config: SecurityConfig;
    private auditEvents: SecurityEvent[] = [];

    constructor() {
        this.config = {
            encryptionEnabled: true,
            biometricEnabled: true,
            deviceSecurityRequired: true,
            auditLoggingEnabled: true,
            piiRedactionLevel: 'basic'
        };
    }

    // Device Security Detection
    async checkDeviceSecurity(): Promise<DeviceSecurityStatus> {
        const violations: string[] = [];

        const isJailbroken = JailMonkey.isJailBroken();
        const isRooted = JailMonkey.isOnExternalStorage();
        const isDebuggingEnabled = JailMonkey.isDebuggedMode();
        const hasHooks = JailMonkey.hookDetected();

        if (isJailbroken) violations.push('Device is jailbroken');
        if (isRooted) violations.push('Device is rooted or on external storage');
        if (isDebuggingEnabled) violations.push('Debug mode is enabled');
        if (hasHooks) violations.push('Runtime manipulation detected');

        const status: DeviceSecurityStatus = {
            isJailbroken,
            isRooted,
            isDebuggingEnabled,
            hasHooks,
            isSecure: violations.length === 0,
            violations
        };

        if (!status.isSecure) {
            await this.logSecurityEvent({
                type: SecurityEventType.DEVICE_SECURITY_VIOLATION,
                details: { violations, status },
                severity: 'high'
            });
        }

        return status;
    }

    // Encryption Services
    async initializeEncryption(): Promise<void> {
        try {
            // Try to retrieve existing encryption key from keychain
            const credentials = await Keychain.getInternetCredentials('remi_encryption_key');

            if (credentials && credentials.password) {
                this.encryptionKey = credentials.password;
            } else {
                // Generate new encryption key
                this.encryptionKey = CryptoJS.lib.WordArray.random(256 / 8).toString();

                // Store in keychain with biometric protection if available
                await Keychain.setInternetCredentials(
                    'remi_encryption_key',
                    'encryption',
                    this.encryptionKey,
                    {
                        accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET_OR_DEVICE_PASSCODE,
                        authenticatePrompt: 'Authenticate to access encryption key',
                    }
                );
            }

            await this.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: { action: 'encryption_key_initialized' },
                severity: 'low'
            });
        } catch (error) {
            await this.logSecurityEvent({
                type: SecurityEventType.ENCRYPTION_ERROR,
                details: { error: error.message },
                severity: 'critical'
            });
            throw new Error('Failed to initialize encryption');
        }
    }

    async encryptData(data: any, fieldPaths?: string[]): Promise<EncryptedData> {
        if (!this.config.encryptionEnabled || !this.encryptionKey) {
            throw new Error('Encryption not initialized');
        }

        try {
            let dataToEncrypt = data;

            // Apply field-level encryption if paths specified
            if (fieldPaths && typeof data === 'object') {
                dataToEncrypt = this.applyFieldEncryption(data, fieldPaths);
            }

            const salt = CryptoJS.lib.WordArray.random(128 / 8);
            const iv = CryptoJS.lib.WordArray.random(128 / 8);

            const key = CryptoJS.PBKDF2(this.encryptionKey, salt, {
                keySize: 256 / 32,
                iterations: 10000
            });

            const encrypted = CryptoJS.AES.encrypt(
                JSON.stringify(dataToEncrypt),
                key,
                { iv: iv }
            );

            return {
                data: encrypted.toString(),
                iv: iv.toString(),
                salt: salt.toString(),
                timestamp: new Date()
            };
        } catch (error) {
            await this.logSecurityEvent({
                type: SecurityEventType.ENCRYPTION_ERROR,
                details: { error: error.message, operation: 'encrypt' },
                severity: 'high'
            });
            throw error;
        }
    }

    async decryptData(encryptedData: EncryptedData): Promise<any> {
        if (!this.encryptionKey) {
            throw new Error('Encryption not initialized');
        }

        try {
            const salt = CryptoJS.enc.Hex.parse(encryptedData.salt);
            const iv = CryptoJS.enc.Hex.parse(encryptedData.iv);

            const key = CryptoJS.PBKDF2(this.encryptionKey, salt, {
                keySize: 256 / 32,
                iterations: 10000
            });

            const decrypted = CryptoJS.AES.decrypt(
                encryptedData.data,
                key,
                { iv: iv }
            );

            const decryptedString = decrypted.toString(CryptoJS.enc.Utf8);
            return JSON.parse(decryptedString);
        } catch (error) {
            await this.logSecurityEvent({
                type: SecurityEventType.ENCRYPTION_ERROR,
                details: { error: error.message, operation: 'decrypt' },
                severity: 'high'
            });
            throw error;
        }
    }

    private applyFieldEncryption(data: any, fieldPaths: string[]): any {
        const result = { ...data };

        fieldPaths.forEach(path => {
            const value = this.getNestedValue(result, path);
            if (value !== undefined) {
                this.setNestedValue(result, path, `[ENCRYPTED:${typeof value}]`);
            }
        });

        return result;
    }

    private getNestedValue(obj: any, path: string): any {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }

    private setNestedValue(obj: any, path: string, value: any): void {
        const keys = path.split('.');
        const lastKey = keys.pop()!;
        const target = keys.reduce((current, key) => {
            if (!current[key]) current[key] = {};
            return current[key];
        }, obj);
        target[lastKey] = value;
    }

    // Secure Storage
    async storeSecurely(key: string, value: any): Promise<void> {
        try {
            const encrypted = await this.encryptData(value);
            await AsyncStorage.setItem(`secure_${key}`, JSON.stringify(encrypted));

            await this.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: { action: 'secure_store', key },
                severity: 'low'
            });
        } catch (error) {
            await this.logSecurityEvent({
                type: SecurityEventType.ENCRYPTION_ERROR,
                details: { error: error.message, operation: 'secure_store', key },
                severity: 'high'
            });
            throw error;
        }
    }

    async retrieveSecurely(key: string): Promise<any> {
        try {
            const encryptedString = await AsyncStorage.getItem(`secure_${key}`);
            if (!encryptedString) return null;

            const encrypted: EncryptedData = JSON.parse(encryptedString);
            const decrypted = await this.decryptData(encrypted);

            await this.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: { action: 'secure_retrieve', key },
                severity: 'low'
            });

            return decrypted;
        } catch (error) {
            await this.logSecurityEvent({
                type: SecurityEventType.ENCRYPTION_ERROR,
                details: { error: error.message, operation: 'secure_retrieve', key },
                severity: 'high'
            });
            throw error;
        }
    }

    // Audit Logging
    async logSecurityEvent(event: Partial<SecurityEvent>): Promise<void> {
        if (!this.config.auditLoggingEnabled) return;

        const securityEvent: SecurityEvent = {
            id: `sec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type: event.type!,
            timestamp: new Date(),
            deviceId: await this.getDeviceId(),
            details: event.details || {},
            severity: event.severity || 'low',
            ...event
        };

        this.auditEvents.push(securityEvent);

        // Store audit events securely
        await this.storeAuditEvents();

        // Send critical events to server immediately
        if (securityEvent.severity === 'critical' || securityEvent.severity === 'high') {
            await this.reportSecurityIncident(securityEvent);
        }
    }

    private async storeAuditEvents(): Promise<void> {
        try {
            // Keep only last 1000 events to manage storage
            const eventsToStore = this.auditEvents.slice(-1000);
            await AsyncStorage.setItem('security_audit_log', JSON.stringify(eventsToStore));
        } catch (error) {
            console.error('Failed to store audit events:', error);
        }
    }

    async getAuditEvents(limit?: number): Promise<SecurityEvent[]> {
        try {
            const stored = await AsyncStorage.getItem('security_audit_log');
            const events = stored ? JSON.parse(stored) : [];
            return limit ? events.slice(-limit) : events;
        } catch (error) {
            console.error('Failed to retrieve audit events:', error);
            return [];
        }
    }

    private async reportSecurityIncident(event: SecurityEvent): Promise<void> {
        try {
            // In a real implementation, this would send to your security monitoring service
            console.warn('Security Incident:', event);

            // Store for later transmission if network is unavailable
            const incidents = await AsyncStorage.getItem('pending_security_incidents') || '[]';
            const pendingIncidents = JSON.parse(incidents);
            pendingIncidents.push(event);
            await AsyncStorage.setItem('pending_security_incidents', JSON.stringify(pendingIncidents));
        } catch (error) {
            console.error('Failed to report security incident:', error);
        }
    }

    private async getDeviceId(): Promise<string> {
        try {
            let deviceId = await AsyncStorage.getItem('device_id');
            if (!deviceId) {
                deviceId = `${Platform.OS}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                await AsyncStorage.setItem('device_id', deviceId);
            }
            return deviceId;
        } catch (error) {
            return `${Platform.OS}_unknown`;
        }
    }

    // Configuration Management
    async updateSecurityConfig(newConfig: Partial<SecurityConfig>): Promise<void> {
        this.config = { ...this.config, ...newConfig };
        await AsyncStorage.setItem('security_config', JSON.stringify(this.config));

        await this.logSecurityEvent({
            type: SecurityEventType.DATA_ACCESS,
            details: { action: 'config_update', changes: newConfig },
            severity: 'medium'
        });
    }

    async getSecurityConfig(): Promise<SecurityConfig> {
        try {
            const stored = await AsyncStorage.getItem('security_config');
            if (stored) {
                this.config = { ...this.config, ...JSON.parse(stored) };
            }
        } catch (error) {
            console.error('Failed to load security config:', error);
        }
        return this.config;
    }

    // Security Status Check
    async getSecurityStatus(): Promise<{
        deviceSecurity: DeviceSecurityStatus;
        encryptionStatus: boolean;
        auditingEnabled: boolean;
        recentIncidents: SecurityEvent[];
    }> {
        const deviceSecurity = await this.checkDeviceSecurity();
        const recentIncidents = await this.getAuditEvents(10);

        return {
            deviceSecurity,
            encryptionStatus: this.encryptionKey !== null,
            auditingEnabled: this.config.auditLoggingEnabled,
            recentIncidents: recentIncidents.filter(e =>
                e.severity === 'high' || e.severity === 'critical'
            )
        };
    }
}

export const securityService = new SecurityService();