/**
 * Unified Contact List - Demo Version (Section 4.11.4, Figure 4.7)
 * 
 * Aggregated contacts from all platforms with relationship intelligence.
 * Shows relationship strength, message counts, last interaction, and communication frequency.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    TextInput,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_CONTACTS } from '../src/data/dummyData';

type SortOption = 'name' | 'recent' | 'strength' | 'frequency';

const PLATFORM_CONFIG: Record<string, { icon: string; color: string }> = {
    gmail: { icon: 'mail', color: '#EA4335' },
    slack: { icon: 'logo-slack', color: '#4A154B' },
    telegram: { icon: 'paper-plane', color: '#0088CC' },
    discord: { icon: 'logo-discord', color: '#5865F2' },
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366' },
};

export default function ContactsDemoScreen() {
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const [sortBy, setSortBy] = useState<SortOption>('strength');

    const getInitials = (name: string) => {
        return name.split(' ').map(word => word[0]).join('').toUpperCase().slice(0, 2);
    };

    const getRelationshipColor = (strength: number) => {
        if (strength >= 80) return '#10B981';
        if (strength >= 50) return '#F59E0B';
        return '#9CA3AF';
    };

    const getFrequencyLabel = (freq: string) => {
        switch (freq.toLowerCase()) {
            case 'high': return { label: 'High', color: '#10B981', bg: '#D1FAE5' };
            case 'medium': return { label: 'Medium', color: '#F59E0B', bg: '#FEF3C7' };
            case 'low': return { label: 'Low', color: '#9CA3AF', bg: '#F3F4F6' };
            default: return { label: freq, color: '#9CA3AF', bg: '#F3F4F6' };
        }
    };

    const formatLastInteraction = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffHours < 168) return `${Math.floor(diffHours / 24)}d ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // Sort contacts based on selection
    const sortedContacts = [...DUMMY_CONTACTS].sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'recent':
                return new Date(b.lastInteraction).getTime() - new Date(a.lastInteraction).getTime();
            case 'strength':
                return b.relationshipStrength - a.relationshipStrength;
            case 'frequency':
                const freqOrder = { 'High': 0, 'Medium': 1, 'Low': 2 };
                return (freqOrder[a.communicationFrequency as keyof typeof freqOrder] || 2) -
                    (freqOrder[b.communicationFrequency as keyof typeof freqOrder] || 2);
            default:
                return 0;
        }
    });

    // Filter contacts based on search
    const filteredContacts = sortedContacts.filter(contact =>
        contact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        contact.primaryEmail.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>Contacts</Text>
                <Text style={styles.headerSubtitle}>
                    {DUMMY_CONTACTS.length} unified contacts from all platforms
                </Text>

                {/* Search Bar */}
                <View style={styles.searchBar}>
                    <Ionicons name="search" size={18} color={theme.colors.textTertiary} />
                    <TextInput
                        style={styles.searchInput}
                        placeholder="Search contacts..."
                        placeholderTextColor={theme.colors.textTertiary}
                        value={searchQuery}
                        onChangeText={setSearchQuery}
                    />
                    {searchQuery && (
                        <TouchableOpacity onPress={() => setSearchQuery('')}>
                            <Ionicons name="close-circle" size={18} color={theme.colors.textTertiary} />
                        </TouchableOpacity>
                    )}
                </View>

                {/* Sort Options */}
                <View style={styles.sortContainer}>
                    <Text style={styles.sortLabel}>Sort by:</Text>
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.sortOptions}>
                        {[
                            { id: 'strength' as SortOption, label: 'Relationship', icon: 'heart' },
                            { id: 'recent' as SortOption, label: 'Recent', icon: 'time' },
                            { id: 'frequency' as SortOption, label: 'Frequency', icon: 'pulse' },
                            { id: 'name' as SortOption, label: 'Name', icon: 'text' },
                        ].map((option) => (
                            <TouchableOpacity
                                key={option.id}
                                style={[styles.sortChip, sortBy === option.id && styles.sortChipActive]}
                                onPress={() => setSortBy(option.id)}
                            >
                                <Ionicons
                                    name={option.icon as any}
                                    size={14}
                                    color={sortBy === option.id ? 'white' : theme.colors.textSecondary}
                                />
                                <Text style={[
                                    styles.sortChipText,
                                    sortBy === option.id && styles.sortChipTextActive
                                ]}>
                                    {option.label}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </ScrollView>
                </View>
            </View>

            {/* Contacts List */}
            <ScrollView style={styles.contactsList} showsVerticalScrollIndicator={false}>
                {filteredContacts.map((contact) => {
                    const strengthColor = getRelationshipColor(contact.relationshipStrength);
                    const freq = getFrequencyLabel(contact.communicationFrequency);

                    return (
                        <TouchableOpacity
                            key={contact.id}
                            activeOpacity={0.8}
                            onPress={() => router.push('/contact-profile')}
                        >
                            <Card style={styles.contactCard}>
                                <View style={styles.contactContent}>
                                    {/* Avatar with Strength Ring */}
                                    <View style={styles.avatarContainer}>
                                        <View style={[styles.strengthRing, { borderColor: strengthColor }]}>
                                            <View style={styles.avatar}>
                                                <Text style={styles.avatarText}>{getInitials(contact.name)}</Text>
                                            </View>
                                        </View>
                                    </View>

                                    {/* Contact Info */}
                                    <View style={styles.contactInfo}>
                                        <View style={styles.nameRow}>
                                            <Text style={styles.contactName}>{contact.name}</Text>
                                            <Text style={styles.lastInteraction}>
                                                {formatLastInteraction(contact.lastInteraction)}
                                            </Text>
                                        </View>

                                        {/* Platform Identities */}
                                        <View style={styles.platformsRow}>
                                            {Object.keys(contact.platformIdentities).map((platform) => {
                                                const config = PLATFORM_CONFIG[platform];
                                                if (!config) return null;
                                                return (
                                                    <View
                                                        key={platform}
                                                        style={[styles.platformDot, { backgroundColor: config.color }]}
                                                    >
                                                        <Ionicons name={config.icon as any} size={10} color="white" />
                                                    </View>
                                                );
                                            })}
                                            <Text style={styles.platformCount}>
                                                {Object.keys(contact.platformIdentities).length} platforms
                                            </Text>
                                        </View>

                                        {/* Metrics Row */}
                                        <View style={styles.metricsRow}>
                                            {/* Relationship Strength */}
                                            <View style={styles.metric}>
                                                <View style={styles.strengthBar}>
                                                    <View style={[
                                                        styles.strengthFill,
                                                        { width: `${contact.relationshipStrength}%`, backgroundColor: strengthColor }
                                                    ]} />
                                                </View>
                                                <Text style={[styles.metricValue, { color: strengthColor }]}>
                                                    {contact.relationshipStrength}%
                                                </Text>
                                            </View>

                                            {/* Message Count */}
                                            <View style={styles.metric}>
                                                <Ionicons name="chatbubble" size={12} color={theme.colors.textSecondary} />
                                                <Text style={styles.metricText}>{contact.totalMessages}</Text>
                                            </View>

                                            {/* Frequency Badge */}
                                            <View style={[styles.frequencyBadge, { backgroundColor: freq.bg }]}>
                                                <Text style={[styles.frequencyText, { color: freq.color }]}>
                                                    {freq.label}
                                                </Text>
                                            </View>
                                        </View>
                                    </View>

                                    {/* Chevron */}
                                    <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
                                </View>
                            </Card>
                        </TouchableOpacity>
                    );
                })}

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
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    headerTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    headerSubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginTop: 4,
        marginBottom: 16,
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 14,
        paddingVertical: 12,
        gap: 10,
    },
    searchInput: {
        flex: 1,
        fontSize: 15,
        color: theme.colors.text,
    },
    sortContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 16,
    },
    sortLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginRight: 10,
    },
    sortOptions: {
        flexDirection: 'row',
    },
    sortChip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
        backgroundColor: theme.colors.surface,
        marginRight: 8,
    },
    sortChipActive: {
        backgroundColor: theme.colors.primary,
    },
    sortChipText: {
        fontSize: 12,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    sortChipTextActive: {
        color: 'white',
    },
    contactsList: {
        flex: 1,
        padding: 16,
    },
    contactCard: {
        marginBottom: 12,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    contactContent: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatarContainer: {
        marginRight: 14,
    },
    strengthRing: {
        width: 52,
        height: 52,
        borderRadius: 26,
        borderWidth: 3,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatar: {
        width: 42,
        height: 42,
        borderRadius: 21,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 15,
        fontWeight: 'bold',
        color: 'white',
    },
    contactInfo: {
        flex: 1,
    },
    nameRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 4,
    },
    contactName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    lastInteraction: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    platformsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        marginBottom: 8,
    },
    platformDot: {
        width: 18,
        height: 18,
        borderRadius: 9,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformCount: {
        fontSize: 11,
        color: theme.colors.textSecondary,
        marginLeft: 4,
    },
    metricsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    metric: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    strengthBar: {
        width: 40,
        height: 4,
        backgroundColor: theme.colors.surface,
        borderRadius: 2,
        overflow: 'hidden',
    },
    strengthFill: {
        height: '100%',
        borderRadius: 2,
    },
    metricValue: {
        fontSize: 11,
        fontWeight: '600',
    },
    metricText: {
        fontSize: 11,
        color: theme.colors.textSecondary,
    },
    frequencyBadge: {
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 10,
    },
    frequencyText: {
        fontSize: 10,
        fontWeight: '600',
    },
});
