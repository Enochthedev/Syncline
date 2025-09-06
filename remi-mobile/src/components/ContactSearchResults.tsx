/**
 * ContactSearchResults Component
 * 
 * Displays contact search results with contact cards and interaction indicators
 */

import React, { useCallback } from 'react';
import {
  View,
  FlatList,
  Text,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { ContactCard } from './ContactCard';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact } from '../types';

interface ContactSearchResultsProps {
  results: UnifiedContact[];
  query: string;
  isLoading: boolean;
  error?: string | null;
  onContactSelect: (contact: UnifiedContact) => void;
  onRefresh?: () => void;
  showDetails?: boolean;
  emptyMessage?: string;
}

export const ContactSearchResults: React.FC<ContactSearchResultsProps> = ({
  results,
  query,
  isLoading,
  error,
  onContactSelect,
  onRefresh,
  showDetails = true,
  emptyMessage,
}) => {
  const { theme } = useTheme();

  // Render individual contact result
  const renderContactResult = useCallback(({ item }: { item: UnifiedContact }) => (
    <ContactCard
      contact={item}
      onPress={onContactSelect}
      showDetails={showDetails}
    />
  ), [onContactSelect, showDetails]);

  // Render empty state
  const renderEmptyState = useCallback(() => {
    if (isLoading) {
      return null;
    }

    if (error) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={[styles.emptyIcon, { color: theme.colors.error }]}>
            ⚠️
          </Text>
          <Text style={[styles.emptyTitle, { color: theme.colors.error }]}>
            Search Error
          </Text>
          <Text style={[styles.emptyMessage, { color: theme.colors.textSecondary }]}>
            {error}
          </Text>
        </View>
      );
    }

    if (query.length >= 2) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={[styles.emptyIcon, { color: theme.colors.textSecondary }]}>
            🔍
          </Text>
          <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
            No contacts found
          </Text>
          <Text style={[styles.emptyMessage, { color: theme.colors.textSecondary }]}>
            {emptyMessage || `No contacts match "${query}"`}
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.emptyContainer}>
        <Text style={[styles.emptyIcon, { color: theme.colors.textSecondary }]}>
          👥
        </Text>
        <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
          Search Contacts
        </Text>
        <Text style={[styles.emptyMessage, { color: theme.colors.textSecondary }]}>
          Type at least 2 characters to search for contacts
        </Text>
      </View>
    );
  }, [isLoading, error, query, emptyMessage, theme]);

  // Render header with result count
  const renderHeader = useCallback(() => {
    if (!query || results.length === 0) {
      return null;
    }

    return (
      <View style={styles.headerContainer}>
        <Text style={[styles.resultCount, { color: theme.colors.textSecondary }]}>
          {results.length} contact{results.length !== 1 ? 's' : ''} found for "{query}"
        </Text>
      </View>
    );
  }, [query, results.length, theme]);

  // Key extractor for FlatList
  const keyExtractor = useCallback((item: UnifiedContact) => item.id, []);

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <FlatList
        data={results}
        renderItem={renderContactResult}
        keyExtractor={keyExtractor}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={renderEmptyState}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={isLoading}
              onRefresh={onRefresh}
              tintColor={theme.colors.primary}
              colors={[theme.colors.primary]}
            />
          ) : undefined
        }
        contentContainerStyle={[
          styles.listContainer,
          results.length === 0 && styles.emptyListContainer,
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        removeClippedSubviews={true}
        maxToRenderPerBatch={10}
        windowSize={10}
        initialNumToRender={10}
        getItemLayout={(data, index) => ({
          length: 120, // Approximate height of ContactCard
          offset: 120 * index,
          index,
        })}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  listContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  emptyListContainer: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  headerContainer: {
    paddingVertical: 8,
    paddingHorizontal: 4,
    marginBottom: 8,
  },
  resultCount: {
    fontSize: 14,
    fontWeight: '500',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
    paddingHorizontal: 32,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyMessage: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
});