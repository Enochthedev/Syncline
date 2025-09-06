/**
 * ContactSearchContainer Component
 * 
 * Container component that integrates all contact search functionality
 * with API integration and state management
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { ContactSearchInput } from './ContactSearchInput';
import { ContactSearchResults } from './ContactSearchResults';
import { ContactSuggestions } from './ContactSuggestions';
import { useDebounce } from '../hooks/useDebounce';
import { useTheme } from '../hooks/useTheme';
import { contactSearchService } from '../services/contactSearchService';
import { UnifiedContact } from '../types';

interface ContactSearchContainerProps {
  onContactSelect: (contact: UnifiedContact) => void;
  initialQuery?: string;
  autoFocus?: boolean;
  showSuggestions?: boolean;
  showRecentContacts?: boolean;
  placeholder?: string;
}

export const ContactSearchContainer: React.FC<ContactSearchContainerProps> = ({
  onContactSelect,
  initialQuery = '',
  autoFocus = false,
  showSuggestions = true,
  showRecentContacts = true,
  placeholder = "Search contacts...",
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState<UnifiedContact[]>([]);
  const [showResults, setShowResults] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const { theme } = useTheme();

  // Real-time contact search
  const {
    data: searchData,
    isLoading: isSearchLoading,
    error: searchError,
    refetch: refetchSearch,
  } = useQuery({
    queryKey: ['contactSearch', debouncedQuery],
    queryFn: () => contactSearchService.searchContactsRealtime(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30000,
    retry: 2,
  });

  // Search suggestions
  const {
    data: suggestionsData,
    isLoading: isSuggestionsLoading,
  } = useQuery({
    queryKey: ['contactSuggestions', debouncedQuery],
    queryFn: () => contactSearchService.getSearchSuggestions(debouncedQuery),
    enabled: debouncedQuery.length >= 1 && showSuggestions,
    staleTime: 60000,
  });

  // Recent contacts (mock data for now)
  const {
    data: recentContactsData,
  } = useQuery({
    queryKey: ['recentContacts'],
    queryFn: async () => {
      // This would be replaced with actual API call
      return [];
    },
    enabled: showRecentContacts && query.length === 0,
    staleTime: 300000, // 5 minutes
  });

  // Update search results when data changes
  useEffect(() => {
    if (searchData?.contacts) {
      setSearchResults(searchData.contacts);
      setShowResults(true);
    } else {
      setSearchResults([]);
      setShowResults(debouncedQuery.length >= 2);
    }
  }, [searchData, debouncedQuery]);

  // Handle query changes
  const handleQueryChange = useCallback((newQuery: string) => {
    setQuery(newQuery);
    if (newQuery.length < 2) {
      setShowResults(false);
      setSearchResults([]);
    }
  }, []);

  // Handle contact selection
  const handleContactSelect = useCallback((contact: UnifiedContact) => {
    setQuery(contact.displayName);
    setShowResults(false);
    onContactSelect(contact);
  }, [onContactSelect]);

  // Handle search results update
  const handleSearchResults = useCallback((results: UnifiedContact[]) => {
    setSearchResults(results);
  }, []);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: any) => {
    if (suggestion.contact) {
      handleContactSelect(suggestion.contact);
    } else {
      setQuery(suggestion.text);
    }
  }, [handleContactSelect]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refetchSearch();
  }, [refetchSearch]);

  // Transform suggestions data
  const transformedSuggestions = suggestionsData?.map((suggestion: any, index: number) => ({
    id: `suggestion-${index}`,
    type: suggestion.type || 'query',
    text: suggestion.text || suggestion.query,
    contact: suggestion.contact,
    metadata: suggestion.metadata,
  })) || [];

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 64 : 0}
    >
      <View style={styles.searchContainer}>
        <ContactSearchInput
          onContactSelect={handleContactSelect}
          onSearchResults={handleSearchResults}
          placeholder={placeholder}
          autoFocus={autoFocus}
          showSuggestions={showSuggestions}
        />
      </View>

      {/* Show suggestions when not searching */}
      {!showResults && (showSuggestions || showRecentContacts) && (
        <View style={styles.suggestionsContainer}>
          <ContactSuggestions
            suggestions={transformedSuggestions}
            recentContacts={recentContactsData || []}
            onSuggestionSelect={handleSuggestionSelect}
            onContactSelect={handleContactSelect}
            isLoading={isSuggestionsLoading}
            showRecentContacts={showRecentContacts}
          />
        </View>
      )}

      {/* Show search results when searching */}
      {showResults && (
        <View style={styles.resultsContainer}>
          <ContactSearchResults
            results={searchResults}
            query={debouncedQuery}
            isLoading={isSearchLoading}
            error={searchError?.message}
            onContactSelect={handleContactSelect}
            onRefresh={handleRefresh}
            showDetails={true}
          />
        </View>
      )}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    zIndex: 1000,
  },
  suggestionsContainer: {
    flex: 1,
  },
  resultsContainer: {
    flex: 1,
  },
});