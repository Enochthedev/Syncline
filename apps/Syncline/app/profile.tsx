/**
 * Enhanced Profile & Settings Screen
 * 
 * Combines user profile with comprehensive settings including:
 * - Platform Connections
 * - Notifications (Nudges)
 * - Privacy & AI Settings
 * - Account management
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Switch,
    Alert,
    ActivityIndicator,
    RefreshControl,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { useAuth } from '../src/contexts/AuthContext';
import { useTheme } from '../src/contexts/ThemeContext';
import { connectionsAPI, ConnectionResponse } from '../src/api/endpoints/connections';
import { LanguageModal } from '../components/Settings/LanguageModal';

type TabId = 'account' | 'connections' | 'notifications' | 'privacy';

const TABS: { id: TabId; label: string; icon: string }[] = [
    { id: 'account', label: 'Account', icon: 'person' },
    { id: 'connections', label: 'Platforms', icon: 'link' },
    { id: 'notifications', label: 'Nudges', icon: 'notifications' },
    { id: 'privacy', label: 'Privacy & AI', icon: 'shield-checkmark' },
];

const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', label: 'WhatsApp' },
    gmail: { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    google_chat: { icon: 'chatbubbles', color: '#00AC47', label: 'Google Chat' },
    slack: { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    discord: { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
    linkedin: { icon: 'logo-linkedin', color: '#0A66C2', label: 'LinkedIn' },
    twitter: { icon: 'logo-twitter', color: '#000000', label: 'X' },
    telegram: { icon: 'paper-plane', color: '#0088CC', label: 'Telegram' },
};

export default function ProfileScreen() {
    const insets = useSafeAreaInsets();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { themeMode, isDark, setThemeMode } = useTheme();

    const [activeTab, setActiveTab] = useState<TabId>('account');
    const [connections, setConnections] = useState<ConnectionResponse[]>([]);
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [languageModalVisible, setLanguageModalVisible] = useState(false);
    const [selectedLanguage, setSelectedLanguage] = useState('en');

    // Notification preferences (local state - would be synced to backend)
    const [commitmentReminders, setCommitmentReminders] = useState(true);
    const [followUpSuggestions, setFollowUpSuggestions] = useState(true);
    const [reconnectionPrompts, setReconnectionPrompts] = useState(true);
    const [pushNotifications, setPushNotifications] = useState(true);

    // AI preferences
    const [entityExtraction, setEntityExtraction] = useState(true);
    const [summaryGeneration, setSummaryGeneration] = useState(true);
    const [commitmentTracking, setCommitmentTracking] = useState(true);
    const [dailySummaries, setDailySummaries] = useState(true);

    useEffect(() => {
        if (activeTab === 'connections') {
            fetchConnections();
        }
    }, [activeTab]);

    const fetchConnections = async () => {
        try {
            setLoading(true);
            if (user?.id) {
                const data = await connectionsAPI.listConnections(user.id);
                setConnections(data.connections || []);
            }
        } catch (error) {
            console.error('Failed to fetch connections:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const onRefresh = useCallback(() => {
        setRefreshing(true);
        fetchConnections();
    }, []);

    const handleDisconnect = async (connectionId: string) => {
        Alert.alert('Disconnect', 'Are you sure you want to disconnect this platform?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Disconnect',
                style: 'destructive',
                onPress: async () => {
                    try {
                        await connectionsAPI.disconnect(connectionId);
                        fetchConnections();
                        Alert.alert('Success', 'Platform disconnected');
                    } catch (error) {
                        Alert.alert('Error', 'Failed to disconnect');
                    }
                }
            }
        ]);
    };

    const handleSync = async (connectionId: string) => {
        try {
            await connectionsAPI.checkHealth(connectionId);
            Alert.alert('Sync Status', 'Connection is healthy and syncing.');
            fetchConnections();
        } catch (error) {
            Alert.alert('Sync Error', 'Connection seems to be down. Please reconnect.');
        }
    };

    const handleLogout = async () => {
        Alert.alert('Logout', 'Are you sure you want to log out?', [
            { text: 'Cancel', style: 'cancel' },
            {
                text: 'Logout',
                style: 'destructive',
                onPress: async () => {
                    try {
                        await logout();
                    } catch (error) {
                        console.error('Logout error:', error);
                        Alert.alert('Error', 'Failed to logout properly');
                    }
                }
            },
        ]);
    };

    const handleLanguageChange = (code: string) => {
        setSelectedLanguage(code);
    };

    const getLanguageName = (code: string) => {
        const languages: { [key: string]: string } = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
        };
        return languages[code] || 'English';
    };

    const formatLastSync = (timestamp?: string) => {
        if (!timestamp) return 'Never';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMins = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return `${Math.floor(diffMins / 1440)}d ago`;
    };

    const getStatusColor = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'active': return '#10B981';
            case 'pending': return '#F59E0B';
            case 'error': return '#EF4444';
            default: return theme.colors.textSecondary;
        }
    };

    const userInitial = user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U';
    const userName = user?.full_name || 'User';
    const userEmail = user?.email || 'user@example.com';

    // Account Tab
    const renderAccountTab = () => (
        <View style={styles.tabContent}>
            {/* Profile Header */}
            <Card style={styles.profileCard}>
                <View style={styles.profileHeader}>
                    <View style={styles.avatarContainer}>
                        <View style={styles.avatar}>
                            <Text style={styles.avatarText}>{userInitial}</Text>
                        </View>
                        <TouchableOpacity style={styles.editBadge}>
                            <Ionicons name="camera" size={14} color="white" />
                        </TouchableOpacity>
                    </View>
                    <View style={styles.profileInfo}>
                        <Text style={styles.profileName}>{userName}</Text>
                        <Text style={styles.profileEmail}>{userEmail}</Text>
                    </View>
                    <TouchableOpacity
                        style={styles.editProfileButton}
                        onPress={() => router.push('/settings/personal-info')}
                    >
                        <Text style={styles.editProfileText}>Edit</Text>
                    </TouchableOpacity>
                </View>
            </Card>

            {/* Appearance */}
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Appearance</Text>
                <View style={styles.themeSelector}>
                    {[
                        { id: 'light', icon: 'sunny', label: 'Light' },
                        { id: 'dark', icon: 'moon', label: 'Dark' },
                        { id: 'system', icon: 'phone-portrait', label: 'System' },
                    ].map((option) => (
                        <TouchableOpacity
                            key={option.id}
                            style={[
                                styles.themeOption,
                                themeMode === option.id && styles.themeOptionActive,
                            ]}
                            onPress={() => setThemeMode(option.id as any)}
                        >
                            <Ionicons
                                name={option.icon as any}
                                size={18}
                                color={themeMode === option.id ? theme.colors.primary : theme.colors.textSecondary}
                            />
                            <Text
                                style={[
                                    styles.themeOptionText,
                                    themeMode === option.id && styles.themeOptionTextActive,
                                ]}
                            >
                                {option.label}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>
            </Card>

            {/* Language & Region */}
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Language & Region</Text>
                <TouchableOpacity
                    style={styles.settingRow}
                    onPress={() => setLanguageModalVisible(true)}
                >
                    <View style={styles.settingInfo}>
                        <Ionicons name="language-outline" size={20} color={theme.colors.textSecondary} />
                        <Text style={styles.settingLabel}>Language</Text>
                    </View>
                    <View style={styles.settingValue}>
                        <Text style={styles.settingValueText}>{getLanguageName(selectedLanguage)}</Text>
                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                    </View>
                </TouchableOpacity>
            </Card>

            {/* Support */}
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Support</Text>
                <TouchableOpacity
                    style={styles.settingRow}
                    onPress={() => router.push('/settings/help-center')}
                >
                    <View style={styles.settingInfo}>
                        <Ionicons name="help-circle-outline" size={20} color={theme.colors.textSecondary} />
                        <Text style={styles.settingLabel}>Help Center</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                </TouchableOpacity>
                <TouchableOpacity style={styles.settingRow}>
                    <View style={styles.settingInfo}>
                        <Ionicons name="star-outline" size={20} color={theme.colors.textSecondary} />
                        <Text style={styles.settingLabel}>Rate App</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                </TouchableOpacity>
            </Card>

            {/* Logout */}
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
                <Ionicons name="log-out-outline" size={20} color={theme.colors.error} />
                <Text style={styles.logoutText}>Log Out</Text>
            </TouchableOpacity>

            <Text style={styles.version}>MESH v1.0.0</Text>
        </View>
    );

    // Connections Tab
    const renderConnectionsTab = () => (
        <View style={styles.tabContent}>
            <Text style={styles.sectionDescription}>
                Manage your connected platforms and sync settings
            </Text>

            {loading ? (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.colors.primary} />
                </View>
            ) : connections.length === 0 ? (
                <Card style={styles.emptyCard}>
                    <Ionicons name="link-outline" size={48} color={theme.colors.textTertiary} />
                    <Text style={styles.emptyTitle}>No Platforms Connected</Text>
                    <Text style={styles.emptySubtitle}>
                        Connect your messaging platforms to unify your communications
                    </Text>
                    <TouchableOpacity
                        style={styles.connectButton}
                        onPress={() => router.push('/(tabs)/connections')}
                    >
                        <Ionicons name="add" size={20} color="white" />
                        <Text style={styles.connectButtonText}>Connect Platform</Text>
                    </TouchableOpacity>
                </Card>
            ) : (
                connections.map((connection) => {
                    const config = PLATFORM_CONFIG[connection.platform.toLowerCase()] || {
                        icon: 'globe',
                        color: theme.colors.primary,
                        label: connection.platform,
                    };

                    return (
                        <Card key={connection.id} style={styles.platformCard}>
                            <View style={styles.platformHeader}>
                                <View style={[styles.platformIcon, { backgroundColor: config.color + '20' }]}>
                                    <Ionicons name={config.icon as any} size={22} color={config.color} />
                                </View>
                                <View style={styles.platformInfo}>
                                    <Text style={styles.platformName}>{config.label}</Text>
                                    <View style={styles.statusRow}>
                                        <View style={[styles.statusDot, { backgroundColor: getStatusColor(connection.status) }]} />
                                        <Text style={styles.platformStatus}>
                                            {connection.status} • Synced {formatLastSync(connection.last_sync_at)}
                                        </Text>
                                    </View>
                                </View>
                            </View>

                            <View style={styles.platformActions}>
                                <TouchableOpacity
                                    style={styles.actionButton}
                                    onPress={() => handleSync(connection.id)}
                                >
                                    <Ionicons name="sync" size={16} color={theme.colors.primary} />
                                    <Text style={styles.actionButtonText}>Sync Now</Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    style={[styles.actionButton, styles.disconnectAction]}
                                    onPress={() => handleDisconnect(connection.id)}
                                >
                                    <Ionicons name="unlink" size={16} color={theme.colors.error} />
                                    <Text style={styles.disconnectButtonText}>Disconnect</Text>
                                </TouchableOpacity>
                            </View>
                        </Card>
                    );
                })
            )}

            {connections.length > 0 && (
                <TouchableOpacity
                    style={styles.addPlatformButton}
                    onPress={() => router.push('/(tabs)/connections')}
                >
                    <Ionicons name="add-circle-outline" size={20} color={theme.colors.primary} />
                    <Text style={styles.addPlatformText}>Add Another Platform</Text>
                </TouchableOpacity>
            )}
        </View>
    );

    // Notifications Tab
    const renderNotificationsTab = () => (
        <View style={styles.tabContent}>
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Nudge Preferences</Text>
                <Text style={styles.cardDescription}>
                    Control when MESH should proactively remind you
                </Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Commitment reminders</Text>
                        <Text style={styles.switchDescription}>24 hours before due date</Text>
                    </View>
                    <Switch
                        value={commitmentReminders}
                        onValueChange={setCommitmentReminders}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Follow-up suggestions</Text>
                        <Text style={styles.switchDescription}>When messages go unanswered for 3+ days</Text>
                    </View>
                    <Switch
                        value={followUpSuggestions}
                        onValueChange={setFollowUpSuggestions}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Reconnection prompts</Text>
                        <Text style={styles.switchDescription}>For contacts inactive 30+ days</Text>
                    </View>
                    <Switch
                        value={reconnectionPrompts}
                        onValueChange={setReconnectionPrompts}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Delivery</Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Push notifications</Text>
                        <Text style={styles.switchDescription}>Receive alerts on your device</Text>
                    </View>
                    <Switch
                        value={pushNotifications}
                        onValueChange={setPushNotifications}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>
            </Card>
        </View>
    );

    // Privacy Tab
    const renderPrivacyTab = () => (
        <View style={styles.tabContent}>
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>AI Processing</Text>
                <Text style={styles.cardDescription}>
                    Configure how MESH analyzes your messages
                </Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Entity extraction</Text>
                        <Text style={styles.switchDescription}>Detect people, dates, and topics</Text>
                    </View>
                    <Switch
                        value={entityExtraction}
                        onValueChange={setEntityExtraction}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Generate summaries</Text>
                        <Text style={styles.switchDescription}>AI-powered message summaries</Text>
                    </View>
                    <Switch
                        value={summaryGeneration}
                        onValueChange={setSummaryGeneration}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Track commitments</Text>
                        <Text style={styles.switchDescription}>Detect deadlines and obligations</Text>
                    </View>
                    <Switch
                        value={commitmentTracking}
                        onValueChange={setCommitmentTracking}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Daily summaries</Text>
                        <Text style={styles.switchDescription}>Generated each evening</Text>
                    </View>
                    <Switch
                        value={dailySummaries}
                        onValueChange={setDailySummaries}
                        trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                    />
                </View>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Data Management</Text>

                <TouchableOpacity
                    style={styles.settingRow}
                    onPress={() => router.push('/settings/privacy-security')}
                >
                    <View style={styles.settingInfo}>
                        <Ionicons name="lock-closed-outline" size={20} color={theme.colors.textSecondary} />
                        <Text style={styles.settingLabel}>Privacy & Security</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                </TouchableOpacity>

                <TouchableOpacity style={styles.exportButton}>
                    <Ionicons name="download-outline" size={18} color={theme.colors.primary} />
                    <Text style={styles.exportButtonText}>Export All Data</Text>
                </TouchableOpacity>
            </Card>
        </View>
    );

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    title: 'Settings',
                    headerShown: true,
                    headerStyle: { backgroundColor: theme.colors.background },
                    headerShadowVisible: false,
                }}
            />

            {/* Tab Bar */}
            <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.tabBar}
                contentContainerStyle={styles.tabBarContent}
            >
                {TABS.map((tab) => (
                    <TouchableOpacity
                        key={tab.id}
                        style={[styles.tab, activeTab === tab.id && styles.tabActive]}
                        onPress={() => setActiveTab(tab.id)}
                    >
                        <Ionicons
                            name={tab.icon as any}
                            size={18}
                            color={activeTab === tab.id ? theme.colors.primary : theme.colors.textSecondary}
                        />
                        <Text style={[
                            styles.tabText,
                            activeTab === tab.id && styles.tabTextActive
                        ]}>
                            {tab.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {/* Tab Content */}
            <ScrollView
                style={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                refreshControl={
                    activeTab === 'connections' ? (
                        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                    ) : undefined
                }
            >
                {activeTab === 'account' && renderAccountTab()}
                {activeTab === 'connections' && renderConnectionsTab()}
                {activeTab === 'notifications' && renderNotificationsTab()}
                {activeTab === 'privacy' && renderPrivacyTab()}
                <View style={{ height: insets.bottom + 40 }} />
            </ScrollView>

            {/* Language Modal */}
            <LanguageModal
                visible={languageModalVisible}
                onClose={() => setLanguageModalVisible(false)}
                selectedLanguage={selectedLanguage}
                onSelectLanguage={handleLanguageChange}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    tabBar: {
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        maxHeight: 48,
    },
    tabBarContent: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 12,
    },
    tab: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 14,
        paddingVertical: 12,
        borderBottomWidth: 2,
        borderBottomColor: 'transparent',
    },
    tabActive: {
        borderBottomColor: theme.colors.primary,
    },
    tabText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    tabTextActive: {
        color: theme.colors.primary,
    },
    scrollContent: {
        flex: 1,
    },
    tabContent: {
        padding: 16,
    },
    sectionDescription: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginBottom: 16,
    },
    loadingContainer: {
        padding: 40,
        alignItems: 'center',
    },
    profileCard: {
        marginBottom: 16,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    profileHeader: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatarContainer: {
        position: 'relative',
        marginRight: 14,
    },
    avatar: {
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: theme.colors.primaryLighter,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.primary,
    },
    editBadge: {
        position: 'absolute',
        bottom: -2,
        right: -2,
        backgroundColor: theme.colors.primary,
        width: 24,
        height: 24,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: theme.colors.background,
    },
    profileInfo: {
        flex: 1,
    },
    profileName: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
    },
    profileEmail: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    editProfileButton: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
    },
    editProfileText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.primary,
    },
    settingsCard: {
        marginBottom: 16,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    cardTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 4,
    },
    cardDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 16,
    },
    themeSelector: {
        flexDirection: 'row',
        gap: 8,
        marginTop: 12,
    },
    themeOption: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        paddingVertical: 10,
        borderRadius: 10,
        backgroundColor: theme.colors.surface,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    themeOptionActive: {
        backgroundColor: theme.colors.primary + '15',
        borderColor: theme.colors.primary,
    },
    themeOptionText: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    themeOptionTextActive: {
        color: theme.colors.primary,
    },
    settingRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 14,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    settingInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    settingLabel: {
        fontSize: 15,
        color: theme.colors.text,
    },
    settingValue: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    settingValueText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    switchRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    switchInfo: {
        flex: 1,
        marginRight: 16,
    },
    switchLabel: {
        fontSize: 15,
        color: theme.colors.text,
    },
    switchDescription: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    emptyCard: {
        padding: 32,
        alignItems: 'center',
        backgroundColor: theme.colors.background,
    },
    emptyTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
    },
    emptySubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginTop: 8,
        lineHeight: 20,
    },
    connectButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 20,
        paddingVertical: 12,
        borderRadius: 12,
        marginTop: 20,
    },
    connectButtonText: {
        fontSize: 15,
        fontWeight: '600',
        color: 'white',
    },
    platformCard: {
        marginBottom: 12,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    platformHeader: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    platformIcon: {
        width: 44,
        height: 44,
        borderRadius: 22,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformInfo: {
        flex: 1,
        marginLeft: 12,
    },
    platformName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 4,
    },
    statusDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        marginRight: 6,
    },
    platformStatus: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    platformActions: {
        flexDirection: 'row',
        gap: 12,
        marginTop: 16,
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    actionButton: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        paddingVertical: 10,
        backgroundColor: theme.colors.surface,
        borderRadius: 10,
    },
    actionButtonText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.primary,
    },
    disconnectAction: {
        backgroundColor: '#FEE2E2',
    },
    disconnectButtonText: {
        fontSize: 13,
        fontWeight: '500',
        color: theme.colors.error,
    },
    addPlatformButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 14,
        backgroundColor: theme.colors.background,
        borderRadius: 12,
        marginTop: 8,
    },
    addPlatformText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.primary,
    },
    exportButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 14,
        backgroundColor: theme.colors.surface,
        borderRadius: 10,
        marginTop: 16,
    },
    exportButtonText: {
        fontSize: 14,
        fontWeight: '500',
        color: theme.colors.primary,
    },
    logoutButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: theme.colors.background,
        padding: 16,
        borderRadius: 12,
        marginTop: 8,
    },
    logoutText: {
        color: theme.colors.error,
        fontSize: 16,
        fontWeight: '600',
    },
    version: {
        textAlign: 'center',
        color: theme.colors.textTertiary,
        fontSize: 12,
        marginTop: 16,
    },
});
