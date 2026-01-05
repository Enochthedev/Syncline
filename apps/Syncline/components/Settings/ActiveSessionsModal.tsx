import React from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';

interface Session {
    id: string;
    device: string;
    deviceType: 'phone' | 'tablet' | 'desktop';
    location: string;
    lastActive: string;
    isCurrent: boolean;
}

interface ActiveSessionsModalProps {
    visible: boolean;
    onClose: () => void;
}

const MOCK_SESSIONS: Session[] = [
    {
        id: '1',
        device: 'iPhone 14 Pro',
        deviceType: 'phone',
        location: 'San Francisco, CA',
        lastActive: 'Active now',
        isCurrent: true,
    },
    {
        id: '2',
        device: 'MacBook Pro',
        deviceType: 'desktop',
        location: 'San Francisco, CA',
        lastActive: '2 hours ago',
        isCurrent: false,
    },
    {
        id: '3',
        device: 'iPad Air',
        deviceType: 'tablet',
        location: 'New York, NY',
        lastActive: '2 days ago',
        isCurrent: false,
    },
];

export const ActiveSessionsModal: React.FC<ActiveSessionsModalProps> = ({ visible, onClose }) => {
    const getDeviceIcon = (deviceType: Session['deviceType']) => {
        switch (deviceType) {
            case 'phone':
                return 'phone-portrait';
            case 'tablet':
                return 'tablet-portrait';
            case 'desktop':
                return 'desktop';
        }
    };

    const handleTerminateSession = (sessionId: string) => {
        Alert.alert(
            'Terminate Session',
            'Are you sure you want to sign out this device?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Sign Out',
                    style: 'destructive',
                    onPress: () => {
                        // TODO: Call API to terminate session
                        Alert.alert('Success', 'Session terminated');
                    },
                },
            ]
        );
    };

    const handleTerminateAll = () => {
        Alert.alert(
            'Terminate All Sessions',
            'This will sign you out of all devices except this one. Are you sure?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Sign Out All',
                    style: 'destructive',
                    onPress: () => {
                        // TODO: Call API to terminate all sessions
                        Alert.alert('Success', 'All other sessions terminated');
                    },
                },
            ]
        );
    };

    return (
        <Modal
            visible={visible}
            animationType="slide"
            transparent
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.container}>
                    <View style={styles.header}>
                        <Text style={styles.title}>Active Sessions</Text>
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <Ionicons name="close" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    </View>

                    <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                        <Text style={styles.description}>
                            Manage devices where you're currently signed in
                        </Text>

                        {MOCK_SESSIONS.map((session) => (
                            <View key={session.id} style={styles.sessionCard}>
                                <View style={styles.sessionLeft}>
                                    <View style={[
                                        styles.deviceIcon,
                                        session.isCurrent && styles.deviceIconCurrent
                                    ]}>
                                        <Ionicons
                                            name={getDeviceIcon(session.deviceType) as any}
                                            size={24}
                                            color={session.isCurrent ? theme.colors.primary : theme.colors.textSecondary}
                                        />
                                    </View>
                                    <View style={styles.sessionInfo}>
                                        <View style={styles.deviceRow}>
                                            <Text style={styles.deviceName}>{session.device}</Text>
                                            {session.isCurrent && (
                                                <View style={styles.currentBadge}>
                                                    <Text style={styles.currentText}>Current</Text>
                                                </View>
                                            )}
                                        </View>
                                        <Text style={styles.location}>{session.location}</Text>
                                        <Text style={styles.lastActive}>{session.lastActive}</Text>
                                    </View>
                                </View>
                                {!session.isCurrent && (
                                    <TouchableOpacity
                                        onPress={() => handleTerminateSession(session.id)}
                                        style={styles.terminateButton}
                                    >
                                        <Ionicons name="log-out-outline" size={20} color={theme.colors.error} />
                                    </TouchableOpacity>
                                )}
                            </View>
                        ))}

                        <TouchableOpacity style={styles.terminateAllButton} onPress={handleTerminateAll}>
                            <Ionicons name="log-out-outline" size={20} color={theme.colors.error} />
                            <Text style={styles.terminateAllText}>Sign Out All Other Devices</Text>
                        </TouchableOpacity>

                        <View style={{ height: 20 }} />
                    </ScrollView>
                </View>
            </View>
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        justifyContent: 'flex-end',
    },
    container: {
        backgroundColor: 'white',
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        paddingBottom: 40,
        maxHeight: '80%',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 20,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    title: {
        fontSize: 20,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    closeButton: {
        padding: 4,
    },
    content: {
        padding: 20,
    },
    description: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginBottom: 20,
    },
    sessionCard: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        marginBottom: 12,
    },
    sessionLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
    },
    deviceIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: theme.colors.borderLight,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    deviceIconCurrent: {
        backgroundColor: theme.colors.primary + '20',
    },
    sessionInfo: {
        flex: 1,
    },
    deviceRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 4,
    },
    deviceName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    currentBadge: {
        backgroundColor: theme.colors.successLight,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
    },
    currentText: {
        fontSize: 11,
        fontWeight: '600',
        color: theme.colors.success,
    },
    location: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 2,
    },
    lastActive: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    terminateButton: {
        padding: 8,
    },
    terminateAllButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: theme.colors.errorLight,
        paddingVertical: 16,
        borderRadius: 12,
        marginTop: 8,
    },
    terminateAllText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.error,
    },
});
