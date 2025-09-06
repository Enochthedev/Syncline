import AsyncStorage from '@react-native-async-storage/async-storage';
import { securityService, SecurityEventType } from './securityService';

export interface PrivacyConfig {
    piiRedactionEnabled: boolean;
    redactionLevel: 'basic' | 'strict' | 'custom';
    dataMinimizationEnabled: boolean;
    consentRequired: boolean;
    retentionPeriodDays: number;
    allowDataExport: boolean;
    allowDataDeletion: boolean;
}

export interface ConsentRecord {
    id: string;
    userId: string;
    consentType: ConsentType;
    granted: boolean;
    timestamp: Date;
    version: string;
    ipAddress?: string;
    userAgent?: string;
}

export enum ConsentType {
    DATA_PROCESSING = 'data_processing',
    AI_ANALYSIS = 'ai_analysis',
    CONTACT_SYNC = 'contact_sync',
    ANALYTICS = 'analytics',
    MARKETING = 'marketing',
    THIRD_PARTY_SHARING = 'third_party_sharing'
}

export interface PIIPattern {
    name: string;
    pattern: RegExp;
    replacement: string;
    confidence: number;
}

export interface DataExportRequest {
    id: string;
    userId: string;
    requestedAt: Date;
    format: 'json' | 'csv' | 'xml';
    status: 'pending' | 'processing' | 'completed' | 'failed';
    downloadUrl?: string;
    expiresAt?: Date;
}

export interface DataDeletionRequest {
    id: string;
    userId: string;
    requestedAt: Date;
    deletionType: 'partial' | 'complete';
    dataTypes: string[];
    status: 'pending' | 'processing' | 'completed' | 'failed';
    completedAt?: Date;
}

class PrivacyService {
    private config: PrivacyConfig;
    private piiPatterns: PIIPattern[];
    private consentRecords: ConsentRecord[] = [];

    constructor() {
        this.config = {
            piiRedactionEnabled: true,
            redactionLevel: 'basic',
            dataMinimizationEnabled: true,
            consentRequired: true,
            retentionPeriodDays: 365,
            allowDataExport: true,
            allowDataDeletion: true
        };

        this.initializePIIPatterns();
    }

    private initializePIIPatterns(): void {
        this.piiPatterns = [
            // Email addresses
            {
                name: 'email',
                pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
                replacement: '[EMAIL_REDACTED]',
                confidence: 0.95
            },
            // Phone numbers (US format)
            {
                name: 'phone_us',
                pattern: /(\+1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})/g,
                replacement: '[PHONE_REDACTED]',
                confidence: 0.9
            },
            // Social Security Numbers
            {
                name: 'ssn',
                pattern: /\b\d{3}-?\d{2}-?\d{4}\b/g,
                replacement: '[SSN_REDACTED]',
                confidence: 0.85
            },
            // Credit Card Numbers
            {
                name: 'credit_card',
                pattern: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
                replacement: '[CARD_REDACTED]',
                confidence: 0.8
            },
            // IP Addresses
            {
                name: 'ip_address',
                pattern: /\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/g,
                replacement: '[IP_REDACTED]',
                confidence: 0.7
            },
            // Names (basic pattern - can be improved with NLP)
            {
                name: 'potential_name',
                pattern: /\b[A-Z][a-z]+ [A-Z][a-z]+\b/g,
                replacement: '[NAME_REDACTED]',
                confidence: 0.6
            }
        ];
    }

    // PII Redaction
    async redactPII(text: string, customPatterns?: PIIPattern[]): Promise<{
        redactedText: string;
        detectedPII: Array<{ type: string; confidence: number; original: string }>;
    }> {
        if (!this.config.piiRedactionEnabled) {
            return { redactedText: text, detectedPII: [] };
        }

        let redactedText = text;
        const detectedPII: Array<{ type: string; confidence: number; original: string }> = [];
        const patterns = customPatterns || this.piiPatterns;

        // Apply redaction based on level
        const minConfidence = this.getMinConfidenceForLevel();

        for (const pattern of patterns) {
            if (pattern.confidence >= minConfidence) {
                const matches = text.match(pattern.pattern);
                if (matches) {
                    matches.forEach(match => {
                        detectedPII.push({
                            type: pattern.name,
                            confidence: pattern.confidence,
                            original: match
                        });
                    });
                    redactedText = redactedText.replace(pattern.pattern, pattern.replacement);
                }
            }
        }

        // Log PII detection event
        if (detectedPII.length > 0) {
            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_ACCESS,
                details: {
                    action: 'pii_redaction',
                    detectedCount: detectedPII.length,
                    types: detectedPII.map(p => p.type)
                },
                severity: 'medium'
            });
        }

        return { redactedText, detectedPII };
    }

    private getMinConfidenceForLevel(): number {
        switch (this.config.redactionLevel) {
            case 'strict': return 0.5;
            case 'basic': return 0.8;
            case 'custom': return 0.7;
            default: return 0.8;
        }
    }

    async redactObjectPII(obj: any, fieldPaths?: string[]): Promise<any> {
        if (!this.config.piiRedactionEnabled) return obj;

        const result = JSON.parse(JSON.stringify(obj)); // Deep clone

        if (fieldPaths) {
            // Redact specific fields
            for (const path of fieldPaths) {
                const value = this.getNestedValue(result, path);
                if (typeof value === 'string') {
                    const { redactedText } = await this.redactPII(value);
                    this.setNestedValue(result, path, redactedText);
                }
            }
        } else {
            // Redact all string fields recursively
            await this.redactObjectRecursive(result);
        }

        return result;
    }

    private async redactObjectRecursive(obj: any): Promise<void> {
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const value = obj[key];
                if (typeof value === 'string') {
                    const { redactedText } = await this.redactPII(value);
                    obj[key] = redactedText;
                } else if (typeof value === 'object' && value !== null) {
                    await this.redactObjectRecursive(value);
                }
            }
        }
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

    // Data Minimization
    async minimizeData(data: any, retainedFields: string[]): Promise<any> {
        if (!this.config.dataMinimizationEnabled) return data;

        const minimized: any = {};

        retainedFields.forEach(field => {
            const value = this.getNestedValue(data, field);
            if (value !== undefined) {
                this.setNestedValue(minimized, field, value);
            }
        });

        await securityService.logSecurityEvent({
            type: SecurityEventType.DATA_ACCESS,
            details: {
                action: 'data_minimization',
                originalFields: Object.keys(data).length,
                retainedFields: retainedFields.length
            },
            severity: 'low'
        });

        return minimized;
    }

    // Consent Management
    async recordConsent(
        userId: string,
        consentType: ConsentType,
        granted: boolean,
        version: string = '1.0'
    ): Promise<ConsentRecord> {
        const consent: ConsentRecord = {
            id: `consent_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            userId,
            consentType,
            granted,
            timestamp: new Date(),
            version
        };

        this.consentRecords.push(consent);
        await this.storeConsentRecords();

        await securityService.logSecurityEvent({
            type: SecurityEventType.DATA_ACCESS,
            details: {
                action: 'consent_recorded',
                consentType,
                granted,
                userId
            },
            severity: 'low'
        });

        return consent;
    }

    async getConsent(userId: string, consentType: ConsentType): Promise<ConsentRecord | null> {
        await this.loadConsentRecords();

        // Get the most recent consent for this user and type
        const consents = this.consentRecords
            .filter(c => c.userId === userId && c.consentType === consentType)
            .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

        return consents.length > 0 ? consents[0] : null;
    }

    async hasValidConsent(userId: string, consentType: ConsentType): Promise<boolean> {
        if (!this.config.consentRequired) return true;

        const consent = await this.getConsent(userId, consentType);
        return consent ? consent.granted : false;
    }

    async getAllConsents(userId: string): Promise<ConsentRecord[]> {
        await this.loadConsentRecords();
        return this.consentRecords.filter(c => c.userId === userId);
    }

    private async storeConsentRecords(): Promise<void> {
        try {
            await AsyncStorage.setItem('consent_records', JSON.stringify(this.consentRecords));
        } catch (error) {
            console.error('Failed to store consent records:', error);
        }
    }

    private async loadConsentRecords(): Promise<void> {
        try {
            const stored = await AsyncStorage.getItem('consent_records');
            if (stored) {
                this.consentRecords = JSON.parse(stored).map((record: any) => ({
                    ...record,
                    timestamp: new Date(record.timestamp)
                }));
            }
        } catch (error) {
            console.error('Failed to load consent records:', error);
        }
    }

    // Data Export
    async requestDataExport(
        userId: string,
        format: 'json' | 'csv' | 'xml' = 'json'
    ): Promise<DataExportRequest> {
        if (!this.config.allowDataExport) {
            throw new Error('Data export is not allowed');
        }

        const exportRequest: DataExportRequest = {
            id: `export_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            userId,
            requestedAt: new Date(),
            format,
            status: 'pending'
        };

        await this.storeExportRequest(exportRequest);

        await securityService.logSecurityEvent({
            type: SecurityEventType.DATA_EXPORT,
            details: {
                action: 'export_requested',
                userId,
                format,
                requestId: exportRequest.id
            },
            severity: 'medium'
        });

        // In a real implementation, this would trigger background processing
        setTimeout(() => this.processDataExport(exportRequest.id), 1000);

        return exportRequest;
    }

    private async processDataExport(requestId: string): Promise<void> {
        try {
            // Simulate export processing
            const request = await this.getExportRequest(requestId);
            if (!request) return;

            request.status = 'processing';
            await this.storeExportRequest(request);

            // Collect user data (this would be more comprehensive in real implementation)
            const userData = await this.collectUserData(request.userId);
            const exportData = await this.formatExportData(userData, request.format);

            // In real implementation, this would upload to secure storage and provide download link
            request.status = 'completed';
            request.downloadUrl = `https://secure-exports.example.com/${requestId}`;
            request.expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

            await this.storeExportRequest(request);

            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_EXPORT,
                details: {
                    action: 'export_completed',
                    userId: request.userId,
                    requestId
                },
                severity: 'medium'
            });
        } catch (error) {
            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_EXPORT,
                details: {
                    action: 'export_failed',
                    requestId,
                    error: error.message
                },
                severity: 'high'
            });
        }
    }

    private async collectUserData(userId: string): Promise<any> {
        // This would collect all user data from various sources
        return {
            profile: await AsyncStorage.getItem(`user_profile_${userId}`),
            contacts: await AsyncStorage.getItem(`user_contacts_${userId}`),
            messages: await AsyncStorage.getItem(`user_messages_${userId}`),
            settings: await AsyncStorage.getItem(`user_settings_${userId}`),
            consents: await this.getAllConsents(userId)
        };
    }

    private async formatExportData(data: any, format: string): Promise<string> {
        switch (format) {
            case 'json':
                return JSON.stringify(data, null, 2);
            case 'csv':
                // Simple CSV conversion (would be more sophisticated in real implementation)
                return this.convertToCSV(data);
            case 'xml':
                return this.convertToXML(data);
            default:
                return JSON.stringify(data, null, 2);
        }
    }

    private convertToCSV(data: any): string {
        // Simplified CSV conversion
        const headers = Object.keys(data).join(',');
        const values = Object.values(data).map(v =>
            typeof v === 'object' ? JSON.stringify(v) : String(v)
        ).join(',');
        return `${headers}\n${values}`;
    }

    private convertToXML(data: any): string {
        // Simplified XML conversion
        let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<export>\n';
        for (const [key, value] of Object.entries(data)) {
            xml += `  <${key}>${typeof value === 'object' ? JSON.stringify(value) : value}</${key}>\n`;
        }
        xml += '</export>';
        return xml;
    }

    // Data Deletion
    async requestDataDeletion(
        userId: string,
        deletionType: 'partial' | 'complete',
        dataTypes: string[] = []
    ): Promise<DataDeletionRequest> {
        if (!this.config.allowDataDeletion) {
            throw new Error('Data deletion is not allowed');
        }

        const deletionRequest: DataDeletionRequest = {
            id: `deletion_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            userId,
            requestedAt: new Date(),
            deletionType,
            dataTypes,
            status: 'pending'
        };

        await this.storeDeletionRequest(deletionRequest);

        await securityService.logSecurityEvent({
            type: SecurityEventType.DATA_DELETION,
            details: {
                action: 'deletion_requested',
                userId,
                deletionType,
                dataTypes,
                requestId: deletionRequest.id
            },
            severity: 'high'
        });

        // In a real implementation, this would trigger background processing
        setTimeout(() => this.processDataDeletion(deletionRequest.id), 1000);

        return deletionRequest;
    }

    private async processDataDeletion(requestId: string): Promise<void> {
        try {
            const request = await this.getDeletionRequest(requestId);
            if (!request) return;

            request.status = 'processing';
            await this.storeDeletionRequest(request);

            if (request.deletionType === 'complete') {
                await this.deleteAllUserData(request.userId);
            } else {
                await this.deletePartialUserData(request.userId, request.dataTypes);
            }

            request.status = 'completed';
            request.completedAt = new Date();
            await this.storeDeletionRequest(request);

            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_DELETION,
                details: {
                    action: 'deletion_completed',
                    userId: request.userId,
                    requestId
                },
                severity: 'high'
            });
        } catch (error) {
            await securityService.logSecurityEvent({
                type: SecurityEventType.DATA_DELETION,
                details: {
                    action: 'deletion_failed',
                    requestId,
                    error: error.message
                },
                severity: 'critical'
            });
        }
    }

    private async deleteAllUserData(userId: string): Promise<void> {
        const keys = await AsyncStorage.getAllKeys();
        const userKeys = keys.filter(key => key.includes(userId));
        await AsyncStorage.multiRemove(userKeys);
    }

    private async deletePartialUserData(userId: string, dataTypes: string[]): Promise<void> {
        for (const dataType of dataTypes) {
            await AsyncStorage.removeItem(`${dataType}_${userId}`);
        }
    }

    // Storage helpers
    private async storeExportRequest(request: DataExportRequest): Promise<void> {
        const requests = await this.getStoredExportRequests();
        const index = requests.findIndex(r => r.id === request.id);
        if (index >= 0) {
            requests[index] = request;
        } else {
            requests.push(request);
        }
        await AsyncStorage.setItem('export_requests', JSON.stringify(requests));
    }

    private async getExportRequest(requestId: string): Promise<DataExportRequest | null> {
        const requests = await this.getStoredExportRequests();
        return requests.find(r => r.id === requestId) || null;
    }

    private async getStoredExportRequests(): Promise<DataExportRequest[]> {
        try {
            const stored = await AsyncStorage.getItem('export_requests');
            return stored ? JSON.parse(stored).map((req: any) => ({
                ...req,
                requestedAt: new Date(req.requestedAt),
                expiresAt: req.expiresAt ? new Date(req.expiresAt) : undefined
            })) : [];
        } catch (error) {
            return [];
        }
    }

    private async storeDeletionRequest(request: DataDeletionRequest): Promise<void> {
        const requests = await this.getStoredDeletionRequests();
        const index = requests.findIndex(r => r.id === request.id);
        if (index >= 0) {
            requests[index] = request;
        } else {
            requests.push(request);
        }
        await AsyncStorage.setItem('deletion_requests', JSON.stringify(requests));
    }

    private async getDeletionRequest(requestId: string): Promise<DataDeletionRequest | null> {
        const requests = await this.getStoredDeletionRequests();
        return requests.find(r => r.id === requestId) || null;
    }

    private async getStoredDeletionRequests(): Promise<DataDeletionRequest[]> {
        try {
            const stored = await AsyncStorage.getItem('deletion_requests');
            return stored ? JSON.parse(stored).map((req: any) => ({
                ...req,
                requestedAt: new Date(req.requestedAt),
                completedAt: req.completedAt ? new Date(req.completedAt) : undefined
            })) : [];
        } catch (error) {
            return [];
        }
    }

    // Configuration
    async updatePrivacyConfig(newConfig: Partial<PrivacyConfig>): Promise<void> {
        this.config = { ...this.config, ...newConfig };
        await AsyncStorage.setItem('privacy_config', JSON.stringify(this.config));

        await securityService.logSecurityEvent({
            type: SecurityEventType.DATA_ACCESS,
            details: {
                action: 'privacy_config_update',
                changes: newConfig
            },
            severity: 'medium'
        });
    }

    async getPrivacyConfig(): Promise<PrivacyConfig> {
        try {
            const stored = await AsyncStorage.getItem('privacy_config');
            if (stored) {
                this.config = { ...this.config, ...JSON.parse(stored) };
            }
        } catch (error) {
            console.error('Failed to load privacy config:', error);
        }
        return this.config;
    }
}

export const privacyService = new PrivacyService();