import React, { useState } from 'react'
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ScrollView, 
  Switch,
  TextInput,
  Alert,
  Modal,
} from 'react-native'
import { useTheme } from '@/hooks/useTheme'
import { useAuth } from '@/hooks/useAuth'
import Icon from 'react-native-vector-icons/Ionicons'
import { API_CONFIG } from '@/constants/api'

interface PlatformConnection {
  id: string
  name: string
  icon: string
  connected: boolean
  lastSync?: Date
  status: 'connected' | 'disconnected' | 'error' | 'syncing'
}

export function SettingsScreen() {
  const { colors } = useTheme()
  const { logout, user } = useAuth()
  const [showApiConfig, setShowApiConfig] = useState(false)
  const [apiBaseUrl, setApiBaseUrl] = useState(API_CONFIG.baseURL)
  const [notificationsEnabled, setNotificationsEnabled] = useState(true)
  const [biometricEnabled, setBiometricEnabled] = useState(false)
  const [darkModeEnabled, setDarkModeEnabled] = useState(false)

  const [platforms] = useState<PlatformConnection[]>([
    {
      id: 'gmail',
      name: 'Gmail',
      icon: 'mail',
      connected: false,
      status: 'disconnected',
    },
    {
      id: 'slack',
      name: 'Slack',
      icon: 'chatbubbles',
      connected: false,
      status: 'disconnected',
    },
    {
      id: 'discord',
      name: 'Discord',
      icon: 'game-controller',
      connected: false,
      status: 'disconnected',
    },
    {
      id: 'whatsapp',
      name: 'WhatsApp',
      icon: 'logo-whatsapp',
      connected: false,
      status: 'disconnected',
    },
  ])

  const handleApiConfigSave = () => {
    Alert.alert(
      'API Configuration',
      `API Base URL updated to: ${apiBaseUrl}`,
      [
        {
          text: 'OK',
          onPress: () => setShowApiConfig(false),
        },
      ]
    )
  }

  const handlePlatformConnect = (platform: PlatformConnection) => {
    Alert.alert(
      `Connect ${platform.name}`,
      `This will open ${platform.name} authentication in your browser.`,
      [
        {
          text: 'Connect',
          onPress: () => {
            Alert.alert('Demo Mode', `${platform.name} connection would be initiated here.`)
          },
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    )
  }

  const handleExportData = () => {
    Alert.alert(
      'Export Data',
      'Choose export format:',
      [
        {
          text: 'JSON',
          onPress: () => Alert.alert('Demo Mode', 'Data would be exported as JSON'),
        },
        {
          text: 'CSV',
          onPress: () => Alert.alert('Demo Mode', 'Data would be exported as CSV'),
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    )
  }

  const settingsItems = [
    { 
      id: 'profile', 
      title: 'Profile Settings', 
      icon: 'person', 
      onPress: () => Alert.alert('Demo Mode', 'Profile settings would open here'),
    },
    { 
      id: 'notifications', 
      title: 'Notification Preferences', 
      icon: 'notifications', 
      onPress: () => Alert.alert('Demo Mode', 'Notification settings would open here'),
    },
    { 
      id: 'privacy', 
      title: 'Privacy & Security', 
      icon: 'shield', 
      onPress: () => Alert.alert('Demo Mode', 'Privacy settings would open here'),
    },
    { 
      id: 'api', 
      title: 'API Configuration', 
      icon: 'settings', 
      onPress: () => setShowApiConfig(true),
    },
    { 
      id: 'export', 
      title: 'Export Data', 
      icon: 'download', 
      onPress: handleExportData,
    },
    { 
      id: 'about', 
      title: 'About R.E.M.I', 
      icon: 'information-circle', 
      onPress: () => Alert.alert('About R.E.M.I', 'Real-time External Memory Interface\nVersion 1.0.0\n\nA unified communication platform with intelligent contact-based search.'),
    },
  ]

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* User Profile */}
      <View style={[styles.profileSection, { backgroundColor: colors.surface }]}>
        <View style={styles.profileInfo}>
          <View style={[styles.avatar, { backgroundColor: colors.primary }]}>
            <Text style={[styles.avatarText, { color: 'white' }]}>
              {user?.name?.charAt(0).toUpperCase() || 'D'}
            </Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={[styles.userName, { color: colors.text }]}>
              {user?.name || 'Demo User'}
            </Text>
            <Text style={[styles.userEmail, { color: colors.textSecondary }]}>
              {user?.email || 'demo@remi.app'}
            </Text>
            <View style={[styles.demoBadge, { backgroundColor: colors.warning }]}>
              <Text style={styles.demoBadgeText}>Demo Mode</Text>
            </View>
          </View>
        </View>
      </View>

      {/* Quick Settings */}
      <View style={[styles.section, { backgroundColor: colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Quick Settings</Text>
        
        <View style={styles.quickSetting}>
          <View style={styles.quickSettingLeft}>
            <Icon name="notifications" size={20} color={colors.textSecondary} />
            <Text style={[styles.quickSettingText, { color: colors.text }]}>
              Push Notifications
            </Text>
          </View>
          <Switch
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
            trackColor={{ false: colors.border, true: colors.primary }}
          />
        </View>

        <View style={styles.quickSetting}>
          <View style={styles.quickSettingLeft}>
            <Icon name="finger-print" size={20} color={colors.textSecondary} />
            <Text style={[styles.quickSettingText, { color: colors.text }]}>
              Biometric Authentication
            </Text>
          </View>
          <Switch
            value={biometricEnabled}
            onValueChange={setBiometricEnabled}
            trackColor={{ false: colors.border, true: colors.primary }}
          />
        </View>

        <View style={styles.quickSetting}>
          <View style={styles.quickSettingLeft}>
            <Icon name="moon" size={20} color={colors.textSecondary} />
            <Text style={[styles.quickSettingText, { color: colors.text }]}>
              Dark Mode
            </Text>
          </View>
          <Switch
            value={darkModeEnabled}
            onValueChange={setDarkModeEnabled}
            trackColor={{ false: colors.border, true: colors.primary }}
          />
        </View>
      </View>

      {/* Connected Platforms */}
      <View style={[styles.section, { backgroundColor: colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Connected Platforms</Text>
        
        {platforms.map((platform) => (
          <TouchableOpacity
            key={platform.id}
            style={styles.platformItem}
            onPress={() => handlePlatformConnect(platform)}
          >
            <View style={styles.platformLeft}>
              <Icon name={platform.icon} size={24} color={colors.textSecondary} />
              <View style={styles.platformInfo}>
                <Text style={[styles.platformName, { color: colors.text }]}>
                  {platform.name}
                </Text>
                <Text style={[styles.platformStatus, { color: colors.textSecondary }]}>
                  {platform.connected ? 'Connected' : 'Not connected'}
                </Text>
              </View>
            </View>
            <View style={styles.platformRight}>
              <View style={[
                styles.statusIndicator,
                { backgroundColor: platform.connected ? colors.success : colors.border }
              ]} />
              <Icon name="chevron-forward" size={16} color={colors.textSecondary} />
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* Settings Items */}
      <View style={[styles.section, { backgroundColor: colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: colors.text }]}>Settings</Text>
        
        {settingsItems.map((item) => (
          <TouchableOpacity
            key={item.id}
            style={[styles.settingsItem, { borderBottomColor: colors.border }]}
            onPress={item.onPress}
          >
            <View style={styles.settingsItemLeft}>
              <Icon name={item.icon} size={24} color={colors.textSecondary} />
              <Text style={[styles.settingsItemText, { color: colors.text }]}>
                {item.title}
              </Text>
            </View>
            <Icon name="chevron-forward" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        ))}
      </View>

      {/* Logout */}
      <View style={styles.logoutSection}>
        <TouchableOpacity
          style={[styles.logoutButton, { backgroundColor: colors.error }]}
          onPress={logout}
        >
          <Icon name="log-out" size={20} color="white" />
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>

      {/* API Configuration Modal */}
      <Modal
        visible={showApiConfig}
        animationType="slide"
        presentationStyle="pageSheet"
      >
        <View style={[styles.modalContainer, { backgroundColor: colors.background }]}>
          <View style={[styles.modalHeader, { borderBottomColor: colors.border }]}>
            <TouchableOpacity onPress={() => setShowApiConfig(false)}>
              <Text style={[styles.modalCancel, { color: colors.primary }]}>Cancel</Text>
            </TouchableOpacity>
            <Text style={[styles.modalTitle, { color: colors.text }]}>API Configuration</Text>
            <TouchableOpacity onPress={handleApiConfigSave}>
              <Text style={[styles.modalSave, { color: colors.primary }]}>Save</Text>
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.modalContent}>
            <View style={styles.configSection}>
              <Text style={[styles.configLabel, { color: colors.text }]}>API Base URL</Text>
              <TextInput
                style={[styles.configInput, { 
                  backgroundColor: colors.surface, 
                  color: colors.text,
                  borderColor: colors.border,
                }]}
                value={apiBaseUrl}
                onChangeText={setApiBaseUrl}
                placeholder="http://localhost:8000"
                placeholderTextColor={colors.textSecondary}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <Text style={[styles.configHint, { color: colors.textSecondary }]}>
                Enter the base URL for your R.E.M.I API server
              </Text>
            </View>

            <View style={styles.configSection}>
              <Text style={[styles.configLabel, { color: colors.text }]}>Connection Test</Text>
              <TouchableOpacity
                style={[styles.testButton, { backgroundColor: colors.primary }]}
                onPress={() => Alert.alert('Demo Mode', 'Connection test would be performed here')}
              >
                <Icon name="wifi" size={16} color="white" />
                <Text style={styles.testButtonText}>Test Connection</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.configSection}>
              <Text style={[styles.configLabel, { color: colors.text }]}>Current Status</Text>
              <View style={[styles.statusCard, { backgroundColor: colors.surface }]}>
                <View style={styles.statusRow}>
                  <Text style={[styles.statusKey, { color: colors.textSecondary }]}>Status:</Text>
                  <Text style={[styles.statusValue, { color: colors.success }]}>Connected (Demo)</Text>
                </View>
                <View style={styles.statusRow}>
                  <Text style={[styles.statusKey, { color: colors.textSecondary }]}>Version:</Text>
                  <Text style={[styles.statusValue, { color: colors.text }]}>1.0.0</Text>
                </View>
                <View style={styles.statusRow}>
                  <Text style={[styles.statusKey, { color: colors.textSecondary }]}>Last Sync:</Text>
                  <Text style={[styles.statusValue, { color: colors.text }]}>Just now</Text>
                </View>
              </View>
            </View>
          </ScrollView>
        </View>
      </Modal>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  profileSection: {
    margin: 16,
    padding: 20,
    borderRadius: 12,
  },
  profileInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  avatarText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    marginBottom: 8,
  },
  demoBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  demoBadgeText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  section: {
    margin: 16,
    marginTop: 0,
    borderRadius: 12,
    overflow: 'hidden',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    padding: 16,
    paddingBottom: 8,
  },
  quickSetting: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  quickSettingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  quickSettingText: {
    fontSize: 16,
    marginLeft: 12,
  },
  platformItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  platformLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  platformInfo: {
    marginLeft: 12,
    flex: 1,
  },
  platformName: {
    fontSize: 16,
    fontWeight: '500',
  },
  platformStatus: {
    fontSize: 14,
    marginTop: 2,
  },
  platformRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  settingsItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
  },
  settingsItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingsItemText: {
    fontSize: 16,
    marginLeft: 12,
  },
  logoutSection: {
    padding: 16,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
  },
  logoutText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  // Modal styles
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  modalCancel: {
    fontSize: 16,
    fontWeight: '500',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  modalSave: {
    fontSize: 16,
    fontWeight: '600',
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  configSection: {
    marginBottom: 24,
  },
  configLabel: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  configInput: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 8,
  },
  configHint: {
    fontSize: 14,
    lineHeight: 20,
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  testButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  statusCard: {
    padding: 16,
    borderRadius: 8,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusKey: {
    fontSize: 14,
    fontWeight: '500',
  },
  statusValue: {
    fontSize: 14,
    fontWeight: '600',
  },
})