import React from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Linking,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';

export default function HelpCenterScreen() {
    const router = useRouter();

    const helpTopics = [
        {
            icon: 'rocket',
            title: 'Getting Started',
            description: 'Learn the basics of Syncline',
            articles: 5,
        },
        {
            icon: 'people',
            title: 'Contacts & Sync',
            description: 'Managing your contacts and connections',
            articles: 8,
        },
        {
            icon: 'chatbubbles',
            title: 'Messages',
            description: 'Unified messaging across platforms',
            articles: 12,
        },
        {
            icon: 'notifications',
            title: 'Notifications',
            description: 'Managing alerts and notifications',
            articles: 6,
        },
        {
            icon: 'link',
            title: 'Platform Connections',
            description: 'Connecting Slack, Gmail, and more',
            articles: 10,
        },
        {
            icon: 'shield-checkmark',
            title: 'Privacy & Security',
            description: 'Keeping your data safe',
            articles: 7,
        },
    ];

    const contactOptions = [
        {
            icon: 'mail',
            title: 'Email Support',
            description: 'support@syncline.app',
            action: () => Linking.openURL('mailto:support@syncline.app'),
        },
        {
            icon: 'chatbubble-ellipses',
            title: 'Live Chat',
            description: 'Chat with our support team',
            action: () => { },
        },
        {
            icon: 'logo-twitter',
            title: 'Twitter',
            description: '@SynclineApp',
            action: () => Linking.openURL('https://twitter.com/synclineapp'),
        },
    ];

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    headerShown: true,
                    headerTitle: 'Help Center',
                    headerLeft: () => (
                        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    ),
                }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                {/* Search */}
                <View style={styles.searchContainer}>
                    <View style={styles.searchBar}>
                        <Ionicons name="search" size={20} color={theme.colors.textTertiary} />
                        <Text style={styles.searchPlaceholder}>Search help articles...</Text>
                    </View>
                </View>

                {/* Help Topics */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Browse Topics</Text>
                    {helpTopics.map((topic, index) => (
                        <TouchableOpacity key={index} style={styles.topicCard}>
                            <View style={[styles.topicIcon, { backgroundColor: theme.colors.primary + '15' }]}>
                                <Ionicons name={topic.icon as any} size={24} color={theme.colors.primary} />
                            </View>
                            <View style={styles.topicInfo}>
                                <Text style={styles.topicTitle}>{topic.title}</Text>
                                <Text style={styles.topicDescription}>{topic.description}</Text>
                                <Text style={styles.topicArticles}>{topic.articles} articles</Text>
                            </View>
                            <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                        </TouchableOpacity>
                    ))}
                </View>

                {/* FAQ */}
                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Frequently Asked</Text>
                    <TouchableOpacity style={styles.faqItem}>
                        <View style={styles.faqLeft}>
                            <Ionicons name="help-circle" size={20} color={theme.colors.info} />
                            <Text style={styles.faqQuestion}>How do I connect a new platform?</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.faqItem}>
                        <View style={styles.faqLeft}>
                            <Ionicons name="help-circle" size={20} color={theme.colors.info} />
                            <Text style={styles.faqQuestion}>How does contact matching work?</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.faqItem}>
                        <View style={styles.faqLeft}>
                            <Ionicons name="help-circle" size={20} color={theme.colors.info} />
                            <Text style={styles.faqQuestion}>Is my data encrypted?</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.faqItem}>
                        <View style={styles.faqLeft}>
                            <Ionicons name="help-circle" size={20} color={theme.colors.info} />
                            <Text style={styles.faqQuestion}>How do I delete my account?</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={16} color={theme.colors.textTertiary} />
                    </TouchableOpacity>
                </Card>

                {/* Contact Support */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Contact Support</Text>
                    {contactOptions.map((option, index) => (
                        <TouchableOpacity
                            key={index}
                            style={styles.contactCard}
                            onPress={option.action}
                        >
                            <View style={[styles.contactIcon, { backgroundColor: theme.colors.primary + '15' }]}>
                                <Ionicons name={option.icon as any} size={20} color={theme.colors.primary} />
                            </View>
                            <View style={styles.contactInfo}>
                                <Text style={styles.contactTitle}>{option.title}</Text>
                                <Text style={styles.contactDescription}>{option.description}</Text>
                            </View>
                            <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                        </TouchableOpacity>
                    ))}
                </View>

                {/* App Info */}
                <Card style={styles.section}>
                    <View style={styles.appInfo}>
                        <Text style={styles.appVersion}>Syncline v1.0.0 (Build 1)</Text>
                        <Text style={styles.appCopyright}>© 2024 Syncline Inc.</Text>
                    </View>
                </Card>

                <View style={{ height: 40 }} />
            </ScrollView>
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
    searchContainer: {
        padding: 16,
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        backgroundColor: 'white',
        paddingHorizontal: 16,
        paddingVertical: 14,
        borderRadius: 12,
        ...theme.shadows.sm,
    },
    searchPlaceholder: {
        fontSize: 16,
        color: theme.colors.textTertiary,
    },
    section: {
        margin: 16,
        marginTop: 0,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 16,
    },
    topicCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'white',
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
        ...theme.shadows.sm,
    },
    topicIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 16,
    },
    topicInfo: {
        flex: 1,
    },
    topicTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    topicDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    topicArticles: {
        fontSize: 12,
        color: theme.colors.primary,
        fontWeight: '600',
    },
    faqItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 14,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    faqLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        flex: 1,
    },
    faqQuestion: {
        fontSize: 14,
        color: theme.colors.text,
        flex: 1,
    },
    contactCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'white',
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
        ...theme.shadows.sm,
    },
    contactIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    contactInfo: {
        flex: 1,
    },
    contactTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    contactDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    appInfo: {
        alignItems: 'center',
        paddingVertical: 8,
    },
    appVersion: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    appCopyright: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
});
