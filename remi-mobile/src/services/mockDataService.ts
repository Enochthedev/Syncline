/**
 * Mock Data Service
 * 
 * Provides mock data and responses for testing without full backend
 */

import { UnifiedContact, ConversationThread, Message, SearchResult, ProactiveInsight, InsightType } from '@/types'

export class MockDataService {
    private static instance: MockDataService
    private contacts: UnifiedContact[] = []
    private threads: ConversationThread[] = []
    private messages: Message[] = []

    static getInstance(): MockDataService {
        if (!MockDataService.instance) {
            MockDataService.instance = new MockDataService()
        }
        return MockDataService.instance
    }

    constructor() {
        this.initializeMockData()
    }

    private initializeMockData(): void {
        // Generate mock contacts
        this.contacts = [
            {
                id: 'contact-1',
                primaryName: 'John Smith',
                displayName: 'John Smith',
                profilePhoto: 'https://i.pravatar.cc/150?img=1',
                identities: [
                    {
                        platform: 'gmail',
                        platformUserId: 'john.smith@company.com',
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
                emails: ['john.smith@company.com', 'john@personal.com'],
                phoneNumbers: ['+1-555-0123'],
                socialProfiles: [
                    {
                        platform: 'linkedin',
                        url: 'https://linkedin.com/in/johnsmith',
                        handle: 'johnsmith',
                    },
                ],
                lastInteraction: new Date('2024-01-15T14:30:00'),
                totalMessages: 127,
                platforms: ['gmail', 'slack'],
                preferredPlatform: 'gmail',
                relationshipStrength: 0.85,
                communicationFrequency: 'high',
                responsePattern: {
                    averageResponseTime: 45,
                    responseRate: 0.92,
                    preferredTimes: ['09:00-12:00', '14:00-17:00'],
                    communicationStyle: 'professional',
                },
                topicAffinity: [
                    { topic: 'project management', frequency: 0.4, sentiment: 'positive' },
                    { topic: 'team meetings', frequency: 0.3, sentiment: 'neutral' },
                    { topic: 'deadlines', frequency: 0.2, sentiment: 'negative' },
                ],
                sharedFiles: [
                    {
                        id: 'file-1',
                        name: 'Project_Proposal.pdf',
                        type: 'application/pdf',
                        size: 2048576,
                        url: 'https://example.com/files/proposal.pdf',
                        sharedAt: new Date('2024-01-10T10:00:00'),
                        platform: 'gmail',
                    },
                ],
                sharedLinks: [
                    {
                        id: 'link-1',
                        url: 'https://github.com/company/project',
                        title: 'Project Repository',
                        description: 'Main project repository',
                        sharedAt: new Date('2024-01-12T15:30:00'),
                        platform: 'slack',
                    },
                ],
                commonContacts: ['contact-2', 'contact-3'],
                createdAt: new Date('2024-01-01T00:00:00'),
                updatedAt: new Date('2024-01-15T14:30:00'),
                lastSyncAt: new Date('2024-01-15T14:30:00'),
            },
            {
                id: 'contact-2',
                primaryName: 'Sarah Johnson',
                displayName: 'Sarah Johnson',
                profilePhoto: 'https://i.pravatar.cc/150?img=2',
                identities: [
                    {
                        platform: 'gmail',
                        platformUserId: 'sarah.johnson@company.com',
                        displayName: 'Sarah Johnson',
                        handle: 'sarah.johnson',
                        verified: true,
                    },
                ],
                emails: ['sarah.johnson@company.com'],
                phoneNumbers: ['+1-555-0456'],
                socialProfiles: [],
                lastInteraction: new Date('2024-01-14T16:45:00'),
                totalMessages: 89,
                platforms: ['gmail'],
                preferredPlatform: 'gmail',
                relationshipStrength: 0.72,
                communicationFrequency: 'medium',
                responsePattern: {
                    averageResponseTime: 120,
                    responseRate: 0.78,
                    preferredTimes: ['10:00-12:00', '15:00-17:00'],
                    communicationStyle: 'casual',
                },
                topicAffinity: [
                    { topic: 'design reviews', frequency: 0.5, sentiment: 'positive' },
                    { topic: 'user feedback', frequency: 0.3, sentiment: 'neutral' },
                ],
                sharedFiles: [],
                sharedLinks: [],
                commonContacts: ['contact-1'],
                createdAt: new Date('2024-01-01T00:00:00'),
                updatedAt: new Date('2024-01-14T16:45:00'),
                lastSyncAt: new Date('2024-01-14T16:45:00'),
            },
            {
                id: 'contact-3',
                primaryName: 'Mike Chen',
                displayName: 'Mike Chen',
                profilePhoto: 'https://i.pravatar.cc/150?img=3',
                identities: [
                    {
                        platform: 'slack',
                        platformUserId: 'U789012',
                        displayName: 'Mike Chen',
                        handle: 'mchen',
                        verified: true,
                    },
                    {
                        platform: 'discord',
                        platformUserId: '345678901234567890',
                        displayName: 'MikeChen#1234',
                        handle: 'MikeChen',
                        verified: false,
                    },
                ],
                emails: ['mike.chen@company.com'],
                phoneNumbers: [],
                socialProfiles: [],
                lastInteraction: new Date('2024-01-13T11:20:00'),
                totalMessages: 45,
                platforms: ['slack', 'discord'],
                preferredPlatform: 'slack',
                relationshipStrength: 0.65,
                communicationFrequency: 'low',
                responsePattern: {
                    averageResponseTime: 240,
                    responseRate: 0.65,
                    preferredTimes: ['13:00-15:00'],
                    communicationStyle: 'casual',
                },
                topicAffinity: [
                    { topic: 'technical discussions', frequency: 0.6, sentiment: 'positive' },
                    { topic: 'code reviews', frequency: 0.4, sentiment: 'neutral' },
                ],
                sharedFiles: [],
                sharedLinks: [],
                commonContacts: ['contact-1'],
                createdAt: new Date('2024-01-01T00:00:00'),
                updatedAt: new Date('2024-01-13T11:20:00'),
                lastSyncAt: new Date('2024-01-13T11:20:00'),
            },
        ]

        // Generate mock threads and messages
        this.generateMockThreadsAndMessages()
    }

    private generateMockThreadsAndMessages(): void {
        // Create threads for each contact
        this.contacts.forEach((contact, index) => {
            const thread: ConversationThread = {
                id: `thread-${contact.id}`,
                platform: contact.preferredPlatform || 'gmail',
                platformThreadId: `platform-thread-${index}`,
                title: `Conversation with ${contact.primaryName}`,
                participants: [contact],
                messageCount: contact.totalMessages,
                createdAt: new Date(contact.createdAt),
                lastMessageAt: new Date(contact.lastInteraction),
                lastReadAt: new Date(contact.lastInteraction),
                summary: {
                    shortSummary: `Recent conversation with ${contact.primaryName} about work topics`,
                    keyPoints: [
                        'Discussed project timeline',
                        'Shared important documents',
                        'Scheduled follow-up meeting',
                    ],
                    actionItems: [
                        {
                            id: `action-${index}-1`,
                            description: 'Review project proposal',
                            assignee: 'me',
                            dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
                            status: 'pending',
                        },
                    ],
                    decisions: [
                        {
                            id: `decision-${index}-1`,
                            description: 'Approved budget increase',
                            decidedBy: contact.primaryName,
                            decidedAt: new Date(contact.lastInteraction),
                            impact: 'medium',
                        },
                    ],
                    nextSteps: ['Schedule team meeting', 'Update project timeline'],
                    generatedAt: new Date(),
                },
                keyTopics: contact.topicAffinity.map(t => t.topic),
                relationshipDynamics: [
                    {
                        participantId: contact.id,
                        role: 'collaborator',
                        influence: contact.relationshipStrength,
                        engagement: contact.relationshipStrength * 0.9,
                    },
                ],
                isMuted: false,
                isArchived: false,
                recentMessages: [],
            }

            this.threads.push(thread)

            // Generate some messages for each thread
            for (let i = 0; i < Math.min(5, contact.totalMessages); i++) {
                const message: Message = {
                    id: `message-${contact.id}-${i}`,
                    threadId: thread.id,
                    platform: thread.platform,
                    platformMessageId: `platform-msg-${contact.id}-${i}`,
                    content: {
                        text: this.generateMockMessageText(contact.primaryName, i),
                        mediaType: 'text',
                    },
                    attachments: [],
                    sender: i % 2 === 0 ? contact : this.getCurrentUser(),
                    recipients: i % 2 === 0 ? [this.getCurrentUser()] : [contact],
                    timestamp: new Date(Date.now() - (5 - i) * 24 * 60 * 60 * 1000),
                    isRead: true,
                    isImportant: i === 0,
                    entities: [],
                    sentiment: {
                        overall: 0.1 + Math.random() * 0.8,
                        confidence: 0.8,
                        emotions: [
                            { emotion: 'positive', score: 0.6 },
                            { emotion: 'neutral', score: 0.3 },
                            { emotion: 'negative', score: 0.1 },
                        ],
                    },
                    topics: contact.topicAffinity.slice(0, 2).map(t => t.topic),
                    commitments: [],
                    searchableText: this.generateMockMessageText(contact.primaryName, i),
                    lastSyncAt: new Date(),
                    syncVersion: 1,
                }

                this.messages.push(message)
            }
        })
    }

    private generateMockMessageText(contactName: string, index: number): string {
        const templates = [
            `Hi ${contactName}, hope you're doing well! Let's discuss the project timeline.`,
            `Thanks for sharing the documents. I'll review them and get back to you.`,
            `The meeting went great! Here are the key takeaways we discussed.`,
            `Quick question about the budget - can we schedule a call to discuss?`,
            `Perfect! I'll send over the updated proposal by end of day.`,
        ]
        return templates[index % templates.length]
    }

    private getCurrentUser(): UnifiedContact {
        return {
            id: 'current-user',
            primaryName: 'You',
            displayName: 'You',
            identities: [],
            emails: ['you@company.com'],
            phoneNumbers: [],
            socialProfiles: [],
            lastInteraction: new Date(),
            totalMessages: 0,
            platforms: [],
            relationshipStrength: 1.0,
            communicationFrequency: 'high',
            responsePattern: {
                averageResponseTime: 30,
                responseRate: 1.0,
                preferredTimes: ['09:00-17:00'],
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
    }

    // Public API methods
    async searchContacts(query: string): Promise<UnifiedContact[]> {
        if (!query || query.length < 2) {
            return []
        }

        const lowercaseQuery = query.toLowerCase()
        return this.contacts.filter(contact =>
            contact.primaryName.toLowerCase().includes(lowercaseQuery) ||
            contact.displayName.toLowerCase().includes(lowercaseQuery) ||
            contact.emails.some(email => email.toLowerCase().includes(lowercaseQuery)) ||
            contact.phoneNumbers.some(phone => phone.includes(query)) ||
            contact.identities.some(identity =>
                identity.displayName.toLowerCase().includes(lowercaseQuery) ||
                (identity.handle && identity.handle.toLowerCase().includes(lowercaseQuery))
            )
        )
    }

    async getContact(contactId: string): Promise<UnifiedContact | null> {
        return this.contacts.find(c => c.id === contactId) || null
    }

    async getContacts(): Promise<UnifiedContact[]> {
        return [...this.contacts]
    }

    async getThreadsForContact(contactId: string): Promise<ConversationThread[]> {
        return this.threads.filter(thread =>
            thread.participants.some(p => p.id === contactId)
        )
    }

    async getMessagesForThread(threadId: string): Promise<Message[]> {
        return this.messages.filter(m => m.threadId === threadId)
    }

    async searchMessages(query: string, contactId?: string): Promise<SearchResult[]> {
        let filteredMessages = this.messages

        if (contactId) {
            const contactThreads = await this.getThreadsForContact(contactId)
            const threadIds = contactThreads.map(t => t.id)
            filteredMessages = filteredMessages.filter(m => threadIds.includes(m.threadId))
        }

        if (query && query.length >= 2) {
            const lowercaseQuery = query.toLowerCase()
            filteredMessages = filteredMessages.filter(m =>
                m.content.text?.toLowerCase().includes(lowercaseQuery) ||
                m.searchableText.toLowerCase().includes(lowercaseQuery)
            )
        }

        return filteredMessages.map(message => ({
            id: message.id,
            type: 'message' as const,
            title: `Message from ${message.sender.primaryName}`,
            snippet: message.content.text?.substring(0, 100) + '...' || '',
            content: message.content.text,
            relevanceScore: 0.8,
            timestamp: message.timestamp,
            contact: message.sender,
            platform: message.platform,
            highlights: [],
            quickActions: [
                {
                    id: 'view-thread',
                    label: 'View Thread',
                    icon: 'chatbubbles',
                    action: () => console.log('View thread:', message.threadId),
                },
            ],
        }))
    }

    async getProactiveInsights(): Promise<ProactiveInsight[]> {
        return [
            {
                id: 'insight-1',
                type: InsightType.FOLLOW_UP_REMINDER,
                title: 'Follow up with John Smith',
                description: 'You promised to send the project proposal by today',
                priority: 'high',
                relatedContacts: [this.contacts[0]],
                relatedMessages: [],
                suggestedActions: [
                    {
                        id: 'send-email',
                        label: 'Send Email',
                        description: 'Send the promised project proposal',
                        actionType: 'email',
                    },
                ],
                createdAt: new Date(),
                isRead: false,
                isActedUpon: false,
            },
            {
                id: 'insight-2',
                type: InsightType.RECONNECTION_SUGGESTION,
                title: 'Reconnect with Sarah Johnson',
                description: 'You haven\'t talked to Sarah in 3 days, which is unusual',
                priority: 'medium',
                relatedContacts: [this.contacts[1]],
                relatedMessages: [],
                suggestedActions: [
                    {
                        id: 'send-message',
                        label: 'Send Message',
                        description: 'Check in with Sarah',
                        actionType: 'message',
                    },
                ],
                createdAt: new Date(),
                isRead: false,
                isActedUpon: false,
            },
        ]
    }

    async getContactSuggestions(partialQuery: string): Promise<string[]> {
        if (!partialQuery || partialQuery.length < 1) {
            return []
        }

        const suggestions = new Set<string>()
        const lowercaseQuery = partialQuery.toLowerCase()

        this.contacts.forEach(contact => {
            if (contact.primaryName.toLowerCase().startsWith(lowercaseQuery)) {
                suggestions.add(contact.primaryName)
            }
            if (contact.displayName.toLowerCase().startsWith(lowercaseQuery)) {
                suggestions.add(contact.displayName)
            }
            contact.emails.forEach(email => {
                if (email.toLowerCase().startsWith(lowercaseQuery)) {
                    suggestions.add(email)
                }
            })
        })

        return Array.from(suggestions).slice(0, 5)
    }

    // Simulate API delays
    private async delay(ms: number = 300): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    async simulateApiCall<T>(data: T, delay: number = 300): Promise<T> {
        await this.delay(delay)
        return data
    }
}

export const mockDataService = MockDataService.getInstance()