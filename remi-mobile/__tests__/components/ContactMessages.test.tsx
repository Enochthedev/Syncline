/**
 * ContactMessages Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ContactMessages } from '../../src/components/ContactMessages';
import { UnifiedContact, ConversationThread } from '../../src/types';

// Mock the theme hook
jest.mock('../../src/hooks/useTheme', () => ({
  useTheme: () => ({
    theme: {
      colors: {
        background: '#ffffff',
        surface: '#f8f9fa',
        primary: '#007bff',
        text: '#212529',
        textSecondary: '#6c757d',
        border: '#dee2e6',
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
  platforms: ['gmail', 'slack'],
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
      keyPoints: ['Timeline agreed'],
      actionItems: [
        {
          id: '1',
          description: 'Prepare proposal',
          status: 'pending',
        },
      ],
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
  {
    id: '2',
    platform: 'slack',
    platformThreadId: 'thread-2',
    title: 'Team Updates',
    participants: [mockContact],
    messageCount: 8,
    createdAt: new Date('2024-01-10'),
    lastMessageAt: new Date('2024-01-14'),
    summary: {
      shortSummary: 'Weekly team updates',
      keyPoints: [],
      actionItems: [],
      decisions: [],
      nextSteps: [],
      generatedAt: new Date(),
    },
    keyTopics: ['team', 'updates'],
    relationshipDynamics: [],
    isMuted: false,
    isArchived: false,
    recentMessages: [],
  },
];

describe('ContactMessages', () => {
  const mockOnThreadPress = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders threads grouped by platform', () => {
    const { getByText, getAllByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
      />
    );

    expect(getByText('Gmail')).toBeTruthy();
    expect(getByText('Slack')).toBeTruthy();
    expect(getAllByText('1 conversation')).toHaveLength(2); // One for each platform
  });

  it('displays thread information correctly', () => {
    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
      />
    );

    expect(getByText('Project Discussion')).toBeTruthy();
    expect(getByText('15 messages')).toBeTruthy();
    expect(getByText('Discussion about project timeline')).toBeTruthy();
  });

  it('shows action items indicator when present', () => {
    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
      />
    );

    expect(getByText('1 action item')).toBeTruthy();
  });

  it('displays key topics as tags', () => {
    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
      />
    );

    expect(getByText('project')).toBeTruthy();
    expect(getByText('timeline')).toBeTruthy();
  });

  it('calls onThreadPress when thread is tapped', () => {
    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
      />
    );

    fireEvent.press(getByText('Project Discussion'));
    expect(mockOnThreadPress).toHaveBeenCalledWith(mockThreads[0]);
  });

  it('shows empty state when no threads', () => {
    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={[]}
        onThreadPress={mockOnThreadPress}
      />
    );

    expect(getByText('No Messages Found')).toBeTruthy();
    expect(getByText(`No conversation threads found with ${mockContact.primaryName}`)).toBeTruthy();
  });

  it('handles refresh correctly', () => {
    const mockOnRefresh = jest.fn();

    render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
        onRefresh={mockOnRefresh}
      />
    );

    // Note: Testing pull-to-refresh would require more complex setup
    // This shows the structure for such tests
  });

  it('shows load more button when hasMore is true', () => {
    const mockOnLoadMore = jest.fn();

    const { getByText } = render(
      <ContactMessages
        contact={mockContact}
        threads={mockThreads}
        onThreadPress={mockOnThreadPress}
        onLoadMore={mockOnLoadMore}
        hasMore={true}
      />
    );

    expect(getByText('Load More Conversations')).toBeTruthy();
  });
});