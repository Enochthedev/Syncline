/**
 * ContactSuggestions Component
 * 
 * Displays search suggestions and recent contacts for mobile
 */

import React, { useCallback } from 'react';
import {
  View,
  FlatList,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact } from '../types';

interface ContactSuggestion {
  id: string;
  type: 'recent' | 'frequent' | 'suggested' | 'query';
  text: string;
  contact?: UnifiedContact;
  metadata?: {
    platform?: string;
    interaction_count?: number;
    last_interaction?: string;
  };
}

interface ContactSuggestionsProps {
  suggestions: ContactSuggestion[];
  recentContacts?: UnifiedContact[];
  onSuggestionSelect: (suggestion: ContactSuggestion) => void;
  onContactSelect: (contact: UnifiedContact) => void;
  isLoading?: boolean;
  maxSuggestions?: number;
  showRecentContacts?: boolean;
}

export const ContactSuggestions: React.FC<ContactSuggestionsProps> = ({
  suggestions,
  recentContacts = [],
  onSuggestionSelect,
  onContactSelect,
  isLoading = false,
  maxSuggestions = 5,
  showRecentContacts = true,
}) => {
  const { theme } = useTheme();

  // Get suggestion icon based on type
  const getSuggestionIcon = useCallback((type: string) => {
    switch (type) {
      case 'recent':
        return '🕒';
      case 'frequent':
        return '⭐';
      case 'suggested':
        return '💡';
      case 'query':
        return '🔍';
      default:
        return '👤';
    }
  }, []);

  // Get suggestion color based on type
  const getSuggestionColor = useCallback((type: string) => {
    switch (type) {
      case 'recent':
        return theme.colors.warning;
      case 'frequent':
        return theme.colors.success;
      case 'suggested':
        return theme.colors.info;
      case 'query':
        return theme.colors.primary;
      default:
        return theme.colors.textSecondary;
    }
  }, [theme]);

  // Render individual suggestion
  const renderSuggestion = useCallback(({ item }: { item: ContactSuggestion }) => (
    <TouchableOpacity
      style={[
        styles.suggestionItem,
        {
          backgroundColor: theme.colors.surface,
          borderColor: getSuggestionColor(item.type),
        },
      ]}
      onPress={() => onSuggestionSelect(item)}
    >
      <View style={styles.suggestionContent}>
        <Text style={styles.suggestionIcon}>
          {getSuggestionIcon(item.type)}
        </Text>
        <Text
          style={[styles.suggestionText, { color: theme.colors.text }]}
          numberOfLines={1}
        >
          {item.text}
        </Text>
        {item.metadata?.platform && (
          <Text
            style={[
              styles.suggestionPlatform,
              { color: getSuggestionColor(item.type) },
            ]}
          >
            {item.metadata.platform.toUpperCase()}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  ), [theme, getSuggestionIcon, getSuggestionColor, onSuggestionSelect]);

  // Render recent contact
  const renderRecentContact = useCallback(({ item }: { item: UnifiedContact }) => (
    <TouchableOpacity
      style={[
        styles.recentContactItem,
        { backgroundColor: theme.colors.surface },
      ]}
      onPress={() => onContactSelect(item)}
    >
      <View style={styles.recentContactContent}>
        {item.profilePhoto ? (
          <View style={styles.avatarContainer}>
            {/* Note: In a real implementation, you'd use Image component */}
            <View style={[styles.avatarPlaceholder, { backgroundColor: theme.colors.primary }]}>
              <Text style={[styles.avatarText, { color: theme.colors.white }]}>
                {item.displayName.charAt(0).toUpperCase()}
              </Text>
            </View>
          </View>
        ) : (
          <View style={[styles.avatarPlaceholder, { backgroundColor: theme.colors.primary }]}>
            <Text style={[styles.avatarText, { color: theme.colors.white }]}>
              {item.displayName.charAt(0).toUpperCase()}
            </Text>
          </View>
        )}
        <View style={styles.recentContactInfo}>
          <Text
            style={[styles.recentContactName, { color: theme.colors.text }]}
            numberOfLines={1}
          >
            {item.displayName}
          </Text>
          <Text
            style={[styles.recentContactMeta, { color: theme.colors.textSecondary }]}
            numberOfLines={1}
          >
            {item.totalMessages} messages
          </Text>
        </View>
        <View style={styles.recentContactIndicators}>
          {item.communicationFrequency === 'high' && (
            <View style={[styles.frequencyIndicator, { backgroundColor: theme.colors.success }]} />
          )}
          {item.platforms.length > 1 && (
            <Text style={[styles.platformCount, { color: theme.colors.textSecondary }]}>
              {item.platforms.length}
            </Text>
          )}
        </View>
      </View>
    </TouchableOpacity>
  ), [theme, onContactSelect]);

  // Key extractors
  const suggestionKeyExtractor = useCallback((item: ContactSuggestion) => item.id, []);
  const contactKeyExtractor = useCallback((item: UnifiedContact) => item.id, []);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={[styles.loadingText, { color: theme.colors.textSecondary }]}>
          Loading suggestions...
        </Text>
      </View>
    );
  }

  const displaySuggestions = suggestions.slice(0, maxSuggestions);
  const displayRecentContacts = recentContacts.slice(0, 5);

  return (
    <View style={styles.container}>
      {/* Search Suggestions */}
      {displaySuggestions.length > 0 && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.colors.textSecondary }]}>
            Suggestions
          </Text>
          <FlatList
            data={displaySuggestions}
            renderItem={renderSuggestion}
            keyExtractor={suggestionKeyExtractor}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.suggestionsList}
          />
        </View>
      )}

      {/* Recent Contacts */}
      {showRecentContacts && displayRecentContacts.length > 0 && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: theme.colors.textSecondary }]}>
            Recent Contacts
          </Text>
          <FlatList
            data={displayRecentContacts}
            renderItem={renderRecentContact}
            keyExtractor={contactKeyExtractor}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.recentContactsList}
          />
        </View>
      )}

      {/* Empty State */}
      {displaySuggestions.length === 0 && displayRecentContacts.length === 0 && (
        <View style={styles.emptyContainer}>
          <Text style={[styles.emptyText, { color: theme.colors.textSecondary }]}>
            Start typing to see suggestions
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingVertical: 8,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginBottom: 8,
    paddingHorizontal: 16,
  },
  suggestionsList: {
    paddingHorizontal: 16,
  },
  suggestionItem: {
    borderRadius: 20,
    borderWidth: 1,
    marginRight: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  suggestionContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  suggestionIcon: {
    fontSize: 14,
    marginRight: 6,
  },
  suggestionText: {
    fontSize: 14,
    fontWeight: '500',
    maxWidth: 120,
  },
  suggestionPlatform: {
    fontSize: 10,
    fontWeight: '600',
    marginLeft: 6,
  },
  recentContactsList: {
    paddingHorizontal: 16,
  },
  recentContactItem: {
    width: 120,
    marginRight: 12,
    borderRadius: 12,
    padding: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  recentContactContent: {
    alignItems: 'center',
  },
  avatarContainer: {
    marginBottom: 8,
  },
  avatarPlaceholder: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  avatarText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  recentContactInfo: {
    alignItems: 'center',
    marginBottom: 4,
  },
  recentContactName: {
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 2,
  },
  recentContactMeta: {
    fontSize: 10,
    textAlign: 'center',
  },
  recentContactIndicators: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  frequencyIndicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  platformCount: {
    fontSize: 10,
    fontWeight: '600',
  },
  loadingContainer: {
    padding: 16,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
  },
  emptyContainer: {
    padding: 16,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
  },
});