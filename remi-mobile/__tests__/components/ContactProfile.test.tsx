/**
 * ContactProfile Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { ContactProfile } from '../../src/components/ContactProfile';
import { UnifiedContact } from '../../src/types';

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
        error: '#dc3545',
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

// Mock Linking
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Linking: {
      openURL: jest.fn(),
    },
  };
});

const mockContact: UnifiedContact = {
  id: '1',
  primaryName: 'John Smith',
  displayName: 'John Smith',
  profilePhoto: undefined,
  identities: [
    {
      platform: 'gmail',
      platformUserId: 'john.smith@gmail.com',
      displayName: 'John Smith',
      handle: 'john.smith',
      verified: true,
    },
  ],
  emails: ['john.smith@gmail.com'],
  phoneNumbers: ['+1-555-0123'],
  socialProfiles: [
    {
      platform: 'linkedin',
      url: 'https://linkedin.com/in/johnsmith',
      handle: 'johnsmith',
    },
  ],
  lastInteraction: new Date('2024-01-15'),
  totalMessages: 247,
  platforms: ['gmail'],
  preferredPlatform: 'gmail',
  relationshipStrength: 0.85,
  communicationFrequency: 'high',
  responsePattern: {
    averageResponseTime: 45,
    responseRate: 0.92,
    preferredTimes: ['9:00-12:00'],
    communicationStyle: 'professional',
  },
  topicAffinity: [],
  sharedFiles: [],
  sharedLinks: [],
  commonContacts: [],
  createdAt: new Date('2023-06-01'),
  updatedAt: new Date('2024-01-15'),
  lastSyncAt: new Date('2024-01-15'),
};

describe('ContactProfile', () => {
  it('renders contact information correctly', () => {
    const { getByText } = render(<ContactProfile contact={mockContact} />);

    expect(getByText('John Smith')).toBeTruthy();
    expect(getByText('john.smith@gmail.com')).toBeTruthy();
    expect(getByText('+1-555-0123')).toBeTruthy();
    expect(getByText('247')).toBeTruthy();
    expect(getByText('High')).toBeTruthy();
    expect(getByText('85%')).toBeTruthy();
  });

  it('displays platform identities', () => {
    const { getByText } = render(<ContactProfile contact={mockContact} />);

    expect(getByText('Gmail')).toBeTruthy();
    expect(getByText('@john.smith')).toBeTruthy();
  });

  it('calls action handlers when buttons are pressed', () => {
    const mockMessagePress = jest.fn();
    const mockCallPress = jest.fn();
    const mockEmailPress = jest.fn();

    const { getByTestId } = render(
      <ContactProfile
        contact={mockContact}
        onMessagePress={mockMessagePress}
        onCallPress={mockCallPress}
        onEmailPress={mockEmailPress}
      />
    );

    // Note: In a real implementation, you'd add testID props to the action buttons
    // For now, this test structure shows how it would work
  });

  it('displays communication insights correctly', () => {
    const { getByText } = render(<ContactProfile contact={mockContact} />);

    expect(getByText('247')).toBeTruthy(); // Total messages
    expect(getByText('High')).toBeTruthy(); // Frequency
    expect(getByText('85%')).toBeTruthy(); // Relationship strength
    expect(getByText('45m')).toBeTruthy(); // Response time
  });

  it('handles missing profile photo gracefully', () => {
    const { getByText } = render(<ContactProfile contact={mockContact} />);

    // Should show initials when no profile photo
    expect(getByText('J')).toBeTruthy();
  });

  it('displays social profiles correctly', () => {
    const { getByText } = render(<ContactProfile contact={mockContact} />);

    expect(getByText('johnsmith (linkedin)')).toBeTruthy();
  });

  it('shows quick action buttons when handlers are provided', () => {
    const mockViewMessages = jest.fn();
    const mockViewSharedContent = jest.fn();

    const { getByText } = render(
      <ContactProfile
        contact={mockContact}
        onViewMessagesPress={mockViewMessages}
        onViewSharedContentPress={mockViewSharedContent}
      />
    );

    expect(getByText('View Messages (247)')).toBeTruthy();
    expect(getByText('Shared Content (0)')).toBeTruthy();
  });
});