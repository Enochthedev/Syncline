import React, { useState, useCallback } from 'react'
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native'
import { useTheme } from '@/hooks/useTheme'
import { useNavigation } from '@react-navigation/native'
import Icon from 'react-native-vector-icons/Ionicons'
import { NaturalLanguageSearch } from '@/components/NaturalLanguageSearch'
import { SearchResultsFilter } from '@/components/SearchResultsFilter'
import { NaturalLanguageSearchResults } from '@/components/NaturalLanguageSearchResults'
import { SearchResult, UnifiedContact } from '@/types'
import { naturalLanguageSearchService } from '@/services/naturalLanguageSearchService'

export function SearchScreen() {
  const { colors } = useTheme()
  const navigation = useNavigation()
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [filteredResults, setFilteredResults] = useState<SearchResult[]>([])
  const [currentQuery, setCurrentQuery] = useState('')
  const [detectedIntent, setDetectedIntent] = useState<string>()
  const [extractedEntities, setExtractedEntities] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)

  // Handle search results change
  const handleResultsChange = useCallback((results: SearchResult[]) => {
    setSearchResults(results)
    setFilteredResults(results)
    setIsSearching(false)
  }, [])

  // Handle query change
  const handleQueryChange = useCallback((query: string) => {
    setCurrentQuery(query)
    if (query.trim()) {
      setIsSearching(true)
    } else {
      setSearchResults([])
      setFilteredResults([])
      setDetectedIntent(undefined)
      setExtractedEntities([])
      setIsSearching(false)
    }
  }, [])

  // Handle intent detection
  const handleIntentDetected = useCallback(async (intent: string, entities: any[]) => {
    setDetectedIntent(intent)
    setExtractedEntities(entities)
    
    // Save to search history
    if (currentQuery.trim()) {
      await naturalLanguageSearchService.saveToHistory(
        currentQuery,
        intent,
        searchResults.length
      )
    }
  }, [currentQuery, searchResults.length])

  // Handle filtered results change
  const handleFilteredResultsChange = useCallback((results: SearchResult[]) => {
    setFilteredResults(results)
  }, [])

  // Handle result press
  const handleResultPress = useCallback((result: SearchResult) => {
    switch (result.type) {
      case 'contact':
        if (result.contact) {
          navigation.navigate('ContactProfile', { contactId: result.contact.id })
        }
        break
      case 'message':
      case 'thread':
        if (result.thread?.id) {
          navigation.navigate('MessageThread', { threadId: result.thread.id })
        }
        break
      case 'file':
        // Handle file opening
        Alert.alert('File', `Opening ${result.title}`)
        break
      default:
        Alert.alert('Result', `Selected: ${result.title}`)
    }
  }, [navigation])

  // Handle contact press
  const handleContactPress = useCallback((contact: UnifiedContact) => {
    navigation.navigate('ContactProfile', { contactId: contact.id })
  }, [navigation])

  // Handle quick action press
  const handleQuickActionPress = useCallback((action: string, result: SearchResult) => {
    switch (action) {
      case 'view_contact':
        if (result.contact) {
          navigation.navigate('ContactProfile', { contactId: result.contact.id })
        }
        break
      case 'view_thread':
        if (result.thread?.id) {
          navigation.navigate('MessageThread', { threadId: result.thread.id })
        }
        break
      case 'share':
        Alert.alert('Share', `Sharing ${result.title}`)
        break
      default:
        Alert.alert('Action', `Performing action: ${action}`)
    }
  }, [navigation])

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Natural Language Search Input */}
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

      {/* Search Results */}
      <View style={styles.resultsContainer}>
        {currentQuery.length === 0 ? (
          <ScrollView style={styles.content} contentContainerStyle={styles.emptyStateContainer}>
            <Icon name="search" size={64} color={colors.textSecondary} />
            <Text style={[styles.emptyTitle, { color: colors.text }]}>
              Natural Language Search
            </Text>
            <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
              Search using natural language like "messages with John" or "files from Sarah"
            </Text>
            
            {/* Example Queries */}
            <View style={styles.examplesContainer}>
              <Text style={[styles.examplesTitle, { color: colors.textSecondary }]}>
                Try these examples:
              </Text>
              {naturalLanguageSearchService.getExampleQueries().slice(0, 5).map((example, index) => (
                <View key={index} style={[styles.exampleItem, { backgroundColor: colors.surface }]}>
                  <Icon name="search" size={16} color={colors.primary} />
                  <Text style={[styles.exampleText, { color: colors.text }]}>
                    "{example}"
                  </Text>
                </View>
              ))}
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
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  searchContainer: {
    padding: 16,
    paddingBottom: 8,
  },
  filterContainer: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  resultsContainer: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  emptyStateContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingVertical: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  examplesContainer: {
    width: '100%',
    alignItems: 'center',
  },
  examplesTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 16,
    textTransform: 'uppercase',
  },
  exampleItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    marginBottom: 8,
    width: '100%',
  },
  exampleText: {
    fontSize: 14,
    marginLeft: 12,
    flex: 1,
  },
})