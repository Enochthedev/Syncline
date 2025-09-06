/**
 * Contact Profile Integration Tests
 * 
 * Tests the integration between ContactProfile, ContactMessages, SharedContent, and MessageThread components
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ContactProfile } from '../../src/components/ContactProfile';
import { ContactMessages } from '../../src/components/ContactMessages';
import { SharedContent } from '../../src/components/SharedContent';
import { MessageThread } from '../../src/components/MessageThread';
import { UnifiedContact, ConversationThread, Message } from '../../src/types';

// Mock the theme hook
jest.mock('../../src/hooks/useTheme', () => ({
  useTheme: () => ({
    theme: {
      colors: {
        background: '#ffffff',
        surface: '#f8f9fa',
        primary: '#007bff',
        success: '#28a745',
        warning: '#ffc107',
        error: '#dc3545',
        text: '#212529',
        textSecondary: '#6c757d',
        border: '#dee2e6',
        white: '#ffffff',
      },
    },
  }),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');

// Mock Linking
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Linking: {
      openURL: jest.fn(),
    },
    Alert: {
      alert: jest.fn(),
    },
  };
});

const createMockContact = (): UnifiedContact => ({
  id: '1',
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
  ],
  emails: ['john.smith@gmail.com'],
  phoneNumbers: ['+1-555-0123'],
  socialProfiles: [],
  lastInteraction: new Date('2024-01-15'),
  totalMessages: 247,
  platforms: ['gmail'],
  preferredPlatform: 'gmail',
  relationshipStrength: 0.85,
  communicationFrequency: 'high',
  responsePattern: {
    averageResponseTime: 45,
    responseRate: 0.92,
    preferredTimes: ['9:00-12:00'],
    communicationStyle: 'professional',
  },
  topicAffinity: [],
  sharedFiles: [
    {
      id: '1',
      name: 'document.pdf',
      type: 'application/pdf',
      size: 1024000,
      url: 'https://example.com/doc.pdf',
      sharedAt: new Date('2024-01-10'),
      platform: 'gmail',
    },
  ],
  sharedLinks: [
    {
      id: '1',
      url: 'https://github.com/project',
      title: 'Project Repository',
      description: 'Main project repo',
      sharedAt: new Date('2024-01-12'),
      platform: 'gmail',
    },
  ],
  commonContacts: [],
  createdAt: new Date('2023-06-01'),
  updatedAt: new Date('2024-01-15'),
  lastSyncAt: new Date('2024-01-15'),
});

describe('Contact Profile Integration', () => {
  let mockContact: UnifiedContact;

  beforeEach(() => {
    mockContact = createMockContact();
  });

  describe('ContactProfile Component', () => {
    it('renders all contact information sections', () => {
      const { getByText } = render(<ContactProfile contact={mockContact} />);

      // Header information
      expect(getByText('John Smith')).toBeTruthy();
      expect(getByText('john.smith@gmail.com')).toBeTruthy();
      expect(getByText('+1-555-0123')).toBeTruthy();

      // Platform identities
      expect(getByText('Gmail')).toBeTruthy();
      expect(getByText('@john.smith')).toBeTruthy();

      // Communication insights
      expect(getByText('247')).toBeTruthy(); // Total messages
      expect(getByText('High')).toBeTruthy(); // Frequency
      expect(getByText('85%')).toBeTruthy(); // Relationship strength
    });

    it('integrates with navigation callbacks', () => {
      const mockViewMessages = jest.fn();
      const mockViewSharedContent = jest.fn();

      const { getByText } = render(
        <ContactProfile
          contact={mockContact}
          onViewMessagesPress={mockViewMessages}
          onViewSharedContentPress={mockViewSharedContent}
        />
      );

      // Quick actions should be available
      expect(getByText('View Messages (247)')).toBeTruthy();
      expect(getByText('Shared Content (2)')).toBeTruthy();
    });
  });

  describe('ContactMessages Component', () => {
    it('displays conversation threads grouped by platform', () => {
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
            shortSummary: 'Discussion about project timeline',
            keyPoints: [],
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
        },
      ];

      const mockOnThreadPress = jest.fn();

      const { getByText } = render(
        <ContactMessages
          contact={mockContact}
          threads={mockThreads}
          onThreadPress={mockOnThreadPress}
        />
      );

      expect(getByText('Gmail')).toBeTruthy();
      expect(getByText('Project Discussion')).toBeTruthy();
      expect(getByText('15 messages')).toBeTruthy();
    });
  });

  describe('SharedContent Component', () => {
    it('displays files and links from contact', () => {
      const { getByText } = render(
        <SharedContent
          contact={mockContact}
          files={mockContact.sharedFiles}
          links={mockContact.sharedLinks}
        />
      );

      expect(getByText('Shared Content with John Smith')).toBeTruthy();
      expect(getByText('1 files • 1 links')).toBeTruthy();
      expect(getByText('document.pdf')).toBeTruthy();
      expect(getByText('Project Repository')).toBeTruthy();
    });

    it('filters content correctly', () => {
      const { getByText, queryByText } = render(
        <SharedContent
          contact={mockContact}
          files={mockContact.sharedFiles}
          links={mockContact.sharedLinks}
        />
      );

      // Filter to files only
      fireEvent.press(getByText('Files'));
      expect(getByText('document.pdf')).toBeTruthy();
      expect(queryByText('Project Repository')).toBeFalsy();

      // Filter to links only
      fireEvent.press(getByText('Links'));
      expect(getByText('Project Repository')).toBeTruthy();
      expect(queryByText('document.pdf')).toBeFalsy();
    });
  });

  describe('MessageThread Component', () => {
    it('displays messages with proper formatting', () => {
      const mockThread: ConversationThread = {
        id: '1',
        platform: 'gmail',
        platformThreadId: 'thread-1',
        title: 'Project Discussion',
        participants: [mockContact],
        messageCount: 2,
        createdAt: new Date('2024-01-01'),
        lastMessageAt: new Date('2024-01-15'),
        summary: {
          shortSummary: 'Discussion about project',
          keyPoints: [],
          actionItems: [],
          decisions: [],
          nextSteps: [],
          generatedAt: new Date(),
        },
        keyTopics: [],
        relationshipDynamics: [],
        isMuted: false,
        isArchived: false,
        recentMessages: [],
      };

      const mockMessages: Message[] = [
        {
          id: '1',
          threadId: '1',
          platform: 'gmail',
          platformMessageId: 'msg-1',
          content: {
            text: 'Hello John, how are you?',
            mediaType: 'text',
          },
          attachments: [],
          sender: mockContact,
          recipients: [],
          timestamp: new Date('2024-01-15T10:00:00'),
          isRead: true,
          isImportant: false,
          entities: [],
          sentiment: {
            overall: 0.1,
            confidence: 0.8,
            emotions: [],
          },
          topics: [],
          commitments: [],
          searchableText: 'Hello John, how are you?',
          lastSyncAt: new Date(),
          syncVersion: 1,
        },
      ];

      const { getByText } = render(
        <MessageThread
          thread={mockThread}
          messages={mockMessages}
        />
      );

      expect(getByText('Project Discussion')).toBeTruthy();
      expect(getByText('2 messages • gmail')).toBeTruthy();
      expect(getByText('Hello John, how are you?')).toBeTruthy();
    });
  });

  describe('Component Integration Flow', () => {
    it('supports navigation flow from profile to messages to thread', () => {
      // This test demonstrates how the components work together
      // In a real app, this would be tested with navigation mocks

      const mockViewMessages = jest.fn();
      const mockThreadPress = jest.fn();

      // 1. Start with ContactProfile
      const { getByText: getProfileText } = render(
        <ContactProfile
          contact={mockContact}
          onViewMessagesPress={mockViewMessages}
        />
      );

      expect(getProfileText('View Messages (247)')).toBeTruthy();

      // 2. Navigate to ContactMessages (would be handled by navigation)
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
            shortSummary: 'Discussion about project',
            keyPoints: [],
            actionItems: [],
            decisions: [],
            nextSteps: [],
            generatedAt: new Date(),
          },
          keyTopics: [],
          relationshipDynamics: [],
          isMuted: false,
          isArchived: false,
          recentMessages: [],
        },
      ];

      const { getByText: getMessagesText } = render(
        <ContactMessages
          contact={mockContact}
          threads={mockThreads}
          onThreadPress={mockThreadPress}
        />
      );

      expect(getMessagesText('Project Discussion')).toBeTruthy();

      // 3. Navigate to MessageThread (would be handled by navigation)
      // This demonstrates the complete flow
    });
  });
});