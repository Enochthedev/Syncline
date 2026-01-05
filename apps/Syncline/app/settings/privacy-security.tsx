import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Switch,
    Alert,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';
import { ChangePasswordModal } from '../../components/Settings/ChangePasswordModal';
import { ActiveSessionsModal } from '../../components/Settings/ActiveSessionsModal';

export default function PrivacySecurityScreen() {
    const router = useRouter();
    const [changePasswordVisible, setChangePasswordVisible] = useState(false);
    const [activeSessionsVisible, setActiveSessionsVisible] = useState(false);

    const [settings, setSettings] = useState({
        twoFactorAuth: true,
        biometricLogin: false,
        shareReadReceipts: true,
        shareOnlineStatus: true,
        shareTypingIndicator: true,
        allowContactSync: true,
        dataEncryption: true,
    });

    const toggleSetting = (key: keyof typeof settings) => {
        setSettings({ ...settings, [key]: !settings[key] });
    };

    const renderToggleRow = (
        label: string,
        description: string,
        isEnabled: boolean,
        onToggle: () => void,
        icon: string,
        recommended?: boolean
    ) => (
        <View style={styles.toggleRow}>
            <View style={styles.toggleLeft}>
                <View style={styles.iconContainer}>
                    <Ionicons name={icon as any} size={20} color={theme.colors.primary} />
                </View>
                <View style={styles.toggleInfo}>
                    <View style={styles.labelRow}>
                        <Text style={styles.toggleLabel}>{label}</Text>
                        {recommended && (
                            <View style={styles.recommendedBadge}>
                                <Text style={styles.recommendedText}>Recommended</Text>
                            </View>
                        )}
                    </View>
                    <Text style={styles.toggleDescription}>{description}</Text>
                </View>
            </View>
            <Switch
                value={isEnabled}
                onValueChange={onToggle}
                trackColor={{ false: theme.colors.borderLight, true: theme.colors.primary + '40' }}
                thumbColor={isEnabled ? theme.colors.primary : theme.colors.textTertiary}
            />
        </View>
    );

    const handleChangePassword = () => {
        setChangePasswordVisible(true);
    };

    const handleManageSessions = () => {
        setActiveSessionsVisible(true);
    };

    const handleDownloadData = () => {
        Alert.alert('Download Data', 'Request a download of your personal data');
    };

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    headerShown: true,
                    headerTitle: 'Privacy & Security',
                    headerLeft: () => (
                        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    ),
                }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                {/* Security */}
                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Security</Text>
                    {renderToggleRow(
                        'Two-Factor Authentication',
                        'Add an extra layer of security to your account',
                        settings.twoFactorAuth,
                        () => toggleSetting('twoFactorAuth'),
                        'shield-checkmark',
                        true
                    )}
                    {renderToggleRow(
                        'Biometric Login',
                        'Use Face ID or fingerprint to log in',
                        settings.biometricLogin,
                        () => toggleSetting('biometricLogin'),
                        'finger-print'
                    )}
                    {renderToggleRow(
                        'End-to-End Encryption',
                        'Encrypt all messages and data',
                        settings.dataEncryption,
                        () => toggleSetting('dataEncryption'),
                        'lock-closed',
                        true
                    )}

                    <TouchableOpacity style={styles.actionButton} onPress={handleChangePassword}>
                        <View style={styles.actionLeft}>
                            <Ionicons name="key-outline" size={20} color={theme.colors.text} />
                            <Text style={styles.actionLabel}>Change Password</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.actionButton} onPress={handleManageSessions}>
                        <View style={styles.actionLeft}>
                            <Ionicons name="phone-portrait-outline" size={20} color={theme.colors.text} />
                            <Text style={styles.actionLabel}>Active Sessions</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                </Card>

                {/* Privacy */}
                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Privacy</Text>
                    {renderToggleRow(
                        'Share Read Receipts',
                        'Let others see when you\'ve read their messages',
                        settings.shareReadReceipts,
                        () => toggleSetting('shareReadReceipts'),
                        'checkmark-done'
                    )}
                    {renderToggleRow(
                        'Share Online Status',
                        'Show when you\'re active',
                        settings.shareOnlineStatus,
                        () => toggleSetting('shareOnlineStatus'),
                        'radio-button-on'
                    )}
                    {renderToggleRow(
                        'Share Typing Indicator',
                        'Show when you\'re typing a message',
                        settings.shareTypingIndicator,
                        () => toggleSetting('shareTypingIndicator'),
                        'create'
                    )}
                    {renderToggleRow(
                        'Contact Sync',
                        'Allow Syncline to access your contacts',
                        settings.allowContactSync,
                        () => toggleSetting('allowContactSync'),
                        'people'
                    )}
                </Card>

                {/* Data & Privacy */}
                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Data & Privacy</Text>
                    <TouchableOpacity style={styles.actionButton} onPress={handleDownloadData}>
                        <View style={styles.actionLeft}>
                            <Ionicons name="download-outline" size={20} color={theme.colors.text} />
                            <View>
                                <Text style={styles.actionLabel}>Download My Data</Text>
                                <Text style={styles.actionDescription}>Export all your data</Text>
                            </View>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.actionButton}>
                        <View style={styles.actionLeft}>
                            <Ionicons name="document-text-outline" size={20} color={theme.colors.text} />
                            <Text style={styles.actionLabel}>Privacy Policy</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>

                    <TouchableOpacity style={styles.actionButton}>
                        <View style={styles.actionLeft}>
                            <Ionicons name="document-outline" size={20} color={theme.colors.text} />
                            <Text style={styles.actionLabel}>Terms of Service</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                </Card>

                <View style={{ height: 40 }} />
            </ScrollView>

            {/* Modals */}
            <ChangePasswordModal
                visible={changePasswordVisible}
                onClose={() => setChangePasswordVisible(false)}
            />

            <ActiveSessionsModal
                visible={activeSessionsVisible}
                onClose={() => setActiveSessionsVisible(false)}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    backButton: {
        padding: 8,
        marginLeft: 8,
    },
    content: {
        flex: 1,
    },
    section: {
        margin: 16,
        marginBottom: 0,
        padding: 20,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 20,
    },
    toggleRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    toggleLeft: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        flex: 1,
        marginRight: 12,
    },
    iconContainer: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: theme.colors.primary + '15',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    toggleInfo: {
        flex: 1,
    },
    labelRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 4,
    },
    toggleLabel: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
    },
    recommendedBadge: {
        backgroundColor: theme.colors.successLight,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
    },
    recommendedText: {
        fontSize: 11,
        fontWeight: '600',
        color: theme.colors.success,
    },
    toggleDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        lineHeight: 18,
    },
    actionButton: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    actionLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        flex: 1,
    },
    actionLabel: {
        fontSize: 15,
        fontWeight: '500',
        color: theme.colors.text,
    },
    actionDescription: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
});
