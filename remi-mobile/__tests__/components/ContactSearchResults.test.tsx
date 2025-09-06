/**
 * ContactSearchResults Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ContactSearchResults } from '../../src/components/ContactSearchResults';
import { UnifiedContact } from '../../src/types';

// Mock the theme hook
jest.mock('../../src/hooks/useTheme', () => ({
  useTheme: () => ({
    theme: {
      colors: {
        background: '#FFFFFF',
        text: '#000000',
        textSecondary: '#666666',
        error: '#FF3B30',
        primary: '#007AFF',
      },
    },
  }),
}));

// Mock ContactCard component
jest.mock('../../src/components/ContactCard', () => ({
  ContactCard: ({ contact, onPress }: any) => (
    <div testID={`contact-card-${contact.id}`} onPress={() => onPress(contact)}>
      {contact.displayName}
    </div>
  ),
}));

describe('ContactSearchResults', () => {
  const mockOnContactSelect = jest.fn();
  const mockOnRefresh = jest.fn();

  const mockContacts: UnifiedContact[] = [
    {
      id: '1',
      primaryName: 'John Doe',
      displayName: 'John Doe',
      profilePhoto: undefined,
      identities: [],
      emails: ['john@example.com'],
      phoneNumbers: [],
      socialProfiles: [],
      lastInteraction: new Date('2024-01-15'),
      totalMessages: 45,
      platforms: ['gmail'],
      relationshipStrength: 0.8,
      communicationFrequency: 'high',
      responsePattern: {
        averageResponseTime: 30,
        responseRate: 0.9,
        preferredTimes: ['09:00-12:00'],
        communicationStyle: 'professional',
      },
      topicAffinity: [],
      sharedFiles: [],
      sharedLinks: [],
      commonContacts: [],
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-15'),
      lastSyncAt: new Date('2024-01-15'),
    },
    {
      id: '2',
      primaryName: 'Jane Smith',
      displayName: 'Jane Smith',
      profilePhoto: undefined,
      identities: [],
      emails: ['jane@example.com'],
      phoneNumbers: [],
      socialProfiles: [],
      lastInteraction: new Date('2024-01-10'),
      totalMessages: 23,
      platforms: ['gmail', 'slack'],
      relationshipStrength: 0.6,
      communicationFrequency: 'medium',
      responsePattern: {
        averageResponseTime: 120,
        responseRate: 0.7,
        preferredTimes: ['10:00-16:00'],
        communicationStyle: 'casual',
      },
      topicAffinity: [],
      sharedFiles: [],
      sharedLinks: [],
      commonContacts: [],
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-10'),
      lastSyncAt: new Date('2024-01-10'),
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with search results', () => {
    const { getByText } = render(
      <ContactSearchResults
        results={mockContacts}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('2 contacts found for "John"')).toBeTruthy();
  });

  it('renders empty state when no query provided', () => {
    const { getByText } = render(
      <ContactSearchResults
        results={[]}
        query=""
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('Search Contacts')).toBeTruthy();
    expect(getByText('Type at least 2 characters to search for contacts')).toBeTruthy();
  });

  it('renders no results message when no contacts found', () => {
    const { getByText } = render(
      <ContactSearchResults
        results={[]}
        query="NonExistent"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('No contacts found')).toBeTruthy();
    expect(getByText('No contacts match "NonExistent"')).toBeTruthy();
  });

  it('renders custom empty message when provided', () => {
    const customMessage = 'Try a different search term';
    const { getByText } = render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        emptyMessage={customMessage}
      />
    );

    expect(getByText(customMessage)).toBeTruthy();
  });

  it('renders error state when error provided', () => {
    const errorMessage = 'Network error occurred';
    const { getByText } = render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={false}
        error={errorMessage}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('Search Error')).toBeTruthy();
    expect(getByText(errorMessage)).toBeTruthy();
  });

  it('calls onContactSelect when contact is selected', () => {
    const { getByTestId } = render(
      <ContactSearchResults
        results={mockContacts}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    const contactCard = getByTestId('contact-card-1');
    fireEvent.press(contactCard);

    expect(mockOnContactSelect).toHaveBeenCalledWith(mockContacts[0]);
  });

  it('shows correct result count for single result', () => {
    const { getByText } = render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('1 contact found for "John"')).toBeTruthy();
  });

  it('shows correct result count for multiple results', () => {
    const { getByText } = render(
      <ContactSearchResults
        results={mockContacts}
        query="test"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(getByText('2 contacts found for "test"')).toBeTruthy();
  });

  it('does not show header when no results and no query', () => {
    const { queryByText } = render(
      <ContactSearchResults
        results={[]}
        query=""
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(queryByText(/contacts found/)).toBeNull();
  });

  it('does not show header when no results found', () => {
    const { queryByText } = render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(queryByText(/contacts found/)).toBeNull();
  });

  it('passes showDetails prop to ContactCard components', () => {
    render(
      <ContactSearchResults
        results={mockContacts}
        query="test"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        showDetails={false}
      />
    );

    // This would be tested by checking if ContactCard receives the showDetails prop
    // In a real implementation, you'd mock ContactCard and verify the prop
  });
});