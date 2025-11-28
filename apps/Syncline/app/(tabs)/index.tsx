import React from 'react';
import { StyleSheet, View, Text, ScrollView, TouchableOpacity, Dimensions, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Card } from '../../components/Card/Card';
import { Badge } from '../../components/Badge/Badge';
import { theme } from '../../src/theme';

const { width } = Dimensions.get('window');

// Mock summary data
const SUMMARIES = [
    {
        id: '1',
        title: 'Team Meeting Notes',
        platform: 'Slack',
        gradient: ['#4A154B', '#611f69'],
        icon: 'logo-slack',
        messageCount: 24,
        summary: 'Q4 roadmap discussion with Sarah and the team. Budget allocation approved, timeline adjustments needed for new features.',
        timestamp: '2h ago',
        participants: 3,
        unread: 5,
    },
    {
        id: '2',
        title: 'Client Approval',
        platform: 'Gmail',
        gradient: ['#EA4335', '#C5221F'],
        icon: 'mail',
        messageCount: 12,
        summary: 'Mockups approved! Development starts Monday. Design team delivering final assets by end of week.',
        timestamp: '5h ago',
        participants: 2,
        unread: 0,
    },
    {
        id: '3',
        title: 'Budget Review',
        platform: 'Discord',
        gradient: ['#5865F2', '#404EBC'],
        icon: 'logo-discord',
        messageCount: 18,
        summary: 'Monthly expenses reviewed. Server costs up 15%. Planning optimization sprint for next week.',
        timestamp: '1d ago',
        participants: 4,
        unread: 2,
    },
];

export default function HomeScreen() {
    const router = useRouter();

    return (
        <View style={styles.container}>
            {/* Gradient Background Header */}
            <LinearGradient
                colors={[theme.colors.primary, theme.colors.primaryDark]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.gradientHeader}
            >
                <View style={styles.headerContent}>
                    <View style={styles.headerTop}>
                        <View>
                            <Text style={styles.greeting}>Welcome back</Text>
                            <Text style={styles.headerSubtitle}>Your daily briefing is ready</Text>
                        </View>
                        <TouchableOpacity style={styles.avatarButton}>
                            <View style={styles.avatar}>
                                <Text style={styles.avatarText}>U</Text>
                            </View>
                        </TouchableOpacity>
                    </View>

                    {/* Stats Dashboard */}
                    <View style={styles.statsContainer}>
                        <View style={styles.statItem}>
                            <View style={[styles.statIconContainer, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
                                <Ionicons name="mail-unread-outline" size={20} color="white" />
                            </View>
                            <View>
                                <Text style={styles.statValue}>24</Text>
                                <Text style={styles.statLabel}>Unread</Text>
                            </View>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.statItem}>
                            <View style={[styles.statIconContainer, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
                                <Ionicons name="chatbubbles-outline" size={20} color="white" />
                            </View>
                            <View>
                                <Text style={styles.statValue}>12</Text>
                                <Text style={styles.statLabel}>Threads</Text>
                            </View>
                        </View>
                        <View style={styles.statDivider} />
                        <View style={styles.statItem}>
                            <View style={[styles.statIconContainer, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
                                <Ionicons name="time-outline" size={20} color="white" />
                            </View>
                            <View>
                                <Text style={styles.statValue}>54</Text>
                                <Text style={styles.statLabel}>Today</Text>
                            </View>
                        </View>
                    </View>
                </View>
            </LinearGradient>

            <ScrollView
                style={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                contentContainerStyle={styles.scrollContainer}
            >
                {/* Quick Actions */}
                <View style={styles.actionsSection}>
                    <TouchableOpacity
                        style={styles.actionButton}
                        onPress={() => router.push('/connections')}
                        activeOpacity={0.8}
                    >
                        <LinearGradient
                            colors={[theme.colors.primary, theme.colors.primaryLight]}
                            style={styles.actionGradient}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 1 }}
                        >
                            <Ionicons name="link" size={24} color="white" />
                            <Text style={styles.actionText}>Connect Apps</Text>
                        </LinearGradient>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={styles.actionButton}
                        onPress={() => router.push('/search')}
                        activeOpacity={0.8}
                    >
                        <LinearGradient
                            colors={[theme.colors.secondary, theme.colors.secondaryLight]}
                            style={styles.actionGradient}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 1 }}
                        >
                            <Ionicons name="search" size={24} color="white" />
                            <Text style={styles.actionText}>AI Search</Text>
                        </LinearGradient>
                    </TouchableOpacity>
                </View>

                {/* AI Summaries Section */}
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <Text style={styles.sectionTitle}>AI Summaries</Text>
                        <TouchableOpacity>
                            <Ionicons name="options-outline" size={24} color={theme.colors.textSecondary} />
                        </TouchableOpacity>
                    </View>

                    {SUMMARIES.map((item) => (
                        <TouchableOpacity key={item.id} activeOpacity={0.9} style={{ marginBottom: 16 }}>
                            <Card padding="none" shadow="sm" style={styles.summaryCard}>
                                <View style={styles.summaryInner}>
                                    <View style={styles.summaryHeader}>
                                        <View style={[styles.platformIcon, { backgroundColor: item.gradient[0] }]}>
                                            <Ionicons name={item.icon as any} size={20} color="white" />
                                        </View>
                                        <View style={styles.summaryTitleContainer}>
                                            <View style={styles.titleRow}>
                                                <Text style={styles.summaryTitle}>{item.title}</Text>
                                                <Text style={styles.timestamp}>{item.timestamp}</Text>
                                            </View>
                                            <View style={styles.summaryMeta}>
                                                <Text style={styles.platformName}>{item.platform}</Text>
                                                {item.unread > 0 && (
                                                    <View style={styles.unreadBadge}>
                                                        <Text style={styles.unreadText}>{item.unread} new</Text>
                                                    </View>
                                                )}
                                            </View>
                                        </View>
                                    </View>

                                    <Text style={styles.summaryContent} numberOfLines={2}>
                                        {item.summary}
                                    </Text>

                                    <View style={styles.summaryFooter}>
                                        <View style={styles.footerItem}>
                                            <Ionicons name="people-outline" size={14} color={theme.colors.textTertiary} />
                                            <Text style={styles.footerText}>{item.participants}</Text>
                                        </View>
                                        <View style={styles.footerItem}>
                                            <Ionicons name="chatbubble-outline" size={14} color={theme.colors.textTertiary} />
                                            <Text style={styles.footerText}>{item.messageCount}</Text>
                                        </View>
                                        <View style={{ flex: 1 }} />
                                        <TouchableOpacity style={styles.readMoreButton}>
                                            <Text style={styles.readMoreText}>Read Summary</Text>
                                            <Ionicons name="arrow-forward" size={14} color={theme.colors.primary} />
                                        </TouchableOpacity>
                                    </View>
                                </View>
                            </Card>
                        </TouchableOpacity>
                    ))}
                </View>

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
    gradientHeader: {
        paddingTop: Platform.OS === 'ios' ? 60 : 40,
        paddingBottom: 30,
        borderBottomLeftRadius: 32,
        borderBottomRightRadius: 32,
    },
    headerContent: {
        paddingHorizontal: 24,
    },
    headerTop: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
    },
    greeting: {
        fontSize: 28,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    headerSubtitle: {
        fontSize: 14,
        color: 'rgba(255, 255, 255, 0.9)',
    },
    avatarButton: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
        padding: 2,
    },
    avatar: {
        flex: 1,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        color: theme.colors.primary,
        fontSize: 18,
        fontWeight: 'bold',
    },
    statsContainer: {
        flexDirection: 'row',
        backgroundColor: 'rgba(255, 255, 255, 0.15)',
        borderRadius: 20,
        padding: 16,
        justifyContent: 'space-between',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    statItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        flex: 1,
        justifyContent: 'center',
    },
    statIconContainer: {
        width: 36,
        height: 36,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
    },
    statValue: {
        fontSize: 20,
        fontWeight: 'bold',
        color: 'white',
        lineHeight: 24,
    },
    statLabel: {
        fontSize: 11,
        color: 'rgba(255, 255, 255, 0.8)',
    },
    statDivider: {
        width: 1,
        height: 32,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
    },
    scrollContent: {
        flex: 1,
    },
    scrollContainer: {
        paddingTop: 24,
        paddingBottom: 40,
    },
    actionsSection: {
        flexDirection: 'row',
        paddingHorizontal: 24,
        gap: 16,
        marginBottom: 32,
    },
    actionButton: {
        flex: 1,
        borderRadius: 20,
        ...theme.shadows.sm,
    },
    actionGradient: {
        padding: 20,
        borderRadius: 20,
        alignItems: 'center',
        flexDirection: 'row',
        gap: 12,
        justifyContent: 'center',
    },
    actionText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
    section: {
        paddingHorizontal: 24,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    sectionTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    summaryCard: {
        borderRadius: 20,
        backgroundColor: 'white',
        borderWidth: 1,
        borderColor: theme.colors.borderLight,
    },
    summaryInner: {
        padding: 20,
    },
    summaryHeader: {
        flexDirection: 'row',
        marginBottom: 16,
    },
    platformIcon: {
        width: 48,
        height: 48,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 16,
    },
    summaryTitleContainer: {
        flex: 1,
        justifyContent: 'center',
    },
    titleRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 4,
    },
    summaryTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
    },
    summaryMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    platformName: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
    unreadBadge: {
        backgroundColor: theme.colors.errorLight,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
    },
    unreadText: {
        color: theme.colors.error,
        fontSize: 11,
        fontWeight: '600',
    },
    summaryContent: {
        fontSize: 15,
        lineHeight: 24,
        color: theme.colors.textSecondary,
        marginBottom: 16,
    },
    summaryFooter: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.borderLight,
    },
    footerItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginRight: 16,
    },
    footerText: {
        fontSize: 13,
        color: theme.colors.textTertiary,
        fontWeight: '500',
    },
    timestamp: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    readMoreButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    readMoreText: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.primary,
    },
});
