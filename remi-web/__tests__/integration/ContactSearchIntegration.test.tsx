/**
 * Contact Search Integration Tests (Web Version)
 * 
 * Tests the complete contact search workflow from input to results
 */

import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContactSearchContainer } from '../../src/components/contacts/ContactSearchContainer';
import { contactSearchService } from '../../src/services/contactSearchService';

// Mock the services
jest.mock('../../src/services/contactSearchService');
jest.mock('../../src/hooks/useDebounce', () => ({
  useDebounce: (value: string) => value,
}));
jest.mock('../../src/utils/cn', () => ({
  cn: (...classes: string[]) => classes.filter(Boolean).join(' '),
}));

const mockContactSearchService = contactSearchService as jest.Mocked<typeof contactSearchService>;

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('Contact Search Integration (Web)', () => {
  const mockOnContactSelect = jest.fn();

  const mockSearchResults = {
    contacts: [
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
        communicationFrequency: 'high' as const,
        responsePattern: {
          averageResponseTime: 30,
          responseRate: 0.9,
          preferredTimes: ['09:00-12:00'],
          communicationStyle: 'professional' as const,
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
        communicationFrequency: 'medium' as const,
        responsePattern: {
          averageResponseTime: 120,
          responseRate: 0.7,
          preferredTimes: ['10:00-16:00'],
          communicationStyle: 'casual' as const,
        },
        topicAffinity: [],
        sharedFiles: [],
        sharedLinks: [],
        commonContacts: [],
        createdAt: new Date('2024-01-01'),
        updatedAt: new Date('2024-01-10'),
        lastSyncAt: new Date('2024-01-10'),
      },
    ],
    suggestions: [
      {
        type: 'name',
        text: 'John Smith',
        contact_id: '3',
      },
    ],
    query: 'John',
    normalized_query: 'john',
    total_results: 2,
    has_more: false,
  };

  const mockSuggestions = [
    {
      type: 'recent',
      text: 'Recent contact',
      contact_id: '4',
    },
    {
      type: 'frequent',
      text: 'Frequent contact',
      contact_id: '5',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockContactSearchService.searchContactsRealtime.mockResolvedValue(mockSearchResults);
    mockContactSearchService.getSearchSuggestions.mockResolvedValue(mockSuggestions);
  });

  it('should complete full search workflow', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          autoFocus={true}
        />
      </TestWrapper>
    );

    // 1. Start typing in search input
    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    // 2. Wait for search API call
    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });

    // 3. Verify search results are displayed
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    // 4. Select a contact
    const contactButton = screen.getByRole('button', { name: /John Doe/ });
    fireEvent.click(contactButton);

    // 5. Verify contact selection callback
    expect(mockOnContactSelect).toHaveBeenCalledWith(mockSearchResults.contacts[0]);
  });

  it('should show suggestions when not searching', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          showSuggestions={true}
        />
      </TestWrapper>
    );

    // Wait for suggestions to load
    await waitFor(() => {
      expect(screen.getByText('Search Suggestions')).toBeInTheDocument();
    });
  });

  it('should handle search errors gracefully', async () => {
    mockContactSearchService.searchContactsRealtime.mockRejectedValue(
      new Error('Network error')
    );

    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    await waitFor(() => {
      expect(screen.getByText('Search Error')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('should handle empty search results', async () => {
    mockContactSearchService.searchContactsRealtime.mockResolvedValue({
      contacts: [],
      suggestions: [],
      query: 'NonExistent',
      normalized_query: 'nonexistent',
      total_results: 0,
      has_more: false,
    });

    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'NonExistent' } });

    await waitFor(() => {
      expect(screen.getByText('No contacts found')).toBeInTheDocument();
      expect(screen.getByText('No contacts match "NonExistent"')).toBeInTheDocument();
    });
  });

  it('should display search result count', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    await waitFor(() => {
      expect(screen.getByText('2 contacts found for "John"')).toBeInTheDocument();
    });
  });

  it('should handle suggestion clicks', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          showSuggestions={true}
        />
      </TestWrapper>
    );

    // Wait for suggestions to load
    await waitFor(() => {
      expect(screen.getByText('Search Suggestions')).toBeInTheDocument();
    });

    // Click on a suggestion
    const suggestionButton = screen.getByText('Recent contact');
    fireEvent.click(suggestionButton);

    // This should update the search input
    const searchInput = screen.getByPlaceholderText('Search contacts...');
    expect(searchInput).toHaveValue('Recent contact');
  });

  it('should show loading state during search', async () => {
    // Mock a delayed response
    mockContactSearchService.searchContactsRealtime.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockSearchResults), 100))
    );

    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Searching contacts...')).toBeInTheDocument();
    });

    // Should show results after loading
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    }, { timeout: 200 });
  });

  it('should support keyboard navigation', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          autoFocus={true}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    
    // Test that input receives focus
    expect(searchInput).toHaveFocus();

    // Test keyboard input
    fireEvent.keyDown(searchInput, { key: 'J', code: 'KeyJ' });
    fireEvent.change(searchInput, { target: { value: 'J' } });
    
    fireEvent.keyDown(searchInput, { key: 'o', code: 'KeyO' });
    fireEvent.change(searchInput, { target: { value: 'Jo' } });
    
    fireEvent.keyDown(searchInput, { key: 'h', code: 'KeyH' });
    fireEvent.change(searchInput, { target: { value: 'Joh' } });
    
    fireEvent.keyDown(searchInput, { key: 'n', code: 'KeyN' });
    fireEvent.change(searchInput, { target: { value: 'John' } });

    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });
  });

  it('should clear search input', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    // Wait for search results
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Clear the input
    fireEvent.change(searchInput, { target: { value: '' } });

    // Should show suggestions again
    await waitFor(() => {
      expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
    });
  });

  it('should handle contact details display', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'John' } });

    await waitFor(() => {
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
      expect(screen.getByText('+1-555-0123')).toBeInTheDocument();
      expect(screen.getByText('GMAIL')).toBeInTheDocument();
      expect(screen.getByText('45 messages')).toBeInTheDocument();
      expect(screen.getByText('80%')).toBeInTheDocument(); // relationship strength
    });
  });

  it('should handle multiple platform indicators', async () => {
    render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search contacts...');
    fireEvent.change(searchInput, { target: { value: 'Jane' } });

    await waitFor(() => {
      expect(screen.getByText('GMAIL')).toBeInTheDocument();
      expect(screen.getByText('SLACK')).toBeInTheDocument();
    });
  });
});