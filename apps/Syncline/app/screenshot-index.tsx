/**
 * Screenshot Demo Index
 * 
 * A navigation hub for all the demo screens created for MESH documentation screenshots.
 * Use this page to quickly access each screen for taking screenshots.
 */

import React from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';

type DemoScreen = {
    id: string;
    title: string;
    figure: string;
    description: string;
    route: string;
    icon: string;
    color: string;
};

const DEMO_SCREENS: DemoScreen[] = [
    {
        id: 'connections',
        title: 'Platform Connections',
        figure: 'Figure 4.1',
        description: 'Connected platforms with sync status and message counts',
        route: '/connections-demo',
        icon: 'link',
        color: '#3B82F6',
    },
    {
        id: 'oauth',
        title: 'OAuth Authorization',
        figure: 'Figure 4.2',
        description: 'Google OAuth consent screen with permissions',
        route: '/oauth-demo',
        icon: 'key',
        color: '#4285F4',
    },
    {
        id: 'messages',
        title: 'Unified Message List',
        figure: 'Figure 4.3',
        description: 'Multi-platform inbox with platform badges',
        route: '/messages-demo',
        icon: 'mail',
        color: '#EA4335',
    },
    {
        id: 'message-detail',
        title: 'Message Detail View',
        figure: 'Figure 4.4',
        description: 'Expanded message with AI entities and summary',
        route: '/messages-demo',
        icon: 'document-text',
        color: '#F59E0B',
    },
    {
        id: 'search',
        title: 'Search Interface',
        figure: 'Figure 4.5 & 4.6',
        description: 'Advanced search with filters and results',
        route: '/advanced-search',
        icon: 'search',
        color: '#8B5CF6',
    },
    {
        id: 'contacts',
        title: 'Unified Contact List',
        figure: 'Figure 4.7',
        description: 'Aggregated contacts with relationship metrics',
        route: '/contacts-demo',
        icon: 'people',
        color: '#10B981',
    },
    {
        id: 'contact-profile',
        title: 'Contact Profile',
        figure: 'Figure 4.8',
        description: 'Detailed contact intelligence and AI insights',
        route: '/contact-profile',
        icon: 'person-circle',
        color: '#06B6D4',
    },
    {
        id: 'thread',
        title: 'Thread View',
        figure: 'Figure 4.9',
        description: 'Conversation thread with AI summary',
        route: '/thread-view',
        icon: 'chatbubbles',
        color: '#EC4899',
    },
    {
        id: 'commitments',
        title: 'Commitment Dashboard',
        figure: 'Figure 4.10 & 4.11',
        description: 'Tracked commitments with source context',
        route: '/(tabs)/commitments',
        icon: 'checkbox',
        color: '#F59E0B',
    },
    {
        id: 'nudges',
        title: 'Nudge Notifications',
        figure: 'Figure 4.12',
        description: 'Proactive reminders and follow-up suggestions',
        route: '/(tabs)/nudges',
        icon: 'notifications',
        color: '#EF4444',
    },
    {
        id: 'daily-summary',
        title: 'Daily Summary',
        figure: 'Figure 4.13',
        description: 'AI-generated communication digest',
        route: '/daily-summary',
        icon: 'newspaper',
        color: '#6366F1',
    },
    {
        id: 'settings',
        title: 'Settings Panel',
        figure: 'Figure 4.14',
        description: 'Configuration for connections, notifications, privacy, AI',
        route: '/settings-demo',
        icon: 'settings',
        color: '#64748B',
    },
    {
        id: 'api-docs',
        title: 'API Documentation',
        figure: 'Figure 4.15',
        description: 'Interactive OpenAPI/Swagger documentation',
        route: '/api-docs',
        icon: 'code-working',
        color: '#1F2937',
    },
    {
        id: 'unified-conversation',
        title: 'Unified Conversation',
        figure: 'Multi-Platform',
        description: 'Single contact conversation across Gmail, Slack, WhatsApp',
        route: '/unified-conversation',
        icon: 'git-merge',
        color: '#8B5CF6',
    },
];

export default function ScreenshotIndexScreen() {
    const router = useRouter();

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerContent}>
                    <View style={styles.headerIcon}>
                        <Ionicons name="camera" size={24} color="white" />
                    </View>
                    <View>
                        <Text style={styles.headerTitle}>MESH Screenshot Demos</Text>
                        <Text style={styles.headerSubtitle}>
                            {DEMO_SCREENS.length} screens ready for documentation
                        </Text>
                    </View>
                </View>
            </View>

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                <Text style={styles.sectionTitle}>Documentation Figures (4.11.x)</Text>

                {DEMO_SCREENS.map((screen) => (
                    <TouchableOpacity
                        key={screen.id}
                        activeOpacity={0.8}
                        onPress={() => router.push(screen.route as any)}
                    >
                        <Card style={styles.screenCard}>
                            <View style={[styles.iconContainer, { backgroundColor: screen.color + '20' }]}>
                                <Ionicons name={screen.icon as any} size={24} color={screen.color} />
                            </View>
                            <View style={styles.screenInfo}>
                                <View style={styles.titleRow}>
                                    <Text style={styles.screenTitle}>{screen.title}</Text>
                                    <View style={styles.figureBadge}>
                                        <Text style={styles.figureText}>{screen.figure}</Text>
                                    </View>
                                </View>
                                <Text style={styles.screenDescription}>{screen.description}</Text>
                            </View>
                            <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                        </Card>
                    </TouchableOpacity>
                ))}

                {/* Instructions */}
                <Card style={styles.instructionsCard}>
                    <View style={styles.instructionsHeader}>
                        <Ionicons name="information-circle" size={20} color={theme.colors.primary} />
                        <Text style={styles.instructionsTitle}>Screenshot Instructions</Text>
                    </View>
                    <Text style={styles.instructionsText}>
                        1. Navigate to the desired screen{'\n'}
                        2. Use your device's screenshot function{'\n'}
                        3. All screens contain dummy data matching the documentation{'\n'}
                        4. Click on messages/contacts to see expanded views
                    </Text>
                </Card>

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
        backgroundColor: theme.colors.primary,
        paddingTop: 60,
        paddingBottom: 24,
        paddingHorizontal: 20,
    },
    headerContent: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 16,
    },
    headerIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    headerTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        color: 'white',
    },
    headerSubtitle: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.8)',
        marginTop: 2,
    },
    content: {
        flex: 1,
        padding: 16,
    },
    sectionTitle: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 12,
        marginTop: 8,
    },
    screenCard: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        marginBottom: 10,
        backgroundColor: theme.colors.background,
    },
    iconContainer: {
        width: 48,
        height: 48,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 14,
    },
    screenInfo: {
        flex: 1,
    },
    titleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 4,
    },
    screenTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    figureBadge: {
        backgroundColor: theme.colors.surface,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
    },
    figureText: {
        fontSize: 10,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    screenDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    instructionsCard: {
        padding: 16,
        marginTop: 16,
        backgroundColor: theme.colors.primaryLighter,
    },
    instructionsHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 12,
    },
    instructionsTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    instructionsText: {
        fontSize: 13,
        color: theme.colors.text,
        lineHeight: 20,
    },
});
