/**
 * SharedContent Component Tests
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { SharedContent } from '../../src/components/SharedContent';
import { UnifiedContact, SharedFile, SharedLink } from '../../src/types';

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
        white: '#ffffff',
      },
    },
  }),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');

// Mock Linking
const mockOpenURL = jest.fn();
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Linking: {
      openURL: mockOpenURL,
    },
    Alert: {
      alert: jest.fn(),
    },
  };
});

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
  platforms: ['gmail'],
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

const mockFiles: SharedFile[] = [
  {
    id: '1',
    name: 'Project_Proposal.pdf',
    type: 'application/pdf',
    size: 2048576,
    url: 'https://example.com/file1.pdf',
    sharedAt: new Date('2024-01-10'),
    platform: 'gmail',
  },
  {
    id: '2',
    name: 'image.jpg',
    type: 'image/jpeg',
    size: 1024000,
    url: 'https://example.com/image.jpg',
    sharedAt: new Date('2024-01-12'),
    platform: 'slack',
  },
];

const mockLinks: SharedLink[] = [
  {
    id: '1',
    url: 'https://github.com/project/repo',
    title: 'Project Repository',
    description: 'Main project repository on GitHub',
    sharedAt: new Date('2024-01-12'),
    platform: 'slack',
  },
  {
    id: '2',
    url: 'https://docs.google.com/document/123',
    title: 'Project Documentation',
    description: 'Comprehensive project documentation',
    sharedAt: new Date('2024-01-11'),
    platform: 'gmail',
  },
];

describe('SharedContent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders header with contact name and counts', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    expect(getByText('Shared Content with John Smith')).toBeTruthy();
    expect(getByText('2 files • 2 links')).toBeTruthy();
  });

  it('displays filter tabs correctly', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    expect(getByText('All')).toBeTruthy();
    expect(getByText('Files')).toBeTruthy();
    expect(getByText('Links')).toBeTruthy();
  });

  it('shows all content by default', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    expect(getByText('Project_Proposal.pdf')).toBeTruthy();
    expect(getByText('image.jpg')).toBeTruthy();
    expect(getByText('Project Repository')).toBeTruthy();
    expect(getByText('Project Documentation')).toBeTruthy();
  });

  it('filters content when filter tabs are pressed', () => {
    const { getByText, queryByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    // Press Files filter
    fireEvent.press(getByText('Files'));
    expect(getByText('Project_Proposal.pdf')).toBeTruthy();
    expect(queryByText('Project Repository')).toBeFalsy();

    // Press Links filter
    fireEvent.press(getByText('Links'));
    expect(getByText('Project Repository')).toBeTruthy();
    expect(queryByText('Project_Proposal.pdf')).toBeFalsy();
  });

  it('displays file information correctly', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    expect(getByText('Project_Proposal.pdf')).toBeTruthy();
    expect(getByText('2.0 MB • application/pdf')).toBeTruthy();
    expect(getByText('gmail •')).toBeTruthy();
  });

  it('displays link information correctly', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    expect(getByText('Project Repository')).toBeTruthy();
    expect(getByText('Main project repository on GitHub')).toBeTruthy();
  });

  it('opens URLs when items are pressed', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    fireEvent.press(getByText('Project_Proposal.pdf'));
    expect(mockOpenURL).toHaveBeenCalledWith('https://example.com/file1.pdf');

    fireEvent.press(getByText('Project Repository'));
    expect(mockOpenURL).toHaveBeenCalledWith('https://github.com/project/repo');
  });

  it('calls custom handlers when provided', () => {
    const mockFilePress = jest.fn();
    const mockLinkPress = jest.fn();

    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
        onFilePress={mockFilePress}
        onLinkPress={mockLinkPress}
      />
    );

    fireEvent.press(getByText('Project_Proposal.pdf'));
    expect(mockFilePress).toHaveBeenCalledWith(mockFiles[0]);

    fireEvent.press(getByText('Project Repository'));
    expect(mockLinkPress).toHaveBeenCalledWith(mockLinks[0]);
  });

  it('shows empty state when no content', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={[]}
        links={[]}
      />
    );

    expect(getByText('No Content Found')).toBeTruthy();
    expect(getByText(`No shared content found with ${mockContact.primaryName}`)).toBeTruthy();
  });

  it('cycles through sort options when sort button is pressed', () => {
    const { getByText } = render(
      <SharedContent
        contact={mockContact}
        files={mockFiles}
        links={mockLinks}
      />
    );

    const sortButton = getByText('Date');
    
    fireEvent.press(sortButton);
    expect(getByText('Name')).toBeTruthy();

    fireEvent.press(getByText('Name'));
    expect(getByText('Platform')).toBeTruthy();

    fireEvent.press(getByText('Platform'));
    expect(getByText('Date')).toBeTruthy();
  });
});