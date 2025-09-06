/**
 * Natural Language Search Component
 * 
 * Provides natural language query processing with intent display,
 * entity highlighting, and search result filtering.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '@/hooks/useTheme';
import { useDebounce } from '@/hooks/useDebounce';
import { contactSearchService } from '@/services/contactSearchService';
import { SearchResult } from '@/types';

export interface NaturalLanguageQueryResult {
  intent: string;
  processed_text: string;
  contacts: any[];
  filters: Record<string, any>;
  temporal_constraints: Record<string, any>;
  entities: any[];
}

export interface NaturalLanguageSearchProps {
  onResultsChange?: (results: SearchResult[]) => void;
  onQueryChange?: (query: string) => void;
  onIntentDetected?: (intent: string, entities: any[]) => void;
  placeholder?: string;
  showHistory?: boolean;
  showSuggestions?: boolean;
}

export function NaturalLanguageSearch({
  onResultsChange,
  onQueryChange,
  onIntentDetected,
  placeholder = "Try 'messages with John' or 'files from Sarah'",
  showHistory = true,
  showSuggestions = true,
}: NaturalLanguageSearchProps) {
  const { colors } = useTheme();
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [queryResult, setQueryResult] = useState<NaturalLanguageQueryResult | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestionsList, setShowSuggestionsList] = useState(false);

  const debouncedQuery = useDebounce(query, 300);

  // Process natural language query
  const processQuery = useCallback(async (queryText: string) => {
    if (!queryText.trim()) {
      setQueryResult(null);
      return;
    }

    setIsProcessing(true);
    try {
      const result = await contactSearchService.processNaturalLanguageQuery(queryText);
      setQueryResult(result);
      
      // Notify parent components
      onIntentDetected?.(result.intent, result.entities);
      
      // Perform search based on detected intent
      await performIntentBasedSearch(result);
      
    } catch (error) {
      console.error('Natural language query processing failed:', error);
      Alert.alert('Search Error', 'Failed to process your query. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  }, [onIntentDetected]);

  // Perform search based on detected intent
  const performIntentBasedSearch = useCallback(async (queryResult: NaturalLanguageQueryResult) => {
    try {
      let searchResults: SearchResult[] = [];

      switch (queryResult.intent) {
        case 'person_search':
        case 'person_messages':
          // Search for messages with specific contacts
          if (queryResult.contacts.length > 0) {
            const contact = queryResult.contacts[0];
            const messageResults = await contactSearchService.searchMessagesByContact(
              contact.id,
              queryResult.processed_text,
              50,
              0,
              true
            );
            searchResults = convertMessageResultsToSearchResults(messageResults);
          }
          break;

        case 'file_search':
          // Search for shared files
          if (queryResult.contacts.length > 0) {
            const contact = queryResult.contacts[0];
            const fileResults = await contactSearchService.getSharedContentWithContact(
              contact.id,
              'files',
              50
            );
            searchResults = convertFileResultsToSearchResults(fileResults);
          }
          break;

        case 'commitment_search':
          // Search for commitments and action items
          searchResults = await searchCommitments(queryResult);
          break;

        default:
          // General search
          searchResults = await performGeneralSearch(queryResult);
      }

      onResultsChange?.(searchResults);
    } catch (error) {
      console.error('Intent-based search failed:', error);
    }
  }, [onResultsChange]);

  // Get search suggestions
  const getSuggestions = useCallback(async (partialQuery: string) => {
    if (!partialQuery.trim() || partialQuery.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      const suggestionResults = await contactSearchService.getSearchSuggestions(partialQuery, 5);
      setSuggestions(suggestionResults);
    } catch (error) {
      console.error('Failed to get suggestions:', error);
      setSuggestions([]);
    }
  }, []);

  // Handle query input change
  const handleQueryChange = useCallback((text: string) => {
    setQuery(text);
    onQueryChange?.(text);
    
    if (showSuggestions) {
      getSuggestions(text);
      setShowSuggestionsList(text.length > 0);
    }
  }, [onQueryChange, showSuggestions, getSuggestions]);

  // Handle query submission
  const handleSubmitQuery = useCallback(() => {
    if (query.trim()) {
      processQuery(query);
      
      // Add to search history
      if (showHistory && !searchHistory.includes(query)) {
        setSearchHistory(prev => [query, ...prev.slice(0, 9)]); // Keep last 10
      }
      
      setShowSuggestionsList(false);
    }
  }, [query, processQuery, showHistory, searchHistory]);

  // Handle suggestion selection
  const handleSelectSuggestion = useCallback((suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestionsList(false);
    processQuery(suggestion);
  }, [processQuery]);

  // Handle history item selection
  const handleSelectHistory = useCallback((historyItem: string) => {
    setQuery(historyItem);
    processQuery(historyItem);
  }, [processQuery]);

  // Process query when debounced query changes
  useEffect(() => {
    if (debouncedQuery) {
      processQuery(debouncedQuery);
    }
  }, [debouncedQuery, processQuery]);

  return (
    <View style={styles.container}>
      {/* Search Input */}
      <View style={[styles.searchContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Icon name="search" size={20} color={colors.textSecondary} style={styles.searchIcon} />
        <TextInput
          style={[styles.searchInput, { color: colors.text }]}
          placeholder={placeholder}
          placeholderTextColor={colors.textSecondary}
          value={query}
          onChangeText={handleQueryChange}
          onSubmitEditing={handleSubmitQuery}
          returnKeyType="search"
          multiline={false}
        />
        {isProcessing && (
          <ActivityIndicator 
            size="small" 
            color={colors.primary} 
            style={styles.loadingIndicator}
            testID="loading-indicator"
          />
        )}
        {query.length > 0 && !isProcessing && (
          <TouchableOpacity 
            onPress={() => handleQueryChange('')} 
            style={styles.clearButton}
            testID="clear-button"
          >
            <Icon name="close" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Query Intent Display */}
      {queryResult && (
        <View style={[styles.intentContainer, { backgroundColor: colors.surface }]}>
          <View style={styles.intentHeader}>
            <Icon name="bulb-outline" size={16} color={colors.primary} />
            <Text style={[styles.intentLabel, { color: colors.primary }]}>
              Detected Intent: {formatIntent(queryResult.intent)}
            </Text>
          </View>
          
          {/* Extracted Entities */}
          {queryResult.entities.length > 0 && (
            <View style={styles.entitiesContainer}>
              <Text style={[styles.entitiesLabel, { color: colors.textSecondary }]}>
                Found:
              </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {queryResult.entities.map((entity, index) => (
                  <View
                    key={index}
                    style={[styles.entityChip, { backgroundColor: colors.primaryLight }]}
                  >
                    <Text style={[styles.entityText, { color: colors.primary }]}>
                      {entity.text} ({entity.type})
                    </Text>
                  </View>
                ))}
              </ScrollView>
            </View>
          )}

          {/* Processed Query */}
          {queryResult.processed_text !== query && (
            <Text style={[styles.processedText, { color: colors.textSecondary }]}>
              Searching for: "{queryResult.processed_text}"
            </Text>
          )}
        </View>
      )}

      {/* Suggestions and History */}
      {showSuggestionsList && (suggestions.length > 0 || searchHistory.length > 0) && (
        <View style={[styles.suggestionsContainer, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          {/* Suggestions */}
          {suggestions.length > 0 && (
            <View style={styles.suggestionSection}>
              <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
                Suggestions
              </Text>
              {suggestions.map((suggestion, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionItem}
                  onPress={() => handleSelectSuggestion(suggestion)}
                >
                  <Icon name="search" size={16} color={colors.textSecondary} />
                  <Text style={[styles.suggestionText, { color: colors.text }]}>
                    {suggestion}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {/* Search History */}
          {showHistory && searchHistory.length > 0 && (
            <View style={styles.suggestionSection}>
              <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
                Recent Searches
              </Text>
              {searchHistory.slice(0, 5).map((historyItem, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.suggestionItem}
                  onPress={() => handleSelectHistory(historyItem)}
                >
                  <Icon name="time" size={16} color={colors.textSecondary} />
                  <Text style={[styles.suggestionText, { color: colors.text }]}>
                    {historyItem}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      )}
    </View>
  );
}

// Helper functions
function formatIntent(intent: string): string {
  const intentMap: Record<string, string> = {
    'person_search': 'Contact Search',
    'person_messages': 'Messages with Contact',
    'file_search': 'File Search',
    'commitment_search': 'Commitments & Tasks',
    'general_search': 'General Search',
  };
  return intentMap[intent] || intent.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function convertMessageResultsToSearchResults(messageResults: any): SearchResult[] {
  // Convert message search results to SearchResult format
  const results: SearchResult[] = [];
  
  if (messageResults.messages) {
    messageResults.messages.forEach((message: any) => {
      results.push({
        id: message.id,
        type: 'message',
        title: message.sender?.displayName || 'Unknown Sender',
        snippet: message.content?.text?.substring(0, 150) || '',
        content: message.content?.text || '',
        relevanceScore: 1.0,
        timestamp: new Date(message.timestamp),
        contact: message.sender,
        platform: message.platform,
        highlights: [],
        quickActions: [],
      });
    });
  }
  
  return results;
}

function convertFileResultsToSearchResults(fileResults: any): SearchResult[] {
  // Convert file search results to SearchResult format
  const results: SearchResult[] = [];
  
  if (fileResults.shared_files) {
    fileResults.shared_files.forEach((file: any) => {
      results.push({
        id: file.id,
        type: 'file',
        title: file.name,
        snippet: `${file.type} • ${formatFileSize(file.size)}`,
        content: file.name,
        relevanceScore: 1.0,
        timestamp: new Date(file.sharedAt),
        platform: file.platform,
        highlights: [],
        quickActions: [],
      });
    });
  }
  
  return results;
}

async function searchCommitments(queryResult: NaturalLanguageQueryResult): Promise<SearchResult[]> {
  // Implement commitment search logic
  // This would integrate with the commitment search API
  return [];
}

async function performGeneralSearch(queryResult: NaturalLanguageQueryResult): Promise<SearchResult[]> {
  // Implement general search logic
  // This would integrate with the general search API
  return [];
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  searchIcon: {
    marginRight: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    lineHeight: 20,
  },
  loadingIndicator: {
    marginLeft: 8,
  },
  clearButton: {
    marginLeft: 8,
    padding: 4,
  },
  intentContainer: {
    marginTop: 8,
    padding: 12,
    borderRadius: 8,
  },
  intentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  intentLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  entitiesContainer: {
    marginBottom: 8,
  },
  entitiesLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  entityChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 8,
  },
  entityText: {
    fontSize: 12,
    fontWeight: '500',
  },
  processedText: {
    fontSize: 12,
    fontStyle: 'italic',
  },
  suggestionsContainer: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    marginTop: 4,
    borderRadius: 8,
    borderWidth: 1,
    maxHeight: 300,
    zIndex: 1000,
  },
  suggestionSection: {
    padding: 8,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  suggestionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 4,
  },
  suggestionText: {
    fontSize: 14,
    marginLeft: 8,
    flex: 1,
  },
});