import React, { useState, useEffect } from 'react'
import { View, StyleSheet, Alert } from 'react-native'
import { RouteProp, useRoute } from '@react-navigation/native'
import { useTheme } from '@/hooks/useTheme'
import { MessageThread } from '@/components/MessageThread'
import { RootStackParamList, ConversationThread, Message, UnifiedContact, TextHighlight, Attachment } from '@/types'

type MessageThreadScreenRouteProp = RouteProp<RootStackParamList, 'MessageThread'>

export function MessageThreadScreen() {
  const { colors } = useTheme()
  const route = useRoute<MessageThreadScreenRouteProp>()
  const { threadId } = route.params

  const [thread, setThread] = useState<ConversationThread | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [highlights, setHighlights] = useState<TextHighlight[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadThreadData()
  }, [threadId])

  const loadThreadData = async () => {
    try {
      setLoading(true)
      
      // Mock contact data
      const mockContact: UnifiedContact = {
        id: 'contact-1',
        primaryName: 'John Smith',
        displayName: 'John Smith',
        profilePhoto: undefined,
        identities: [],
        emails: ['john.smith@gmail.com'],
        phoneNumbers: [],
        socialProfiles: [],
        lastInteraction: new Date(),
        totalMessages: 247,
        platforms: ['gmail'],
        relationshipStrength: 0.85,
        communicationFrequency: 'high',
        responsePattern: {
          averageResponseTime: 45,
          responseRate: 0.92,
          preferredTimes: [],
          communicationStyle: 'professional',
        },
        topicAffinity: [],
        sharedFiles: [],
        sharedLinks: [],
        commonContacts: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        lastSyncAt: new Date(),
      }

      // Mock thread data
      const mockThread: ConversationThread = {
        id: threadId,
        platform: 'gmail',
        platformThreadId: 'thread-1',
        title: 'Project Discussion',
        participants: [mockContact],
        messageCount: 5,
        createdAt: new Date('2024-01-01'),
        lastMessageAt: new Date('2024-01-15'),
        summary: {
          shortSummary: 'Discussion about project timeline and deliverables',
          keyPoints: ['Timeline agreed', 'Budget approved'],
          actionItems: [],
          decisions: [],
          nextSteps: [],
          generatedAt: new Date(),
        },
        keyTopics: ['project', 'timeline'],
        relationshipDynamics: [],
        isMuted: false,
        isArchived: false,
        recentMessages: [],
      }

      // Mock messages data
      const mockMessages: Message[] = [
        {
          id: '1',
          threadId: threadId,
          platform: 'gmail',
          platformMessageId: 'msg-1',
          content: {
            text: 'Hi John, I wanted to discuss the project timeline with you.',
            mediaType: 'text',
          },
          attachments: [],
          sender: {
            id: 'current-user',
            primaryName: 'You',
            displayName: 'You',
            profilePhoto: undefined,
            identities: [],
            emails: [],
            phoneNumbers: [],
            socialProfiles: [],
            lastInteraction: new Date(),
            totalMessages: 0,
            platforms: [],
            relationshipStrength: 0,
            communicationFrequency: 'high',
            responsePattern: {
              averageResponseTime: 0,
              responseRate: 0,
              preferredTimes: [],
              communicationStyle: 'casual',
            },
            topicAffinity: [],
            sharedFiles: [],
            sharedLinks: [],
            commonContacts: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            lastSyncAt: new Date(),
          },
          recipients: [mockContact],
          timestamp: new Date('2024-01-15T10:00:00'),
          isRead: true,
          isImportant: false,
          entities: [],
          sentiment: {
            overall: 0.1,
            confidence: 0.8,
            emotions: [],
          },
          topics: ['project', 'timeline'],
          commitments: [],
          searchableText: 'Hi John, I wanted to discuss the project timeline with you.',
          lastSyncAt: new Date(),
          syncVersion: 1,
        },
        {
          id: '2',
          threadId: threadId,
          platform: 'gmail',
          platformMessageId: 'msg-2',
          content: {
            text: 'Sure! I think we can deliver the first milestone by the end of this month. What do you think?',
            mediaType: 'text',
          },
          attachments: [
            {
              id: 'att-1',
              name: 'project_timeline.pdf',
              type: 'application/pdf',
              size: 1024000,
              url: 'https://example.com/timeline.pdf',
              thumbnailUrl: undefined,
            },
          ],
          sender: mockContact,
          recipients: [],
          timestamp: new Date('2024-01-15T10:15:00'),
          isRead: true,
          isImportant: false,
          entities: [
            {
              id: 'entity-1',
              type: 'DATE',
              text: 'end of this month',
              confidence: 0.95,
              startOffset: 45,
              endOffset: 63,
            },
          ],
          sentiment: {
            overall: 0.3,
            confidence: 0.7,
            emotions: [],
          },
          topics: ['milestone', 'timeline'],
          commitments: [
            {
              id: 'commit-1',
              description: 'Deliver first milestone by end of month',
              assignee: 'John Smith',
              dueDate: new Date('2024-01-31'),
              status: 'pending',
              priority: 'medium',
              extractedAt: new Date(),
              confidence: 0.9,
            },
          ],
          searchableText: 'Sure! I think we can deliver the first milestone by the end of this month. What do you think?',
          lastSyncAt: new Date(),
          syncVersion: 1,
        },
      ]

      setThread(mockThread)
      setMessages(mockMessages.reverse()) // Reverse for inverted FlatList
    } catch (error) {
      console.error('Error loading thread data:', error)
      Alert.alert('Error', 'Failed to load conversation')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    
    if (!query.trim()) {
      setHighlights([])
      return
    }

    // Simple search highlighting - in real app, this would come from the API
    const newHighlights: TextHighlight[] = []
    messages.forEach(message => {
      if (message.content.text) {
        const text = message.content.text.toLowerCase()
        const searchTerm = query.toLowerCase()
        let index = text.indexOf(searchTerm)
        
        while (index !== -1) {
          newHighlights.push({
            start: index,
            end: index + searchTerm.length,
            text: message.content.text,
          })
          index = text.indexOf(searchTerm, index + 1)
        }
      }
    })
    
    setHighlights(newHighlights)
  }

  const handleMessagePress = (message: Message) => {
    Alert.alert('Message Details', `Message from ${message.sender.primaryName} at ${message.timestamp.toLocaleString()}`)
  }

  const handleAttachmentPress = (attachment: Attachment) => {
    Alert.alert('Attachment', `Would you like to download ${attachment.name}?`)
  }

  if (loading || !thread) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: colors.background }]}>
        {/* Add loading spinner here */}
      </View>
    )
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <MessageThread
        thread={thread}
        messages={messages}
        searchQuery={searchQuery}
        highlights={highlights}
        loading={loading}
        onRefresh={loadThreadData}
        onMessagePress={handleMessagePress}
        onAttachmentPress={handleAttachmentPress}
        onSearch={handleSearch}
        hasMore={false}
      />
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