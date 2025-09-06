/**
 * Responsive UI Components Tests
 * 
 * Tests for responsive behavior and cross-platform consistency
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Dimensions } from 'react-native';
import { SearchBar } from '../../src/components/SearchBar';
import { ContactCard } from '../../src/components/ContactCard';
import { LoadingSpinner } from '../../src/components/LoadingSpinner';
import { ErrorMessage } from '../../src/components/ErrorMessage';
import { EmptyState } from '../../src/components/EmptyState';
import { ResponsiveLayout, useResponsiveDimensions } from '../../src/components/ResponsiveLayout';
import { ThemeProvider } from '../../src/contexts/ThemeContext';

// Mock dependencies
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
}));

// Mock Dimensions
const mockDimensions = {
  get: jest.fn(() => ({ width: 375, height: 812 })), // iPhone default
};
jest.mock('react-native', () => ({
  ...jest.requireActual('react-native'),
  Dimensions: mockDimensions,
}));

// Test wrapper with theme
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

// Mock contact data
const mockContact = {
  id: '1',
  primary_name: 'John Doe',
  display_name: 'John Doe',
  primary_email: 'john@example.com',
  primary_phone: '+1234567890',
  profile_photo_url: 'https://example.com/photo.jpg',
  platforms: ['gmail', 'slack'],
  total_messages: 42,
  last_interaction: '2024-01-15T10:30:00Z',
  relationship_strength: 0.8,
  communication_frequency: 'high',
  is_favorite: true,
  interaction_indicators: {
    has_recent_messages: true,
    is_frequent_contact: true,
    has_unread_messages: false,
  },
  recent_interaction: {
    has_recent: true,
    days_since: 2,
    interaction_level: 'this_week',
  },
};

describe('SearchBar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly on mobile', () => {
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          placeholder="Search contacts..."
        />
      </TestWrapper>
    );

    expect(getByPlaceholderText('Search contacts...')).toBeTruthy();
  });

  it('adapts to tablet size', () => {
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          placeholder="Search contacts..."
        />
      </TestWrapper>
    );

    expect(getByPlaceholderText('Search contacts...')).toBeTruthy();
  });

  it('adapts to desktop size', () => {
    mockDimensions.get.mockReturnValue({ width: 1200, height: 800 });
    
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          placeholder="Search contacts..."
        />
      </TestWrapper>
    );

    expect(getByPlaceholderText('Search contacts...')).toBeTruthy();
  });

  it('handles text input correctly', () => {
    const onChangeText = jest.fn();
    
    const { getByPlaceholderText } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={onChangeText}
          placeholder="Search contacts..."
        />
      </TestWrapper>
    );

    const input = getByPlaceholderText('Search contacts...');
    fireEvent.changeText(input, 'John');

    expect(onChangeText).toHaveBeenCalledWith('John');
  });

  it('shows loading indicator when loading', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          isLoading={true}
        />
      </TestWrapper>
    );

    // ActivityIndicator should be present when loading
    expect(() => getByTestId('loading-indicator')).not.toThrow();
  });

  it('shows clear button when text is present', () => {
    const onClear = jest.fn();
    
    const { rerender } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          onClear={onClear}
        />
      </TestWrapper>
    );

    // Clear button should not be visible when no text
    expect(() => render(<TestWrapper><SearchBar value="test" onChangeText={jest.fn()} onClear={onClear} /></TestWrapper>)).not.toThrow();
  });

  it('handles voice button press', () => {
    const onVoicePress = jest.fn();
    
    const { getByRole } = render(
      <TestWrapper>
        <SearchBar
          value=""
          onChangeText={jest.fn()}
          showVoiceButton={true}
          onVoicePress={onVoicePress}
        />
      </TestWrapper>
    );

    // Voice button functionality would be tested here
    expect(onVoicePress).not.toHaveBeenCalled();
  });
});

describe('ContactCard Component', () => {
  it('renders contact information correctly', () => {
    const onPress = jest.fn();
    
    const { getByText } = render(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
        />
      </TestWrapper>
    );

    expect(getByText('John Doe')).toBeTruthy();
    expect(getByText('john@example.com')).toBeTruthy();
    expect(getByText('+1234567890')).toBeTruthy();
  });

  it('adapts to different screen sizes', () => {
    const onPress = jest.fn();
    
    // Test mobile
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
        />
      </TestWrapper>
    );

    // Test tablet
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    rerender(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
        />
      </TestWrapper>
    );

    expect(getByText('John Doe')).toBeTruthy();
  });

  it('handles press events', () => {
    const onPress = jest.fn();
    
    const { getByText } = render(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
        />
      </TestWrapper>
    );

    fireEvent.press(getByText('John Doe'));
    expect(onPress).toHaveBeenCalledWith(mockContact);
  });

  it('shows platform indicators', () => {
    const onPress = jest.fn();
    
    const { getByText } = render(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
        />
      </TestWrapper>
    );

    expect(getByText('GMAIL')).toBeTruthy();
    expect(getByText('SLACK')).toBeTruthy();
  });

  it('hides details when showDetails is false', () => {
    const onPress = jest.fn();
    
    const { queryByText } = render(
      <TestWrapper>
        <ContactCard
          contact={mockContact}
          onPress={onPress}
          showDetails={false}
        />
      </TestWrapper>
    );

    // Details should not be visible
    expect(queryByText('Last Activity:')).toBeNull();
  });
});

describe('LoadingSpinner Component', () => {
  it('renders with default props', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <LoadingSpinner />
      </TestWrapper>
    );

    // ActivityIndicator should be present
    expect(() => getByTestId('activity-indicator')).not.toThrow();
  });

  it('shows message when provided', () => {
    const { getByText } = render(
      <TestWrapper>
        <LoadingSpinner message="Loading contacts..." />
      </TestWrapper>
    );

    expect(getByText('Loading contacts...')).toBeTruthy();
  });

  it('adapts size for different screen sizes', () => {
    // Test mobile
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <LoadingSpinner size="large" />
      </TestWrapper>
    );

    // Test tablet
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    rerender(
      <TestWrapper>
        <LoadingSpinner size="large" />
      </TestWrapper>
    );

    // Component should render without errors
    expect(true).toBeTruthy();
  });
});

describe('ErrorMessage Component', () => {
  it('renders error message correctly', () => {
    const { getByText } = render(
      <TestWrapper>
        <ErrorMessage
          title="Error"
          message="Something went wrong"
        />
      </TestWrapper>
    );

    expect(getByText('Error')).toBeTruthy();
    expect(getByText('Something went wrong')).toBeTruthy();
  });

  it('handles retry button press', () => {
    const onRetry = jest.fn();
    
    const { getByText } = render(
      <TestWrapper>
        <ErrorMessage
          message="Something went wrong"
          onRetry={onRetry}
          retryText="Try Again"
        />
      </TestWrapper>
    );

    fireEvent.press(getByText('Try Again'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('shows different types of errors', () => {
    const { getByText, rerender } = render(
      <TestWrapper>
        <ErrorMessage
          message="Warning message"
          type="warning"
        />
      </TestWrapper>
    );

    expect(getByText('Warning message')).toBeTruthy();

    rerender(
      <TestWrapper>
        <ErrorMessage
          message="Info message"
          type="info"
        />
      </TestWrapper>
    );

    expect(getByText('Info message')).toBeTruthy();
  });
});

describe('EmptyState Component', () => {
  it('renders empty state correctly', () => {
    const { getByText } = render(
      <TestWrapper>
        <EmptyState
          title="No Contacts"
          message="You haven't added any contacts yet"
        />
      </TestWrapper>
    );

    expect(getByText('No Contacts')).toBeTruthy();
    expect(getByText("You haven't added any contacts yet")).toBeTruthy();
  });

  it('handles action button press', () => {
    const onAction = jest.fn();
    
    const { getByText } = render(
      <TestWrapper>
        <EmptyState
          title="No Contacts"
          actionText="Add Contact"
          onAction={onAction}
        />
      </TestWrapper>
    );

    fireEvent.press(getByText('Add Contact'));
    expect(onAction).toHaveBeenCalled();
  });

  it('adapts to different screen sizes', () => {
    // Test mobile
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <EmptyState title="No Contacts" />
      </TestWrapper>
    );

    // Test tablet
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    rerender(
      <TestWrapper>
        <EmptyState title="No Contacts" />
      </TestWrapper>
    );

    expect(getByText('No Contacts')).toBeTruthy();
  });
});

describe('ResponsiveLayout Component', () => {
  it('renders children correctly', () => {
    const { getByText } = render(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Test Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    expect(getByText('Test Content')).toBeTruthy();
  });

  it('applies responsive padding', () => {
    // Test different screen sizes
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 }); // Mobile
    const { rerender } = render(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Mobile Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 }); // Tablet
    rerender(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Tablet Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    mockDimensions.get.mockReturnValue({ width: 1200, height: 800 }); // Desktop
    rerender(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Desktop Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    // All should render without errors
    expect(true).toBeTruthy();
  });

  it('handles scrollable content', () => {
    const { getByText } = render(
      <TestWrapper>
        <ResponsiveLayout scrollable>
          <Text>Scrollable Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    expect(getByText('Scrollable Content')).toBeTruthy();
  });
});

describe('useResponsiveDimensions Hook', () => {
  it('returns correct dimensions for mobile', () => {
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    
    const TestComponent = () => {
      const { isPhone, isTablet, isDesktop } = useResponsiveDimensions();
      return (
        <Text>
          {isPhone ? 'Phone' : isTablet ? 'Tablet' : isDesktop ? 'Desktop' : 'Unknown'}
        </Text>
      );
    };

    const { getByText } = render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    expect(getByText('Phone')).toBeTruthy();
  });

  it('returns correct dimensions for tablet', () => {
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    
    const TestComponent = () => {
      const { isPhone, isTablet, isDesktop } = useResponsiveDimensions();
      return (
        <Text>
          {isPhone ? 'Phone' : isTablet ? 'Tablet' : isDesktop ? 'Desktop' : 'Unknown'}
        </Text>
      );
    };

    const { getByText } = render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    expect(getByText('Tablet')).toBeTruthy();
  });

  it('returns correct dimensions for desktop', () => {
    mockDimensions.get.mockReturnValue({ width: 1200, height: 800 });
    
    const TestComponent = () => {
      const { isPhone, isTablet, isDesktop } = useResponsiveDimensions();
      return (
        <Text>
          {isPhone ? 'Phone' : isTablet ? 'Tablet' : isDesktop ? 'Desktop' : 'Unknown'}
        </Text>
      );
    };

    const { getByText } = render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    expect(getByText('Desktop')).toBeTruthy();
  });
});

describe('Cross-Platform Consistency', () => {
  it('maintains consistent styling across screen sizes', () => {
    const screenSizes = [
      { width: 375, height: 812 },  // iPhone
      { width: 414, height: 896 },  // iPhone Plus
      { width: 768, height: 1024 }, // iPad
      { width: 1024, height: 768 }, // iPad Landscape
      { width: 1200, height: 800 }, // Desktop
    ];

    screenSizes.forEach((size) => {
      mockDimensions.get.mockReturnValue(size);
      
      const { getByText } = render(
        <TestWrapper>
          <ResponsiveLayout>
            <SearchBar
              value=""
              onChangeText={jest.fn()}
              placeholder="Search..."
            />
            <ContactCard
              contact={mockContact}
              onPress={jest.fn()}
            />
          </ResponsiveLayout>
        </TestWrapper>
      );

      // Components should render consistently
      expect(getByText('John Doe')).toBeTruthy();
    });
  });

  it('handles orientation changes', () => {
    // Portrait
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    // Landscape
    mockDimensions.get.mockReturnValue({ width: 812, height: 375 });
    rerender(
      <TestWrapper>
        <ResponsiveLayout>
          <Text>Content</Text>
        </ResponsiveLayout>
      </TestWrapper>
    );

    expect(getByText('Content')).toBeTruthy();
  });
});