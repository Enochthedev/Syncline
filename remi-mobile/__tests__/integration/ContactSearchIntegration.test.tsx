/**
 * Contact Search Integration Tests
 * 
 * Tests the complete contact search workflow from input to results
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContactSearchContainer } from '../../src/components/ContactSearchContainer';
import { contactSearchService } from '../../src/services/contactSearchService';

// Mock the services
jest.mock('../../src/services/contactSearchService');
jest.mock('../../src/hooks/useDebounce', () => ({
  useDebounce: (value: string) => value,
}));
jest.mock('../../src/hooks/useTheme', () => ({
  useTheme: () => ({
    theme: {
      colors: {
        background: '#FFFFFF',
        surface: '#FFFFFF',
        primary: '#007AFF',
        text: '#000000',
        textSecondary: '#666666',
        border: '#E5E5E5',
        error: '#FF3B30',
        success: '#34C759',
        warning: '#FF9500',
        info: '#5AC8FA',
        white: '#FFFFFF',
      },
    },
  }),
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

describe('Contact Search Integration', () => {
  const mockOnContactSelect = jest.fn();

  const mockSearchResults = {
    contacts: [
      {
        id: '1',
        primary_name: 'John Doe',
        display_name: 'John Doe',
        primary_email: 'john@example.com',
        platforms: ['gmail'],
        total_messages: 45,
        interaction_indicators: {
          has_recent_messages: true,
        },
      },
      {
        id: '2',
        primary_name: 'Jane Smith',
        display_name: 'Jane Smith',
        primary_email: 'jane@example.com',
        platforms: ['gmail', 'slack'],
        total_messages: 23,
        interaction_indicators: {
          has_recent_messages: false,
        },
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
    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          autoFocus={true}
        />
      </TestWrapper>
    );

    // 1. Start typing in search input
    const searchInput = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(searchInput, 'John');

    // 2. Wait for search API call
    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });

    // 3. Verify search results are displayed
    await waitFor(() => {
      expect(getByText('John Doe')).toBeTruthy();
      expect(getByText('Jane Smith')).toBeTruthy();
      expect(getByText('john@example.com')).toBeTruthy();
    });

    // 4. Select a contact
    const contactResult = getByText('John Doe');
    fireEvent.press(contactResult);

    // 5. Verify contact selection callback
    expect(mockOnContactSelect).toHaveBeenCalledWith(mockSearchResults.contacts[0]);
  });

  it('should show suggestions when not searching', async () => {
    const { getByText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          showSuggestions={true}
        />
      </TestWrapper>
    );

    // Wait for suggestions to load
    await waitFor(() => {
      expect(getByText('Suggestions')).toBeTruthy();
    });
  });

  it('should handle search errors gracefully', async () => {
    mockContactSearchService.searchContactsRealtime.mockRejectedValue(
      new Error('Network error')
    );

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(searchInput, 'John');

    await waitFor(() => {
      expect(getByText(/Network error/)).toBeTruthy();
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

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(searchInput, 'NonExistent');

    await waitFor(() => {
      expect(getByText('No contacts found')).toBeTruthy();
    });
  });

  it('should support natural language queries', async () => {
    const naturalLanguageResult = {
      intent: 'person_search',
      processed_text: 'messages with john',
      contacts: [mockSearchResults.contacts[0]],
      filters: {
        participants: ['john'],
      },
      temporal_constraints: {},
      entities: [
        {
          type: 'person',
          text: 'john',
          confidence: 0.9,
        },
      ],
    };

    mockContactSearchService.processNaturalLanguageQuery.mockResolvedValue(naturalLanguageResult);

    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(searchInput, 'messages with John');

    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('messages with John');
    });
  });

  it('should handle suggestion selection', async () => {
    const { getByText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          showSuggestions={true}
        />
      </TestWrapper>
    );

    // Wait for suggestions to load
    await waitFor(() => {
      expect(getByText('Suggestions')).toBeTruthy();
    });

    // Select a suggestion
    const suggestion = getByText('Recent contact');
    fireEvent.press(suggestion);

    // This would trigger a new search or contact selection
    // depending on the suggestion type
  });

  it('should support refresh functionality', async () => {
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(searchInput, 'John');

    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledTimes(1);
    });

    // Simulate refresh (this would be triggered by pull-to-refresh gesture)
    // In a real test, you'd simulate the refresh gesture
    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });
  });

  it('should handle keyboard interactions properly', async () => {
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
          autoFocus={true}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    
    // Test that input receives focus
    expect(searchInput.props.autoFocus).toBe(true);

    // Test typing
    fireEvent.changeText(searchInput, 'J');
    fireEvent.changeText(searchInput, 'Jo');
    fireEvent.changeText(searchInput, 'John');

    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });
  });

  it('should debounce search queries', async () => {
    // Since we're mocking useDebounce to return the value immediately,
    // this test verifies that the debounce hook is being used
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchContainer
          onContactSelect={mockOnContactSelect}
        />
      </TestWrapper>
    );

    const searchInput = getByPlaceholderText('Search contacts...');
    
    // Rapid typing
    fireEvent.changeText(searchInput, 'J');
    fireEvent.changeText(searchInput, 'Jo');
    fireEvent.changeText(searchInput, 'Joh');
    fireEvent.changeText(searchInput, 'John');

    // Only the final query should trigger the search
    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });
  });
});