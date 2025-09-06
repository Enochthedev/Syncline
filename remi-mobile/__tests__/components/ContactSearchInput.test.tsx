/**
 * ContactSearchInput Component Tests
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContactSearchInput } from '../../src/components/ContactSearchInput';
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
        primary: '#007AFF',
        surface: '#FFFFFF',
        text: '#000000',
        textSecondary: '#666666',
        border: '#E5E5E5',
        error: '#FF3B30',
        success: '#34C759',
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

describe('ContactSearchInput', () => {
  const mockOnContactSelect = jest.fn();
  const mockOnSearchResults = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockContactSearchService.searchContactsRealtime.mockResolvedValue({
      contacts: [],
      suggestions: [],
      query: '',
      normalized_query: '',
      total_results: 0,
      has_more: false,
    });
  });

  it('renders correctly with default props', () => {
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    expect(getByPlaceholderText('Search contacts...')).toBeTruthy();
  });

  it('renders with custom placeholder', () => {
    const customPlaceholder = 'Find a contact';
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
          placeholder={customPlaceholder}
        />
      </TestWrapper>
    );

    expect(getByPlaceholderText(customPlaceholder)).toBeTruthy();
  });

  it('calls search service when typing', async () => {
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    await waitFor(() => {
      expect(mockContactSearchService.searchContactsRealtime).toHaveBeenCalledWith('John');
    });
  });

  it('shows clear button when text is entered', () => {
    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    expect(getByText('✕')).toBeTruthy();
  });

  it('clears input when clear button is pressed', () => {
    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');
    
    const clearButton = getByText('✕');
    fireEvent.press(clearButton);

    expect(mockOnSearchResults).toHaveBeenCalledWith([]);
  });

  it('displays search results when available', async () => {
    const mockResults = {
      contacts: [
        {
          id: '1',
          primary_name: 'John Doe',
          display_name: 'John Doe',
          primary_email: 'john@example.com',
          platforms: ['gmail'],
          interaction_indicators: {
            has_recent_messages: true,
          },
        },
      ],
      suggestions: [],
      query: 'John',
      normalized_query: 'john',
      total_results: 1,
      has_more: false,
    };

    mockContactSearchService.searchContactsRealtime.mockResolvedValue(mockResults);

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    await waitFor(() => {
      expect(getByText('John Doe')).toBeTruthy();
      expect(getByText('john@example.com')).toBeTruthy();
    });
  });

  it('calls onContactSelect when contact is selected', async () => {
    const mockContact = {
      id: '1',
      primary_name: 'John Doe',
      display_name: 'John Doe',
      primary_email: 'john@example.com',
      platforms: ['gmail'],
      interaction_indicators: {
        has_recent_messages: true,
      },
    };

    const mockResults = {
      contacts: [mockContact],
      suggestions: [],
      query: 'John',
      normalized_query: 'john',
      total_results: 1,
      has_more: false,
    };

    mockContactSearchService.searchContactsRealtime.mockResolvedValue(mockResults);

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    await waitFor(() => {
      const contactButton = getByText('John Doe');
      fireEvent.press(contactButton);
      expect(mockOnContactSelect).toHaveBeenCalledWith(mockContact);
    });
  });

  it('displays error message when search fails', async () => {
    mockContactSearchService.searchContactsRealtime.mockRejectedValue(
      new Error('Search failed')
    );

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    await waitFor(() => {
      expect(getByText('Search failed. Please try again.')).toBeTruthy();
    });
  });

  it('displays no results message when no contacts found', async () => {
    const mockResults = {
      contacts: [],
      suggestions: [],
      query: 'NonExistent',
      normalized_query: 'nonexistent',
      total_results: 0,
      has_more: false,
    };

    mockContactSearchService.searchContactsRealtime.mockResolvedValue(mockResults);

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'NonExistent');

    await waitFor(() => {
      expect(getByText('No contacts found for "NonExistent"')).toBeTruthy();
    });
  });

  it('displays suggestions when available', async () => {
    const mockResults = {
      contacts: [],
      suggestions: [
        {
          type: 'name',
          text: 'John Smith',
          contact_id: '1',
        },
      ],
      query: 'John',
      normalized_query: 'john',
      total_results: 0,
      has_more: false,
    };

    mockContactSearchService.searchContactsRealtime.mockResolvedValue(mockResults);

    const { getByPlaceholderText, getByText } = render(
      <TestWrapper>
        <ContactSearchInput
          onContactSelect={mockOnContactSelect}
          onSearchResults={mockOnSearchResults}
          showSuggestions={true}
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    await waitFor(() => {
      expect(getByText('Suggestions')).toBeTruthy();
    });
  });
});