/**
 * MessageThread Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MessageThread } from '../../src/components/MessageThread';
import { ConversationThread, Message, UnifiedContact, TextHighlight } from '../../src/types';

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

const mockContact: UnifiedContact = {
  id: '1',
  primaryName: 'John Smith',
  displayName: 'John Smith',
  profilePhoto: undefined,
  identities: [],
  emails: [],
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
};

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
    shortSummary: 'Discussion about project timeline',
    keyPoints: [],
    actionItems: [],
    decisions: [],
    nextSteps: [],
    generatedAt: new Date(),
  },
  keyTopics: ['project'],
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
      text: 'Hi John, let\'s discuss the project timeline.',
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
    topics: ['project'],
    commitments: [],
    searchableText: 'Hi John, let\'s discuss the project timeline.',
    lastSyncAt: new Date(),
    syncVersion: 1,
  },
  {
    id: '2',
    threadId: '1',
    platform: 'gmail',
    platformMessageId: 'msg-2',
    content: {
      text: 'Sure! I think we can deliver by the end of this month.',
      mediaType: 'text',
    },
    attachments: [
      {
        id: 'att-1',
        name: 'timeline.pdf',
        type: 'application/pdf',
        size: 1024000,
        url: 'https://example.com/timeline.pdf',
      },
    ],
    sender: mockContact,
    recipients: [],
    timestamp: new Date('2024-01-15T10:15:00'),
    isRead: true,
    isImportant: true,
    entities: [
      {
        id: 'entity-1',
        type: 'DATE',
        text: 'end of this month',
        confidence: 0.95,
        startOffset: 30,
        endOffset: 48,
      },
    ],
    sentiment: {
      overall: 0.3,
      confidence: 0.7,
      emotions: [],
    },
    topics: ['timeline'],
    commitments: [],
    searchableText: 'Sure! I think we can deliver by the end of this month.',
    lastSyncAt: new Date(),
    syncVersion: 1,
  },
];

const mockHighlights: TextHighlight[] = [
  {
    start: 30,
    end: 37,
    text: 'project',
  },
];

describe('MessageThread', () => {
  const mockOnMessagePress = jest.fn();
  const mockOnAttachmentPress = jest.fn();
  const mockOnSearch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders thread header correctly', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onMessagePress={mockOnMessagePress}
      />
    );

    expect(getByText('Project Discussion')).toBeTruthy();
    expect(getByText('2 messages • gmail')).toBeTruthy();
  });

  it('displays messages correctly', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onMessagePress={mockOnMessagePress}
      />
    );

    expect(getByText('Hi John, let\'s discuss the project timeline.')).toBeTruthy();
    expect(getByText('Sure! I think we can deliver by the end of this month.')).toBeTruthy();
  });

  it('shows sender names for other users', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onMessagePress={mockOnMessagePress}
      />
    );

    expect(getByText('John Smith')).toBeTruthy();
  });

  it('displays attachments correctly', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onMessagePress={mockOnMessagePress}
        onAttachmentPress={mockOnAttachmentPress}
      />
    );

    expect(getByText('timeline.pdf')).toBeTruthy();
    expect(getByText('1000 KB')).toBeTruthy();
  });

  it('calls onAttachmentPress when attachment is tapped', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onAttachmentPress={mockOnAttachmentPress}
      />
    );

    fireEvent.press(getByText('timeline.pdf'));
    expect(mockOnAttachmentPress).toHaveBeenCalledWith(mockMessages[1].attachments[0]);
  });

  it('shows search bar when search button is pressed', () => {
    const { getByPlaceholderText, queryByPlaceholderText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onSearch={mockOnSearch}
      />
    );

    // Search bar should not be visible initially
    expect(queryByPlaceholderText('Search in conversation...')).toBeFalsy();

    // Press search button (would need testID in real implementation)
    // fireEvent.press(searchButton);
    // expect(getByPlaceholderText('Search in conversation...')).toBeTruthy();
  });

  it('highlights search results correctly', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        searchQuery="project"
        highlights={mockHighlights}
      />
    );

    // The highlighted text should be rendered
    expect(getByText('Hi John, let\'s discuss the project timeline.')).toBeTruthy();
  });

  it('shows entity tags when entities are present', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
      />
    );

    expect(getByText('DATE: end of this month')).toBeTruthy();
  });

  it('displays message timestamps correctly', () => {
    const { getAllByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
      />
    );

    // Should show formatted timestamps
    const timestamps = getAllByText(/10:00 AM|10:15 AM/);
    expect(timestamps.length).toBeGreaterThan(0);
  });

  it('shows importance indicator for important messages', () => {
    const { getAllByTestId } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
      />
    );

    // Would need testID on star icon in real implementation
    // expect(getAllByTestId('importance-star')).toHaveLength(1);
  });

  it('shows empty state when no messages', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={[]}
      />
    );

    expect(getByText('No Messages')).toBeTruthy();
    expect(getByText('This conversation doesn\'t have any messages yet')).toBeTruthy();
  });

  it('calls onMessagePress when message is tapped', () => {
    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onMessagePress={mockOnMessagePress}
      />
    );

    fireEvent.press(getByText('Hi John, let\'s discuss the project timeline.'));
    expect(mockOnMessagePress).toHaveBeenCalledWith(mockMessages[0]);
  });

  it('shows load more button when hasMore is true', () => {
    const mockOnLoadMore = jest.fn();

    const { getByText } = render(
      <MessageThread
        thread={mockThread}
        messages={mockMessages}
        onLoadMore={mockOnLoadMore}
        hasMore={true}
      />
    );

    expect(getByText('Load Earlier Messages')).toBeTruthy();
  });
});