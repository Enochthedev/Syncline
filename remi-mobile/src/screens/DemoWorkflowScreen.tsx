/**
 * Demo Workflow Screen
 * 
 * Demonstrates the complete contact search workflow from search input to contact profile
 */

import React, { useState, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  SafeAreaView,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import { useTheme } from '@/hooks/useTheme'
import { ContactSearchInput } from '@/components/ContactSearchInput'
import { ContactCard } from '@/components/ContactCard'
import { SearchBar } from '@/components/SearchBar'
import { NaturalLanguageSearch } from '@/components/NaturalLanguageSearch'
import { mockDataService } from '@/services/mockDataService'
import { UnifiedContact, SearchResult } from '@/types'
import Icon from 'react-native-vector-icons/Ionicons'

type DemoStep = 'welcome' | 'search' | 'results' | 'profile' | 'messages' | 'insights'

interface DemoState {
  currentStep: DemoStep
  selectedContact: UnifiedContact | null
  searchResults: UnifiedContact[]
  searchQuery: string
  messageResults: SearchResult[]
}

export function DemoWorkflowScreen() {
  const navigation = useNavigation()
  const { colors } = useTheme()
  
  const [demoState, setDemoState] = useState<DemoState>({
    currentStep: 'welcome',
    selectedContact: null,
    searchResults: [],
    searchQuery: '',
    messageResults: [],
  })

  const [showNaturalLanguage, setShowNaturalLanguage] = useState(false)

  // Demo workflow handlers
  const handleStartDemo = useCallback(() => {
    setDemoState(prev => ({ ...prev, currentStep: 'search' }))
  }, [])

  const handleSearchResults = useCallback((results: UnifiedContact[]) => {
    setDemoState(prev => ({
      ...prev,
      searchResults: results,
      currentStep: results.length > 0 ? 'results' : 'search',
    }))
  }, [])

  const handleContactSelect = useCallback(async (contact: UnifiedContact) => {
    setDemoState(prev => ({
      ...prev,
      selectedContact: contact,
      currentStep: 'profile',
    }))

    // Load messages for the selected contact
    try {
      const messages = await mockDataService.searchMessages('', contact.id)
      setDemoState(prev => ({
        ...prev,
        messageResults: messages,
      }))
    } catch (error) {
      console.error('Error loading messages:', error)
    }
  }, [])

  const handleViewMessages = useCallback(() => {
    if (demoState.selectedContact) {
      setDemoState(prev => ({ ...prev, currentStep: 'messages' }))
    }
  }, [demoState.selectedContact])

  const handleViewInsights = useCallback(() => {
    if (demoState.selectedContact) {
      setDemoState(prev => ({ ...prev, currentStep: 'insights' }))
    }
  }, [demoState.selectedContact])

  const handleNavigateToProfile = useCallback(() => {
    if (demoState.selectedContact) {
      navigation.navigate('ContactProfile' as never, { 
        contactId: demoState.selectedContact.id 
      } as never)
    }
  }, [navigation, demoState.selectedContact])

  const handleNavigateToMessages = useCallback(() => {
    if (demoState.selectedContact) {
      // Find a thread for this contact
      const threadId = `thread-${demoState.selectedContact.id}`
      navigation.navigate('MessageThread' as never, { 
        threadId 
      } as never)
    }
  }, [navigation, demoState.selectedContact])

  const handleResetDemo = useCallback(() => {
    setDemoState({
      currentStep: 'welcome',
      selectedContact: null,
      searchResults: [],
      searchQuery: '',
      messageResults: [],
    })
    setShowNaturalLanguage(false)
  }, [])

  const renderWelcomeStep = () => (
    <View style={styles.stepContainer}>
      <Icon name="rocket" size={64} color={colors.primary} />
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        Welcome to R.E.M.I Demo
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        Experience the power of contact-based search and AI insights with sample data.
      </Text>
      
      <View style={styles.demoFeatures}>
        <View style={styles.demoFeature}>
          <Icon name="search" size={20} color={colors.primary} />
          <Text style={[styles.featureText, { color: colors.text }]}>
            Smart contact search with fuzzy matching
          </Text>
        </View>
        <View style={styles.demoFeature}>
          <Icon name="chatbubbles" size={20} color={colors.primary} />
          <Text style={[styles.featureText, { color: colors.text }]}>
            Natural language message queries
          </Text>
        </View>
        <View style={styles.demoFeature}>
          <Icon name="analytics" size={20} color={colors.primary} />
          <Text style={[styles.featureText, { color: colors.text }]}>
            AI-powered relationship insights
          </Text>
        </View>
        <View style={styles.demoFeature}>
          <Icon name="people" size={20} color={colors.primary} />
          <Text style={[styles.featureText, { color: colors.text }]}>
            Unified contact profiles across platforms
          </Text>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.primaryButton, { backgroundColor: colors.primary }]}
        onPress={handleStartDemo}
      >
        <Text style={styles.primaryButtonText}>Start Demo</Text>
      </TouchableOpacity>
    </View>
  )

  const renderSearchStep = () => (
    <View style={styles.stepContainer}>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        Search for Contacts
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        Try searching for contacts using names, emails, or handles. The system supports fuzzy matching and typo tolerance.
      </Text>

      <View style={styles.searchContainer}>
        <ContactSearchInput
          onContactSelect={handleContactSelect}
          onSearchResults={handleSearchResults}
          placeholder="Try searching for 'John', 'Sarah', or 'Mike'..."
          showSuggestions={true}
        />
      </View>

      <View style={styles.searchOptions}>
        <TouchableOpacity
          style={[styles.optionButton, { backgroundColor: colors.surface }]}
          onPress={() => setShowNaturalLanguage(!showNaturalLanguage)}
        >
          <Icon name="chatbubble-ellipses" size={16} color={colors.primary} />
          <Text style={[styles.optionButtonText, { color: colors.primary }]}>
            Try Natural Language
          </Text>
        </TouchableOpacity>
      </View>

      {showNaturalLanguage && (
        <View style={styles.naturalLanguageContainer}>
          <NaturalLanguageSearch
            onResults={(results) => {
              Alert.alert('Demo Mode', `Found ${results.length} results for your query`)
            }}
            placeholder="Try 'messages with John' or 'files from Sarah'"
          />
        </View>
      )}

      <View style={styles.exampleQueries}>
        <Text style={[styles.exampleTitle, { color: colors.text }]}>
          Example Searches:
        </Text>
        {['John Smith', 'Sarah Johnson', 'Mike Chen', 'john@company.com'].map((query) => (
          <TouchableOpacity
            key={query}
            style={[styles.exampleQuery, { backgroundColor: colors.surface }]}
            onPress={async () => {
              const results = await mockDataService.searchContacts(query)
              handleSearchResults(results)
            }}
          >
            <Text style={[styles.exampleQueryText, { color: colors.text }]}>
              {query}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  )

  const renderResultsStep = () => (
    <View style={styles.stepContainer}>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        Search Results
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        Found {demoState.searchResults.length} contact{demoState.searchResults.length !== 1 ? 's' : ''}. 
        Tap on a contact to view their profile and relationship insights.
      </Text>

      <View style={styles.resultsContainer}>
        {demoState.searchResults.map((contact) => (
          <ContactCard
            key={contact.id}
            contact={contact}
            onPress={handleContactSelect}
            showDetails={true}
          />
        ))}
      </View>

      <TouchableOpacity
        style={[styles.secondaryButton, { borderColor: colors.primary }]}
        onPress={() => setDemoState(prev => ({ ...prev, currentStep: 'search' }))}
      >
        <Text style={[styles.secondaryButtonText, { color: colors.primary }]}>
          Search Again
        </Text>
      </TouchableOpacity>
    </View>
  )

  const renderProfileStep = () => (
    <View style={styles.stepContainer}>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        Contact Profile
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        View unified contact information, communication patterns, and relationship insights.
      </Text>

      {demoState.selectedContact && (
        <View style={styles.profileContainer}>
          <ContactCard
            contact={demoState.selectedContact}
            onPress={() => {}}
            showDetails={true}
          />

          <View style={styles.profileActions}>
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: colors.primary }]}
              onPress={handleViewMessages}
            >
              <Icon name="chatbubbles" size={16} color="white" />
              <Text style={styles.actionButtonText}>View Messages</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: colors.secondary }]}
              onPress={handleViewInsights}
            >
              <Icon name="analytics" size={16} color="white" />
              <Text style={styles.actionButtonText}>View Insights</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.profileStats}>
            <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
              <Text style={[styles.statNumber, { color: colors.primary }]}>
                {demoState.selectedContact.totalMessages}
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                Messages
              </Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
              <Text style={[styles.statNumber, { color: colors.primary }]}>
                {Math.round(demoState.selectedContact.relationshipStrength * 100)}%
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                Relationship
              </Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: colors.surface }]}>
              <Text style={[styles.statNumber, { color: colors.primary }]}>
                {demoState.selectedContact.platforms.length}
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                Platforms
              </Text>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.primaryButton, { backgroundColor: colors.primary }]}
            onPress={handleNavigateToProfile}
          >
            <Text style={styles.primaryButtonText}>Open Full Profile</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  )

  const renderMessagesStep = () => (
    <View style={styles.stepContainer}>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        Message History
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        Browse conversation threads and search through message history with this contact.
      </Text>

      <View style={styles.messagesContainer}>
        <View style={[styles.messagesSummary, { backgroundColor: colors.surface }]}>
          <Text style={[styles.messagesSummaryTitle, { color: colors.text }]}>
            Conversation Summary
          </Text>
          <Text style={[styles.messagesSummaryText, { color: colors.textSecondary }]}>
            Recent discussions about project timelines, document sharing, and team coordination.
          </Text>
        </View>

        <View style={styles.messagesStats}>
          <View style={[styles.messagesStat, { backgroundColor: colors.surface }]}>
            <Text style={[styles.messagesStatNumber, { color: colors.primary }]}>
              {demoState.messageResults.length}
            </Text>
            <Text style={[styles.messagesStatLabel, { color: colors.textSecondary }]}>
              Messages
            </Text>
          </View>
          <View style={[styles.messagesStat, { backgroundColor: colors.surface }]}>
            <Text style={[styles.messagesStatNumber, { color: colors.success }]}>
              2
            </Text>
            <Text style={[styles.messagesStatLabel, { color: colors.textSecondary }]}>
              Threads
            </Text>
          </View>
          <View style={[styles.messagesStat, { backgroundColor: colors.surface }]}>
            <Text style={[styles.messagesStatNumber, { color: colors.warning }]}>
              3
            </Text>
            <Text style={[styles.messagesStatLabel, { color: colors.textSecondary }]}>
              Files
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.primaryButton, { backgroundColor: colors.primary }]}
          onPress={handleNavigateToMessages}
        >
          <Text style={styles.primaryButtonText}>Open Message Thread</Text>
        </TouchableOpacity>
      </View>
    </View>
  )

  const renderInsightsStep = () => (
    <View style={styles.stepContainer}>
      <Text style={[styles.stepTitle, { color: colors.text }]}>
        AI Insights
      </Text>
      <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
        AI-powered analysis of communication patterns, relationship strength, and suggested actions.
      </Text>

      <View style={styles.insightsContainer}>
        <View style={[styles.insightCard, { backgroundColor: colors.surface }]}>
          <View style={styles.insightHeader}>
            <Icon name="trending-up" size={20} color={colors.success} />
            <Text style={[styles.insightTitle, { color: colors.text }]}>
              Communication Trend
            </Text>
          </View>
          <Text style={[styles.insightText, { color: colors.textSecondary }]}>
            Communication frequency has increased 25% this month, indicating stronger collaboration.
          </Text>
        </View>

        <View style={[styles.insightCard, { backgroundColor: colors.surface }]}>
          <View style={styles.insightHeader}>
            <Icon name="time" size={20} color={colors.warning} />
            <Text style={[styles.insightTitle, { color: colors.text }]}>
              Response Pattern
            </Text>
          </View>
          <Text style={[styles.insightText, { color: colors.textSecondary }]}>
            Average response time: 45 minutes. Best times to reach: 9-12 AM, 2-5 PM.
          </Text>
        </View>

        <View style={[styles.insightCard, { backgroundColor: colors.surface }]}>
          <View style={styles.insightHeader}>
            <Icon name="bulb" size={20} color={colors.primary} />
            <Text style={[styles.insightTitle, { color: colors.text }]}>
              Suggested Action
            </Text>
          </View>
          <Text style={[styles.insightText, { color: colors.textSecondary }]}>
            Follow up on the project proposal mentioned in your last conversation.
          </Text>
        </View>
      </View>
    </View>
  )

  const renderCurrentStep = () => {
    switch (demoState.currentStep) {
      case 'welcome':
        return renderWelcomeStep()
      case 'search':
        return renderSearchStep()
      case 'results':
        return renderResultsStep()
      case 'profile':
        return renderProfileStep()
      case 'messages':
        return renderMessagesStep()
      case 'insights':
        return renderInsightsStep()
      default:
        return renderWelcomeStep()
    }
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Icon name="chevron-back" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          Demo Workflow
        </Text>
        <TouchableOpacity onPress={handleResetDemo}>
          <Icon name="refresh" size={24} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {/* Progress Indicator */}
      <View style={styles.progressContainer}>
        {['welcome', 'search', 'results', 'profile', 'messages', 'insights'].map((step, index) => {
          const isActive = step === demoState.currentStep
          const isCompleted = ['welcome', 'search', 'results', 'profile', 'messages', 'insights']
            .indexOf(demoState.currentStep) > index
          
          return (
            <View
              key={step}
              style={[
                styles.progressStep,
                {
                  backgroundColor: isActive 
                    ? colors.primary 
                    : isCompleted 
                      ? colors.success 
                      : colors.border,
                },
              ]}
            />
          )
        })}
      </View>

      {/* Content */}
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {renderCurrentStep()}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  progressContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
  },
  progressStep: {
    flex: 1,
    height: 4,
    borderRadius: 2,
  },
  content: {
    flex: 1,
  },
  stepContainer: {
    padding: 20,
    alignItems: 'center',
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 12,
    marginTop: 16,
  },
  stepDescription: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  demoFeatures: {
    width: '100%',
    marginBottom: 32,
  },
  demoFeature: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  featureText: {
    fontSize: 16,
    marginLeft: 12,
    flex: 1,
  },
  searchContainer: {
    width: '100%',
    marginBottom: 20,
  },
  searchOptions: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 20,
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  optionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  naturalLanguageContainer: {
    width: '100%',
    marginBottom: 20,
  },
  exampleQueries: {
    width: '100%',
  },
  exampleTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
  },
  exampleQuery: {
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  exampleQueryText: {
    fontSize: 14,
  },
  resultsContainer: {
    width: '100%',
    marginBottom: 20,
  },
  profileContainer: {
    width: '100%',
    alignItems: 'center',
  },
  profileActions: {
    flexDirection: 'row',
    gap: 12,
    marginVertical: 20,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  actionButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 6,
  },
  profileStats: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  statCard: {
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    minWidth: 80,
  },
  statNumber: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
  messagesContainer: {
    width: '100%',
  },
  messagesSummary: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 20,
  },
  messagesSummaryTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  messagesSummaryText: {
    fontSize: 14,
    lineHeight: 20,
  },
  messagesStats: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  messagesStat: {
    flex: 1,
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  messagesStatNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  messagesStatLabel: {
    fontSize: 12,
    textAlign: 'center',
  },
  insightsContainer: {
    width: '100%',
  },
  insightCard: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  insightText: {
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    minWidth: 200,
  },
  primaryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: 'center',
    minWidth: 200,
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
})