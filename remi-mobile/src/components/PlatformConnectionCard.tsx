/**
 * Platform Connection Card Component
 * 
 * Displays individual platform connection status with health indicators,
 * sync information, and quick actions.
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { PlatformConnection } from '../services/platformConnectionService';

interface PlatformConnectionCardProps {
  connection: PlatformConnection;
  onConnect: (platform: string) => void;
  onDisconnect: (platform: string) => void;
  onSettings: (platform: string) => void;
  onSync: (platform: string) => void;
  onTroubleshoot: (platform: string) => void;
}

export const PlatformConnectionCard: React.FC<PlatformConnectionCardProps> = ({
  connection,
  onConnect,
  onDisconnect,
  onSettings,
  onSync,
  onTroubleshoot,
}) => {
  const { theme } = useTheme();

  const getStatusColor = (status: PlatformConnection['connectionStatus']) => {
    switch (status) {
      case 'healthy':
        return theme.colors.success;
      case 'degraded':
        return theme.colors.warning;
      case 'unhealthy':
        return theme.colors.error;
      case 'authenticating':
        return theme.colors.info;
      case 'disconnected':
      default:
        return theme.colors.textSecondary;
    }
  };

  const getStatusText = (status: PlatformConnection['connectionStatus']) => {
    switch (status) {
      case 'healthy':
        return 'Connected';
      case 'degraded':
        return 'Issues Detected';
      case 'unhealthy':
        return 'Connection Problems';
      case 'authenticating':
        return 'Connecting...';
      case 'disconnected':
      default:
        return 'Disconnected';
    }
  };

  const getPlatformIcon = (platform: string) => {
    // In a real app, you'd use actual icons
    const icons: Record<string, string> = {
      gmail: '📧',
      slack: '💬',
      discord: '🎮',
      whatsapp: '📱',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform] || '🔗';
  };

  const formatLastSync = (lastSyncTime?: Date) => {
    if (!lastSyncTime) return 'Never';
    
    const now = new Date();
    const diff = now.getTime() - lastSyncTime.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  const handleDisconnect = () => {
    Alert.alert(
      'Disconnect Platform',
      `Are you sure you want to disconnect ${connection.displayName}? This will stop syncing data from this platform.`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Disconnect', 
          style: 'destructive',
          onPress: () => onDisconnect(connection.platform)
        },
      ]
    );
  };

  const styles = StyleSheet.create({
    card: {
      backgroundColor: theme.colors.surface,
      borderRadius: 12,
      padding: 16,
      marginVertical: 8,
      marginHorizontal: 16,
      shadowColor: theme.colors.shadow,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
      elevation: 3,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 12,
    },
    icon: {
      fontSize: 24,
      marginRight: 12,
    },
    titleContainer: {
      flex: 1,
    },
    title: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.colors.text,
      marginBottom: 2,
    },
    status: {
      fontSize: 14,
      fontWeight: '500',
    },
    statusIndicator: {
      width: 8,
      height: 8,
      borderRadius: 4,
      marginLeft: 8,
    },
    details: {
      marginBottom: 16,
    },
    detailRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 6,
    },
    detailLabel: {
      fontSize: 14,
      color: theme.colors.textSecondary,
    },
    detailValue: {
      fontSize: 14,
      color: theme.colors.text,
      fontWeight: '500',
    },
    errorText: {
      fontSize: 12,
      color: theme.colors.error,
      marginTop: 4,
      fontStyle: 'italic',
    },
    actions: {
      flexDirection: 'row',
      justifyContent: 'space-between',
    },
    actionButton: {
      flex: 1,
      paddingVertical: 8,
      paddingHorizontal: 12,
      borderRadius: 8,
      marginHorizontal: 4,
      alignItems: 'center',
    },
    primaryAction: {
      backgroundColor: theme.colors.primary,
    },
    secondaryAction: {
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    dangerAction: {
      backgroundColor: theme.colors.error,
    },
    actionText: {
      fontSize: 14,
      fontWeight: '500',
    },
    primaryActionText: {
      color: theme.colors.surface,
    },
    secondaryActionText: {
      color: theme.colors.text,
    },
    dangerActionText: {
      color: theme.colors.surface,
    },
    disabledCard: {
      opacity: 0.6,
    },
    enabledToggle: {
      position: 'absolute',
      top: 16,
      right: 16,
      width: 20,
      height: 20,
      borderRadius: 10,
      borderWidth: 2,
      borderColor: theme.colors.primary,
      backgroundColor: connection.isEnabled ? theme.colors.primary : 'transparent',
    },
  });

  return (
    <View style={[styles.card, !connection.isEnabled && styles.disabledCard]}>
      <View style={styles.enabledToggle} />
      
      <View style={styles.header}>
        <Text style={styles.icon}>{getPlatformIcon(connection.platform)}</Text>
        <View style={styles.titleContainer}>
          <Text style={styles.title}>{connection.displayName}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Text style={[styles.status, { color: getStatusColor(connection.connectionStatus) }]}>
              {getStatusText(connection.connectionStatus)}
            </Text>
            <View 
              style={[
                styles.statusIndicator, 
                { backgroundColor: getStatusColor(connection.connectionStatus) }
              ]} 
            />
          </View>
        </View>
      </View>

      {connection.isConnected && (
        <View style={styles.details}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Last Sync</Text>
            <Text style={styles.detailValue}>{formatLastSync(connection.lastSyncTime)}</Text>
          </View>
          
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Sync Frequency</Text>
            <Text style={styles.detailValue}>
              {connection.syncPreferences.syncFrequency.charAt(0).toUpperCase() + 
               connection.syncPreferences.syncFrequency.slice(1)}
            </Text>
          </View>
          
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Success Rate</Text>
            <Text style={styles.detailValue}>
              {connection.healthMetrics.successfulSyncs > 0 
                ? Math.round((connection.healthMetrics.successfulSyncs / 
                   (connection.healthMetrics.successfulSyncs + connection.healthMetrics.failedSyncs)) * 100)
                : 0}%
            </Text>
          </View>

          {connection.lastError && (
            <Text style={styles.errorText}>
              Last Error: {connection.lastError}
            </Text>
          )}
        </View>
      )}

      <View style={styles.actions}>
        {!connection.isConnected ? (
          <TouchableOpacity
            style={[styles.actionButton, styles.primaryAction]}
            onPress={() => onConnect(connection.platform)}
          >
            <Text style={[styles.actionText, styles.primaryActionText]}>Connect</Text>
          </TouchableOpacity>
        ) : (
          <>
            <TouchableOpacity
              style={[styles.actionButton, styles.secondaryAction]}
              onPress={() => onSync(connection.platform)}
            >
              <Text style={[styles.actionText, styles.secondaryActionText]}>Sync</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.actionButton, styles.secondaryAction]}
              onPress={() => onSettings(connection.platform)}
            >
              <Text style={[styles.actionText, styles.secondaryActionText]}>Settings</Text>
            </TouchableOpacity>
            
            {connection.connectionStatus !== 'healthy' && (
              <TouchableOpacity
                style={[styles.actionButton, styles.secondaryAction]}
                onPress={() => onTroubleshoot(connection.platform)}
              >
                <Text style={[styles.actionText, styles.secondaryActionText]}>Fix</Text>
              </TouchableOpacity>
            )}
            
            <TouchableOpacity
              style={[styles.actionButton, styles.dangerAction]}
              onPress={handleDisconnect}
            >
              <Text style={[styles.actionText, styles.dangerActionText]}>Disconnect</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </View>
  );
};