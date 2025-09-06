/**
 * Natural Language Search Demo Screen
 * 
 * Demonstrates the natural language search functionality with examples
 * and interactive features for testing and showcasing capabilities.
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useTheme } from '@/hooks/useTheme';
import Icon from 'react-native-vector-icons/Ionicons';
import { NaturalLanguageSearch } from '@/components/NaturalLanguageSearch';
import { SearchResultsFilter } from '@/components/SearchResultsFilter';
import { NaturalLanguageSearchResults } from '@/components/NaturalLanguageSearchResults';
import { SearchResult, UnifiedContact } from '@/types';
import { naturalLanguageSearchService } from '@/services/naturalLanguageSearchService';

export function NaturalLanguageSearchDemoScreen() {
  const { colors } = useTheme();
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [filteredResults, setFilteredResults] = useState<SearchResult[]>([]);
  const [currentQuery, setCurrentQuery] = useState('');
  const [detectedIntent, setDetectedIntent] = useState<string>();
  const [extractedEntities, setExtractedEntities] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showExamples, setShowExamples] = useState(true);

  // Example queries for demonstration
  const exampleQueries = [
    'messages with John Smith',
    'files from Sarah last week',
    'commitments to the team',
    'photos shared by mom',
    'documents about project alpha',
    'calls with clients this month',
    'emails from support',
    'shared links about AI',
  ];

  // Mock search results for demo purposes
  const generateMockResults = useCallback((query: string, intent: string): SearchResult[] => {
    const mockResults: SearchResult[] = [];
    
    switch (intent) {
      case 'person_messages':
        mockResults.push(
          {
            id: '1',
            type: 'message',
            title: 'John Smith',
            snippet: 'Hey, how are you doing? I wanted to follow up on our conversation about the project.',
            content: 'Hey, how are you doing? I wanted to follow up on our conversation about the project. Let me know if you have any questions.',
            relevanceScore: 0.95,
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
            contact: {
              id: '1',
              primaryName: 'John Smith',
              displayName: 'John Smith',
              profilePhoto: undefined,
              identities: [],
              emails: ['john@example.com'],
              phoneNumbers: [],
              socialProfiles: [],
              lastInteraction: new Date(),
              totalMessages: 25,
              platforms: ['email'],
              relationshipStrength: 0.8,
              communicationFrequency: 'high' as const,
              responsePattern: {
                averageResponseTime: 30,
                responseRate: 0.9,
                preferredTimes: ['9-12', '14-17'],
                communicationStyle: 'casual' as const,
              },
              topicAffinity: [],
              sharedFiles: [],
              sharedLinks: [],
              commonContacts: [],
              createdAt: new Date(),
              updatedAt: new Date(),
              lastSyncAt: new Date(),
            },
            platform: 'email',
            highlights: [{ start: 0, end: 10, text: 'John Smith' }],
            quickActions: [
              { id: 'reply', label: 'Reply', icon: 'mail', action: () => {} },
              { id: 'view_contact', label: 'View Contact', icon: 'person', action: () => {} },
            ],
          },
          {
            id: '2',
            type: 'message',
            title: 'John Smith',
            snippet: 'Thanks for the update! The presentation looks great.',
            content: 'Thanks for the update! The presentation looks great. I have a few minor suggestions that I\'ll send over later.',
            relevanceScore: 0.87,
            timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
            contact: {
              id: '1',
              primaryName: 'John Smith',
              displayName: 'John Smith',
              profilePhoto: undefined,
              identities: [],
              emails: ['john@example.com'],
              phoneNumbers: [],
              socialProfiles: [],
              lastInteraction: new Date(),
              totalMessages: 25,
              platforms: ['email'],
              relationshipStrength: 0.8,
              communicationFrequency: 'high' as const,
              responsePattern: {
                averageResponseTime: 30,
                responseRate: 0.9,
                preferredTimes: ['9-12', '14-17'],
                communicationStyle: 'casual' as const,
              },
              topicAffinity: [],
              sharedFiles: [],
              sharedLinks: [],
              commonContacts: [],
              createdAt: new Date(),
              updatedAt: new Date(),
              lastSyncAt: new Date(),
            },
            platform: 'slack',
            highlights: [{ start: 0, end: 10, text: 'John Smith' }],
            quickActions: [
              { id: 'reply', label: 'Reply', icon: 'chatbubble', action: () => {} },
              { id: 'view_thread', label: 'View Thread', icon: 'chatbubbles', action: () => {} },
            ],
          }
        );
        break;

      case 'file_search':
        mockResults.push(
          {
            id: '3',
            type: 'file',
            title: 'Project_Proposal.pdf',
            snippet: 'PDF • 2.3 MB • Shared by Sarah Johnson',
            content: 'Project_Proposal.pdf',
            relevanceScore: 0.92,
            timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
            contact: {
              id: '2',
              primaryName: 'Sarah Johnson',
              displayName: 'Sarah Johnson',
              profilePhoto: undefined,
              identities: [],
              emails: ['sarah@example.com'],
              phoneNumbers: [],
              socialProfiles: [],
              lastInteraction: new Date(),
              totalMessages: 15,
              platforms: ['email'],
              relationshipStrength: 0.7,
              communicationFrequency: 'medium' as const,
              responsePattern: {
                averageResponseTime: 60,
                responseRate: 0.8,
                preferredTimes: ['10-12', '15-17'],
                communicationStyle: 'formal' as const,
              },
              topicAffinity: [],
              sharedFiles: [],
              sharedLinks: [],
              commonContacts: [],
              createdAt: new Date(),
              updatedAt: new Date(),
              lastSyncAt: new Date(),
            },
            platform: 'email',
            highlights: [{ start: 0, end: 7, text: 'Project' }],
            quickActions: [
              { id: 'download', label: 'Download', icon: 'download', action: () => {} },
              { id: 'share', label: 'Share', icon: 'share', action: () => {} },
            ],
          }
        );
        break;

      default:
        mockResults.push(
          {
            id: '4',
            type: 'message',
            title: 'General Search Result',
            snippet: `Found content related to "${query}"`,
            content: `This is a general search result for the query: ${query}`,
            relevanceScore: 0.75,
            timestamp: new Date(),
            highlights: [],
            quickActions: [],
          }
        );
    }

    return mockResults;
  }, []);

  // Handle search results change
  const handleResultsChange = useCallback((results: SearchResult[]) => {
    setSearchResults(results);
    setFilteredResults(results);
    setIsSearching(false);
    setShowExamples(false);
  }, []);

  // Handle query change
  const handleQueryChange = useCallback((query: string) => {
    setCurrentQuery(query);
    if (query.trim()) {
      setIsSearching(true);
      setShowExamples(false);
    } else {
      setSearchResults([]);
      setFilteredResults([]);
      setDetectedIntent(undefined);
      setExtractedEntities([]);
      setIsSearching(false);
      setShowExamples(true);
    }
  }, []);

  // Handle intent detection
  const handleIntentDetected = useCallback(async (intent: string, entities: any[]) => {
    setDetectedIntent(intent);
    setExtractedEntities(entities);
    
    // Generate mock results for demo
    const mockResults = generateMockResults(currentQuery, intent);
    setSearchResults(mockResults);
    setFilteredResults(mockResults);
    setIsSearching(false);
    
    // Save to search history
    if (currentQuery.trim()) {
      await naturalLanguageSearchService.saveToHistory(
        currentQuery,
        intent,
        mockResults.length
      );
    }
  }, [currentQuery, generateMockResults]);

  // Handle filtered results change
  const handleFilteredResultsChange = useCallback((results: SearchResult[]) => {
    setFilteredResults(results);
  }, []);

  // Handle result press
  const handleResultPress = useCallback((result: SearchResult) => {
    Alert.alert(
      'Result Selected',
      `You selected: ${result.title}\nType: ${result.type}`,
      [{ text: 'OK' }]
    );
  }, []);

  // Handle contact press
  const handleContactPress = useCallback((contact: UnifiedContact) => {
    Alert.alert(
      'Contact Selected',
      `You selected: ${contact.displayName}`,
      [{ text: 'OK' }]
    );
  }, []);

  // Handle quick action press
  const handleQuickActionPress = useCallback((action: string, result: SearchResult) => {
    Alert.alert(
      'Quick Action',
      `Action: ${action}\nOn: ${result.title}`,
      [{ text: 'OK' }]
    );
  }, []);

  // Handle example query press
  const handleExamplePress = useCallback((example: string) => {
    setCurrentQuery(example);
    handleQueryChange(example);
  }, [handleQueryChange]);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface, borderBottomColor: colors.border }]}>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          Natural Language Search Demo
        </Text>
        <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
          Try searching using natural language queries
        </Text>
      </View>

      {/* Search Input */}
      <View style={styles.searchContainer}>
        <NaturalLanguageSearch
          onResultsChange={handleResultsChange}
          onQueryChange={handleQueryChange}
          onIntentDetected={handleIntentDetected}
          placeholder="Try 'messages with John' or 'files from Sarah'"
          showHistory={true}
          showSuggestions={true}
        />
      </View>

      {/* Search Results Filter */}
      {searchResults.length > 0 && (
        <View style={styles.filterContainer}>
          <SearchResultsFilter
            results={searchResults}
            onFilteredResultsChange={handleFilteredResultsChange}
            detectedIntent={detectedIntent}
            extractedEntities={extractedEntities}
          />
        </View>
      )}

      {/* Content */}
      <View style={styles.content}>
        {showExamples ? (
          <ScrollView style={styles.examplesContainer} contentContainerStyle={styles.examplesContent}>
            <View style={styles.examplesHeader}>
              <Icon name="bulb" size={32} color={colors.primary} />
              <Text style={[styles.examplesTitle, { color: colors.text }]}>
                Try These Examples
              </Text>
              <Text style={[styles.examplesSubtitle, { color: colors.textSecondary }]}>
                Tap any example to see how natural language search works
              </Text>
            </View>

            <View style={styles.examplesList}>
              {exampleQueries.map((example, index) => (
                <TouchableOpacity
                  key={index}
                  style={[styles.exampleItem, { backgroundColor: colors.surface, borderColor: colors.border }]}
                  onPress={() => handleExamplePress(example)}
                  activeOpacity={0.7}
                >
                  <Icon name="search" size={16} color={colors.primary} />
                  <Text style={[styles.exampleText, { color: colors.text }]}>
                    "{example}"
                  </Text>
                  <Icon name="chevron-forward" size={16} color={colors.textSecondary} />
                </TouchableOpacity>
              ))}
            </View>

            {/* Features Info */}
            <View style={[styles.featuresContainer, { backgroundColor: colors.surface }]}>
              <Text style={[styles.featuresTitle, { color: colors.text }]}>
                Features Demonstrated
              </Text>
              <View style={styles.featuresList}>
                <View style={styles.featureItem}>
                  <Icon name="checkmark-circle" size={16} color={colors.success} />
                  <Text style={[styles.featureText, { color: colors.textSecondary }]}>
                    Intent detection and entity extraction
                  </Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="checkmark-circle" size={16} color={colors.success} />
                  <Text style={[styles.featureText, { color: colors.textSecondary }]}>
                    Search result filtering and grouping
                  </Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="checkmark-circle" size={16} color={colors.success} />
                  <Text style={[styles.featureText, { color: colors.textSecondary }]}>
                    Search history and suggestions
                  </Text>
                </View>
                <View style={styles.featureItem}>
                  <Icon name="checkmark-circle" size={16} color={colors.success} />
                  <Text style={[styles.featureText, { color: colors.textSecondary }]}>
                    Highlighted search results
                  </Text>
                </View>
              </View>
            </View>
          </ScrollView>
        ) : (
          <NaturalLanguageSearchResults
            results={filteredResults}
            query={currentQuery}
            intent={detectedIntent}
            entities={extractedEntities}
            onResultPress={handleResultPress}
            onContactPress={handleContactPress}
            onQuickActionPress={handleQuickActionPress}
            loading={isSearching}
            emptyMessage={`No results found for "${currentQuery}"`}
          />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
  },
  searchContainer: {
    padding: 16,
    paddingBottom: 8,
  },
  filterContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  content: {
    flex: 1,
  },
  examplesContainer: {
    flex: 1,
  },
  examplesContent: {
    padding: 16,
  },
  examplesHeader: {
    alignItems: 'center',
    marginBottom: 32,
  },
  examplesTitle: {
    fontSize: 24,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  examplesSubtitle: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 22,
  },
  examplesList: {
    marginBottom: 32,
  },
  exampleItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 8,
  },
  exampleText: {
    fontSize: 16,
    marginLeft: 12,
    flex: 1,
  },
  featuresContainer: {
    padding: 16,
    borderRadius: 12,
  },
  featuresTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  featuresList: {
    gap: 12,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  featureText: {
    fontSize: 14,
    marginLeft: 8,
    flex: 1,
  },
});