/**
 * Semantic Search Component
 * 
 * Advanced search interface with:
 * - Natural language queries
 * - Unified search across messages and memories
 * - Advanced filters and result ranking
 * - Search history and saved searches
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    FlatList, 
    TouchableOpacity, 
    ActivityIndicator,
    Modal,
    ScrollView
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Search, 
    Filter, 
    History, 
    Bookmark, 
    Star, 
    MessageCircle, 
    Brain,
    Calendar,
    User,
    X,
    ChevronDown,
    ChevronUp
} from '@tamagui/lucide-icons';
import { useAI } from '../../src/hooks/useAI';
import { 
    SemanticSearchResult, 
    MemorySearchResult, 
    SearchFilters, 
    SearchResults,
    Platform,
    MemoryType,
    MemoryImportance
} from '../../src/types';
import { PLATFORM_COLORS, PLATFORM_NAMES } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '$background',
});

const SearchHeader = styled(View, {
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
});

const SearchContainer = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$4',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginBottom: '$3',
});

const SearchInput = styled(TextInput, {
    flex: 1,
    fontSize: '$4',
    color: '$color',
    marginLeft: '$2',
});

const FilterButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginLeft: '$2',
});

const HistoryButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginLeft: '$2',
});

const ResultsContainer = styled(View, {
    flex: 1,
});

const SectionHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    backgroundColor: '$gray2',
});

const ResultItem = styled(TouchableOpacity, {
    backgroundColor: '$background',
    marginHorizontal: '$4',
    marginVertical: '$2',
    borderRadius: '$4',
    padding: '$4',
    borderLeftWidth: 4,
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
});

const ResultHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$2',
});

const ResultMeta = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: '$2',
});

const MetaChip = styled(View, {
    backgroundColor: '$gray3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
});

const ScoreChip = styled(View, {
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

const FilterModal: React.FC<FilterModalProps> = ({
    visible,
    onClose,
    filters,
    onFiltersChange,
}) => {
    const [localFilters, setLocalFilters] = useState<SearchFilters>(filters);

    useEffect(() => {
        setLocalFilters(filters);
    }, [filters]);

    const handleApply = useCallback(() => {
        onFiltersChange(localFilters);
        onClose();
    }, [localFilters, onFiltersChange, onClose]);

    const handleReset = useCallback(() => {
        const resetFilters: SearchFilters = {};
        setLocalFilters(resetFilters);
        onFiltersChange(resetFilters);
        onClose();
    }, [onFiltersChange, onClose]);

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={onClose}
        >
            <View style={{
                flex: 1,
                backgroundColor: 'rgba(0,0,0,0.5)',
                justifyContent: 'flex-end',
            }}>
                <View style={{
                    backgroundColor: '$background',
                    borderTopLeftRadius: 20,
                    borderTopRightRadius: 20,
                    maxHeight: '80%',
                }}>
                    <View style={{
                        flexDirection: 'row',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        paddingHorizontal: 20,
                        paddingVertical: 16,
                        borderBottomWidth: 1,
                        borderBottomColor: '$gray4',
                    }}>
                        <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                            Search Filters
                        </Text>
                        <TouchableOpacity onPress={onClose}>
                            <X size={24} color="$gray11" />
                        </TouchableOpacity>
                    </View>

                    <ScrollView style={{ maxHeight: 400 }}>
                        {/* Platforms */}
                        <View style={{ padding: 20 }}>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color', marginBottom: 12 }}>
                                Platforms
                            </Text>
                            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                                {Object.entries(PLATFORM_NAMES).map(([key, name]) => {
                                    const isSelected = localFilters.platforms?.includes(key as Platform);
                                    return (
                                        <TouchableOpacity
                                            key={key}
                                            onPress={() => {
                                                const platforms = localFilters.platforms || [];
                                                const newPlatforms = isSelected
                                                    ? platforms.filter(p => p !== key)
                                                    : [...platforms, key as Platform];
                                                setLocalFilters({
                                                    ...localFilters,
                                                    platforms: newPlatforms.length > 0 ? newPlatforms : undefined,
                                                });
                                            }}
                                            style={{
                                                flexDirection: 'row',
                                                alignItems: 'center',
                                                backgroundColor: isSelected ? PLATFORM_COLORS[key as Platform] + '20' : '$gray2',
                                                borderRadius: 8,
                                                paddingHorizontal: 12,
                                                paddingVertical: 8,
                                                marginRight: 8,
                                                marginBottom: 8,
                                                borderWidth: 1,
                                                borderColor: isSelected ? PLATFORM_COLORS[key as Platform] : 'transparent',
                                            }}
                                        >
                                            <View style={{
                                                width: 12,
                                                height: 12,
                                                borderRadius: 6,
                                                backgroundColor: PLATFORM_COLORS[key as Platform],
                                                marginRight: 6,
                                            }} />
                                            <Text style={{
                                                color: isSelected ? PLATFORM_COLORS[key as Platform] : '$gray11',
                                                fontWeight: isSelected ? '600' : 'normal',
                                            }}>
                                                {name}
                                            </Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>
                        </View>

                        {/* Memory Types */}
                        <View style={{ padding: 20, paddingTop: 0 }}>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color', marginBottom: 12 }}>
                                Memory Types
                            </Text>
                            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                                {(['fact', 'commitment', 'preference', 'relationship', 'personal', 'task', 'event', 'insight'] as MemoryType[]).map((type) => {
                                    const isSelected = localFilters.memory_types?.includes(type);
                                    return (
                                        <TouchableOpacity
                                            key={type}
                                            onPress={() => {
                                                const memoryTypes = localFilters.memory_types || [];
                                                const newTypes = isSelected
                                                    ? memoryTypes.filter(t => t !== type)
                                                    : [...memoryTypes, type];
                                                setLocalFilters({
                                                    ...localFilters,
                                                    memory_types: newTypes.length > 0 ? newTypes : undefined,
                                                });
                                            }}
                                            style={{
                                                backgroundColor: isSelected ? '$blue3' : '$gray2',
                                                borderRadius: 8,
                                                paddingHorizontal: 12,
                                                paddingVertical: 8,
                                                marginRight: 8,
                                                marginBottom: 8,
                                                borderWidth: 1,
                                                borderColor: isSelected ? '$blue8' : 'transparent',
                                            }}
                                        >
                                            <Text style={{
                                                color: isSelected ? '$blue11' : '$gray11',
                                                fontWeight: isSelected ? '600' : 'normal',
                                                textTransform: 'capitalize',
                                            }}>
                                                {type}
                                            </Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>
                        </View>

                        {/* Date Range */}
                        <View style={{ padding: 20, paddingTop: 0 }}>
                            <Text style={{ fontSize: 16, fontWeight: '600', color: '$color', marginBottom: 12 }}>
                                Date Range
                            </Text>
                            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
                                {[
                                    { label: 'Today', days: 1 },
                                    { label: 'This Week', days: 7 },
                                    { label: 'This Month', days: 30 },
                                    { label: 'This Year', days: 365 },
                                ].map((range) => {
                                    const endDate = new Date();
                                    const startDate = new Date();
                                    startDate.setDate(endDate.getDate() - range.days);
                                    
                                    const isSelected = localFilters.date_range?.start === startDate.toISOString().split('T')[0];
                                    
                                    return (
                                        <TouchableOpacity
                                            key={range.label}
                                            onPress={() => {
                                                setLocalFilters({
                                                    ...localFilters,
                                                    date_range: isSelected ? undefined : {
                                                        start: startDate.toISOString().split('T')[0],
                                                        end: endDate.toISOString().split('T')[0],
                                                    },
                                                });
                                            }}
                                            style={{
                                                backgroundColor: isSelected ? '$green3' : '$gray2',
                                                borderRadius: 8,
                                                paddingHorizontal: 12,
                                                paddingVertical: 8,
                                                marginRight: 8,
                                                marginBottom: 8,
                                                borderWidth: 1,
                                                borderColor: isSelected ? '$green8' : 'transparent',
                                            }}
                                        >
                                            <Text style={{
                                                color: isSelected ? '$green11' : '$gray11',
                                                fontWeight: isSelected ? '600' : 'normal',
                                            }}>
                                                {range.label}
                                            </Text>
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>
                        </View>
                    </ScrollView>

                    <View style={{
                        flexDirection: 'row',
                        justifyContent: 'space-between',
                        paddingHorizontal: 20,
                        paddingVertical: 16,
                        borderTopWidth: 1,
                        borderTopColor: '$gray4',
                    }}>
                        <TouchableOpacity
                            onPress={handleReset}
                            style={{
                                backgroundColor: '$gray3',
                                borderRadius: 8,
                                paddingHorizontal: 20,
                                paddingVertical: 12,
                            }}
                        >
                            <Text style={{ color: '$gray11', fontWeight: '500' }}>Reset</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            onPress={handleApply}
                            style={{
                                backgroundColor: '$blue8',
                                borderRadius: 8,
                                paddingHorizontal: 20,
                                paddingVertical: 12,
                            }}
                        >
                            <Text style={{ color: 'white', fontWeight: '500' }}>Apply Filters</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </Modal>
    );
};

// =============================================================================
// Main Component
// =============================================================================

interface SemanticSearchProps {
    onResultSelect?: (result: SemanticSearchResult | MemorySearchResult, type: 'message' | 'memory') => void;
    placeholder?: string;
    maxResults?: number;
}

export const SemanticSearch: React.FC<SemanticSearchProps> = ({
    onResultSelect,
    placeholder = "Search messages and memories...",
    maxResults = 20,
}) => {
    const [query, setQuery] = useState('');
    const [filters, setFilters] = useState<SearchFilters>({});
    const [showFilters, setShowFilters] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [searchHistory, setSearchHistory] = useState<string[]>([]);
    const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
        messages: true,
        memories: true,
    });

    const { unifiedSearch, loading, error } = useAI();
    const [results, setResults] = useState<SearchResults | null>(null);

    // Debounced search
    const debouncedSearch = useCallback(
        debounce(async (searchQuery: string, searchFilters: SearchFilters) => {
            if (searchQuery.trim()) {
                try {
                    const searchResults = await unifiedSearch(searchQuery, searchFilters, maxResults);
                    setResults(searchResults);
                    
                    // Add to search history
                    setSearchHistory(prev => {
                        const newHistory = [searchQuery, ...prev.filter(q => q !== searchQuery)].slice(0, 10);
                        return newHistory;
                    });
                } catch (err) {
                    console.error('Search failed:', err);
                    setResults(null);
                }
            } else {
                setResults(null);
            }
        }, 300),
        [unifiedSearch, maxResults]
    );

    const handleQueryChange = useCallback((text: string) => {
        setQuery(text);
        debouncedSearch(text, filters);
    }, [debouncedSearch, filters]);

    const handleFilterChange = useCallback((newFilters: SearchFilters) => {
        setFilters(newFilters);
        if (query.trim()) {
            debouncedSearch(query, newFilters);
        }
    }, [query, debouncedSearch]);

    const handleHistorySelect = useCallback((historyQuery: string) => {
        setQuery(historyQuery);
        setShowHistory(false);
        debouncedSearch(historyQuery, filters);
    }, [debouncedSearch, filters]);

    // Toggle section expansion
    const toggleSection = useCallback((section: string) => {
        setExpandedSections(prev => ({
            ...prev,
            [section]: !prev[section],
        }));
    }, []);

    // Highlight search terms in text
    const highlightText = useCallback((text: string, searchQuery: string) => {
        if (!searchQuery.trim()) return text;

        const terms = searchQuery.toLowerCase().split(' ').filter(term => term.length > 2);
        let highlightedText = text;

        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlightedText = highlightedText.replace(regex, '**$1**');
        });

        const parts = highlightedText.split('**');
        return parts.map((part, index) => 
            index % 2 === 1 ? (
                <HighlightedText key={index}>{part}</HighlightedText>
            ) : (
                <Text key={index}>{part}</Text>
            )
        );
    }, []);

    // Render message result
    const renderMessageResult = useCallback(({ item }: { item: SemanticSearchResult }) => (
        <ResultItem
            onPress={() => onResultSelect?.(item, 'message')}
            style={{ borderLeftColor: PLATFORM_COLORS[item.platform] }}
        >
            <ResultHeader>
                <View style={{ flex: 1 }}>
                    <ResultMeta>
                        <MetaChip>
                            <Text style={{ fontSize: 12, color: '$gray11' }}>
                                {PLATFORM_NAMES[item.platform]}
                            </Text>
                        </MetaChip>
                        <MetaChip>
                            <Text style={{ fontSize: 12, color: '$gray11' }}>
                                {item.sender}
                            </Text>
                        </MetaChip>
                        <MetaChip>
                            <Text style={{ fontSize: 12, color: '$gray11' }}>
                                {new Date(item.timestamp).toLocaleDateString()}
                            </Text>
                        </MetaChip>
                    </ResultMeta>
                </View>
                <ScoreChip>
                    <Text style={{ fontSize: 12, color: '$green11' }}>
                        {Math.round(item.similarity_score * 100)}%
                    </Text>
                </ScoreChip>
            </ResultHeader>
            
            <SnippetText>
                {highlightText(item.snippet, query)}
            </SnippetText>
        </ResultItem>
    ), [onResultSelect, highlightText, query]);

    // Render memory result
    const renderMemoryResult = useCallback(({ item }: { item: MemorySearchResult }) => (
        <ResultItem
            onPress={() => onResultSelect?.(item, 'memory')}
            style={{ borderLeftColor: '$purple8' }}
        >
            <ResultHeader>
                <View style={{ flex: 1 }}>
                    <ResultMeta>
                        <MetaChip>
                            <Text style={{ fontSize: 12, color: '$gray11', textTransform: 'capitalize' }}>
                                {item.memory_type}
                            </Text>
                        </MetaChip>
                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                            {Array.from({ length: item.importance }, (_, i) => (
                                <Star key={i} size={10} color="$yellow9" fill="$yellow9" />
                            ))}
                        </View>
                    </ResultMeta>
                </View>
                <ScoreChip>
                    <Text style={{ fontSize: 12, color: '$green11' }}>
                        {Math.round(item.relevance_score * 100)}%
                    </Text>
                </ScoreChip>
            </ResultHeader>
            
            <SnippetText>
                {highlightText(item.snippet, query)}
            </SnippetText>
        </ResultItem>
    ), [onResultSelect, highlightText, query]);

    // Active filters count
    const activeFiltersCount = useMemo(() => {
        let count = 0;
        if (filters.platforms?.length) count++;
        if (filters.memory_types?.length) count++;
        if (filters.date_range) count++;
        if (filters.has_attachments !== undefined) count++;
        if (filters.sentiment) count++;
        if (filters.importance_min) count++;
        return count;
    }, [filters]);

    return (
        <Container>
            {/* Search Header */}
            <SearchHeader>
                <SearchContainer>
                    <Brain size={20} color="$purple9" />
                    <SearchInput
                        value={query}
                        onChangeText={handleQueryChange}
                        placeholder={placeholder}
                        placeholderTextColor="$gray9"
                        autoCapitalize="none"
                        autoCorrect={false}
                    />
                    <HistoryButton onPress={() => setShowHistory(!showHistory)}>
                        <History size={16} color="$gray11" />
                    </HistoryButton>
                    <FilterButton onPress={() => setShowFilters(true)}>
                        <Filter size={16} color="$blue11" />
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

                {/* Search History */}
                {showHistory && searchHistory.length > 0 && (
                    <View style={{ backgroundColor: '$gray1', borderRadius: 8, padding: 12, marginTop: 8 }}>
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '$color', marginBottom: 8 }}>
                            Recent Searches
                        </Text>
                        {searchHistory.map((historyQuery, index) => (
                            <TouchableOpacity
                                key={index}
                                onPress={() => handleHistorySelect(historyQuery)}
                                style={{
                                    flexDirection: 'row',
                                    alignItems: 'center',
                                    paddingVertical: 6,
                                }}
                            >
                                <History size={14} color="$gray9" />
                                <Text style={{ marginLeft: 8, color: '$gray11', flex: 1 }}>
                                    {historyQuery}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                )}
            </SearchHeader>

            {/* Loading State */}
            {loading && (
                <LoadingContainer>
                    <ActivityIndicator size="small" color="$purple9" />
                    <Text style={{ marginLeft: 8, color: '$gray11' }}>Searching...</Text>
                </LoadingContainer>
            )}

            {/* Error State */}
            {error && (
                <View style={{ padding: 16, backgroundColor: '$red2', borderRadius: 8, margin: 16 }}>
                    <Text style={{ color: '$red11', textAlign: 'center' }}>{error}</Text>
                </View>
            )}

            {/* Results */}
            {!loading && !error && results && (
                <ResultsContainer>
                    <ScrollView showsVerticalScrollIndicator={false}>
                        {/* Messages Section */}
                        {results.messages.length > 0 && (
                            <>
                                <SectionHeader>
                                    <TouchableOpacity
                                        onPress={() => toggleSection('messages')}
                                        style={{ flexDirection: 'row', alignItems: 'center' }}
                                    >
                                        <MessageCircle size={20} color="$blue9" />
                                        <Text style={{ marginLeft: 8, fontSize: 16, fontWeight: '600', color: '$color' }}>
                                            Messages ({results.total_messages})
                                        </Text>
                                        {expandedSections.messages ? (
                                            <ChevronUp size={20} color="$gray9" style={{ marginLeft: 8 }} />
                                        ) : (
                                            <ChevronDown size={20} color="$gray9" style={{ marginLeft: 8 }} />
                                        )}
                                    </TouchableOpacity>
                                </SectionHeader>
                                {expandedSections.messages && (
                                    <FlatList
                                        data={results.messages}
                                        renderItem={renderMessageResult}
                                        keyExtractor={(item) => item.message_id}
                                        scrollEnabled={false}
                                    />
                                )}
                            </>
                        )}

                        {/* Memories Section */}
                        {results.memories.length > 0 && (
                            <>
                                <SectionHeader>
                                    <TouchableOpacity
                                        onPress={() => toggleSection('memories')}
                                        style={{ flexDirection: 'row', alignItems: 'center' }}
                                    >
                                        <Brain size={20} color="$purple9" />
                                        <Text style={{ marginLeft: 8, fontSize: 16, fontWeight: '600', color: '$color' }}>
                                            Memories ({results.total_memories})
                                        </Text>
                                        {expandedSections.memories ? (
                                            <ChevronUp size={20} color="$gray9" style={{ marginLeft: 8 }} />
                                        ) : (
                                            <ChevronDown size={20} color="$gray9" style={{ marginLeft: 8 }} />
                                        )}
                                    </TouchableOpacity>
                                </SectionHeader>
                                {expandedSections.memories && (
                                    <FlatList
                                        data={results.memories}
                                        renderItem={renderMemoryResult}
                                        keyExtractor={(item) => item.memory_id}
                                        scrollEnabled={false}
                                    />
                                )}
                            </>
                        )}

                        {/* Query Stats */}
                        <View style={{ padding: 16, alignItems: 'center' }}>
                            <Text style={{ color: '$gray9', fontSize: 12 }}>
                                Found {results.total_messages + results.total_memories} results in {results.query_time_ms}ms
                            </Text>
                        </View>
                    </ScrollView>
                </ResultsContainer>
            )}

            {/* Empty State */}
            {!loading && !error && (!results || (results.messages.length === 0 && results.memories.length === 0)) && query.trim() && (
                <EmptyState>
                    <Search size={48} color="$gray8" />
                    <Text style={{ color: '$gray11', marginTop: 16, textAlign: 'center' }}>
                        No results found for "{query}"
                    </Text>
                    <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                        Try different keywords or adjust filters
                    </Text>
                </EmptyState>
            )}

            {/* Default State */}
            {!loading && !error && !query.trim() && (
                <EmptyState>
                    <Brain size={48} color="$purple8" />
                    <Text style={{ color: '$gray11', marginTop: 16, textAlign: 'center' }}>
                        Semantic Search
                    </Text>
                    <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                        Search messages and memories using natural language
                    </Text>
                </EmptyState>
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

export default SemanticSearch;