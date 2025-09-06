import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  TouchableOpacity,
  Alert,
  ActivityIndicator
} from 'react-native';
import { useSecurity } from '../contexts/SecurityContext';
import { ConsentType } from '../services/privacyService';
import { SecurityEvent } from '../services/securityService';

interface SecuritySettingsProps {
  onClose?: () => void;
}

export const SecuritySettings: React.FC<SecuritySettingsProps> = ({ onClose }) => {
  const {
    securityConfig,
    privacyConfig,
    deviceSecurity,
    biometricCapabilities,
    recentSecurityEvents,
    checkDeviceSecurity,
    refreshSecurityEvents,
    recordConsent,
    hasConsent,
    requestDataExport,
    requestDataDeletion
  } = useSecurity();

  const [loading, setLoading] = useState(false);
  const [consents, setConsents] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadConsents();
    refreshSecurityEvents();
  }, []);

  const loadConsents = async () => {
    const consentTypes = Object.values(ConsentType);
    const consentStatus: Record<string, boolean> = {};
    
    for (const type of consentTypes) {
      consentStatus[type] = await hasConsent(type);
    }
    
    setConsents(consentStatus);
  };

  const handleConsentChange = async (consentType: ConsentType, granted: boolean) => {
    try {
      await recordConsent(consentType, granted);
      setConsents(prev => ({ ...prev, [consentType]: granted }));
    } catch (error) {
      Alert.alert('Error', 'Failed to update consent. Please try again.');
    }
  };

  const handleDeviceSecurityCheck = async () => {
    setLoading(true);
    try {
      const status = await checkDeviceSecurity();
      
      if (status.isSecure) {
        Alert.alert('Device Security', 'Your device passes all security checks.');
      } else {
        Alert.alert(
          'Security Violations Detected',
          `The following security issues were found:\n\n${status.violations.join('\n')}\n\nSome features may be limited for your protection.`,
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to check device security.');
    } finally {
      setLoading(false);
    }
  };

  const handleDataExport = () => {
    Alert.alert(
      'Export Data',
      'Choose the format for your data export:',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'JSON', onPress: () => exportData('json') },
        { text: 'CSV', onPress: () => exportData('csv') },
        { text: 'XML', onPress: () => exportData('xml') }
      ]
    );
  };

  const exportData = async (format: 'json' | 'csv' | 'xml') => {
    try {
      setLoading(true);
      await requestDataExport(format);
    } catch (error) {
      Alert.alert('Error', 'Failed to request data export.');
    } finally {
      setLoading(false);
    }
  };

  const handleDataDeletion = () => {
    Alert.alert(
      'Delete Data',
      'What type of deletion would you like to perform?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Partial Deletion', 
          onPress: () => requestDataDeletion('partial') 
        },
        { 
          text: 'Complete Deletion', 
          style: 'destructive',
          onPress: () => requestDataDeletion('complete') 
        }
      ]
    );
  };

  const getSecurityStatusColor = () => {
    if (!deviceSecurity) return '#888888';
    return deviceSecurity.isSecure ? '#4CAF50' : '#F44336';
  };

  const getSecurityStatusText = () => {
    if (!deviceSecurity) return 'Unknown';
    return deviceSecurity.isSecure ? 'Secure' : 'Violations Detected';
  };

  const formatConsentType = (type: ConsentType): string => {
    return type.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join(' ');
  };

  const getEventSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#F44336';
      case 'high': return '#FF9800';
      case 'medium': return '#FFC107';
      case 'low': return '#4CAF50';
      default: return '#888888';
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Security & Privacy</Text>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Device Security Status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Device Security</Text>
        
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Security Status:</Text>
          <View style={styles.statusIndicator}>
            <View 
              style={[
                styles.statusDot, 
                { backgroundColor: getSecurityStatusColor() }
              ]} 
            />
            <Text style={[styles.statusText, { color: getSecurityStatusColor() }]}>
              {getSecurityStatusText()}
            </Text>
          </View>
        </View>

        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Biometric Available:</Text>
          <Text style={styles.statusValue}>
            {biometricCapabilities?.isAvailable ? 'Yes' : 'No'}
          </Text>
        </View>

        {biometricCapabilities?.isAvailable && (
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Biometric Type:</Text>
            <Text style={styles.statusValue}>
              {biometricCapabilities.biometryType || 'Unknown'}
            </Text>
          </View>
        )}

        <TouchableOpacity 
          style={styles.actionButton}
          onPress={handleDeviceSecurityCheck}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.actionButtonText}>Check Device Security</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Security Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Security Settings</Text>
        
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Encryption Enabled</Text>
          <Switch
            value={securityConfig?.encryptionEnabled || false}
            disabled={true} // Always enabled for security
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={securityConfig?.encryptionEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>

        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Biometric Authentication</Text>
          <Switch
            value={securityConfig?.biometricEnabled || false}
            disabled={!biometricCapabilities?.isAvailable}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={securityConfig?.biometricEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>

        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Audit Logging</Text>
          <Switch
            value={securityConfig?.auditLoggingEnabled || false}
            disabled={true} // Always enabled for compliance
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={securityConfig?.auditLoggingEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Privacy Controls */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Privacy Controls</Text>
        
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>PII Redaction Level</Text>
          <Text style={styles.settingValue}>
            {privacyConfig?.redactionLevel || 'Basic'}
          </Text>
        </View>

        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Data Minimization</Text>
          <Switch
            value={privacyConfig?.dataMinimizationEnabled || false}
            disabled={true} // Always enabled for privacy
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={privacyConfig?.dataMinimizationEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Consent Management */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data Processing Consents</Text>
        
        {Object.values(ConsentType).map((consentType) => (
          <View key={consentType} style={styles.settingRow}>
            <Text style={styles.settingLabel}>
              {formatConsentType(consentType)}
            </Text>
            <Switch
              value={consents[consentType] || false}
              onValueChange={(value) => handleConsentChange(consentType, value)}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={consents[consentType] ? '#f5dd4b' : '#f4f3f4'}
            />
          </View>
        ))}
      </View>

      {/* Data Rights */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data Rights</Text>
        
        <TouchableOpacity 
          style={styles.actionButton}
          onPress={handleDataExport}
          disabled={loading}
        >
          <Text style={styles.actionButtonText}>Export My Data</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={[styles.actionButton, styles.dangerButton]}
          onPress={handleDataDeletion}
          disabled={loading}
        >
          <Text style={styles.actionButtonText}>Delete My Data</Text>
        </TouchableOpacity>
      </View>

      {/* Recent Security Events */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Recent Security Events</Text>
        
        {recentSecurityEvents.length === 0 ? (
          <Text style={styles.noEventsText}>No recent security events</Text>
        ) : (
          recentSecurityEvents.slice(0, 5).map((event) => (
            <View key={event.id} style={styles.eventRow}>
              <View style={styles.eventHeader}>
                <Text style={styles.eventType}>{event.type}</Text>
                <View 
                  style={[
                    styles.severityBadge,
                    { backgroundColor: getEventSeverityColor(event.severity) }
                  ]}
                >
                  <Text style={styles.severityText}>{event.severity}</Text>
                </View>
              </View>
              <Text style={styles.eventTime}>
                {new Date(event.timestamp).toLocaleString()}
              </Text>
            </View>
          ))
        )}

        <TouchableOpacity 
          style={styles.refreshButton}
          onPress={refreshSecurityEvents}
        >
          <Text style={styles.refreshButtonText}>Refresh Events</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333333',
  },
  closeButton: {
    padding: 8,
  },
  closeButtonText: {
    fontSize: 18,
    color: '#666666',
  },
  section: {
    backgroundColor: '#ffffff',
    marginTop: 10,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 16,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  statusLabel: {
    fontSize: 16,
    color: '#666666',
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '500',
  },
  statusValue: {
    fontSize: 16,
    color: '#333333',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  settingLabel: {
    fontSize: 16,
    color: '#333333',
    flex: 1,
  },
  settingValue: {
    fontSize: 16,
    color: '#666666',
    textTransform: 'capitalize',
  },
  actionButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginTop: 12,
    alignItems: 'center',
  },
  dangerButton: {
    backgroundColor: '#F44336',
  },
  actionButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  noEventsText: {
    fontSize: 16,
    color: '#888888',
    textAlign: 'center',
    paddingVertical: 20,
  },
  eventRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  eventHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  eventType: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333333',
    flex: 1,
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  severityText: {
    fontSize: 12,
    color: '#ffffff',
    fontWeight: '500',
    textTransform: 'uppercase',
  },
  eventTime: {
    fontSize: 12,
    color: '#888888',
  },
  refreshButton: {
    alignItems: 'center',
    paddingVertical: 12,
    marginTop: 8,
  },
  refreshButtonText: {
    fontSize: 16,
    color: '#007AFF',
  },
});