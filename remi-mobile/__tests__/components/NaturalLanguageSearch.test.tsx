/**
 * Natural Language Search Component Tests
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NaturalLanguageSearch } from '@/components/NaturalLanguageSearch';
import { contactSearchService } from '@/services/contactSearchService';

// Mock the contact search service
jest.mock('@/services/contactSearchService', () => ({
  contactSearchService: {
    processNaturalLanguageQuery: jest.fn(),
    getSearchSuggestions: jest.fn(),
    searchMessagesByContact: jest.fn(),
    getSharedContentWithContact: jest.fn(),
  },
}));

// Mock the theme hook
jest.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({
    colors: {
      background: '#FFFFFF',
      surface: '#F5F5F5',
      primary: '#007AFF',
      primaryLight: '#E3F2FD',
      text: '#000000',
      textSecondary: '#666666',
      border: '#E0E0E0',
      onPrimary: '#FFFFFF',
    },
  }),
}));

// Mock the debounce hook
jest.mock('@/hooks/useDebounce', () => ({
  useDebounce: (value: any) => value,
}));

describe('NaturalLanguageSearch', () => {
  const mockOnResultsChange = jest.fn();
  const mockOnQueryChange = jest.fn();
  const mockOnIntentDetected = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with default props', () => {
    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    expect(getByPlaceholderText("Try 'messages with John' or 'files from Sarah'")).toBeTruthy();
  });

  it('renders with custom placeholder', () => {
    const customPlaceholder = 'Search for anything...';
    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
        placeholder={customPlaceholder}
      />
    );

    expect(getByPlaceholderText(customPlaceholder)).toBeTruthy();
  });

  it('calls onQueryChange when text input changes', () => {
    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');

    expect(mockOnQueryChange).toHaveBeenCalledWith('messages with John');
  });

  it('processes natural language query when text is entered', async () => {
    const mockQueryResult = {
      intent: 'person_messages',
      processed_text: 'messages with John',
      contacts: [{ id: '1', displayName: 'John Smith' }],
      filters: {},
      temporal_constraints: {},
      entities: [{ text: 'John', type: 'PERSON' }],
    };

    (contactSearchService.processNaturalLanguageQuery as jest.Mock).mockResolvedValue(mockQueryResult);
    (contactSearchService.searchMessagesByContact as jest.Mock).mockResolvedValue({
      messages: [
        {
          id: '1',
          content: { text: 'Hello from John' },
          sender: { displayName: 'John Smith' },
          timestamp: new Date().toISOString(),
          platform: 'email',
        },
      ],
    });

    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');

    await waitFor(() => {
      expect(contactSearchService.processNaturalLanguageQuery).toHaveBeenCalledWith('messages with John');
      expect(mockOnIntentDetected).toHaveBeenCalledWith('person_messages', [{ text: 'John', type: 'PERSON' }]);
    });
  });

  it('displays detected intent and entities', async () => {
    const mockQueryResult = {
      intent: 'person_messages',
      processed_text: 'messages with John',
      contacts: [{ id: '1', displayName: 'John Smith' }],
      filters: {},
      temporal_constraints: {},
      entities: [{ text: 'John', type: 'PERSON' }],
    };

    (contactSearchService.processNaturalLanguageQuery as jest.Mock).mockResolvedValue(mockQueryResult);
    (contactSearchService.searchMessagesByContact as jest.Mock).mockResolvedValue({ messages: [] });

    const { getByPlaceholderText, getByText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');

    await waitFor(() => {
      expect(getByText('Detected Intent: Messages with Contact')).toBeTruthy();
      expect(getByText('John (PERSON)')).toBeTruthy();
    });
  });

  it('shows loading indicator while processing', async () => {
    (contactSearchService.processNaturalLanguageQuery as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    const { getByPlaceholderText, getByTestId } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');

    // Check if loading indicator is shown
    await waitFor(() => {
      expect(getByTestId('loading-indicator')).toBeTruthy();
    });
  });

  it('gets search suggestions when enabled', async () => {
    const mockSuggestions = ['messages with John', 'files from John'];
    (contactSearchService.getSearchSuggestions as jest.Mock).mockResolvedValue(mockSuggestions);

    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
        showSuggestions={true}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages');

    await waitFor(() => {
      expect(contactSearchService.getSearchSuggestions).toHaveBeenCalledWith('messages', 5);
    });
  });

  it('handles different intent types correctly', async () => {
    const fileSearchResult = {
      intent: 'file_search',
      processed_text: 'files from Sarah',
      contacts: [{ id: '2', displayName: 'Sarah Johnson' }],
      filters: {},
      temporal_constraints: {},
      entities: [{ text: 'Sarah', type: 'PERSON' }],
    };

    (contactSearchService.processNaturalLanguageQuery as jest.Mock).mockResolvedValue(fileSearchResult);
    (contactSearchService.getSharedContentWithContact as jest.Mock).mockResolvedValue({
      shared_files: [
        {
          id: '1',
          name: 'document.pdf',
          type: 'pdf',
          size: 1024,
          sharedAt: new Date().toISOString(),
          platform: 'email',
        },
      ],
    });

    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'files from Sarah');

    await waitFor(() => {
      expect(contactSearchService.getSharedContentWithContact).toHaveBeenCalledWith('2', 'files', 50);
      expect(mockOnIntentDetected).toHaveBeenCalledWith('file_search', [{ text: 'Sarah', type: 'PERSON' }]);
    });
  });

  it('clears query when clear button is pressed', () => {
    const { getByPlaceholderText, getByTestId } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'test query');

    const clearButton = getByTestId('clear-button');
    fireEvent.press(clearButton);

    expect(mockOnQueryChange).toHaveBeenCalledWith('');
  });

  it('handles API errors gracefully', async () => {
    (contactSearchService.processNaturalLanguageQuery as jest.Mock).mockRejectedValue(
      new Error('API Error')
    );

    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');

    await waitFor(() => {
      expect(contactSearchService.processNaturalLanguageQuery).toHaveBeenCalled();
      // Component should handle error gracefully without crashing
    });
  });

  it('submits query on return key press', () => {
    const { getByPlaceholderText } = render(
      <NaturalLanguageSearch
        onResultsChange={mockOnResultsChange}
        onQueryChange={mockOnQueryChange}
        onIntentDetected={mockOnIntentDetected}
      />
    );

    const input = getByPlaceholderText("Try 'messages with John' or 'files from Sarah'");
    fireEvent.changeText(input, 'messages with John');
    fireEvent(input, 'submitEditing');

    // Should trigger query processing
    expect(contactSearchService.processNaturalLanguageQuery).toHaveBeenCalledWith('messages with John');
  });
});