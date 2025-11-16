---
inclusion: manual
---

# R.E.M.I Frontend Development Steering Guide

## Overview

This steering document provides comprehensive guidance for developing the R.E.M.I frontend applications (React Native mobile app and Progressive Web App) with advanced contact-based auto-search capabilities. Use this guide when working on any frontend-related tasks.

## Architecture Principles

### Contact-First Design Philosophy
- **Primary Focus**: Every UI component should prioritize contact-based interactions
- **Search-Centric**: Contact search should be accessible from every screen
- **Relationship Intelligence**: Display contact insights and communication patterns prominently
- **Cross-Platform Consistency**: Maintain unified UX across mobile and web while optimizing for each platform

### Technology Stack Standards

#### React Native Mobile App
```typescript
// Core Dependencies
"react-native": "0.72+",
"typescript": "5.0+",
"@react-navigation/native": "6+",
"@react-navigation/bottom-tabs": "6+",
"@react-navigation/stack": "6+",
"zustand": "4+", // or "@reduxjs/toolkit": "1.9+"
"@tanstack/react-query": "4+",

// Native Functionality
"react-native-keychain": "8+",
"react-native-biometrics": "3+",
"@react-native-voice/voice": "3+",
"@react-native-firebase/messaging": "18+",
"react-native-sqlite-storage": "6+",
"@react-native-async-storage/async-storage": "1.19+",
"react-native-gesture-handler": "2+",
"@react-native-netinfo": "9+",

// Testing
"jest": "29+",
"detox": "20+",
"@testing-library/react-native": "12+"
```

#### Progressive Web App
```typescript
// Core Dependencies
"react": "18+",
"typescript": "5.0+",
"next": "13+",
"@reduxjs/toolkit": "1.9+",
"@tanstack/react-query": "4+",

// PWA Features
"next-pwa": "5+",
"workbox-webpack-plugin": "6+",
"idb": "7+", // IndexedDB wrapper

// Testing
"jest": "29+",
"@testing-library/react": "13+",
"@playwright/test": "1.35+"
```

## API Integration Standards

### Backend Connection Configuration
```typescript
// API Base Configuration
const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
};

// WebSocket Configuration
const WS_CONFIG = {
  url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10
};
```

### Required API Endpoints Integration
```typescript
// Core API Endpoints to Integrate
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
  },
  
  // Contact-based search (PRIMARY FEATURE)
  SEARCH: {
    MESSAGES: '/api/v1/search/',
    CONTACTS: '/api/v1/participants/',
    COMMITMENTS: '/api/v1/search/commitments',
    FILES: '/api/v1/search/files',
    SUGGESTIONS: '/api/v1/search/suggestions',
  },
  
  // Contact management
  CONTACTS: {
    LIST: '/api/v1/participants/',
    DETAIL: '/api/v1/participants/{id}',
    DOSSIER: '/api/v1/contacts/dossiers/{id}',
    MERGE: '/api/v1/contacts/merge',
  },
  
  // Messages and threads
  MESSAGES: {
    LIST: '/api/v1/messages/',
    THREADS: '/api/v1/threads/',
    THREAD_DETAIL: '/api/v1/threads/{id}',
  },
  
  // Platform connections
  PLATFORMS: {
    LIST: '/api/v1/platforms/',
    CONNECT: '/api/v1/platforms/{platform}/connect',
    STATUS: '/api/v1/platforms/{platform}/status',
    DISCONNECT: '/api/v1/platforms/{platform}',
  },
  
  // Real-time WebSocket
  WEBSOCKET: '/ws',
};
```

## Contact-Based Auto-Search Implementation Guide

### Core Contact Search Component Pattern
```typescript
// Standard Contact Search Component Structure
interface ContactSearchProps {
  onContactSelect: (contact: UnifiedContact) => void;
  placeholder?: string;
  showVoiceSearch?: boolean;
  showAdvancedFilters?: boolean;
  autoFocus?: boolean;
}

// Required Features for Contact Search
const ContactSearchFeatures = {
  // Real-time search with debouncing (300ms)
  realTimeSearch: true,
  
  // Fuzzy matching for names, emails, handles
  fuzzyMatching: true,
  
  // Voice search integration
  voiceSearch: true,
  
  // Contact suggestions with photos and platform indicators
  visualSuggestions: true,
  
  // Natural language processing ("messages with John")
  naturalLanguageQueries: true,
  
  // Quick access to shared files and conversation history
  contextualActions: true,
};
```

### Contact Data Model Standards
```typescript
// Unified Contact Interface (MUST be consistent across mobile and web)
interface UnifiedContact {
  id: string;
  primaryName: string;
  displayName: string;
  profilePhoto?: string;
  
  // Platform identities
  identities: ContactIdentity[];
  
  // Contact information
  emails: string[];
  phoneNumbers: string[];
  socialProfiles: SocialProfile[];
  
  // Communication metadata
  lastInteraction: Date;
  totalMessages: number;
  platforms: string[];
  preferredPlatform?: string;
  
  // AI-generated insights
  relationshipStrength: number; // 0-1 scale
  communicationFrequency: 'high' | 'medium' | 'low';
  responsePattern: ResponsePattern;
  topicAffinity: TopicAffinity[];
  
  // Shared content
  sharedFiles: SharedFile[];
  sharedLinks: SharedLink[];
  commonContacts: string[];
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
  lastSyncAt: Date;
}

interface ContactIdentity {
  platform: string;
  platformUserId: string;
  displayName: string;
  handle?: string;
  profileUrl?: string;
  verified: boolean;
}
```

## Component Development Standards

### React Native Component Patterns
```typescript
// Standard React Native Component Structure
import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useContacts } from '../hooks/useContacts';

interface ComponentProps {
  // Always include proper TypeScript interfaces
}

export const ComponentName: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  // State management
  const [localState, setLocalState] = useState();
  
  // Custom hooks for business logic
  const { contacts, searchContacts, isLoading } = useContacts();
  
  // Memoized callbacks for performance
  const handleAction = useCallback(() => {
    // Implementation
  }, [dependencies]);
  
  // Effects for side effects
  useEffect(() => {
    // Setup and cleanup
  }, [dependencies]);
  
  return (
    <View style={styles.container}>
      {/* Component JSX */}
    </View>
  );
};

// StyleSheet at bottom of file
const styles = StyleSheet.create({
  container: {
    flex: 1,
    // Styles
  },
});
```

### Web Component Patterns
```typescript
// Standard React Web Component Structure
import React, { useState, useEffect, useCallback } from 'react';
import { useContacts } from '../hooks/useContacts';
import styles from './ComponentName.module.css';

interface ComponentProps {
  // TypeScript interfaces
}

export const ComponentName: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  // State and hooks
  const [localState, setLocalState] = useState();
  const { contacts, searchContacts, isLoading } = useContacts();
  
  // Memoized callbacks
  const handleAction = useCallback(() => {
    // Implementation
  }, [dependencies]);
  
  return (
    <div className={styles.container}>
      {/* Component JSX */}
    </div>
  );
};
```

## State Management Patterns

### Contact State Management
```typescript
// Zustand Store for Contact Management (Mobile)
interface ContactStore {
  contacts: UnifiedContact[];
  searchResults: UnifiedContact[];
  selectedContact: UnifiedContact | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  searchContacts: (query: string) => Promise<void>;
  selectContact: (contact: UnifiedContact) => void;
  clearSearch: () => void;
  updateContact: (contact: UnifiedContact) => void;
}

// Redux Toolkit Slice for Contact Management (Web)
const contactSlice = createSlice({
  name: 'contacts',
  initialState: {
    contacts: [],
    searchResults: [],
    selectedContact: null,
    isLoading: false,
    error: null,
  },
  reducers: {
    setSearchResults: (state, action) => {
      state.searchResults = action.payload;
    },
    selectContact: (state, action) => {
      state.selectedContact = action.payload;
    },
    // Additional reducers
  },
});
```

## Real-Time Integration Standards

### WebSocket Connection Management
```typescript
// Standard WebSocket Hook Pattern
export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const ws = useRef<WebSocket | null>(null);
  
  const connect = useCallback(() => {
    // Connection logic with automatic reconnection
  }, []);
  
  const sendMessage = useCallback((type: string, data: any) => {
    // Send message logic
  }, []);
  
  // Handle different message types
  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'contact_update':
        // Update contact cache
        break;
      case 'message_received':
        // Handle new messages
        break;
      case 'insight_notification':
        // Show proactive notifications
        break;
    }
  }, []);
  
  return { isConnected, lastMessage, sendMessage };
};
```

## Offline Storage Standards

### React Native Storage (SQLite + AsyncStorage)
```typescript
// SQLite Schema for Contact Caching
const CREATE_CONTACTS_TABLE = `
  CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    search_text TEXT NOT NULL,
    last_interaction INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
  );
`;

// Full-text search table
const CREATE_CONTACTS_FTS = `
  CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
    id,
    primary_name,
    display_name,
    email,
    phone,
    platforms,
    content='contacts'
  );
`;
```

### Web Storage (IndexedDB)
```typescript
// IndexedDB Schema for Web App
interface REMIDatabase extends DBSchema {
  contacts: {
    key: string;
    value: UnifiedContact;
    indexes: {
      'by-name': string;
      'by-platform': string;
      'by-last-interaction': Date;
    };
  };
  searchCache: {
    key: string;
    value: {
      query: string;
      results: UnifiedContact[];
      timestamp: Date;
      expiresAt: Date;
    };
  };
}
```

## Security Implementation Standards

### Authentication and Token Management
```typescript
// Secure Token Storage (Mobile)
import Keychain from 'react-native-keychain';

export const TokenManager = {
  async storeTokens(accessToken: string, refreshToken: string): Promise<void> {
    await Keychain.setInternetCredentials(
      'remi-auth',
      'user',
      JSON.stringify({ accessToken, refreshToken })
    );
  },
  
  async getTokens(): Promise<{ accessToken: string; refreshToken: string } | null> {
    const credentials = await Keychain.getInternetCredentials('remi-auth');
    if (credentials) {
      return JSON.parse(credentials.password);
    }
    return null;
  },
};

// Secure Token Storage (Web)
export const WebTokenManager = {
  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },
  
  getAccessToken(): string | null {
    return localStorage.getItem('auth_token');
  },
};
```

### Biometric Authentication (Mobile Only)
```typescript
import ReactNativeBiometrics from 'react-native-biometrics';

export const BiometricAuth = {
  async isAvailable(): Promise<boolean> {
    const { available } = await ReactNativeBiometrics.isSensorAvailable();
    return available;
  },
  
  async authenticate(): Promise<boolean> {
    const { success } = await ReactNativeBiometrics.simplePrompt({
      promptMessage: 'Authenticate to access R.E.M.I'
    });
    return success;
  },
};
```

## Testing Standards

### Unit Testing Patterns
```typescript
// React Native Testing
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { ContactSearchBar } from '../ContactSearchBar';

describe('ContactSearchBar', () => {
  test('should search contacts with fuzzy matching', async () => {
    const mockOnContactSelect = jest.fn();
    const { getByPlaceholderText } = render(
      <ContactSearchBar onContactSelect={mockOnContactSelect} />
    );
    
    const input = getByPlaceholderText(/search contacts/i);
    fireEvent.changeText(input, 'jon smith');
    
    await waitFor(() => {
      // Verify search results
    });
  });
});

// Web Testing
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ContactSearchBar } from '../ContactSearchBar';

describe('ContactSearchBar', () => {
  test('should display contact suggestions', async () => {
    render(<ContactSearchBar onContactSelect={jest.fn()} />);
    
    const input = screen.getByPlaceholderText(/search contacts/i);
    fireEvent.change(input, { target: { value: 'John' } });
    
    await waitFor(() => {
      expect(screen.getByText(/john smith/i)).toBeInTheDocument();
    });
  });
});
```

### E2E Testing Standards
```typescript
// Detox E2E Testing (Mobile)
describe('Contact Search Flow', () => {
  it('should search and select contact', async () => {
    await element(by.id('search-tab')).tap();
    await element(by.id('contact-search-input')).typeText('John');
    await waitFor(element(by.id('contact-suggestions'))).toBeVisible();
    await element(by.id('contact-suggestion-0')).tap();
    await expect(element(by.id('contact-profile'))).toBeVisible();
  });
});

// Playwright E2E Testing (Web)
test('contact search workflow', async ({ page }) => {
  await page.goto('/search');
  await page.fill('[data-testid=contact-search]', 'John');
  await page.waitForSelector('[data-testid=contact-suggestions]');
  await page.click('[data-testid=contact-suggestion]:first-child');
  await expect(page.locator('[data-testid=contact-profile]')).toBeVisible();
});
```

## Performance Optimization Guidelines

### React Native Performance
```typescript
// Use FlatList for large contact lists
import { FlatList } from 'react-native';

const ContactList: React.FC = ({ contacts }) => {
  const renderContact = useCallback(({ item }: { item: UnifiedContact }) => (
    <ContactItem contact={item} />
  ), []);
  
  const keyExtractor = useCallback((item: UnifiedContact) => item.id, []);
  
  return (
    <FlatList
      data={contacts}
      renderItem={renderContact}
      keyExtractor={keyExtractor}
      removeClippedSubviews={true}
      maxToRenderPerBatch={10}
      windowSize={10}
      initialNumToRender={10}
    />
  );
};

// Image optimization
import FastImage from 'react-native-fast-image';

const ContactAvatar: React.FC<{ uri: string }> = ({ uri }) => (
  <FastImage
    source={{ uri }}
    style={styles.avatar}
    resizeMode={FastImage.resizeMode.cover}
  />
);
```

### Web Performance
```typescript
// Virtual scrolling for large lists
import { FixedSizeList as List } from 'react-window';

const ContactList: React.FC = ({ contacts }) => {
  const Row = ({ index, style }: { index: number; style: any }) => (
    <div style={style}>
      <ContactItem contact={contacts[index]} />
    </div>
  );
  
  return (
    <List
      height={600}
      itemCount={contacts.length}
      itemSize={80}
    >
      {Row}
    </List>
  );
};

// Image lazy loading
import { lazy, Suspense } from 'react';

const LazyContactAvatar = lazy(() => import('./ContactAvatar'));

const ContactItem: React.FC = ({ contact }) => (
  <div>
    <Suspense fallback={<div>Loading...</div>}>
      <LazyContactAvatar src={contact.profilePhoto} />
    </Suspense>
  </div>
);
```

## Deployment Configuration

### React Native Deployment
```bash
# iOS Deployment
cd ios && pod install
react-native run-ios --configuration Release

# Android Deployment
cd android && ./gradlew assembleRelease

# CodePush for OTA updates
appcenter codepush release-react remi-mobile-ios ios
appcenter codepush release-react remi-mobile-android android
```

### Web Deployment
```bash
# Build for production
npm run build

# Deploy to Vercel
vercel --prod

# Deploy to Netlify
netlify deploy --prod --dir=out
```

## Environment Configuration Templates

### Mobile Environment Variables
```bash
# .env.development
API_BASE_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
ENVIRONMENT=development
ENABLE_FLIPPER=true

# .env.production
API_BASE_URL=https://api.remi.com
WS_URL=wss://api.remi.com/ws
ENVIRONMENT=production
ENABLE_FLIPPER=false
```

### Web Environment Variables
```bash
# .env.local
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development

# .env.production
REACT_APP_API_URL=https://api.remi.com
REACT_APP_WS_URL=wss://api.remi.com/ws
REACT_APP_ENVIRONMENT=production
```

## Development Workflow Standards

### Git Workflow
```bash
# Feature development
git checkout -b feature/contact-search-enhancement
git commit -m "feat: add voice search to contact search bar"
git push origin feature/contact-search-enhancement

# Commit message format
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting changes
refactor: code refactoring
test: adding tests
chore: maintenance tasks
```

### Code Review Checklist
- [ ] Contact search functionality works with fuzzy matching
- [ ] Voice search integration is properly implemented
- [ ] Real-time sync is working correctly
- [ ] Offline capabilities are functional
- [ ] Security measures are in place (token storage, biometric auth)
- [ ] Performance optimizations are applied
- [ ] Unit tests and E2E tests are passing
- [ ] TypeScript types are properly defined
- [ ] Error handling is comprehensive
- [ ] Accessibility features are implemented

## Repository Structure Standards

### Mobile Repository (`remi-mobile`)
```
remi-mobile/
├── src/
│   ├── components/
│   ├── screens/
│   ├── navigation/
│   ├── services/
│   ├── hooks/
│   ├── utils/
│   ├── types/
│   └── constants/
├── android/
├── ios/
├── __tests__/
└── docs/
```

### Web Repository (`remi-web`)
```
remi-web/
├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── services/
│   ├── store/
│   ├── utils/
│   ├── types/
│   └── constants/
├── public/
├── __tests__/
└── docs/
```

This steering document provides comprehensive guidance for implementing the R.E.M.I frontend applications with advanced contact-based auto-search capabilities. Follow these standards and patterns when working on any frontend development tasks.