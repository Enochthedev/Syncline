/**
 * Platform Settings Modal Component
 * 
 * Provides comprehensive settings management for individual platform connections
 * including sync preferences, privacy settings, and platform-specific options.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  TouchableOpacity,
  Switch,
  StyleSheet,
  Alert,
  TextInput,
  Platform,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { 
  PlatformConnection, 
  PlatformSyncPreferences, 
  platformConnectionService 
} from '../services/platformConnectionService';
import { LoadingSpinner } from './LoadingSpinner';

interface PlatformSettingsModalProps {
  visible: boolean;
  platform: string;
  onClose: () => void;
  onSave: (platform: string) => void;
}

export const PlatformSettingsModal: React.FC<PlatformSettingsModalProps> = ({
  visible,
  platform,
  onClose,
  onSave,
}) => {
  const { theme } = useTheme();
  const [connection, setConnection] = useState<PlatformConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncPreferences, setSyncPreferences] = useState<PlatformSyncPreferences | null>(null);
  const [platformSettings, setPlatformSettings] = useState<Record<string, any>>({});

  useEffect(() => {
    if (visible && platform) {
      loadConnectionSettings();
    }
  }, [visible, platform]);

  const loadConnectionSettings = async () => {
    try {
      setLoading(true);
      const conn = await platformConnectionService.getConnection(platform);
      if (conn) {
        setConnection(conn);
        setSyncPreferences({ ...conn.syncPreferences });
        setPlatformSettings({ ...conn.platformSpecificSettings });
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to load platform settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!syncPreferences || !connection) return;

    try {
      setSaving(true);
      
      // Update sync preferences
      await platformConnectionService.updateSyncPreferences(platform, syncPreferences);
      
      // Update platform-specific settings
      await platformConnectionService.updatePlatformSettings(platform, platformSettings);
      
      Alert.alert('Success', 'Settings saved successfully', [
        { text: 'OK', onPress: () => onSave(platform) }
      ]);
    } catch (error) {
      Alert.alert('Error', error instanceof Error ? error.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateSyncPreference = <K extends keyof PlatformSyncPreferences>(
    key: K,
    value: PlatformSyncPreferences[K]
  ) => {
    if (syncPreferences) {
      setSyncPreferences({ ...syncPreferences, [key]: value });
    }
  };

  const updateDataFilter = (filterKey: string, value: any) => {
    if (syncPreferences) {
      setSyncPreferences({
        ...syncPreferences,
        dataFilters: {
          ...syncPreferences.dataFilters,
          [filterKey]: value,
        },
      });
    }
  };

  const updatePrivacySetting = (settingKey: string, value: any) => {
    if (syncPreferences) {
      setSyncPreferences({
        ...syncPreferences,
        privacySettings: {
          ...syncPreferences.privacySettings,
          [settingKey]: value,
        },
      });
    }
  };

  const updatePlatformSetting = (settingKey: string, value: any) => {
    setPlatformSettings({
      ...platformSettings,
      [settingKey]: value,
    });
  };

  const getPlatformDisplayName = (platform: string) => {
    const names: Record<string, string> = {
      gmail: 'Gmail',
      slack: 'Slack',
      discord: 'Discord',
      whatsapp: 'WhatsApp',
      twitter: 'Twitter',
      linkedin: 'LinkedIn',
    };
    return names[platform] || platform;
  };

  const getPlatformSpecificSettings = (platform: string) => {
    switch (platform) {
      case 'gmail':
        return [
          {
            key: 'includeSpam',
            label: 'Include Spam Folder',
            type: 'boolean',
            description: 'Sync messages from the spam folder',
          },
          {
            key: 'includeDrafts',
            label: 'Include Drafts',
            type: 'boolean',
            description: 'Sync draft messages',
          },
          {
            key: 'maxAttachmentSize',
            label: 'Max Attachment Size (MB)',
            type: 'number',
            description: 'Maximum size for attachment downloads',
          },
        ];
      case 'slack':
        return [
          {
            key: 'includePrivateChannels',
            label: 'Include Private Channels',
            type: 'boolean',
            description: 'Sync messages from private channels you have access to',
          },
          {
            key: 'includeBotMessages',
            label: 'Include Bot Messages',
            type: 'boolean',
            description: 'Sync messages from bots and integrations',
          },
          {
            key: 'syncThreads',
            label: 'Sync Thread Replies',
            type: 'boolean',
            description: 'Include threaded conversation replies',
          },
        ];
      case 'discord':
        return [
          {
            key: 'includeVoiceChannels',
            label: 'Include Voice Channel Activity',
            type: 'boolean',
            description: 'Track voice channel join/leave events',
          },
          {
            key: 'syncReactions',
            label: 'Sync Message Reactions',
            type: 'boolean',
            description: 'Include emoji reactions on messages',
          },
        ];
      default:
        return [];
    }
  };

  const renderSettingItem = (setting: any) => {
    const currentValue = platformSettings[setting.key];

    switch (setting.type) {
      case 'boolean':
        return (
          <View key={setting.key} style={styles.settingItem}>
            <View style={styles.settingContent}>
              <Text style={styles.settingLabel}>{setting.label}</Text>
              <Text style={styles.settingDescription}>{setting.description}</Text>
            </View>
            <Switch
              value={currentValue || false}
              onValueChange={(value) => updatePlatformSetting(setting.key, value)}
              trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
              thumbColor={currentValue ? theme.colors.primary : theme.colors.textSecondary}
            />
          </View>
        );
      case 'number':
        return (
          <View key={setting.key} style={styles.settingItem}>
            <View style={styles.settingContent}>
              <Text style={styles.settingLabel}>{setting.label}</Text>
              <Text style={styles.settingDescription}>{setting.description}</Text>
            </View>
            <TextInput
              style={styles.numberInput}
              value={currentValue?.toString() || ''}
              onChangeText={(text) => {
                const numValue = parseInt(text) || 0;
                updatePlatformSetting(setting.key, numValue);
              }}
              keyboardType="numeric"
              placeholder="0"
            />
          </View>
        );
      default:
        return null;
    }
  };

  const styles = StyleSheet.create({
    modal: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 16,
      backgroundColor: theme.colors.surface,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
      paddingTop: Platform.OS === 'ios' ? 50 : 16,
    },
    headerTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.colors.text,
    },
    headerButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
    },
    cancelButton: {
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    saveButton: {
      backgroundColor: theme.colors.primary,
    },
    headerButtonText: {
      fontSize: 14,
      fontWeight: '500',
    },
    cancelButtonText: {
      color: theme.colors.text,
    },
    saveButtonText: {
      color: theme.colors.surface,
    },
    content: {
      flex: 1,
    },
    scrollView: {
      flex: 1,
    },
    section: {
      backgroundColor: theme.colors.surface,
      marginVertical: 8,
      paddingVertical: 16,
    },
    sectionHeader: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.colors.text,
      paddingHorizontal: 16,
      marginBottom: 12,
    },
    settingItem: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
    },
    settingContent: {
      flex: 1,
      marginRight: 16,
    },
    settingLabel: {
      fontSize: 16,
      color: theme.colors.text,
      marginBottom: 4,
    },
    settingDescription: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      lineHeight: 18,
    },
    picker: {
      minWidth: 120,
    },
    pickerButton: {
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    pickerButtonText: {
      fontSize: 14,
      color: theme.colors.text,
    },
    numberInput: {
      minWidth: 80,
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
      fontSize: 14,
      color: theme.colors.text,
      textAlign: 'center',
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    loadingText: {
      fontSize: 16,
      color: theme.colors.textSecondary,
      marginTop: 16,
    },
    warningBox: {
      backgroundColor: theme.colors.warningLight,
      padding: 12,
      margin: 16,
      borderRadius: 8,
      borderLeftWidth: 4,
      borderLeftColor: theme.colors.warning,
    },
    warningText: {
      fontSize: 14,
      color: theme.colors.text,
      lineHeight: 18,
    },
  });

  if (loading) {
    return (
      <Modal visible={visible} animationType="slide" presentationStyle="fullScreen">
        <View style={styles.modal}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Loading Settings...</Text>
            <TouchableOpacity style={[styles.headerButton, styles.cancelButton]} onPress={onClose}>
              <Text style={[styles.headerButtonText, styles.cancelButtonText]}>Cancel</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.loadingContainer}>
            <LoadingSpinner />
            <Text style={styles.loadingText}>Loading platform settings...</Text>
          </View>
        </View>
      </Modal>
    );
  }

  if (!connection || !syncPreferences) {
    return null;
  }

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="fullScreen">
      <View style={styles.modal}>
        <View style={styles.header}>
          <TouchableOpacity style={[styles.headerButton, styles.cancelButton]} onPress={onClose}>
            <Text style={[styles.headerButtonText, styles.cancelButtonText]}>Cancel</Text>
          </TouchableOpacity>
          
          <Text style={styles.headerTitle}>
            {getPlatformDisplayName(platform)} Settings
          </Text>
          
          <TouchableOpacity 
            style={[styles.headerButton, styles.saveButton]} 
            onPress={handleSave}
            disabled={saving}
          >
            <Text style={[styles.headerButtonText, styles.saveButtonText]}>
              {saving ? 'Saving...' : 'Save'}
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollView}>
          {/* Sync Settings */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>Synchronization</Text>
            
            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Enable Sync</Text>
                <Text style={styles.settingDescription}>
                  Allow data synchronization from this platform
                </Text>
              </View>
              <Switch
                value={syncPreferences.enabled}
                onValueChange={(value) => updateSyncPreference('enabled', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.enabled ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Sync Messages</Text>
                <Text style={styles.settingDescription}>
                  Synchronize messages and conversations
                </Text>
              </View>
              <Switch
                value={syncPreferences.syncMessages}
                onValueChange={(value) => updateSyncPreference('syncMessages', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.syncMessages ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Sync Contacts</Text>
                <Text style={styles.settingDescription}>
                  Synchronize contact information
                </Text>
              </View>
              <Switch
                value={syncPreferences.syncContacts}
                onValueChange={(value) => updateSyncPreference('syncContacts', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.syncContacts ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Sync Files</Text>
                <Text style={styles.settingDescription}>
                  Synchronize file attachments and media
                </Text>
              </View>
              <Switch
                value={syncPreferences.syncFiles}
                onValueChange={(value) => updateSyncPreference('syncFiles', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.syncFiles ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Sync Frequency</Text>
                <Text style={styles.settingDescription}>
                  How often to check for new data
                </Text>
              </View>
              <TouchableOpacity style={styles.pickerButton}>
                <Text style={styles.pickerButtonText}>
                  {syncPreferences.syncFrequency.charAt(0).toUpperCase() + 
                   syncPreferences.syncFrequency.slice(1)}
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Privacy Settings */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>Privacy & Security</Text>
            
            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>PII Redaction</Text>
                <Text style={styles.settingDescription}>
                  Automatically redact personally identifiable information
                </Text>
              </View>
              <Switch
                value={syncPreferences.privacySettings.enablePIIRedaction}
                onValueChange={(value) => updatePrivacySetting('enablePIIRedaction', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.privacySettings.enablePIIRedaction ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>AI Analysis</Text>
                <Text style={styles.settingDescription}>
                  Enable AI-powered insights and analysis
                </Text>
              </View>
              <Switch
                value={syncPreferences.privacySettings.enableAIAnalysis}
                onValueChange={(value) => updatePrivacySetting('enableAIAnalysis', value)}
                trackColor={{ false: theme.colors.border, true: theme.colors.primaryLight }}
                thumbColor={syncPreferences.privacySettings.enableAIAnalysis ? theme.colors.primary : theme.colors.textSecondary}
              />
            </View>

            <View style={styles.settingItem}>
              <View style={styles.settingContent}>
                <Text style={styles.settingLabel}>Data Retention (Days)</Text>
                <Text style={styles.settingDescription}>
                  How long to keep synchronized data locally
                </Text>
              </View>
              <TextInput
                style={styles.numberInput}
                value={syncPreferences.privacySettings.dataRetentionDays?.toString() || '365'}
                onChangeText={(text) => {
                  const days = parseInt(text) || 365;
                  updatePrivacySetting('dataRetentionDays', days);
                }}
                keyboardType="numeric"
                placeholder="365"
              />
            </View>
          </View>

          {/* Platform-Specific Settings */}
          {getPlatformSpecificSettings(platform).length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>
                {getPlatformDisplayName(platform)} Specific
              </Text>
              {getPlatformSpecificSettings(platform).map(renderSettingItem)}
            </View>
          )}

          {/* Warning about data usage */}
          <View style={styles.warningBox}>
            <Text style={styles.warningText}>
              ⚠️ Changing sync settings may affect data usage and battery life. 
              Real-time sync provides the best experience but uses more resources.
            </Text>
          </View>
        </ScrollView>
      </View>
    </Modal>
  );
};