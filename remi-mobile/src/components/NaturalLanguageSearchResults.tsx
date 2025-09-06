/**
 * Natural Language Search Results Component
 * 
 * Displays search results with highlighting, intent-based grouping,
 * and quick actions based on detected entities.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '@/hooks/useTheme';
import { SearchResult, UnifiedContact } from '@/types';

export interface NaturalLanguageSearchResultsProps {
  results: SearchResult[];
  query: string;
  intent?: string;
  entities?: any[];
  onResultPress: (result: SearchResult) => void;
  onContactPress?: (contact: UnifiedContact) => void;
  onQuickActionPress?: (action: string, result: SearchResult) => void;
  loading?: boolean;
  emptyMessage?: string;
}

export function NaturalLanguageSearchResults({
  results,
  query,
  intent,
  entities = [],
  onResultPress,
  onContactPress,
  onQuickActionPress,
  loading = false,
  emptyMessage = 'No results found for your query',
}: NaturalLanguageSearchResultsProps) {
  const { colors } = useTheme();
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  // Group results by type for better organization
  const groupedResults = useCallback(() => {
    const groups: Record<string, SearchResult[]> = {};
    
    results.forEach(result => {
      const type = result.type;
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(result);
    });

    return groups;
  }, [results]);

  // Toggle expanded state for a result
  const toggleExpanded = useCallback((resultId: string) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev);
      if (newSet.has(resultId)) {
        newSet.delete(resultId);
      } else {
        newSet.add(resultId);
      }
      return newSet;
    });
  }, []);

  // Handle quick action press
  const handleQuickAction = useCallback((action: string, result: SearchResult) => {
    onQuickActionPress?.(action, result);
  }, [onQuickActionPress]);

  // Render highlighted text
  const renderHighlightedText = useCallback((text: string, highlights: any[] = []) => {
    if (!highlights.length) {
      return <Text style={[styles.resultContent, { color: colors.text }]}>{text}</Text>;
    }

    const parts: Array<{ text: string; highlighted: boolean }> = [];
    let lastIndex = 0;

    highlights.forEach(highlight => {
      // Add non-highlighted text before this highlight
      if (highlight.start > lastIndex) {
        parts.push({
          text: text.substring(lastIndex, highlight.start),
          highlighted: false,
        });
      }

      // Add highlighted text
      parts.push({
        text: text.substring(highlight.start, highlight.end),
        highlighted: true,
      });

      lastIndex = highlight.end;
    });

    // Add remaining non-highlighted text
    if (lastIndex < text.length) {
      parts.push({
        text: text.substring(lastIndex),
        highlighted: false,
      });
    }

    return (
      <Text style={[styles.resultContent, { color: colors.text }]}>
        {parts.map((part, index) => (
          <Text
            key={index}
            style={part.highlighted ? [styles.highlightedText, { backgroundColor: colors.primaryLight, color: colors.primary }] : undefined}
          >
            {part.text}
          </Text>
        ))}
      </Text>
    );
  }, [colors]);

  // Render result item
  const renderResultItem = useCallback((result: SearchResult) => {
    const isExpanded = expandedResults.has(result.id);
    const showExpandButton = result.content && result.content.length > 200;

    return (
      <TouchableOpacity
        key={result.id}
        style={[styles.resultItem, { backgroundColor: colors.surface, borderColor: colors.border }]}
        onPress={() => onResultPress(result)}
        activeOpacity={0.7}
      >
        {/* Result Header */}
        <View style={styles.resultHeader}>
          <View style={styles.resultTypeIcon}>
            <Icon
              name={getResultTypeIcon(result.type)}
              size={16}
              color={colors.primary}
            />
          </View>
          
          <View style={styles.resultHeaderContent}>
            <Text style={[styles.resultTitle, { color: colors.text }]} numberOfLines={2}>
              {result.title}
            </Text>
            
            <View style={styles.resultMeta}>
              {result.platform && (
                <View style={[styles.platformBadge, { backgroundColor: colors.primaryLight }]}>
                  <Text style={[styles.platformText, { color: colors.primary }]}>
                    {result.platform}
                  </Text>
                </View>
              )}
              
              <Text style={[styles.resultTimestamp, { color: colors.textSecondary }]}>
                {formatTimestamp(result.timestamp)}
              </Text>
              
              <View style={styles.relevanceScore}>
                <Icon name="star" size={12} color={colors.warning} />
                <Text style={[styles.scoreText, { color: colors.textSecondary }]}>
                  {Math.round(result.relevanceScore * 100)}%
                </Text>
              </View>
            </View>
          </View>

          {/* Contact Avatar */}
          {result.contact && (
            <TouchableOpacity
              style={styles.contactAvatar}
              onPress={() => onContactPress?.(result.contact!)}
            >
              {result.contact.profilePhoto ? (
                <Image
                  source={{ uri: result.contact.profilePhoto }}
                  style={styles.avatarImage}
                />
              ) : (
                <View style={[styles.avatarPlaceholder, { backgroundColor: colors.primaryLight }]}>
                  <Text style={[styles.avatarText, { color: colors.primary }]}>
                    {result.contact.displayName.charAt(0).toUpperCase()}
                  </Text>
                </View>
              )}
            </TouchableOpacity>
          )}
        </View>

        {/* Result Content */}
        <View style={styles.resultBody}>
          {renderHighlightedText(
            isExpanded ? result.content || result.snippet : result.snippet,
            result.highlights
          )}
          
          {showExpandButton && (
            <TouchableOpacity
              style={styles.expandButton}
              onPress={() => toggleExpanded(result.id)}
            >
              <Text style={[styles.expandButtonText, { color: colors.primary }]}>
                {isExpanded ? 'Show Less' : 'Show More'}
              </Text>
              <Icon
                name={isExpanded ? 'chevron-up' : 'chevron-down'}
                size={16}
                color={colors.primary}
              />
            </TouchableOpacity>
          )}
        </View>

        {/* Quick Actions */}
        {result.quickActions && result.quickActions.length > 0 && (
          <View style={styles.quickActions}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {result.quickActions.map((action, index) => (
                <TouchableOpacity
                  key={index}
                  style={[styles.quickActionButton, { borderColor: colors.border }]}
                  onPress={() => handleQuickAction(action.id, result)}
                >
                  <Icon name={action.icon} size={14} color={colors.primary} />
                  <Text style={[styles.quickActionText, { color: colors.primary }]}>
                    {action.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}
      </TouchableOpacity>
    );
  }, [
    colors,
    expandedResults,
    onResultPress,
    onContactPress,
    renderHighlightedText,
    toggleExpanded,
    handleQuickAction,
  ]);

  // Render results by group
  const renderResultGroup = useCallback((type: string, groupResults: SearchResult[]) => {
    return (
      <View key={type} style={styles.resultGroup}>
        <View style={styles.groupHeader}>
          <Icon
            name={getResultTypeIcon(type)}
            size={18}
            color={colors.primary}
          />
          <Text style={[styles.groupTitle, { color: colors.text }]}>
            {formatResultType(type)} ({groupResults.length})
          </Text>
        </View>
        
        {groupResults.map(renderResultItem)}
      </View>
    );
  }, [colors, renderResultItem]);

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
        <Icon name="search" size={48} color={colors.textSecondary} />
        <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
          Processing your query...
        </Text>
      </View>
    );
  }

  if (results.length === 0) {
    return (
      <View style={[styles.emptyContainer, { backgroundColor: colors.background }]}>
        <Icon name="search" size={48} color={colors.textSecondary} />
        <Text style={[styles.emptyTitle, { color: colors.text }]}>
          {emptyMessage}
        </Text>
        <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
          Try rephrasing your query or using different keywords
        </Text>
        
        {/* Query suggestions based on intent */}
        {intent && (
          <View style={styles.suggestionsContainer}>
            <Text style={[styles.suggestionsTitle, { color: colors.textSecondary }]}>
              Try these examples:
            </Text>
            {getIntentExamples(intent).map((example, index) => (
              <Text key={index} style={[styles.suggestionExample, { color: colors.primary }]}>
                "{example}"
              </Text>
            ))}
          </View>
        )}
      </View>
    );
  }

  const groups = groupedResults();

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Results Summary */}
      <View style={[styles.summaryContainer, { backgroundColor: colors.surface }]}>
        <Text style={[styles.summaryText, { color: colors.text }]}>
          Found {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
        </Text>
        {intent && (
          <Text style={[styles.intentText, { color: colors.textSecondary }]}>
            Intent: {formatIntent(intent)}
          </Text>
        )}
      </View>

      {/* Grouped Results */}
      {Object.entries(groups).map(([type, groupResults]) =>
        renderResultGroup(type, groupResults)
      )}
    </ScrollView>
  );
}

// Helper functions
function getResultTypeIcon(type: string): string {
  const iconMap: Record<string, string> = {
    message: 'chatbubble-outline',
    file: 'document-outline',
    contact: 'person-outline',
    commitment: 'checkmark-circle-outline',
    thread: 'chatbubbles-outline',
  };
  return iconMap[type] || 'search-outline';
}

function formatResultType(type: string): string {
  const typeMap: Record<string, string> = {
    message: 'Messages',
    file: 'Files',
    contact: 'Contacts',
    commitment: 'Commitments',
    thread: 'Conversations',
  };
  return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
}

function formatIntent(intent: string): string {
  const intentMap: Record<string, string> = {
    person_search: 'Contact Search',
    person_messages: 'Messages with Contact',
    file_search: 'File Search',
    commitment_search: 'Commitments & Tasks',
    general_search: 'General Search',
  };
  return intentMap[intent] || intent.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatTimestamp(timestamp: Date): string {
  const now = new Date();
  const diff = now.getTime() - timestamp.getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  
  return timestamp.toLocaleDateString();
}

function getIntentExamples(intent: string): string[] {
  const examples: Record<string, string[]> = {
    person_search: [
      'messages with John Smith',
      'conversations with Sarah',
    ],
    file_search: [
      'files from John',
      'documents shared by Sarah',
    ],
    commitment_search: [
      'commitments to the team',
      'tasks assigned to me',
    ],
    general_search: [
      'project updates',
      'meeting notes',
    ],
  };
  
  return examples[intent] || [
    'messages with [contact name]',
    'files from [contact name]',
  ];
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  loadingText: {
    fontSize: 16,
    marginTop: 16,
    textAlign: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
  suggestionsContainer: {
    marginTop: 24,
    alignItems: 'center',
  },
  suggestionsTitle: {
    fontSize: 14,
    marginBottom: 8,
  },
  suggestionExample: {
    fontSize: 14,
    fontStyle: 'italic',
    marginBottom: 4,
  },
  summaryContainer: {
    padding: 16,
    marginBottom: 8,
  },
  summaryText: {
    fontSize: 16,
    fontWeight: '600',
  },
  intentText: {
    fontSize: 14,
    marginTop: 4,
  },
  resultGroup: {
    marginBottom: 16,
  },
  groupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  groupTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  resultItem: {
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  resultHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  resultTypeIcon: {
    marginRight: 12,
    marginTop: 2,
  },
  resultHeaderContent: {
    flex: 1,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 22,
    marginBottom: 4,
  },
  resultMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  platformBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    marginRight: 8,
  },
  platformText: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  resultTimestamp: {
    fontSize: 12,
    marginRight: 8,
  },
  relevanceScore: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scoreText: {
    fontSize: 12,
    marginLeft: 2,
  },
  contactAvatar: {
    marginLeft: 12,
  },
  avatarImage: {
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  avatarPlaceholder: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 14,
    fontWeight: '600',
  },
  resultBody: {
    marginLeft: 28,
  },
  resultContent: {
    fontSize: 14,
    lineHeight: 20,
  },
  highlightedText: {
    paddingHorizontal: 2,
    borderRadius: 2,
    fontWeight: '600',
  },
  expandButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  expandButtonText: {
    fontSize: 14,
    fontWeight: '500',
    marginRight: 4,
  },
  quickActions: {
    marginTop: 12,
    marginLeft: 28,
  },
  quickActionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    marginRight: 8,
  },
  quickActionText: {
    fontSize: 12,
    marginLeft: 4,
  },
});