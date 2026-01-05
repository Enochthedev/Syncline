import React from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Card } from '../Card/Card';

interface BriefingModalProps {
    visible: boolean;
    onClose: () => void;
    summary: string;
}

export const BriefingModal: React.FC<BriefingModalProps> = ({
    visible,
    onClose,
    summary,
}) => {
    // Helper to render rich text summary
    const renderSummary = (text: string) => {
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return (
            <Text style={styles.summaryText}>
                {parts.map((part, index) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                        return (
                            <Text key={index} style={styles.highlightText}>
                                {part.slice(2, -2)}
                            </Text>
                        );
                    }
                    return <Text key={index}>{part}</Text>;
                })}
            </Text>
        );
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.modalContainer}>
                    {/* Header */}
                    <LinearGradient
                        colors={[theme.colors.primary, theme.colors.primaryDark]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={styles.header}
                    >
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <Ionicons name="close" size={28} color="white" />
                        </TouchableOpacity>

                        <View style={styles.headerIcon}>
                            <Ionicons name="sparkles" size={32} color="white" />
                        </View>
                        <Text style={styles.headerTitle}>Daily Briefing</Text>
                        <Text style={styles.headerSubtitle}>Tuesday, Nov 17</Text>
                    </LinearGradient>

                    <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                        {/* Audio Player Placeholder */}
                        <Card style={styles.playerCard}>
                            <TouchableOpacity style={styles.playButton}>
                                <Ionicons name="play" size={32} color="white" style={{ marginLeft: 4 }} />
                            </TouchableOpacity>
                            <View style={styles.playerInfo}>
                                <Text style={styles.playerTitle}>Listen to summary</Text>
                                <Text style={styles.playerDuration}>2:15 • AI Generated</Text>
                            </View>
                        </Card>

                        {/* Full Summary */}
                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Executive Summary</Text>
                            {renderSummary(summary)}
                        </View>

                        {/* Key Takeaways */}
                        <View style={styles.section}>
                            <Text style={styles.sectionTitle}>Key Takeaways</Text>
                            <View style={styles.takeawayItem}>
                                <Ionicons name="alert-circle-outline" size={20} color={theme.colors.warning} />
                                <Text style={styles.takeawayText}>Q4 Designs need approval by EOD.</Text>
                            </View>
                            <View style={styles.takeawayItem}>
                                <Ionicons name="cash-outline" size={20} color={theme.colors.success} />
                                <Text style={styles.takeawayText}>Budget review meeting at 2 PM.</Text>
                            </View>
                            <View style={styles.takeawayItem}>
                                <Ionicons name="people-outline" size={20} color={theme.colors.info} />
                                <Text style={styles.takeawayText}>Team sync scheduled for tomorrow.</Text>
                            </View>
                        </View>
                    </ScrollView>
                </View>
            </View>
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: theme.colors.overlay,
        justifyContent: 'flex-end',
    },
    modalContainer: {
        backgroundColor: theme.colors.background,
        borderTopLeftRadius: 32,
        borderTopRightRadius: 32,
        height: '90%',
        overflow: 'hidden',
    },
    header: {
        padding: 24,
        paddingTop: 32,
        alignItems: 'center',
    },
    closeButton: {
        position: 'absolute',
        top: 24,
        right: 24,
        zIndex: 10,
        padding: 4,
    },
    headerIcon: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    headerSubtitle: {
        fontSize: 16,
        color: 'rgba(255,255,255,0.8)',
    },
    content: {
        padding: 24,
    },
    playerCard: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: theme.colors.surface,
        borderRadius: 20,
        marginBottom: 32,
        gap: 16,
    },
    playButton: {
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
        ...theme.shadows.md,
    },
    playerInfo: {
        flex: 1,
    },
    playerTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 4,
    },
    playerDuration: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    section: {
        marginBottom: 32,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 16,
    },
    summaryText: {
        fontSize: 16,
        lineHeight: 26,
        color: theme.colors.textSecondary,
    },
    highlightText: {
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    takeawayItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    takeawayText: {
        fontSize: 15,
        color: theme.colors.text,
        flex: 1,
    },
});
