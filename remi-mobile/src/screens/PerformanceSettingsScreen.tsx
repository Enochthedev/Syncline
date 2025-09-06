import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  TouchableOpacity,
  Alert,
  Share,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { usePerformance } from '../contexts/PerformanceContext';
import { useTheme } from '../hooks/useTheme';
import { useRenderPerformance } from '../hooks/usePerformanceMonitoring';

interface SettingRowProps {
  title: string;
  description?: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  disabled?: boolean;
}

const SettingRow: React.FC<SettingRowProps> = ({
  title,
  description,
  value,
  onValueChange,
  disabled = false,
}) => {
  const { theme } = useTheme();

  return (
    <View style={[styles.settingRow, { borderBottomColor: theme.colors.border }]}>
      <View style={styles.settingInfo}>
        <Text style={[styles.settingTitle, { color: theme.colors.text }]}>
          {title}
        </Text>
        {description && (
          <Text style={[styles.settingDescription, { color: theme.colors.textSecondary }]}>
            {description}
          </Text>
        )}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        trackColor={{
          false: theme.colors.border,
          true: theme.colors.primary,
        }}
        thumbColor={value ? theme.colors.white : theme.colors.textSecondary}
      />
    </View>
  );
};

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  status?: 'good' | 'warning' | 'error';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, status = 'good' }) => {
  const { theme } = useTheme();

  const getStatusColor = () => {
    switch (status) {
      case 'warning':
        return theme.colors.warning;
      case 'error':
        return theme.colors.error;
      default:
        return theme.colors.success;
    }
  };

  return (
    <View style={[styles.metricCard, { backgroundColor: theme.colors.surface }]}>
      <Text style={[styles.metricTitle, { color: theme.colors.textSecondary }]}>
        {title}
      </Text>
      <View style={styles.metricValue}>
        <Text style={[styles.metricNumber, { color: getStatusColor() }]}>
          {value}
        </Text>
        {unit && (
          <Text style={[styles.metricUnit, { color: theme.colors.textSecondary }]}>
            {unit}
          </Text>
        )}
      </View>
    </View>
  );
};

export const PerformanceSettingsScreen: React.FC = () => {
  const { theme } = useTheme();
  const {
    metrics,
    memoryStats,
    batteryStats,
    powerSavingMode,
    deviceCapabilities,
    currentProfile,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    forceMemoryCleanup,
    setBatteryOptimization,
    forcePowerSavingMode,
    updatePerformanceProfile,
    exportPerformanceData,
    getPerformanceRecommendations,
  } = usePerformance();

  useRenderPerformance('PerformanceSettingsScreen');

  const [settings, setSettings] = useState({
    performanceMonitoring: isMonitoring,
    memoryOptimization: currentProfile?.enableMemoryOptimization ?? true,
    batteryOptimization: currentProfile?.enableBatteryOptimization ?? true,
    imageOptimization: currentProfile?.enableImageOptimization ?? true,
    virtualization: currentProfile?.enableVirtualization ?? true,
  });

  const [recommendations, setRecommendations] = useState<string[]>([]);

  useEffect(() => {
    setRecommendations(getPerformanceRecommendations());
  }, [getPerformanceRecommendations]);

  const handleSettingChange = (key: keyof typeof settings, value: boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));

    switch (key) {
      case 'performanceMonitoring':
        if (value) {
          startMonitoring();
        } else {
          stopMonitoring();
        }
        break;

      case 'memoryOptimization':
        updatePerformanceProfile({ enableMemoryOptimization: value });
        break;

      case 'batteryOptimization':
        setBatteryOptimization(value);
        updatePerformanceProfile({ enableBatteryOptimization: value });
        break;

      case 'imageOptimization':
        updatePerformanceProfile({ enableImageOptimization: value });
        break;

      case 'virtualization':
        updatePerformanceProfile({ enableVirtualization: value });
        break;
    }
  };

  const handleMemoryCleanup = async () => {
    try {
      await forceMemoryCleanup();
      Alert.alert('Success', 'Memory cleanup completed successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to cleanup memory');
    }
  };

  const handleExportData = async () => {
    try {
      const data = await exportPerformanceData();
      await Share.share({
        message: data,
        title: 'Performance Data Export',
      });
    } catch (error) {
      Alert.alert('Error', 'Failed to export performance data');
    }
  };

  const handlePowerSavingMode = () => {
    Alert.alert(
      'Power Saving Mode',
      'Select power saving level:',
      [
        { text: 'None', onPress: () => forcePowerSavingMode('none') },
        { text: 'Light', onPress: () => forcePowerSavingMode('light') },
        { text: 'Moderate', onPress: () => forcePowerSavingMode('moderate') },
        { text: 'Aggressive', onPress: () => forcePowerSavingMode('aggressive') },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const getMemoryStatus = (): 'good' | 'warning' | 'error' => {
    if (!memoryStats) return 'good';
    if (memoryStats.memoryUsagePercentage > 0.9) return 'error';
    if (memoryStats.memoryUsagePercentage > 0.7) return 'warning';
    return 'good';
  };

  const getBatteryStatus = (): 'good' | 'warning' | 'error' => {
    if (!batteryStats) return 'good';
    if (batteryStats.batteryLevel < 0.1) return 'error';
    if (batteryStats.batteryLevel < 0.2) return 'warning';
    return 'good';
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Performance Metrics */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Performance Metrics
          </Text>
          
          <View style={styles.metricsGrid}>
            {memoryStats && (
              <MetricCard
                title="Memory Usage"
                value={Math.round(memoryStats.memoryUsagePercentage * 100)}
                unit="%"
                status={getMemoryStatus()}
              />
            )}
            
            {batteryStats && (
              <MetricCard
                title="Battery Level"
                value={Math.round(batteryStats.batteryLevel * 100)}
                unit="%"
                status={getBatteryStatus()}
              />
            )}
            
            {metrics && (
              <>
                <MetricCard
                  title="App Launch"
                  value={Math.round(metrics.appLaunchTime)}
                  unit="ms"
                  status={metrics.appLaunchTime > 3000 ? 'warning' : 'good'}
                />
                
                <MetricCard
                  title="Search Response"
                  value={Math.round(metrics.searchResponseTime)}
                  unit="ms"
                  status={metrics.searchResponseTime > 1000 ? 'warning' : 'good'}
                />
              </>
            )}
          </View>
        </View>

        {/* Device Information */}
        {deviceCapabilities && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Device Information
            </Text>
            
            <View style={[styles.deviceInfo, { backgroundColor: theme.colors.surface }]}>
              <Text style={[styles.deviceInfoText, { color: theme.colors.text }]}>
                Device Type: {deviceCapabilities.isLowEndDevice ? 'Low-End' : 'High-End'}
              </Text>
              <Text style={[styles.deviceInfoText, { color: theme.colors.text }]}>
                Total Memory: {Math.round(deviceCapabilities.totalMemory / (1024 * 1024 * 1024))}GB
              </Text>
              <Text style={[styles.deviceInfoText, { color: theme.colors.text }]}>
                CPU Cores: {deviceCapabilities.cpuCount}
              </Text>
              <Text style={[styles.deviceInfoText, { color: theme.colors.text }]}>
                Profile: {currentProfile?.name || 'Unknown'}
              </Text>
            </View>
          </View>
        )}

        {/* Performance Settings */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Performance Settings
          </Text>
          
          <View style={[styles.settingsContainer, { backgroundColor: theme.colors.surface }]}>
            <SettingRow
              title="Performance Monitoring"
              description="Track app performance metrics and bottlenecks"
              value={settings.performanceMonitoring}
              onValueChange={(value) => handleSettingChange('performanceMonitoring', value)}
            />
            
            <SettingRow
              title="Memory Optimization"
              description="Automatically cleanup unused memory and cache"
              value={settings.memoryOptimization}
              onValueChange={(value) => handleSettingChange('memoryOptimization', value)}
            />
            
            <SettingRow
              title="Battery Optimization"
              description="Reduce power consumption when battery is low"
              value={settings.batteryOptimization}
              onValueChange={(value) => handleSettingChange('batteryOptimization', value)}
            />
            
            <SettingRow
              title="Image Optimization"
              description="Compress and cache images for better performance"
              value={settings.imageOptimization}
              onValueChange={(value) => handleSettingChange('imageOptimization', value)}
            />
            
            <SettingRow
              title="List Virtualization"
              description="Optimize large lists for better scrolling performance"
              value={settings.virtualization}
              onValueChange={(value) => handleSettingChange('virtualization', value)}
            />
          </View>
        </View>

        {/* Power Saving Mode */}
        {powerSavingMode && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Power Saving Mode
            </Text>
            
            <View style={[styles.powerSavingInfo, { backgroundColor: theme.colors.surface }]}>
              <Text style={[styles.powerSavingLevel, { color: theme.colors.text }]}>
                Current Level: {powerSavingMode.level.charAt(0).toUpperCase() + powerSavingMode.level.slice(1)}
              </Text>
              <Text style={[styles.powerSavingDescription, { color: theme.colors.textSecondary }]}>
                Sync Interval: {Math.round(powerSavingMode.syncInterval / 1000)}s
              </Text>
              <Text style={[styles.powerSavingDescription, { color: theme.colors.textSecondary }]}>
                Background Processing: {powerSavingMode.backgroundProcessingEnabled ? 'Enabled' : 'Disabled'}
              </Text>
              <Text style={[styles.powerSavingDescription, { color: theme.colors.textSecondary }]}>
                Image Quality: {powerSavingMode.imageQuality}
              </Text>
            </View>
          </View>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Recommendations
            </Text>
            
            <View style={[styles.recommendationsContainer, { backgroundColor: theme.colors.surface }]}>
              {recommendations.map((recommendation, index) => (
                <Text
                  key={index}
                  style={[styles.recommendationText, { color: theme.colors.text }]}
                >
                  • {recommendation}
                </Text>
              ))}
            </View>
          </View>
        )}

        {/* Actions */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Actions
          </Text>
          
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.primary }]}
              onPress={handleMemoryCleanup}
            >
              <Text style={[styles.actionButtonText, { color: theme.colors.white }]}>
                Clean Memory
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.secondary }]}
              onPress={handlePowerSavingMode}
            >
              <Text style={[styles.actionButtonText, { color: theme.colors.white }]}>
                Power Saving
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.info }]}
              onPress={handleExportData}
            >
              <Text style={[styles.actionButtonText, { color: theme.colors.white }]}>
                Export Data
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  metricCard: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  metricTitle: {
    fontSize: 12,
    fontWeight: '500',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  metricValue: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  metricNumber: {
    fontSize: 24,
    fontWeight: '700',
  },
  metricUnit: {
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 4,
  },
  deviceInfo: {
    padding: 16,
    borderRadius: 12,
  },
  deviceInfoText: {
    fontSize: 14,
    marginBottom: 4,
  },
  settingsContainer: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  settingInfo: {
    flex: 1,
    marginRight: 16,
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 2,
  },
  settingDescription: {
    fontSize: 12,
    lineHeight: 16,
  },
  powerSavingInfo: {
    padding: 16,
    borderRadius: 12,
  },
  powerSavingLevel: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  powerSavingDescription: {
    fontSize: 14,
    marginBottom: 4,
  },
  recommendationsContainer: {
    padding: 16,
    borderRadius: 12,
  },
  recommendationText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 8,
  },
  actionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
});

export default PerformanceSettingsScreen;