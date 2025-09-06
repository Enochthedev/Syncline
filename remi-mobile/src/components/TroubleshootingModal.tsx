/**
 * Troubleshooting Modal Component
 * 
 * Provides connection troubleshooting with error diagnosis,
 * suggested actions, and automated fixes.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { 
  ConnectionTroubleshootingInfo,
  TroubleshootingIssue,
  SuggestedAction,
  platformConnectionService 
} from '../services/platformConnectionService';
import { LoadingSpinner } from './LoadingSpinner';

interface TroubleshootingModalProps {
  visible: boolean;
  platform: string;
  onClose: () => void;
  onFixed: (platform: string) => void;
}

export const TroubleshootingModal: React.FC<TroubleshootingModalProps> = ({
  visible,
  platform,
  onClose,
  onFixed,
}) => {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [troubleshootingInfo, setTroubleshootingInfo] = useState<ConnectionTroubleshootingInfo | null>(null);
  const [executingActions, setExecutingActions] = useState<Set<string>>(new Set());
  const [completedActions, setCompletedActions] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (visible && platform) {
      loadTroubleshootingInfo();
    }
  }, [visible, platform]);

  const loadTroubleshootingInfo = async () => {
    try {
      setLoading(true);
      const info = await platformConnectionService.getTroubleshootingInfo(platform);
      setTroubleshootingInfo(info);
    } catch (error) {
      Alert.alert('Error', 'Failed to load troubleshooting information');
    } finally {
      setLoading(false);
    }
  };

  const executeAction = async (action: SuggestedAction) => {
    try {
      setExecutingActions(prev => new Set(prev).add(action.id));
      
      const success = await platformConnectionService.executeTroubleshootingAction(platform, action.id);
      
      if (success) {
        setCompletedActions(prev => new Set(prev).add(action.id));
        
        // Reload troubleshooting info to see if issues are resolved
        await loadTroubleshootingInfo();
        
        Alert.alert(
          'Action Completed',
          `${action.title} was executed successfully.`,
          [
            { text: 'OK' }
          ]
        );
        
        // Check if all critical issues are resolved
        if (troubleshootingInfo && troubleshootingInfo.issues.every(issue => 
          issue.severity !== 'critical' && issue.severity !== 'high'
        )) {
          Alert.alert(
            'Issues Resolved',
            'All critical issues have been resolved. The platform connection should now be working properly.',
            [
              { text: 'OK', onPress: () => onFixed(platform) }
            ]
          );
        }
      } else {
        Alert.alert(
          'Action Failed',
          `Failed to execute ${action.title}. Please try again or contact support.`
        );
      }
    } catch (error) {
      Alert.alert(
        'Action Error',
        error instanceof Error ? error.message : 'Failed to execute troubleshooting action'
      );
    } finally {
      setExecutingActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(action.id);
        return newSet;
      });
    }
  };

  const getSeverityColor = (severity: TroubleshootingIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return theme.colors.error;
      case 'high':
        return theme.colors.error;
      case 'medium':
        return theme.colors.warning;
      case 'low':
        return theme.colors.info;
      default:
        return theme.colors.textSecondary;
    }
  };

  const getSeverityIcon = (severity: TroubleshootingIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return '🚨';
      case 'high':
        return '⚠️';
      case 'medium':
        return '⚡';
      case 'low':
        return 'ℹ️';
      default:
        return '❓';
    }
  };

  const getActionIcon = (actionType: SuggestedAction['actionType']) => {
    switch (actionType) {
      case 'reconnect':
        return '🔄';
      case 'refresh_token':
        return '🔑';
      case 'check_permissions':
        return '🔐';
      case 'contact_support':
        return '📞';
      case 'retry_sync':
        return '🔄';
      default:
        return '🛠️';
    }
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

  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
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
    closeButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    closeButtonText: {
      fontSize: 14,
      fontWeight: '500',
      color: theme.colors.text,
    },
    content: {
      flex: 1,
    },
    scrollView: {
      flex: 1,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    loadingText: {
      fontSize: 16,
      color: theme.colors.textSecondary,
      marginTop: 16,
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
    issueItem: {
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
    },
    issueHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 8,
    },
    issueIcon: {
      fontSize: 20,
      marginRight: 12,
    },
    issueTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.colors.text,
      flex: 1,
    },
    severityBadge: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 12,
      alignSelf: 'flex-start',
    },
    severityText: {
      fontSize: 12,
      fontWeight: '500',
      color: theme.colors.surface,
    },
    issueDescription: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      marginBottom: 8,
      lineHeight: 18,
    },
    issueTimestamp: {
      fontSize: 12,
      color: theme.colors.textSecondary,
      fontStyle: 'italic',
    },
    causesContainer: {
      marginTop: 8,
    },
    causesTitle: {
      fontSize: 14,
      fontWeight: '500',
      color: theme.colors.text,
      marginBottom: 4,
    },
    causeItem: {
      fontSize: 12,
      color: theme.colors.textSecondary,
      marginLeft: 16,
      marginBottom: 2,
    },
    actionItem: {
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
    },
    actionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 8,
    },
    actionIcon: {
      fontSize: 20,
      marginRight: 12,
    },
    actionTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.colors.text,
      flex: 1,
    },
    actionBadge: {
      paddingHorizontal: 8,
      paddingVertical: 4,
      borderRadius: 12,
      backgroundColor: theme.colors.info,
    },
    actionBadgeText: {
      fontSize: 12,
      fontWeight: '500',
      color: theme.colors.surface,
    },
    actionDescription: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      marginBottom: 12,
      lineHeight: 18,
    },
    actionFooter: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    actionTime: {
      fontSize: 12,
      color: theme.colors.textSecondary,
    },
    actionButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.colors.primary,
    },
    actionButtonDisabled: {
      backgroundColor: theme.colors.textSecondary,
    },
    actionButtonCompleted: {
      backgroundColor: theme.colors.success,
    },
    actionButtonText: {
      fontSize: 14,
      fontWeight: '500',
      color: theme.colors.surface,
    },
    noIssuesContainer: {
      padding: 32,
      alignItems: 'center',
    },
    noIssuesIcon: {
      fontSize: 48,
      marginBottom: 16,
    },
    noIssuesTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.colors.success,
      marginBottom: 8,
      textAlign: 'center',
    },
    noIssuesText: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      textAlign: 'center',
      lineHeight: 18,
    },
    diagnosticSection: {
      backgroundColor: theme.colors.background,
      margin: 16,
      padding: 16,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    diagnosticTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.colors.text,
      marginBottom: 8,
    },
    diagnosticItem: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginBottom: 4,
    },
    diagnosticLabel: {
      fontSize: 12,
      color: theme.colors.textSecondary,
    },
    diagnosticValue: {
      fontSize: 12,
      color: theme.colors.text,
      fontWeight: '500',
    },
  });

  if (loading) {
    return (
      <Modal visible={visible} animationType="slide" presentationStyle="fullScreen">
        <View style={styles.modal}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Loading Diagnostics...</Text>
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Text style={styles.closeButtonText}>Close</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.loadingContainer}>
            <LoadingSpinner />
            <Text style={styles.loadingText}>Analyzing connection issues...</Text>
          </View>
        </View>
      </Modal>
    );
  }

  if (!troubleshootingInfo) {
    return null;
  }

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="fullScreen">
      <View style={styles.modal}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>
            {getPlatformDisplayName(platform)} Troubleshooting
          </Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollView}>
          {/* Issues Section */}
          {troubleshootingInfo.issues.length > 0 ? (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>
                Detected Issues ({troubleshootingInfo.issues.length})
              </Text>
              
              {troubleshootingInfo.issues.map((issue) => (
                <View key={issue.id} style={styles.issueItem}>
                  <View style={styles.issueHeader}>
                    <Text style={styles.issueIcon}>{getSeverityIcon(issue.severity)}</Text>
                    <Text style={styles.issueTitle}>{issue.title}</Text>
                    <View style={[styles.severityBadge, { backgroundColor: getSeverityColor(issue.severity) }]}>
                      <Text style={styles.severityText}>{issue.severity.toUpperCase()}</Text>
                    </View>
                  </View>
                  
                  <Text style={styles.issueDescription}>{issue.description}</Text>
                  <Text style={styles.issueTimestamp}>
                    Last occurred: {formatTimestamp(issue.lastOccurred)}
                  </Text>
                  
                  {issue.possibleCauses.length > 0 && (
                    <View style={styles.causesContainer}>
                      <Text style={styles.causesTitle}>Possible causes:</Text>
                      {issue.possibleCauses.map((cause, index) => (
                        <Text key={index} style={styles.causeItem}>• {cause}</Text>
                      ))}
                    </View>
                  )}
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.noIssuesContainer}>
              <Text style={styles.noIssuesIcon}>✅</Text>
              <Text style={styles.noIssuesTitle}>No Issues Detected</Text>
              <Text style={styles.noIssuesText}>
                Your {getPlatformDisplayName(platform)} connection appears to be working properly.
              </Text>
            </View>
          )}

          {/* Suggested Actions Section */}
          {troubleshootingInfo.suggestedActions.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>
                Suggested Actions ({troubleshootingInfo.suggestedActions.length})
              </Text>
              
              {troubleshootingInfo.suggestedActions.map((action) => {
                const isExecuting = executingActions.has(action.id);
                const isCompleted = completedActions.has(action.id);
                
                return (
                  <View key={action.id} style={styles.actionItem}>
                    <View style={styles.actionHeader}>
                      <Text style={styles.actionIcon}>{getActionIcon(action.actionType)}</Text>
                      <Text style={styles.actionTitle}>{action.title}</Text>
                      {action.automated && (
                        <View style={styles.actionBadge}>
                          <Text style={styles.actionBadgeText}>AUTO</Text>
                        </View>
                      )}
                    </View>
                    
                    <Text style={styles.actionDescription}>{action.description}</Text>
                    
                    <View style={styles.actionFooter}>
                      {action.estimatedTime && (
                        <Text style={styles.actionTime}>
                          Estimated time: {action.estimatedTime}
                        </Text>
                      )}
                      
                      <TouchableOpacity
                        style={[
                          styles.actionButton,
                          isExecuting && styles.actionButtonDisabled,
                          isCompleted && styles.actionButtonCompleted,
                        ]}
                        onPress={() => executeAction(action)}
                        disabled={isExecuting || isCompleted}
                      >
                        <Text style={styles.actionButtonText}>
                          {isExecuting ? 'Executing...' : isCompleted ? 'Completed' : 'Execute'}
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                );
              })}
            </View>
          )}

          {/* Diagnostic Data Section */}
          <View style={styles.diagnosticSection}>
            <Text style={styles.diagnosticTitle}>Diagnostic Information</Text>
            
            <View style={styles.diagnosticItem}>
              <Text style={styles.diagnosticLabel}>Connection Status:</Text>
              <Text style={styles.diagnosticValue}>
                {troubleshootingInfo.diagnosticData.connectionStatus || 'Unknown'}
              </Text>
            </View>
            
            {troubleshootingInfo.diagnosticData.lastSyncTime && (
              <View style={styles.diagnosticItem}>
                <Text style={styles.diagnosticLabel}>Last Sync:</Text>
                <Text style={styles.diagnosticValue}>
                  {formatTimestamp(new Date(troubleshootingInfo.diagnosticData.lastSyncTime))}
                </Text>
              </View>
            )}
            
            {troubleshootingInfo.diagnosticData.lastError && (
              <View style={styles.diagnosticItem}>
                <Text style={styles.diagnosticLabel}>Last Error:</Text>
                <Text style={[styles.diagnosticValue, { color: theme.colors.error }]}>
                  {troubleshootingInfo.diagnosticData.lastError}
                </Text>
              </View>
            )}
            
            {troubleshootingInfo.diagnosticData.healthMetrics && (
              <>
                <View style={styles.diagnosticItem}>
                  <Text style={styles.diagnosticLabel}>Success Rate:</Text>
                  <Text style={styles.diagnosticValue}>
                    {Math.round((troubleshootingInfo.diagnosticData.healthMetrics.successfulSyncs / 
                     (troubleshootingInfo.diagnosticData.healthMetrics.successfulSyncs + 
                      troubleshootingInfo.diagnosticData.healthMetrics.failedSyncs)) * 100) || 0}%
                  </Text>
                </View>
                
                <View style={styles.diagnosticItem}>
                  <Text style={styles.diagnosticLabel}>Error Count:</Text>
                  <Text style={styles.diagnosticValue}>
                    {troubleshootingInfo.diagnosticData.healthMetrics.errorCount}
                  </Text>
                </View>
              </>
            )}
          </View>
        </ScrollView>
      </View>
    </Modal>
  );
};