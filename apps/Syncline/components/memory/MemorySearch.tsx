/**
 * Memory Search Component
 * 
 * Provides semantic search interface for memories with:
 * - Real-time search with debouncing
 * - Advanced filters (type, importance, platform)
 * - Search result highlighting and relevance scoring
 * - Quick actions for memory management
 */

import React, { useState, useCallback, useMemo } from 'react';
import { View, Text, TextInput, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { styled } from '@tamagui/core';
import { Search, Filter, Star, Clock, User, Tag } from '@tamagui/lucide-icons';
import { useMemorySearch } from '../../src/hooks/useMemory';
import { MemorySearchResult, MemoryType, MemoryImportance, Platform } from '../../src/types';
import { PLATFORM_COLORS } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: 'transparent',
    padding: '$4',
});

const SearchContainer = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    borderRadius: '$4',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginBottom: '$3',
});

const SearchInput = styled(TextInput, {
    flex: 1,
    fontSize: 16,
    color: '#1f2937',
    marginLeft: 8,
});

const FilterButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e0e7ff',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginLeft: '$2',
});

const ResultItem = styled(TouchableOpacity, {
    backgroundColor: '#ffffff',
    borderRadius: '$3',
    padding: '$3',
    marginBottom: '$2',
    borderLeftWidth: 4,
    borderLeftColor: '#6366f1',
});

const ResultHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$2',
});

const MemoryTypeTag = styled(View, {
    backgroundColor: '$blue3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const ImportanceStars = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
});

const RelevanceScore = styled(View, {
    backgroundColor: '$green3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
});

const SnippetText = styled(Text, {
    fontSize: '$3',
    color: '$gray11',
    lineHeight: '$4',
});

const HighlightedText = styled(Text, {
    backgroundColor: '$yellow4',
    color: '$gray12',
    fontWeight: 'bold',
});

const EmptyState = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$8',
});

const LoadingContainer = styled(View, {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$4',
});

// =============================================================================
// Filter Modal Component
// =============================================================================

interface FilterModalProps {
    visible: boolean;
    onClose: () => void;
    filters: SearchFilters;
    onFiltersChange: (filters: SearchFilters) => void;
}

interface SearchFilters {
    memory_types?: MemoryType[];
    importance_min?: MemoryImportance;
    platform?: Platform;
}

const FilterModal: React.FC<FilterModalProps> = ({
    visible,
    onClose,
    filters,
    onFiltersChange,
}) => {
    // Filter modal implementation would go here
    // For brevity, showing simplified version
    return null;
};

// =============================================================================
// Main Component
// =============================================================================

interface MemorySearchProps {
    contactId?: string;
    threadId?: string;
    onMemorySelect?: (memory: MemorySearchResult) => void;
    placeholder?: string;
}

export const MemorySearch: React.FC<MemorySearchProps> = ({
    contactId,
    threadId,
    onMemorySelect,
    placeholder = "Search memories...",
}) => {
    const [query, setQuery] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState<SearchFilters>({});

    const { results, loading, error, searchMemories, clearResults } = useMemorySearch();

    // Debounced search
    const debouncedSearch = useCallback(
        debounce((searchQuery: string) => {
            if (searchQuery.trim()) {
                searchMemories(searchQuery, {
                    contact_id: contactId,
                    ...filters,
                });
            } else {
                clearResults();
            }
        }, 300),
        [contactId, filters, searchMemories, clearResults]
    );

    const handleQueryChange = useCallback((text: string) => {
        setQuery(text);
        debouncedSearch(text);
    }, [debouncedSearch]);

    const handleFilterChange = useCallback((newFilters: SearchFilters) => {
        setFilters(newFilters);
        if (query.trim()) {
            searchMemories(query, {
                contact_id: contactId,
                ...newFilters,
            });
        }
    }, [query, contactId, searchMemories]);

    // Render importance stars
    const renderImportanceStars = useCallback((importance: MemoryImportance) => {
        return (
            <ImportanceStars>
                {Array.from({ length: 5 }, (_, i) => (
                    <Star
                        key={i}
                        size={12}
                        color={i < importance ? '$yellow9' : '$gray6'}
                        fill={i < importance ? '$yellow9' : 'transparent'}
                    />
                ))}
            </ImportanceStars>
        );
    }, []);

    // Render memory type with color
    const getMemoryTypeColor = useCallback((type: MemoryType) => {
        const colors: Record<MemoryType, string> = {
            fact: '$blue8',
            commitment: '$red8',
            preference: '$purple8',
            relationship: '$pink8',
            personal: '$green8',
            task: '$orange8',
            event: '$cyan8',
            insight: '$yellow8',
        };
        return colors[type] || '$gray8';
    }, []);

    // Highlight search terms in snippet
    const highlightSnippet = useCallback((snippet: string, searchQuery: string) => {
        if (!searchQuery.trim()) return snippet;

        const terms = searchQuery.toLowerCase().split(' ').filter(term => term.length > 2);
        let highlightedSnippet = snippet;

        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlightedSnippet = highlightedSnippet.replace(regex, '**$1**');
        });

        // Split by ** and render with highlighting
        const parts = highlightedSnippet.split('**');
        return parts.map((part, index) =>
            index % 2 === 1 ? (
                <HighlightedText key={index}>{part}</HighlightedText>
            ) : (
                <Text key={index}>{part}</Text>
            )
        );
    }, []);

    // Render search result item
    const renderResultItem = useCallback(({ item }: { item: MemorySearchResult }) => (
        <ResultItem
            onPress={() => onMemorySelect?.(item)}
            style={{
                borderLeftColor: getMemoryTypeColor(item.memory_type),
            }}
        >
            <ResultHeader>
                <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
                    <MemoryTypeTag>
                        <Text style={{ fontSize: 12, color: '$blue11', textTransform: 'capitalize' }}>
                            {item.memory_type}
                        </Text>
                    </MemoryTypeTag>
                    <View style={{ marginLeft: 8 }}>
                        {renderImportanceStars(item.importance)}
                    </View>
                </View>
                <RelevanceScore>
                    <Text style={{ fontSize: 12, color: '$green11' }}>
                        {Math.round(item.relevance_score * 100)}%
                    </Text>
                </RelevanceScore>
            </ResultHeader>

            <SnippetText>
                {highlightSnippet(item.snippet, query)}
            </SnippetText>
        </ResultItem>
    ), [onMemorySelect, getMemoryTypeColor, renderImportanceStars, highlightSnippet, query]);

    // Active filters count
    const activeFiltersCount = useMemo(() => {
        let count = 0;
        if (filters.memory_types?.length) count++;
        if (filters.importance_min) count++;
        if (filters.platform) count++;
        return count;
    }, [filters]);

    return (
        <Container>
            {/* Search Input */}
            <SearchContainer>
                <Search size={20} color="#9ca3af" />
                <SearchInput
                    value={query}
                    onChangeText={handleQueryChange}
                    placeholder={placeholder}
                    placeholderTextColor="#9ca3af"
                    autoCapitalize="none"
                    autoCorrect={false}
                />
                <FilterButton onPress={() => setShowFilters(true)}>
                    <Filter size={16} color="#4f46e5" />
                    {activeFiltersCount > 0 && (
                        <View style={{
                            backgroundColor: '$red9',
                            borderRadius: 8,
                            width: 16,
                            height: 16,
                            justifyContent: 'center',
                            alignItems: 'center',
                            marginLeft: 4,
                        }}>
                            <Text style={{ color: 'white', fontSize: 10, fontWeight: 'bold' }}>
                                {activeFiltersCount}
                            </Text>
                        </View>
                    )}
                </FilterButton>
            </SearchContainer>

            {/* Loading State */}
            {loading && (
                <LoadingContainer>
                    <ActivityIndicator size="small" color="$blue9" />
                    <Text style={{ marginLeft: 8, color: '$gray11' }}>Searching memories...</Text>
                </LoadingContainer>
            )}

            {/* Error State */}
            {error && (
                <View style={{ padding: 16, backgroundColor: '$red2', borderRadius: 8, marginBottom: 16 }}>
                    <Text style={{ color: '$red11', textAlign: 'center' }}>{error}</Text>
                </View>
            )}

            {/* Results */}
            {!loading && !error && (
                <>
                    {results.length > 0 ? (
                        <>
                            <Text style={{ color: '$gray11', marginBottom: 8 }}>
                                Found {results.length} memories
                            </Text>
                            <FlatList
                                data={results}
                                renderItem={renderResultItem}
                                keyExtractor={(item) => item.memory_id}
                                showsVerticalScrollIndicator={false}
                            />
                        </>
                    ) : query.trim() ? (
                        <EmptyState>
                            <Search size={48} color="#9ca3af" />
                            <Text style={{ color: '#6b7280', marginTop: 16, textAlign: 'center' }}>
                                No memories found for "{query}"
                            </Text>
                            <Text style={{ color: '#9ca3af', marginTop: 8, textAlign: 'center' }}>
                                Try different keywords or adjust filters
                            </Text>
                        </EmptyState>
                    ) : (
                        <EmptyState>
                            <Search size={48} color="#9ca3af" />
                            <Text style={{ color: '#6b7280', marginTop: 16, textAlign: 'center' }}>
                                Search your memories
                            </Text>
                            <Text style={{ color: '#9ca3af', marginTop: 8, textAlign: 'center' }}>
                                Find facts, commitments, preferences, and insights
                            </Text>
                        </EmptyState>
                    )}
                </>
            )}

            {/* Filter Modal */}
            <FilterModal
                visible={showFilters}
                onClose={() => setShowFilters(false)}
                filters={filters}
                onFiltersChange={handleFilterChange}
            />
        </Container>
    );
};

// =============================================================================
// Utility Functions
// =============================================================================

function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

export default MemorySearch;