/**
 * Platform Connections Screen
 * 
 * Main screen for managing platform connections with OAuth flows,
 * settings management, and troubleshooting capabilities.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Alert,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTheme } from '../hooks/useTheme';
import { PlatformConnectionsList } from '../components/PlatformConnectionsList';
import { OAuthFlowModal } from '../components/OAuthFlowModal';
import { PlatformSettingsModal } from '../components/PlatformSettingsModal';
import { TroubleshootingModal } from '../components/TroubleshootingModal';

export const PlatformConnectionsScreen: React.FC = () => {
  const { theme } = useTheme();
  const [oauthModalVisible, setOauthModalVisible] = useState(false);
  const [settingsModalVisible, setSettingsModalVisible] = useState(false);
  const [troubleshootingModalVisible, setTroubleshootingModalVisible] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('');
  const [refreshKey, setRefreshKey] = useState(0);

  // Refresh the connections list when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      setRefreshKey(prev => prev + 1);
    }, [])
  );

  const handleNavigateToOAuth = (platform: string) => {
    setSelectedPlatform(platform);
    setOauthModalVisible(true);
  };

  const handleNavigateToSettings = (platform: string) => {
    setSelectedPlatform(platform);
    setSettingsModalVisible(true);
  };

  const handleNavigateToTroubleshooting = (platform: string) => {
    setSelectedPlatform(platform);
    setTroubleshootingModalVisible(true);
  };

  const handleOAuthSuccess = (platform: string) => {
    setOauthModalVisible(false);
    setSelectedPlatform('');
    setRefreshKey(prev => prev + 1);
    
    Alert.alert(
      'Connection Successful',
      `${platform} has been connected successfully! You can now sync your data.`,
      [{ text: 'OK' }]
    );
  };

  const handleOAuthCancel = () => {
    setOauthModalVisible(false);
    setSelectedPlatform('');
  };

  const handleOAuthError = (error: string) => {
    setOauthModalVisible(false);
    setSelectedPlatform('');
    
    Alert.alert(
      'Connection Failed',
      `Failed to connect platform: ${error}`,
      [{ text: 'OK' }]
    );
  };

  const handleSettingsSave = (platform: string) => {
    setSettingsModalVisible(false);
    setSelectedPlatform('');
    setRefreshKey(prev => prev + 1);
  };

  const handleSettingsClose = () => {
    setSettingsModalVisible(false);
    setSelectedPlatform('');
  };

  const handleTroubleshootingFixed = (platform: string) => {
    setTroubleshootingModalVisible(false);
    setSelectedPlatform('');
    setRefreshKey(prev => prev + 1);
    
    Alert.alert(
      'Issues Resolved',
      `Connection issues for ${platform} have been resolved.`,
      [{ text: 'OK' }]
    );
  };

  const handleTroubleshootingClose = () => {
    setTroubleshootingModalVisible(false);
    setSelectedPlatform('');
  };

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
  });

  return (
    <View style={styles.container}>
      <PlatformConnectionsList
        key={refreshKey}
        onNavigateToSettings={handleNavigateToSettings}
        onNavigateToTroubleshooting={handleNavigateToTroubleshooting}
        onNavigateToOAuth={handleNavigateToOAuth}
      />

      <OAuthFlowModal
        visible={oauthModalVisible}
        platform={selectedPlatform}
        onSuccess={handleOAuthSuccess}
        onCancel={handleOAuthCancel}
        onError={handleOAuthError}
      />

      <PlatformSettingsModal
        visible={settingsModalVisible}
        platform={selectedPlatform}
        onClose={handleSettingsClose}
        onSave={handleSettingsSave}
      />

      <TroubleshootingModal
        visible={troubleshootingModalVisible}
        platform={selectedPlatform}
        onClose={handleTroubleshootingClose}
        onFixed={handleTroubleshootingFixed}
      />
    </View>
  );
};