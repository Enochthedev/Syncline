import React, { useState } from 'react';
import { StyleSheet, View, Text, ScrollView, TouchableOpacity, Dimensions } from 'react-native';
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
        icon: '💬',
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
        icon: '📧',
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
        icon: '💰',
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
                style={styles.gradientHeader}
            >
                <View style={styles.header}>
                    <View>
                        <Text style={styles.greeting}>Good Morning 👋</Text>
                        <Text style={styles.headerSubtitle}>Here's what happened today</Text>
                    </View>
                    <TouchableOpacity style={styles.avatarButton}>
                        <LinearGradient
                            colors={['rgba(255,255,255,0.3)', 'rgba(255,255,255,0.1)']}
                            style={styles.avatar}
                        >
                            <Text style={styles.avatarText}>U</Text>
                        </LinearGradient>
                    </TouchableOpacity>
                </View>

                {/* Quick Stats - Inside gradient */}
                <View style={styles.statsRow}>
                    <View style={styles.statItem}>
                        <Text style={styles.statValue}>24</Text>
                        <Text style={styles.statLabel}>Unread</Text>
                    </View>
                    <View style={styles.statDivider} />
                    <View style={styles.statItem}>
                        <Text style={styles.statValue}>12</Text>
                        <Text style={styles.statLabel}>Threads</Text>
                    </View>
                    <View style={styles.statDivider} />
                    <View style={styles.statItem}>
                        <Text style={styles.statValue}>54</Text>
                        <Text style={styles.statLabel}>Today</Text>
                    </View>
                </View>
            </LinearGradient>

            <ScrollView
                style={styles.scrollContent}
                showsVerticalScrollIndicator={false}
                contentContainerStyle={styles.scrollContainer}
            >
                {/* AI Summaries Section */}
                <View style={styles.section}>
                    <View style={styles.sectionHeader}>
                        <View>
                            <Text style={styles.sectionTitle}>AI Summaries</Text>
                            <Text style={styles.sectionSubtitle}>Powered by your messages</Text>
                        </View>
                        <TouchableOpacity>
                            <Ionicons name="add-circle" size={28} color={theme.colors.primary} />
                        </TouchableOpacity>
                    </View>

                    {SUMMARIES.map((item, index) => (
                        <TouchableOpacity key={item.id} activeOpacity={0.9} style={{ marginBottom: 16 }}>
                            <Card padding="none" shadow="md">
                                <LinearGradient
                                    colors={item.gradient}
                                    start={{ x: 0, y: 0 }}
                                    end={{ x: 1, y: 0 }}
                                    style={styles.summaryGradientBorder}
                                >
                                    <View style={styles.summaryInner}>
                                        <View style={styles.summaryHeader}>
                                            <View style={styles.summaryIconContainer}>
                                                <Text style={styles.summaryIcon}>{item.icon}</Text>
                                            </View>
                                            <View style={styles.summaryTitleContainer}>
                                                <Text style={styles.summaryTitle}>{item.title}</Text>
                                                <View style={styles.summaryMeta}>
                                                    <Badge variant="secondary" size="sm">{item.platform}</Badge>
                                                    {item.unread > 0 && (
                                                        <View style={styles.unreadBadge}>
                                                            <Text style={styles.unreadText}>{item.unread}</Text>
                                                        </View>
                                                    )}
                                                </View>
                                            </View>
                                        </View>

                                        <Text style={styles.summaryContent} numberOfLines={2}>
                                            {item.summary}
                                        </Text>

                                        <View style={styles.summaryFooter}>
                                            <View style={styles.footerLeft}>
                                                <Ionicons name="people-outline" size={14} color={theme.colors.textTertiary} />
                                                <Text style={styles.footerText}>{item.participants} people</Text>
                                                <Text style={styles.footerDot}>•</Text>
                                                <Ionicons name="chatbubble-outline" size={14} color={theme.colors.textTertiary} />
                                                <Text style={styles.footerText}>{item.messageCount}</Text>
                                            </View>
                                            <Text style={styles.timestamp}>{item.timestamp}</Text>
                                        </View>
                                    </View>
                                </LinearGradient>
                            </Card>
                        </TouchableOpacity>
                    ))}
                </View>

                {/* Quick Actions */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Quick Actions</Text>

                    <View style={styles.actionsGrid}>
                        <TouchableOpacity
                            style={styles.actionCard}
                            onPress={() => router.push('/connections')}
                            activeOpacity={0.8}
                        >
                            <LinearGradient
                                colors={[theme.colors.primary, theme.colors.primaryLight]}
                                style={styles.actionGradient}
                            >
                                <Ionicons name="link-outline" size={32} color="white" />
                                <Text style={styles.actionText}>Connect Apps</Text>
                            </LinearGradient>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.actionCard}
                            onPress={() => router.push('/search')}
                            activeOpacity={0.8}
                        >
                            <LinearGradient
                                colors={[theme.colors.secondary, theme.colors.secondaryLight]}
                                style={styles.actionGradient}
                            >
                                <Ionicons name="search-outline" size={32} color="white" />
                                <Text style={styles.actionText}>AI Search</Text>
                            </LinearGradient>
                        </TouchableOpacity>
                    </View>
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
        paddingTop: 60,
        paddingBottom: 24,
        borderBottomLeftRadius: 32,
        borderBottomRightRadius: 32,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 24,
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
        color: 'rgba(255, 255, 255, 0.8)',
    },
    avatarButton: {
        width: 48,
        height: 48,
    },
    avatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: 'rgba(255, 255, 255, 0.3)',
    },
    avatarText: {
        color: 'white',
        fontSize: 20,
        fontWeight: 'bold',
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        paddingHorizontal: 24,
        paddingVertical: 20,
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        marginHorizontal: 24,
        borderRadius: 16,
    },
    statItem: {
        alignItems: 'center',
    },
    statValue: {
        fontSize: 32,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    statLabel: {
        fontSize: 12,
        color: 'rgba(255, 255, 255, 0.8)',
    },
    statDivider: {
        width: 1,
        backgroundColor: 'rgba(255, 255, 255, 0.2)',
    },
    scrollContent: {
        flex: 1,
    },
    scrollContainer: {
        paddingTop: 24,
    },
    section: {
        paddingHorizontal: 24,
        marginBottom: 32,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    sectionTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 2,
    },
    sectionSubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    summaryGradientBorder: {
        padding: 3,
        borderRadius: 16,
    },
    summaryInner: {
        backgroundColor: 'white',
        borderRadius: 13,
        padding: 16,
    },
    summaryHeader: {
        flexDirection: 'row',
        marginBottom: 12,
    },
    summaryIconContainer: {
        width: 40,
        height: 40,
        borderRadius: 12,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    summaryIcon: {
        fontSize: 20,
    },
    summaryTitleContainer: {
        flex: 1,
    },
    summaryTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 6,
    },
    summaryMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    unreadBadge: {
        backgroundColor: theme.colors.error,
        borderRadius: 10,
        paddingHorizontal: 8,
        paddingVertical: 2,
        minWidth: 24,
        alignItems: 'center',
    },
    unreadText: {
        color: 'white',
        fontSize: 11,
        fontWeight: '700',
    },
    summaryContent: {
        fontSize: 15,
        lineHeight: 22,
        color: theme.colors.textSecondary,
        marginBottom: 12,
    },
    summaryFooter: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    footerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    footerText: {
        fontSize: 13,
        color: theme.colors.textTertiary,
    },
    footerDot: {
        fontSize: 13,
        color: theme.colors.textTertiary,
    },
    timestamp: {
        fontSize: 13,
        color: theme.colors.textTertiary,
        fontWeight: '500',
    },
    actionsGrid: {
        flexDirection: 'row',
        gap: 16,
    },
    actionCard: {
        flex: 1,
        borderRadius: 16,
        overflow: 'hidden',
        ...theme.shadows.md,
    },
    actionGradient: {
        paddingVertical: 32,
        paddingHorizontal: 20,
        alignItems: 'center',
        gap: 12,
    },
    actionText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '700',
    },
});
