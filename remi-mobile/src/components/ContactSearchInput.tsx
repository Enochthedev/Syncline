/**
 * ContactSearchInput Component
 * 
 * Real-time contact search input with fuzzy matching and suggestions
 * Integrates with the contact auto-search API endpoints
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  Keyboard,
} from 'react-native';
import { useDebounce } from '../hooks/useDebounce';
import { useContactSearchWithSuggestions, useContactSearchErrorHandler } from '../hooks/useContactSearch';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { usePerformance } from '../contexts/PerformanceContext';
import { useRenderPerformance, useAsyncPerformance } from '../hooks/usePerformanceMonitoring';
import OptimizedFlatList from './OptimizedFlatList';
import { ContactSuggestion } from './ContactSuggestion';
import { useTheme } from '../hooks/useTheme';
import { ErrorBoundary } from './ErrorBoundary';

interface ContactSearchInputProps {
  onContactSelect: (contact: any) => void;
  onSearchResults: (results: any[]) => void;
  placeholder?: string;
  autoFocus?: boolean;
  showSuggestions?: boolean;
}

export const ContactSearchInput: React.FC<ContactSearchInputProps> = ({
  onContactSelect,
  onSearchResults,
  placeholder = "Search contacts...",
  autoFocus = false,
  showSuggestions = true,
}) => {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const { theme } = useTheme();
  const { isOnline } = useNetworkStatus();
  const { handleError } = useContactSearchErrorHandler();
  
  // Performance monitoring
  const { recordSearchResponse, measureAsync } = usePerformance();
  const { measureAsync: measureAsyncPerf } = useAsyncPerformance();
  useRenderPerformance('ContactSearchInput');

  // Enhanced contact search with suggestions
  const {
    contacts,
    suggestions,
    isSearching,
    isLoading,
    searchError,
    hasError,
    refetchSearch,
  } = useContactSearchWithSuggestions(debouncedQuery, {
    enabled: isOnline,
  });

  // Update parent with search results
  useEffect(() => {
    onSearchResults(contacts);
  }, [contacts, onSearchResults]);

  // Handle text input changes
  const handleQueryChange = useCallback((text: string) => {
    setQuery(text);
    setShowResults(text.length >= 2);
  }, []);

  // Handle contact selection with performance tracking
  const handleContactSelect = useCallback(async (contact: any) => {
    await measureAsyncPerf(async () => {
      setQuery(contact.primary_name || contact.display_name);
      setShowResults(false);
      Keyboard.dismiss();
      onContactSelect(contact);
    }, 'contact_selection');
  }, [onContactSelect, measureAsyncPerf]);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: any) => {
    if (suggestion.contact_id) {
      // If suggestion has a contact, select it
      const contact = contacts.find((c: any) => c.id === suggestion.contact_id);
      if (contact) {
        handleContactSelect(contact);
      }
    } else {
      // If it's a text suggestion, update query
      setQuery(suggestion.text);
    }
  }, [contacts, handleContactSelect]);

  // Clear search
  const handleClear = useCallback(() => {
    setQuery('');
    setShowResults(false);
    onSearchResults([]);
  }, [onSearchResults]);

  // Handle retry for failed searches
  const handleRetry = useCallback(() => {
    refetchSearch();
  }, [refetchSearch]);

  // Highlight matching text
  const highlightText = useCallback((text: string, query: string) => {
    if (!query || query.length < 2) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => {
      if (part.toLowerCase() === query.toLowerCase()) {
        return (
          <Text key={index} style={[styles.highlightedText, { backgroundColor: theme.colors.primary, color: theme.colors.white }]}>
            {part}
          </Text>
        );
      }
      return part;
    });
  }, [theme]);

  // Render search result item
  const renderSearchResult = useCallback(({ item }: { item: any }) => (
    <TouchableOpacity
      style={[styles.resultItem, { borderBottomColor: theme.colors.border }]}
      onPress={() => handleContactSelect(item)}
    >
      <View style={styles.contactInfo}>
        <Text style={[styles.contactName, { color: theme.colors.text }]}>
          {highlightText(item.primary_name || item.display_name, debouncedQuery)}
        </Text>
        {item.primary_email && (
          <Text style={[styles.contactEmail, { color: theme.colors.textSecondary }]}>
            {highlightText(item.primary_email, debouncedQuery)}
          </Text>
        )}
        <View style={styles.platformIndicators}>
          {item.platforms?.map((platform: string) => (
            <View
              key={platform}
              style={[styles.platformBadge, { backgroundColor: theme.colors.primary }]}
            >
              <Text style={[styles.platformText, { color: theme.colors.white }]}>
                {platform.toUpperCase()}
              </Text>
            </View>
          ))}
        </View>
      </View>
      <View style={styles.resultActions}>
        {item.interaction_indicators?.has_recent_messages && (
          <View style={[styles.recentIndicator, { backgroundColor: theme.colors.success }]} />
        )}
        {item.total_messages && (
          <Text style={[styles.messageCount, { color: theme.colors.textSecondary }]}>
            {item.total_messages}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  ), [theme, handleContactSelect, highlightText, debouncedQuery]);

  // Render suggestion item
  const renderSuggestion = useCallback(({ item }: { item: any }) => (
    <ContactSuggestion
      suggestion={item}
      onSelect={handleSuggestionSelect}
    />
  ), [handleSuggestionSelect]);

  return (
    <ErrorBoundary>
      <View style={styles.container}>
        {/* Search Input */}
        <View style={[styles.inputContainer, { backgroundColor: theme.colors.surface }]}>
          <TextInput
            style={[styles.input, { color: theme.colors.text }]}
            value={query}
            onChangeText={handleQueryChange}
            placeholder={placeholder}
            placeholderTextColor={theme.colors.textSecondary}
            autoFocus={autoFocus}
            autoCorrect={false}
            autoCapitalize="words"
            editable={isOnline}
          />
          {(isLoading || isSearching) && (
            <ActivityIndicator
              size="small"
              color={theme.colors.primary}
              style={styles.loadingIndicator}
            />
          )}
          {query.length > 0 && (
            <TouchableOpacity onPress={handleClear} style={styles.clearButton}>
              <Text style={[styles.clearText, { color: theme.colors.textSecondary }]}>
                ✕
              </Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Offline indicator */}
        {!isOnline && (
          <View style={[styles.offlineIndicator, { backgroundColor: theme.colors.warning }]}>
            <Text style={[styles.offlineText, { color: theme.colors.white }]}>
              Offline - Search unavailable
            </Text>
          </View>
        )}

        {/* Search Results */}
        {showResults && (
          <View style={[styles.resultsContainer, { backgroundColor: theme.colors.surface }]}>
            {hasError && (
              <View style={styles.errorContainer}>
                <Text style={[styles.errorText, { color: theme.colors.error }]}>
                  {handleError(searchError)}
                </Text>
                <TouchableOpacity onPress={handleRetry} style={styles.retryButton}>
                  <Text style={[styles.retryText, { color: theme.colors.primary }]}>
                    Try Again
                  </Text>
                </TouchableOpacity>
              </View>
            )}

            {contacts && contacts.length > 0 && (
              <OptimizedFlatList
                data={contacts}
                renderItem={renderSearchResult}
                keyExtractor={(item) => item.id}
                style={styles.resultsList}
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={false}
                enableVirtualization={true}
                enableImageOptimization={true}
                enableMemoryOptimization={true}
                estimatedItemSize={80}
                maxToRenderPerBatch={10}
                windowSize={5}
              />
            )}

            {showSuggestions && suggestions && suggestions.length > 0 && (
              <View style={styles.suggestionsSection}>
                <Text style={[styles.sectionTitle, { color: theme.colors.textSecondary }]}>
                  Suggestions
                </Text>
                <OptimizedFlatList
                  data={suggestions}
                  renderItem={renderSuggestion}
                  keyExtractor={(item, index) => `suggestion-${index}`}
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  style={styles.suggestionsList}
                  enableVirtualization={false}
                  enableImageOptimization={false}
                  enableMemoryOptimization={false}
                />
              </View>
            )}

            {debouncedQuery.length >= 2 && 
             !isLoading && 
             !isSearching &&
             !hasError &&
             (!contacts || contacts.length === 0) && (
              <View style={styles.noResultsContainer}>
                <Text style={[styles.noResultsText, { color: theme.colors.textSecondary }]}>
                  No contacts found for "{debouncedQuery}"
                </Text>
              </View>
            )}
          </View>
        )}
      </View>
    </ErrorBoundary>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    zIndex: 1000,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: '400',
  },
  loadingIndicator: {
    marginLeft: 8,
  },
  clearButton: {
    padding: 4,
    marginLeft: 8,
  },
  clearText: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  resultsContainer: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    borderRadius: 12,
    marginTop: 4,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    maxHeight: 400,
  },
  resultsList: {
    maxHeight: 250,
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  contactInfo: {
    flex: 1,
  },
  contactName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  contactEmail: {
    fontSize: 14,
    marginBottom: 4,
  },
  platformIndicators: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  platformBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: 4,
    marginTop: 2,
  },
  platformText: {
    fontSize: 10,
    fontWeight: '600',
  },
  resultActions: {
    alignItems: 'center',
  },
  recentIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginBottom: 4,
  },
  messageCount: {
    fontSize: 10,
    fontWeight: '600',
  },
  highlightedText: {
    paddingHorizontal: 2,
    borderRadius: 2,
  },
  suggestionsSection: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  suggestionsList: {
    flexGrow: 0,
  },
  errorContainer: {
    padding: 16,
    alignItems: 'center',
  },
  errorText: {
    fontSize: 14,
    textAlign: 'center',
  },
  noResultsContainer: {
    padding: 16,
    alignItems: 'center',
  },
  noResultsText: {
    fontSize: 14,
    textAlign: 'center',
  },
  offlineIndicator: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginTop: 4,
    alignItems: 'center',
  },
  offlineText: {
    fontSize: 12,
    fontWeight: '600',
  },
  retryButton: {
    marginTop: 8,
    paddingVertical: 4,
    paddingHorizontal: 12,
  },
  retryText: {
    fontSize: 14,
    fontWeight: '600',
  },
});