/**
 * Enhanced Search Interface (Section 4.11.3)
 * 
 * Hybrid search interface with advanced filtering options.
 * Demonstrates natural language search with keyword and semantic modes.
 */

import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TextInput,
    ScrollView,
    TouchableOpacity,
    Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';
import { DUMMY_SEARCH_RESULTS } from '../src/data/dummyData';

const { width } = Dimensions.get('window');

type SearchMode = 'hybrid' | 'keyword' | 'semantic';
type SortOrder = 'relevance' | 'newest' | 'oldest';

const PLATFORMS = [
    { id: 'gmail', label: 'Gmail', color: '#EA4335', icon: 'mail' },
    { id: 'slack', label: 'Slack', color: '#4A154B', icon: 'logo-slack' },
    { id: 'discord', label: 'Discord', color: '#5865F2', icon: 'logo-discord' },
    { id: 'telegram', label: 'Telegram', color: '#0088CC', icon: 'paper-plane' },
    { id: 'whatsapp', label: 'WhatsApp', color: '#25D366', icon: 'logo-whatsapp' },
];

export default function AdvancedSearchScreen() {
    const [query, setQuery] = useState('what did I promise Sarah about budget');
    const [showFilters, setShowFilters] = useState(true);
    const [searchMode, setSearchMode] = useState<SearchMode>('hybrid');
    const [sortOrder, setSortOrder] = useState<SortOrder>('relevance');
    const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState('Last 30 days');
    const [hasSearched, setHasSearched] = useState(true);
    const [results, setResults] = useState(DUMMY_SEARCH_RESULTS);

    const togglePlatform = (platformId: string) => {
        setSelectedPlatforms(prev =>
            prev.includes(platformId)
                ? prev.filter(p => p !== platformId)
                : [...prev, platformId]
        );
    };

    const handleSearch = () => {
        setHasSearched(true);
        // In real app, this would call the search API
        setResults(DUMMY_SEARCH_RESULTS);
    };

    const renderStars = (score: number) => {
        const stars = Math.round(score * 5);
        return (
            <View style={styles.starsContainer}>
                {[1, 2, 3, 4, 5].map(i => (
                    <Ionicons
                        key={i}
                        name={i <= stars ? 'star' : 'star-outline'}
                        size={12}
                        color={i <= stars ? '#F59E0B' : theme.colors.textTertiary}
                    />
                ))}
            </View>
        );
    };

    const getPlatformConfig = (platformId: string) => {
        return PLATFORMS.find(p => p.id === platformId) ||
            { label: platformId, color: theme.colors.textSecondary, icon: 'chatbubble' };
    };

    return (
        <View style={styles.container}>
            {/* Search Header */}
            <View style={styles.searchHeader}>
                <View style={styles.searchBarContainer}>
                    <Ionicons name="search" size={20} color={theme.colors.textTertiary} />
                    <TextInput
                        style={styles.searchInput}
                        placeholder="Search messages..."
                        placeholderTextColor={theme.colors.textTertiary}
                        value={query}
                        onChangeText={setQuery}
                        onSubmitEditing={handleSearch}
                        returnKeyType="search"
                    />
                    {query.length > 0 && (
                        <TouchableOpacity onPress={() => setQuery('')}>
                            <Ionicons name="close-circle" size={20} color={theme.colors.textTertiary} />
                        </TouchableOpacity>
                    )}
                </View>

                {/* Search Mode Toggle */}
                <View style={styles.modeContainer}>
                    <Text style={styles.modeLabel}>Search Mode:</Text>
                    <View style={styles.modeToggle}>
                        {(['hybrid', 'keyword', 'semantic'] as SearchMode[]).map((mode) => (
                            <TouchableOpacity
                                key={mode}
                                style={[styles.modeButton, searchMode === mode && styles.modeButtonActive]}
                                onPress={() => setSearchMode(mode)}
                            >
                                <Text style={[styles.modeButtonText, searchMode === mode && styles.modeButtonTextActive]}>
                                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                </View>

                {/* Filter Toggle */}
                <TouchableOpacity
                    style={styles.filterToggle}
                    onPress={() => setShowFilters(!showFilters)}
                >
                    <Ionicons name="options" size={18} color={theme.colors.primary} />
                    <Text style={styles.filterToggleText}>
                        {showFilters ? 'Hide Filters' : 'Show Filters'}
                    </Text>
                    <Ionicons
                        name={showFilters ? 'chevron-up' : 'chevron-down'}
                        size={16}
                        color={theme.colors.primary}
                    />
                </TouchableOpacity>
            </View>

            <View style={styles.mainContent}>
                {/* Filter Panel (Sidebar) */}
                {showFilters && (
                    <View style={styles.filterPanel}>
                        <ScrollView showsVerticalScrollIndicator={false}>
                            {/* Platform Filter */}
                            <View style={styles.filterSection}>
                                <Text style={styles.filterTitle}>Platform</Text>
                                {PLATFORMS.map(platform => (
                                    <TouchableOpacity
                                        key={platform.id}
                                        style={styles.checkboxRow}
                                        onPress={() => togglePlatform(platform.id)}
                                    >
                                        <View style={[
                                            styles.checkbox,
                                            selectedPlatforms.includes(platform.id) && {
                                                backgroundColor: platform.color,
                                                borderColor: platform.color,
                                            }
                                        ]}>
                                            {selectedPlatforms.includes(platform.id) && (
                                                <Ionicons name="checkmark" size={12} color="white" />
                                            )}
                                        </View>
                                        <Ionicons name={platform.icon as any} size={16} color={platform.color} />
                                        <Text style={styles.checkboxLabel}>{platform.label}</Text>
                                    </TouchableOpacity>
                                ))}
                            </View>

                            {/* Date Range */}
                            <View style={styles.filterSection}>
                                <Text style={styles.filterTitle}>Date Range</Text>
                                <TouchableOpacity style={styles.datePickerButton}>
                                    <Ionicons name="calendar-outline" size={16} color={theme.colors.textSecondary} />
                                    <Text style={styles.datePickerText}>{dateRange}</Text>
                                    <Ionicons name="chevron-down" size={14} color={theme.colors.textSecondary} />
                                </TouchableOpacity>
                            </View>

                            {/* Content Type */}
                            <View style={styles.filterSection}>
                                <Text style={styles.filterTitle}>Content Type</Text>
                                {['Text only', 'With attachments', 'With links'].map(type => (
                                    <TouchableOpacity key={type} style={styles.radioRow}>
                                        <View style={styles.radio}>
                                            {type === 'Text only' && <View style={styles.radioFill} />}
                                        </View>
                                        <Text style={styles.radioLabel}>{type}</Text>
                                    </TouchableOpacity>
                                ))}
                            </View>

                            {/* Message Type */}
                            <View style={styles.filterSection}>
                                <Text style={styles.filterTitle}>Message Type</Text>
                                {['Sent by me', 'Received', 'Both'].map(type => (
                                    <TouchableOpacity key={type} style={styles.radioRow}>
                                        <View style={styles.radio}>
                                            {type === 'Both' && <View style={styles.radioFill} />}
                                        </View>
                                        <Text style={styles.radioLabel}>{type}</Text>
                                    </TouchableOpacity>
                                ))}
                            </View>

                            {/* Sort Order */}
                            <View style={styles.filterSection}>
                                <Text style={styles.filterTitle}>Sort By</Text>
                                <View style={styles.sortButtons}>
                                    {(['relevance', 'newest', 'oldest'] as SortOrder[]).map(order => (
                                        <TouchableOpacity
                                            key={order}
                                            style={[styles.sortButton, sortOrder === order && styles.sortButtonActive]}
                                            onPress={() => setSortOrder(order)}
                                        >
                                            <Text style={[styles.sortButtonText, sortOrder === order && styles.sortButtonTextActive]}>
                                                {order.charAt(0).toUpperCase() + order.slice(1)}
                                            </Text>
                                        </TouchableOpacity>
                                    ))}
                                </View>
                            </View>
                        </ScrollView>
                    </View>
                )}

                {/* Results Panel */}
                <ScrollView style={styles.resultsPanel} showsVerticalScrollIndicator={false}>
                    {/* Results Header */}
                    <View style={styles.resultsHeader}>
                        <Text style={styles.resultsCount}>
                            {results.length} results for "{query}"
                        </Text>
                        <View style={styles.resultsMeta}>
                            <View style={styles.metaBadge}>
                                <Ionicons name="sparkles" size={12} color={theme.colors.primary} />
                                <Text style={styles.metaBadgeText}>AI-powered search</Text>
                            </View>
                        </View>
                    </View>

                    {/* Search Results */}
                    {results.map((result) => {
                        const platform = getPlatformConfig(result.platform);

                        return (
                            <TouchableOpacity key={result.id} activeOpacity={0.8}>
                                <Card style={styles.resultCard}>
                                    {/* Result Header */}
                                    <View style={styles.resultHeader}>
                                        <View style={styles.resultMeta}>
                                            {renderStars(result.relevanceScore)}
                                            <View style={[styles.platformBadge, { backgroundColor: platform.color + '20' }]}>
                                                <Ionicons name={platform.icon as any} size={12} color={platform.color} />
                                                <Text style={[styles.platformText, { color: platform.color }]}>
                                                    {platform.label}
                                                </Text>
                                            </View>
                                            <Text style={styles.resultDate}>{result.date}</Text>
                                        </View>
                                        <View style={[
                                            styles.matchTypeBadge,
                                            result.matchType === 'semantic' ? styles.semanticBadge : styles.keywordBadge
                                        ]}>
                                            <Text style={[
                                                styles.matchTypeText,
                                                result.matchType === 'semantic' ? styles.semanticText : styles.keywordText
                                            ]}>
                                                {result.matchType === 'semantic' ? 'Semantic' : 'Keyword'} Match
                                            </Text>
                                        </View>
                                    </View>

                                    {/* Sender */}
                                    <Text style={styles.resultSender}>{result.sender}</Text>

                                    {/* Highlighted Snippet */}
                                    <View style={styles.snippetContainer}>
                                        <Text style={styles.snippetText}>
                                            {result.highlightedSnippet.split(/<mark>|<\/mark>/).map((part, idx) => (
                                                <Text
                                                    key={idx}
                                                    style={idx % 2 === 1 ? styles.highlightedText : undefined}
                                                >
                                                    {part}
                                                </Text>
                                            ))}
                                        </Text>
                                        <Text style={styles.ellipsis}>...</Text>
                                    </View>

                                    {/* Entities */}
                                    <View style={styles.entitiesContainer}>
                                        {result.entities.map((entity, idx) => (
                                            <View key={idx} style={styles.entityPill}>
                                                <Text style={styles.entityText}>{entity}</Text>
                                            </View>
                                        ))}
                                    </View>

                                    {/* Actions */}
                                    <View style={styles.resultActions}>
                                        <TouchableOpacity style={styles.resultAction}>
                                            <Text style={styles.resultActionText}>View Full Message</Text>
                                        </TouchableOpacity>
                                        {result.threadId && (
                                            <TouchableOpacity style={styles.resultAction}>
                                                <Text style={styles.resultActionText}>View Thread</Text>
                                            </TouchableOpacity>
                                        )}
                                        <TouchableOpacity style={styles.moreButton}>
                                            <Ionicons name="ellipsis-horizontal" size={16} color={theme.colors.textSecondary} />
                                        </TouchableOpacity>
                                    </View>
                                </Card>
                            </TouchableOpacity>
                        );
                    })}

                    <View style={{ height: 100 }} />
                </ScrollView>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    searchHeader: {
        backgroundColor: theme.colors.background,
        padding: 16,
        paddingTop: 60,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    searchBarContainer: {
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
        fontSize: 16,
        color: theme.colors.text,
    },
    modeContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 12,
        gap: 12,
    },
    modeLabel: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    modeToggle: {
        flexDirection: 'row',
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
        padding: 2,
    },
    modeButton: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 6,
    },
    modeButtonActive: {
        backgroundColor: theme.colors.primary,
    },
    modeButtonText: {
        fontSize: 12,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    modeButtonTextActive: {
        color: 'white',
    },
    filterToggle: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginTop: 12,
    },
    filterToggleText: {
        fontSize: 14,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    mainContent: {
        flex: 1,
        flexDirection: 'row',
    },
    filterPanel: {
        width: 180,
        backgroundColor: theme.colors.background,
        borderRightWidth: 1,
        borderRightColor: theme.colors.border,
        padding: 16,
    },
    filterSection: {
        marginBottom: 20,
    },
    filterTitle: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        marginBottom: 10,
    },
    checkboxRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingVertical: 6,
    },
    checkbox: {
        width: 18,
        height: 18,
        borderRadius: 4,
        borderWidth: 1.5,
        borderColor: theme.colors.border,
        alignItems: 'center',
        justifyContent: 'center',
    },
    checkboxLabel: {
        fontSize: 13,
        color: theme.colors.text,
    },
    datePickerButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingVertical: 8,
        paddingHorizontal: 10,
        backgroundColor: theme.colors.surface,
        borderRadius: 6,
    },
    datePickerText: {
        flex: 1,
        fontSize: 13,
        color: theme.colors.text,
    },
    radioRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        paddingVertical: 6,
    },
    radio: {
        width: 16,
        height: 16,
        borderRadius: 8,
        borderWidth: 1.5,
        borderColor: theme.colors.border,
        alignItems: 'center',
        justifyContent: 'center',
    },
    radioFill: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: theme.colors.primary,
    },
    radioLabel: {
        fontSize: 13,
        color: theme.colors.text,
    },
    sortButtons: {
        gap: 6,
    },
    sortButton: {
        paddingVertical: 6,
        paddingHorizontal: 10,
        backgroundColor: theme.colors.surface,
        borderRadius: 6,
    },
    sortButtonActive: {
        backgroundColor: theme.colors.primary,
    },
    sortButtonText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    sortButtonTextActive: {
        color: 'white',
        fontWeight: '500',
    },
    resultsPanel: {
        flex: 1,
        padding: 16,
    },
    resultsHeader: {
        marginBottom: 16,
    },
    resultsCount: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    resultsMeta: {
        flexDirection: 'row',
        marginTop: 6,
    },
    metaBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: theme.colors.primaryLighter,
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    metaBadgeText: {
        fontSize: 11,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    resultCard: {
        marginBottom: 12,
        padding: 16,
        backgroundColor: theme.colors.background,
    },
    resultHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    resultMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    starsContainer: {
        flexDirection: 'row',
        gap: 1,
    },
    platformBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 4,
    },
    platformText: {
        fontSize: 11,
        fontWeight: '500',
    },
    resultDate: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    matchTypeBadge: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 4,
    },
    semanticBadge: {
        backgroundColor: '#8B5CF620',
    },
    keywordBadge: {
        backgroundColor: '#3B82F620',
    },
    matchTypeText: {
        fontSize: 10,
        fontWeight: '600',
    },
    semanticText: {
        color: '#8B5CF6',
    },
    keywordText: {
        color: '#3B82F6',
    },
    resultSender: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 6,
    },
    snippetContainer: {
        flexDirection: 'row',
        marginBottom: 10,
    },
    snippetText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        flex: 1,
    },
    highlightedText: {
        backgroundColor: '#FEF3C7',
        color: theme.colors.text,
        fontWeight: '500',
    },
    ellipsis: {
        fontSize: 14,
        color: theme.colors.textTertiary,
    },
    entitiesContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 6,
        marginBottom: 12,
    },
    entityPill: {
        backgroundColor: theme.colors.surface,
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    entityText: {
        fontSize: 11,
        color: theme.colors.textSecondary,
    },
    resultActions: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        gap: 16,
    },
    resultAction: {
        paddingVertical: 4,
    },
    resultActionText: {
        fontSize: 13,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    moreButton: {
        marginLeft: 'auto',
        padding: 4,
    },
});
