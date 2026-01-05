/**
 * User Settings Panel (Section 4.11.9, Figure 4.14)
 * 
 * Settings interface for configuring MESH behavior and preferences.
 * Includes platform connections, notifications, privacy, and AI preferences.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Switch,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_SETTINGS } from '../src/data/dummyData';

type TabId = 'platforms' | 'notifications' | 'privacy' | 'ai';

const TABS: { id: TabId; label: string; icon: string }[] = [
    { id: 'platforms', label: 'Connections', icon: 'link' },
    { id: 'notifications', label: 'Notifications', icon: 'notifications' },
    { id: 'privacy', label: 'Privacy', icon: 'shield-checkmark' },
    { id: 'ai', label: 'AI Preferences', icon: 'sparkles' },
];

const PLATFORM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    gmail: { icon: 'mail', color: '#EA4335', label: 'Gmail' },
    slack: { icon: 'logo-slack', color: '#4A154B', label: 'Slack' },
    discord: { icon: 'logo-discord', color: '#5865F2', label: 'Discord' },
};

export default function SettingsDemoScreen() {
    const [activeTab, setActiveTab] = useState<TabId>('platforms');
    const settings = DUMMY_SETTINGS;

    // Toggle states for switches
    const [commitmentReminders, setCommitmentReminders] = useState(settings.notifications.commitmentReminders);
    const [followUpSuggestions, setFollowUpSuggestions] = useState(settings.notifications.followUpSuggestions);
    const [reconnectionPrompts, setReconnectionPrompts] = useState(settings.notifications.reconnectionPrompts);
    const [inAppNotifications, setInAppNotifications] = useState(settings.notifications.deliveryChannels.inApp);
    const [emailNotifications, setEmailNotifications] = useState(settings.notifications.deliveryChannels.email);
    const [pushNotifications, setPushNotifications] = useState(settings.notifications.deliveryChannels.push);
    const [entityExtraction, setEntityExtraction] = useState(settings.privacy.aiProcessing.entityExtraction);
    const [summaryGeneration, setSummaryGeneration] = useState(settings.privacy.aiProcessing.summaryGeneration);
    const [commitmentTracking, setCommitmentTracking] = useState(settings.privacy.aiProcessing.commitmentTracking);
    const [dataSharing, setDataSharing] = useState(settings.privacy.aiProcessing.dataSharing);
    const [microSummaries, setMicroSummaries] = useState(settings.aiPreferences.microSummaries);
    const [threadSummaries, setThreadSummaries] = useState(settings.aiPreferences.threadSummaries);
    const [dailySummaries, setDailySummaries] = useState(settings.aiPreferences.dailySummaries);

    const formatLastSync = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMins = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minutes ago`;
        return `${Math.floor(diffMins / 60)} hours ago`;
    };

    const renderPlatformsTab = () => (
        <View style={styles.tabContent}>
            <Text style={styles.sectionDescription}>
                Manage your connected platforms and sync settings
            </Text>

            {Object.entries(settings.platformSync).map(([platformKey, platformSettings]) => {
                const config = PLATFORM_CONFIG[platformKey];
                if (!config) return null;

                return (
                    <Card key={platformKey} style={styles.platformCard}>
                        <View style={styles.platformHeader}>
                            <View style={[styles.platformIcon, { backgroundColor: config.color + '20' }]}>
                                <Ionicons name={config.icon as any} size={20} color={config.color} />
                            </View>
                            <View style={styles.platformInfo}>
                                <Text style={styles.platformName}>{config.label}</Text>
                                <Text style={styles.platformStatus}>
                                    Last sync: {formatLastSync(platformSettings.lastSync)}
                                </Text>
                            </View>
                        </View>

                        <View style={styles.platformSettings}>
                            <View style={styles.settingRow}>
                                <Text style={styles.settingLabel}>Sync Frequency</Text>
                                <View style={styles.settingValue}>
                                    <Text style={styles.settingValueText}>
                                        {platformSettings.syncFrequency === 'realtime' ? 'Real-time' : platformSettings.syncFrequency}
                                    </Text>
                                    <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                                </View>
                            </View>

                            {platformSettings.folders && (
                                <View style={styles.settingRow}>
                                    <Text style={styles.settingLabel}>Folders</Text>
                                    <View style={styles.settingValue}>
                                        <Text style={styles.settingValueText}>
                                            {platformSettings.folders.join(', ')}
                                        </Text>
                                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                                    </View>
                                </View>
                            )}

                            {platformSettings.channels && (
                                <View style={styles.settingRow}>
                                    <Text style={styles.settingLabel}>Channels</Text>
                                    <View style={styles.settingValue}>
                                        <Text style={styles.settingValueText}>
                                            {platformSettings.channels === 'all' ? 'All joined channels' : platformSettings.channels}
                                        </Text>
                                    </View>
                                </View>
                            )}

                            {platformSettings.servers && (
                                <View style={styles.settingRow}>
                                    <Text style={styles.settingLabel}>Servers</Text>
                                    <View style={styles.settingValue}>
                                        <Text style={styles.settingValueText}>
                                            {platformSettings.servers} connected
                                        </Text>
                                    </View>
                                </View>
                            )}
                        </View>

                        <View style={styles.platformActions}>
                            <TouchableOpacity style={styles.actionButton}>
                                <Ionicons name="sync" size={16} color={theme.colors.primary} />
                                <Text style={styles.actionButtonText}>Reconnect</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={[styles.actionButton, styles.disconnectAction]}>
                                <Ionicons name="unlink" size={16} color={theme.colors.error} />
                                <Text style={styles.disconnectButtonText}>Disconnect</Text>
                            </TouchableOpacity>
                        </View>
                    </Card>
                );
            })}
        </View>
    );

    const renderNotificationsTab = () => (
        <View style={styles.tabContent}>
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Nudge Preferences</Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Commitment reminders</Text>
                        <Text style={styles.switchDescription}>24 hours before due</Text>
                    </View>
                    <Switch
                        value={commitmentReminders}
                        onValueChange={setCommitmentReminders}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Follow-up suggestions</Text>
                        <Text style={styles.switchDescription}>After 3 days of no response</Text>
                    </View>
                    <Switch
                        value={followUpSuggestions}
                        onValueChange={setFollowUpSuggestions}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Reconnection prompts</Text>
                        <Text style={styles.switchDescription}>After 30 days of inactivity</Text>
                    </View>
                    <Switch
                        value={reconnectionPrompts}
                        onValueChange={setReconnectionPrompts}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Delivery Channels</Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>In-app notifications</Text>
                    </View>
                    <Switch
                        value={inAppNotifications}
                        onValueChange={setInAppNotifications}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Email notifications</Text>
                    </View>
                    <Switch
                        value={emailNotifications}
                        onValueChange={setEmailNotifications}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Push notifications (mobile)</Text>
                    </View>
                    <Switch
                        value={pushNotifications}
                        onValueChange={setPushNotifications}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>
            </Card>
        </View>
    );

    const renderPrivacyTab = () => (
        <View style={styles.tabContent}>
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Data Retention</Text>

                <TouchableOpacity style={styles.selectRow}>
                    <Text style={styles.selectLabel}>Keep messages for</Text>
                    <View style={styles.selectValue}>
                        <Text style={styles.selectValueText}>Indefinitely</Text>
                        <Ionicons name="chevron-down" size={16} color={theme.colors.textSecondary} />
                    </View>
                </TouchableOpacity>

                <TouchableOpacity style={styles.selectRow}>
                    <Text style={styles.selectLabel}>Auto-delete after</Text>
                    <View style={styles.selectValue}>
                        <Text style={styles.selectValueText}>Never</Text>
                        <Ionicons name="chevron-down" size={16} color={theme.colors.textSecondary} />
                    </View>
                </TouchableOpacity>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>AI Processing</Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Enable entity extraction</Text>
                        <Text style={styles.switchDescription}>Detect people, dates, topics</Text>
                    </View>
                    <Switch
                        value={entityExtraction}
                        onValueChange={setEntityExtraction}
                        trackColor={{ true: theme.colors.primary }}
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
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Track commitments</Text>
                        <Text style={styles.switchDescription}>Detect obligations and deadlines</Text>
                    </View>
                    <Switch
                        value={commitmentTracking}
                        onValueChange={setCommitmentTracking}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Share data for model improvement</Text>
                        <Text style={styles.switchDescription}>Help improve MESH AI</Text>
                    </View>
                    <Switch
                        value={dataSharing}
                        onValueChange={setDataSharing}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Data Export</Text>
                <TouchableOpacity style={styles.exportButton}>
                    <Ionicons name="download" size={18} color={theme.colors.primary} />
                    <Text style={styles.exportButtonText}>Export All Data</Text>
                </TouchableOpacity>
            </Card>
        </View>
    );

    const renderAITab = () => (
        <View style={styles.tabContent}>
            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Summary Generation</Text>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Micro-summaries</Text>
                        <Text style={styles.switchDescription}>Brief summaries for each message</Text>
                    </View>
                    <Switch
                        value={microSummaries}
                        onValueChange={setMicroSummaries}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Thread summaries</Text>
                        <Text style={styles.switchDescription}>For threads with 3+ messages</Text>
                    </View>
                    <Switch
                        value={threadSummaries}
                        onValueChange={setThreadSummaries}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>

                <View style={styles.switchRow}>
                    <View style={styles.switchInfo}>
                        <Text style={styles.switchLabel}>Daily summaries</Text>
                        <Text style={styles.switchDescription}>Generated at 6:00 PM</Text>
                    </View>
                    <Switch
                        value={dailySummaries}
                        onValueChange={setDailySummaries}
                        trackColor={{ true: theme.colors.primary }}
                    />
                </View>
            </Card>

            <Card style={styles.settingsCard}>
                <Text style={styles.cardTitle}>Search Preferences</Text>

                <TouchableOpacity style={styles.selectRow}>
                    <Text style={styles.selectLabel}>Default search mode</Text>
                    <View style={styles.selectValue}>
                        <Text style={styles.selectValueText}>Hybrid</Text>
                        <Ionicons name="chevron-down" size={16} color={theme.colors.textSecondary} />
                    </View>
                </TouchableOpacity>

                <TouchableOpacity style={styles.selectRow}>
                    <Text style={styles.selectLabel}>Results per page</Text>
                    <View style={styles.selectValue}>
                        <Text style={styles.selectValueText}>20</Text>
                        <Ionicons name="chevron-down" size={16} color={theme.colors.textSecondary} />
                    </View>
                </TouchableOpacity>
            </Card>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Settings</Text>
            </View>

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
            <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
                {activeTab === 'platforms' && renderPlatformsTab()}
                {activeTab === 'notifications' && renderNotificationsTab()}
                {activeTab === 'privacy' && renderPrivacyTab()}
                {activeTab === 'ai' && renderAITab()}
                <View style={{ height: 100 }} />
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        padding: 20,
        paddingTop: 60,
        backgroundColor: theme.colors.background,
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    tabBar: {
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    tabBarContent: {
        paddingHorizontal: 16,
        gap: 8,
    },
    tab: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 2,
        borderBottomColor: 'transparent',
    },
    tabActive: {
        borderBottomColor: theme.colors.primary,
    },
    tabText: {
        fontSize: 14,
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
    platformCard: {
        marginBottom: 16,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    platformHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
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
    platformStatus: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    platformSettings: {
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        paddingTop: 12,
    },
    settingRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 10,
    },
    settingLabel: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    settingValue: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    settingValueText: {
        fontSize: 14,
        color: theme.colors.text,
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
    settingsCard: {
        marginBottom: 16,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    cardTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
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
    selectRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 14,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    selectLabel: {
        fontSize: 15,
        color: theme.colors.text,
    },
    selectValue: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    selectValueText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    exportButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 14,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
    },
    exportButtonText: {
        fontSize: 15,
        fontWeight: '500',
        color: theme.colors.primary,
    },
});
