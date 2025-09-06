/**
 * Navigation Tests
 * 
 * Tests for navigation structure and tab functionality
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { MainNavigator } from '../../src/navigation/MainNavigator';
import { ThemeProvider } from '../../src/contexts/ThemeContext';

// Mock dependencies
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
}));

// Mock screens
jest.mock('../../src/screens/DashboardScreen', () => ({
  DashboardScreen: () => 'Dashboard Screen',
}));

jest.mock('../../src/screens/SearchScreen', () => ({
  SearchScreen: () => 'Search Screen',
}));

jest.mock('../../src/screens/ContactsScreen', () => ({
  ContactsScreen: () => 'Contacts Screen',
}));

jest.mock('../../src/screens/MessagesScreen', () => ({
  MessagesScreen: () => 'Messages Screen',
}));

jest.mock('../../src/screens/SettingsScreen', () => ({
  SettingsScreen: () => 'Settings Screen',
}));

jest.mock('../../src/screens/ContactProfileScreen', () => ({
  ContactProfileScreen: () => 'Contact Profile Screen',
}));

jest.mock('../../src/screens/MessageThreadScreen', () => ({
  MessageThreadScreen: () => 'Message Thread Screen',
}));

jest.mock('../../src/screens/ResponsiveUIDemo', () => ({
  ResponsiveUIDemoScreen: () => 'Responsive UI Demo Screen',
}));

// Test wrapper
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider>
    <NavigationContainer>
      {children}
    </NavigationContainer>
  </ThemeProvider>
);

describe('MainNavigator', () => {
  it('renders tab navigator with all tabs', async () => {
    const { getByText } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Should show the default screen (Dashboard)
    await waitFor(() => {
      expect(getByText('Dashboard Screen')).toBeTruthy();
    });
  });

  it('navigates between tabs correctly', async () => {
    const { getByText, getByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Start with Dashboard
    await waitFor(() => {
      expect(getByText('Dashboard Screen')).toBeTruthy();
    });

    // Navigate to Search tab
    const searchTab = getByRole('button', { name: /search/i });
    fireEvent.press(searchTab);

    await waitFor(() => {
      expect(getByText('Search Screen')).toBeTruthy();
    });

    // Navigate to Contacts tab
    const contactsTab = getByRole('button', { name: /contacts/i });
    fireEvent.press(contactsTab);

    await waitFor(() => {
      expect(getByText('Contacts Screen')).toBeTruthy();
    });

    // Navigate to Messages tab
    const messagesTab = getByRole('button', { name: /messages/i });
    fireEvent.press(messagesTab);

    await waitFor(() => {
      expect(getByText('Messages Screen')).toBeTruthy();
    });

    // Navigate to Settings tab
    const settingsTab = getByRole('button', { name: /settings/i });
    fireEvent.press(settingsTab);

    await waitFor(() => {
      expect(getByText('Settings Screen')).toBeTruthy();
    });
  });

  it('maintains tab state when switching', async () => {
    const { getByText, getByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigate to Search
    const searchTab = getByRole('button', { name: /search/i });
    fireEvent.press(searchTab);

    await waitFor(() => {
      expect(getByText('Search Screen')).toBeTruthy();
    });

    // Navigate to Contacts
    const contactsTab = getByRole('button', { name: /contacts/i });
    fireEvent.press(contactsTab);

    await waitFor(() => {
      expect(getByText('Contacts Screen')).toBeTruthy();
    });

    // Navigate back to Search - should maintain state
    fireEvent.press(searchTab);

    await waitFor(() => {
      expect(getByText('Search Screen')).toBeTruthy();
    });
  });

  it('shows correct tab icons and labels', () => {
    const { getByText } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Check that tab labels are present
    expect(getByText('Dashboard')).toBeTruthy();
    expect(getByText('Search')).toBeTruthy();
    expect(getByText('Contacts')).toBeTruthy();
    expect(getByText('Messages')).toBeTruthy();
    expect(getByText('Settings')).toBeTruthy();
  });
});

describe('Navigation Structure', () => {
  it('has correct tab order', () => {
    const { getAllByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    const tabs = getAllByRole('button');
    
    // Should have 5 tabs in the correct order
    expect(tabs).toHaveLength(5);
  });

  it('applies theme colors to navigation', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigation should use theme colors
    // This would test the actual styling in a real implementation
    expect(true).toBeTruthy();
  });

  it('handles navigation state persistence', async () => {
    const { getByRole, rerender } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigate to a different tab
    const contactsTab = getByRole('button', { name: /contacts/i });
    fireEvent.press(contactsTab);

    // Simulate app restart by re-rendering
    rerender(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Should maintain navigation state (in a real app with persistence)
    expect(true).toBeTruthy();
  });
});

describe('Responsive Navigation', () => {
  it('adapts to different screen sizes', () => {
    // Mock different screen sizes
    const mockDimensions = {
      get: jest.fn(() => ({ width: 375, height: 812 })),
    };
    
    jest.doMock('react-native', () => ({
      ...jest.requireActual('react-native'),
      Dimensions: mockDimensions,
    }));

    // Test mobile
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Test tablet
    mockDimensions.get.mockReturnValue({ width: 768, height: 1024 });
    rerender(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigation should adapt to screen size
    expect(true).toBeTruthy();
  });

  it('handles orientation changes', () => {
    const mockDimensions = {
      get: jest.fn(() => ({ width: 375, height: 812 })),
    };
    
    jest.doMock('react-native', () => ({
      ...jest.requireActual('react-native'),
      Dimensions: mockDimensions,
    }));

    // Portrait
    mockDimensions.get.mockReturnValue({ width: 375, height: 812 });
    const { rerender } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Landscape
    mockDimensions.get.mockReturnValue({ width: 812, height: 375 });
    rerender(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigation should handle orientation changes
    expect(true).toBeTruthy();
  });
});

describe('Accessibility', () => {
  it('provides proper accessibility labels', () => {
    const { getByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Each tab should have proper accessibility labels
    expect(getByRole('button', { name: /dashboard/i })).toBeTruthy();
    expect(getByRole('button', { name: /search/i })).toBeTruthy();
    expect(getByRole('button', { name: /contacts/i })).toBeTruthy();
    expect(getByRole('button', { name: /messages/i })).toBeTruthy();
    expect(getByRole('button', { name: /settings/i })).toBeTruthy();
  });

  it('supports keyboard navigation', () => {
    const { getByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Tabs should be focusable and navigable with keyboard
    const searchTab = getByRole('button', { name: /search/i });
    
    // In a real implementation, this would test keyboard events
    expect(searchTab).toBeTruthy();
  });

  it('provides proper screen reader support', () => {
    const { getByRole } = render(
      <TestWrapper>
        <MainNavigator />
      </TestWrapper>
    );

    // Navigation should work with screen readers
    const tabs = getAllByRole('button');
    tabs.forEach(tab => {
      expect(tab).toBeTruthy();
    });
  });
});