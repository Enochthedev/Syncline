import React, { useState, useEffect } from 'react'
import { View, StyleSheet, Alert } from 'react-native'
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native'
import { StackNavigationProp } from '@react-navigation/stack'
import { useTheme } from '@/hooks/useTheme'
import { ContactProfile } from '@/components/ContactProfile'
import { ContactMessages } from '@/components/ContactMessages'
import { SharedContent } from '@/components/SharedContent'
import { RootStackParamList, UnifiedContact, ConversationThread } from '@/types'

type ContactProfileScreenRouteProp = RouteProp<RootStackParamList, 'ContactProfile'>
type ContactProfileScreenNavigationProp = StackNavigationProp<RootStackParamList, 'ContactProfile'>

type ViewMode = 'profile' | 'messages' | 'shared'

export function ContactProfileScreen() {
  const { colors } = useTheme()
  const route = useRoute<ContactProfileScreenRouteProp>()
  const navigation = useNavigation<ContactProfileScreenNavigationProp>()
  const { contactId } = route.params

  const [contact, setContact] = useState<UnifiedContact | null>(null)
  const [threads, setThreads] = useState<ConversationThread[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('profile')
  const [loading, setLoading] = useState(true)

  // Mock data for demonstration - replace with actual API calls
  useEffect(() => {
    loadContactData()
  }, [contactId])

  const loadContactData = async () => {
    try {
      setLoading(true)
      
      // Mock contact data - replace with actual API call
      const mockContact: UnifiedContact = {
        id: contactId,
        primaryName: 'John Smith',
        displayName: 'John Smith',
        profilePhoto: undefined,
        identities: [
          {
            platform: 'gmail',
            platformUserId: 'john.smith@gmail.com',
            displayName: 'John Smith',
            handle: 'john.smith',
            verified: true,
          },
          {
            platform: 'slack',
            platformUserId: 'U123456',
            displayName: 'John Smith',
            handle: 'jsmith',
            verified: true,
          },
        ],
        emails: ['john.smith@gmail.com', 'j.smith@company.com'],
        phoneNumbers: ['+1-555-0123'],
        socialProfiles: [
          {
            platform: 'linkedin',
            url: 'https://linkedin.com/in/johnsmith',
            handle: 'johnsmith',
          },
        ],
        lastInteraction: new Date('2024-01-15'),
        totalMessages: 247,
        platforms: ['gmail', 'slack'],
        preferredPlatform: 'gmail',
        relationshipStrength: 0.85,
        communicationFrequency: 'high',
        responsePattern: {
          averageResponseTime: 45,
          responseRate: 0.92,
          preferredTimes: ['9:00-12:00', '14:00-17:00'],
          communicationStyle: 'professional',
        },
        topicAffinity: [
          { topic: 'project management', frequency: 15, sentiment: 'positive' },
          { topic: 'team meetings', frequency: 12, sentiment: 'neutral' },
        ],
        sharedFiles: [
          {
            id: '1',
            name: 'Project_Proposal.pdf',
            type: 'application/pdf',
            size: 2048576,
            url: 'https://example.com/file1.pdf',
            sharedAt: new Date('2024-01-10'),
            platform: 'gmail',
          },
        ],
        sharedLinks: [
          {
            id: '1',
            url: 'https://github.com/project/repo',
            title: 'Project Repository',
            description: 'Main project repository on GitHub',
            sharedAt: new Date('2024-01-12'),
            platform: 'slack',
          },
        ],
        commonContacts: [],
        createdAt: new Date('2023-06-01'),
        updatedAt: new Date('2024-01-15'),
        lastSyncAt: new Date('2024-01-15'),
      }

      // Mock threads data
      const mockThreads: ConversationThread[] = [
        {
          id: '1',
          platform: 'gmail',
          platformThreadId: 'thread-1',
          title: 'Project Discussion',
          participants: [mockContact],
          messageCount: 15,
          createdAt: new Date('2024-01-01'),
          lastMessageAt: new Date('2024-01-15'),
          summary: {
            shortSummary: 'Discussion about project timeline and deliverables',
            keyPoints: ['Timeline agreed', 'Budget approved'],
            actionItems: [
              {
                id: '1',
                description: 'Prepare project proposal',
                assignee: 'John Smith',
                dueDate: new Date('2024-01-20'),
                status: 'pending',
              },
            ],
            decisions: [],
            nextSteps: ['Review proposal', 'Schedule follow-up'],
            generatedAt: new Date('2024-01-15'),
          },
          keyTopics: ['project', 'timeline', 'budget'],
          relationshipDynamics: [],
          isMuted: false,
          isArchived: false,
          recentMessages: [],
        },
      ]

      setContact(mockContact)
      setThreads(mockThreads)
    } catch (error) {
      console.error('Error loading contact data:', error)
      Alert.alert('Error', 'Failed to load contact information')
    } finally {
      setLoading(false)
    }
  }

  const handleMessagePress = () => {
    Alert.alert('Message', 'Message functionality not implemented yet')
  }

  const handleCallPress = () => {
    if (contact?.phoneNumbers.length) {
      Alert.alert('Call', `Would you like to call ${contact.phoneNumbers[0]}?`)
    }
  }

  const handleEmailPress = () => {
    if (contact?.emails.length) {
      Alert.alert('Email', `Would you like to email ${contact.emails[0]}?`)
    }
  }

  const handleViewMessagesPress = () => {
    setViewMode('messages')
  }

  const handleViewSharedContentPress = () => {
    setViewMode('shared')
  }

  const handleThreadPress = (thread: ConversationThread) => {
    navigation.navigate('MessageThread', { threadId: thread.id })
  }

  const handleBackToProfile = () => {
    setViewMode('profile')
  }

  if (loading || !contact) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: colors.background }]}>
        {/* Add loading spinner here */}
      </View>
    )
  }

  const renderContent = () => {
    switch (viewMode) {
      case 'messages':
        return (
          <ContactMessages
            contact={contact}
            threads={threads}
            loading={loading}
            onRefresh={loadContactData}
            onThreadPress={handleThreadPress}
          />
        )
      case 'shared':
        return (
          <SharedContent
            contact={contact}
            files={contact.sharedFiles}
            links={contact.sharedLinks}
            loading={loading}
            onRefresh={loadContactData}
          />
        )
      default:
        return (
          <ContactProfile
            contact={contact}
            onMessagePress={handleMessagePress}
            onCallPress={handleCallPress}
            onEmailPress={handleEmailPress}
            onViewMessagesPress={handleViewMessagesPress}
            onViewSharedContentPress={handleViewSharedContentPress}
          />
        )
    }
  }

  // Update navigation header based on view mode
  React.useLayoutEffect(() => {
    navigation.setOptions({
      title: viewMode === 'profile' ? 'Contact Profile' : 
             viewMode === 'messages' ? 'Messages' : 'Shared Content',
      headerLeft: viewMode !== 'profile' ? () => (
        <View style={{ marginLeft: 16 }}>
          {/* Add back button for non-profile views */}
        </View>
      ) : undefined,
    })
  }, [navigation, viewMode])

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {renderContent()}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
})