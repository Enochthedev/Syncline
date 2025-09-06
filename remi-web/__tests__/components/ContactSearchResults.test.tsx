/**
 * ContactSearchResults Component Tests (Web Version)
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ContactSearchResults } from '../../src/components/contacts/ContactSearchResults';
import { UnifiedContact } from '../../src/types';

// Mock the cn utility
jest.mock('../../src/utils/cn', () => ({
  cn: (...classes: string[]) => classes.filter(Boolean).join(' '),
}));

describe('ContactSearchResults', () => {
  const mockOnContactSelect = jest.fn();

  const mockContacts: UnifiedContact[] = [
    {
      id: '1',
      primaryName: 'John Doe',
      displayName: 'John Doe',
      profilePhoto: undefined,
      identities: [],
      emails: ['john@example.com'],
      phoneNumbers: ['+1-555-0123'],
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
    render(
      <ContactSearchResults
        results={mockContacts}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('2 contacts found for "John"')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={true}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('Searching contacts...')).toBeInTheDocument();
  });

  it('renders empty state when no query provided', () => {
    render(
      <ContactSearchResults
        results={[]}
        query=""
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('Search Contacts')).toBeInTheDocument();
    expect(screen.getByText('Type at least 2 characters to search for contacts')).toBeInTheDocument();
  });

  it('renders no results message when no contacts found', () => {
    render(
      <ContactSearchResults
        results={[]}
        query="NonExistent"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('No contacts found')).toBeInTheDocument();
    expect(screen.getByText('No contacts match "NonExistent"')).toBeInTheDocument();
  });

  it('renders custom empty message when provided', () => {
    const customMessage = 'Try a different search term';
    render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        emptyMessage={customMessage}
      />
    );

    expect(screen.getByText(customMessage)).toBeInTheDocument();
  });

  it('renders error state when error provided', () => {
    const errorMessage = 'Network error occurred';
    render(
      <ContactSearchResults
        results={[]}
        query="test"
        isLoading={false}
        error={errorMessage}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('Search Error')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('calls onContactSelect when contact is clicked', () => {
    render(
      <ContactSearchResults
        results={mockContacts}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    const contactButton = screen.getByRole('button', { name: /John Doe/ });
    fireEvent.click(contactButton);

    expect(mockOnContactSelect).toHaveBeenCalledWith(mockContacts[0]);
  });

  it('displays contact information correctly', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        showDetails={true}
      />
    );

    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('+1-555-0123')).toBeInTheDocument();
    expect(screen.getByText('GMAIL')).toBeInTheDocument();
    expect(screen.getByText('45 messages')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument(); // relationship strength
  });

  it('shows platform indicators correctly', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[1]]}
        query="Jane"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('GMAIL')).toBeInTheDocument();
    expect(screen.getByText('SLACK')).toBeInTheDocument();
  });

  it('shows communication frequency indicator', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        showDetails={true}
      />
    );

    expect(screen.getByText('High frequency')).toBeInTheDocument();
  });

  it('shows recent activity indicator for recent contacts', () => {
    const recentContact = {
      ...mockContacts[0],
      lastInteraction: new Date(), // Today
    };

    render(
      <ContactSearchResults
        results={[recentContact]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    // Check for the green dot indicator (recent activity)
    const recentIndicator = document.querySelector('.bg-green-500');
    expect(recentIndicator).toBeInTheDocument();
  });

  it('does not show details when showDetails is false', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
        showDetails={false}
      />
    );

    expect(screen.queryByText('45 messages')).not.toBeInTheDocument();
    expect(screen.queryByText('80%')).not.toBeInTheDocument();
  });

  it('shows correct result count for single result', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    expect(screen.getByText('1 contact found for "John"')).toBeInTheDocument();
  });

  it('handles quick action buttons', () => {
    render(
      <ContactSearchResults
        results={[mockContacts[0]]}
        query="John"
        isLoading={false}
        onContactSelect={mockOnContactSelect}
      />
    );

    const messageButton = screen.getByTitle('Send message');
    const profileButton = screen.getByTitle('View profile');

    expect(messageButton).toBeInTheDocument();
    expect(profileButton).toBeInTheDocument();

    // Test that clicking quick actions doesn't trigger contact selection
    fireEvent.click(messageButton);
    expect(mockOnContactSelect).not.toHaveBeenCalled();
  });
});