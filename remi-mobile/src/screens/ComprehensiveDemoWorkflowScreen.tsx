/**
 * Comprehensive Demo Workflow Screen
 * Showcases complete end-to-end contact-based search functionality
 */

import React, { useState, useEffect } from 'react'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import Icon from 'react-native-vector-icons/Ionicons'
import { useTheme } from '@/hooks/useTheme'
import { unifiedBusinessLogic } from '@/services/unifiedBusinessLogic'
import { ContactSearchInput } from '@/components/ContactSearchInput'
import { ContactCard } from '@/components/ContactCard'
import { LoadingSpinner } from '@/components/LoadingSpinner'

interface DemoState {
  currentStep: number
  searchQuery: string
  searchResults: any
  selectedContact: any
  loading: boolean
  error: string | null
}

export function ComprehensiveDemoWorkflowScreen() {
  const navigation = useNavigation()
  const { colors } = useTheme()
  
  const [demoState, setDemoState] = useState<DemoState>({
    currentStep: 0,
    searchQuery: '',
    searchResults: null,
    selectedContact: null,
    loading: false,
    error: null
  })

  const demoSteps = [
    {
      id: 'welcome',
      title: 'Welcome to R.E.M.I Demo',
      description: 'Experience intelligent contact-based search',
      icon: 'play-circle'
    },
    {
      id: 'natural-search',
      title: 'Natural Language Search',
      description: 'Search using natural language queries',
      icon: 'chatbubble-ellipses'
    },
    {
      id: 'contact-discovery',
      title: 'Contact Discovery',
      description: 'Find contacts across platforms',
      icon: 'people'
    },
    {
      id: 'insights',
      title: 'AI Insights',
      description: 'View relationship insights',
      icon: 'analytics'
    },
    {
      id: 'complete',
      title: 'Demo Complete',
      description: 'Ready to get started!',
      icon: 'checkmark-circle'
    }
  ]

  useEffect(() => {
    initializeDemo()
  }, [])

  const initializeDemo = async () => {
    try {
      setDemoState(prev => ({ ...prev, loading: true }))
      await unifiedBusinessLogic.initialize()
      setDemoState(prev => ({ ...prev, loading: false }))
    } catch (error) {
      setDemoState(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to initialize demo'
      }))
    }
  }

  const nextStep = async () => {
    const currentStepData = demoSteps[demoState.currentStep]
    
    try {
      setDemoState(prev => ({ ...prev, loading: true }))
      
      // Simulate step actions
      switch (currentStepData.id) {
        case 'natural-search':
          setDemoState(prev => ({ ...prev, searchQuery: 'messages from John last week' }))
          break
        case 'contact-discovery':
          const mockResults = {
            contacts: [
              {
                id: '1',
                name: 'John Smith',
                email: 'john@example.com',
                platforms: ['gmail', 'slack']
              }
            ]
          }
          setDemoState(prev => ({ ...prev, searchResults: mockResults }))
          break
        case 'insights':
          setDemoState(prev => ({ 
            ...prev, 
            selectedContact: prev.searchResults?.contacts[0] 
          }))
          break
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      if (demoState.currentStep < demoSteps.length - 1) {
        setDemoState(prev => ({ 
          ...prev, 
          currentStep: prev.currentStep + 1,
          loading: false 
        }))
      } else {
        setDemoState(prev => ({ ...prev, loading: false }))
        Alert.alert(
          'Demo Complete!',
          'Ready to start using R.E.M.I?',
          [
            { text: 'Later', style: 'cancel' },
            { text: 'Get Started', onPress: () => navigation.navigate('PlatformConnections' as never) }
          ]
        )
      }
    } catch (error) {
      setDemoState(prev => ({ ...prev, loading: false, error: 'Demo step failed' }))
    }
  }

  const currentStep = demoSteps[demoState.currentStep]

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Icon name="arrow-back" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          R.E.M.I Demo
        </Text>
        <View style={{ width: 24 }} />
      </View>

      {/* Progress */}
      <View style={[styles.progressContainer, { backgroundColor: colors.surface }]}>
        <Text style={[styles.progressText, { color: colors.text }]}>
          Step {demoState.currentStep + 1} of {demoSteps.length}
        </Text>
        <View style={[styles.progressBar, { backgroundColor: colors.border }]}>
          <View 
            style={[
              styles.progressFill, 
              { 
                backgroundColor: colors.primary,
                width: `${((demoState.currentStep + 1) / demoSteps.length) * 100}%`
              }
            ]} 
          />
        </View>
      </View>

      {/* Content */}
      <ScrollView style={styles.content}>
        <View style={styles.stepHeader}>
          <View style={[styles.stepIcon, { backgroundColor: `${colors.primary}20` }]}>
            <Icon name={currentStep.icon} size={40} color={colors.primary} />
          </View>
          <Text style={[styles.stepTitle, { color: colors.text }]}>
            {currentStep.title}
          </Text>
          <Text style={[styles.stepDescription, { color: colors.textSecondary }]}>
            {currentStep.description}
          </Text>
        </View>

        {/* Demo Content */}
        <View style={styles.demoContent}>
          {currentStep.id === 'natural-search' && (
            <View>
              <ContactSearchInput
                value={demoState.searchQuery}
                onChangeText={() => {}}
                placeholder="Try: 'messages from John last week'"
                disabled={true}
              />
              {demoState.searchQuery && (
                <View style={styles.queryAnalysis}>
                  <Text style={[styles.analysisTitle, { color: colors.text }]}>
                    Query Analysis:
                  </Text>
                  <Text style={[styles.analysisText, { color: colors.textSecondary }]}>
                    • Person: John{'\n'}
                    • Time: Last week{'\n'}
                    • Type: Messages
                  </Text>
                </View>
              )}
            </View>
          )}

          {currentStep.id === 'contact-discovery' && demoState.searchResults && (
            <View>
              {demoState.searchResults.contacts.map((contact: any) => (
                <ContactCard
                  key={contact.id}
                  contact={contact}
                  onPress={() => {}}
                  showPlatforms={true}
                />
              ))}
            </View>
          )}

          {currentStep.id === 'insights' && demoState.selectedContact && (
            <View style={styles.insightsContainer}>
              <ContactCard
                contact={demoState.selectedContact}
                onPress={() => {}}
                showInsights={true}
              />
              <View style={styles.insightsList}>
                <Text style={[styles.insightsTitle, { color: colors.text }]}>
                  AI Insights:
                </Text>
                <Text style={[styles.insightText, { color: colors.textSecondary }]}>
                  • High communication frequency{'\n'}
                  • Strong relationship (85%){'\n'}
                  • Best contact time: 10 AM - 2 PM
                </Text>
              </View>
            </View>
          )}
        </View>

        {demoState.loading && (
          <View style={styles.loadingContainer}>
            <LoadingSpinner size="large" />
            <Text style={[styles.loadingText, { color: colors.text }]}>
              Processing...
            </Text>
          </View>
        )}
      </ScrollView>

      {/* Navigation */}
      <View style={[styles.navigation, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={nextStep}
          disabled={demoState.loading}
          style={[
            styles.nextButton, 
            { 
              backgroundColor: demoState.loading ? colors.border : colors.primary,
              opacity: demoState.loading ? 0.5 : 1
            }
          ]}
        >
          <Text style={[styles.nextButtonText, { color: colors.surface }]}>
            {demoState.currentStep === demoSteps.length - 1 ? 'Finish Demo' : 'Next Step'}
          </Text>
          <Icon name="chevron-forward" size={20} color={colors.surface} />
        </TouchableOpacity>
      </View>
    </View>
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
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  progressContainer: {
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  progressText: {
    fontSize: 14,
    marginBottom: 8,
    textAlign: 'center',
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  content: {
    flex: 1,
  },
  stepHeader: {
    alignItems: 'center',
    padding: 20,
  },
  stepIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  stepDescription: {
    fontSize: 16,
    textAlign: 'center',
    lineHeight: 24,
  },
  demoContent: {
    padding: 20,
  },
  queryAnalysis: {
    marginTop: 20,
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  analysisTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  analysisText: {
    fontSize: 14,
    lineHeight: 20,
  },
  insightsContainer: {
    gap: 16,
  },
  insightsList: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  insightsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  insightText: {
    fontSize: 14,
    lineHeight: 20,
  },
  loadingContainer: {
    alignItems: 'center',
    padding: 40,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  navigation: {
    padding: 20,
  },
  nextButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 12,
    gap: 8,
  },
  nextButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
})

export default ComprehensiveDemoWorkflowScreen