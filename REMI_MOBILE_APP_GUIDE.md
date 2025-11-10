# R.E.M.I Mobile App Development Guide

## Project Overview

This repository contains the React Native mobile application for R.E.M.I (Real-time External Memory Interface), providing intelligent contact-based auto-search, real-time synchronization, and cross-platform communication insights for iOS and Android devices.

## Technology Stack

**React Native Mobile App:**
- React Native 0.72+ with TypeScript 5.0+
- React Navigation 6+ for navigation
- Zustand/Redux Toolkit for state management
- React Query for API state management
- Native modules for device-specific functionality

**Key Libraries:**
- `react-native-keychain` - Secure token storage
- `react-native-biometrics` - Biometric authentication
- `@react-native-voice/voice` - Voice search
- `@react-native-firebase/messaging` - Push notifications
- `react-native-sqlite-storage` - Local database
- `@react-native-async-storage/async-storage` - Local storage
- `react-native-gesture-handler` - Gesture support
- `@react-native-netinfo` - Network status

## Project Structure

```
apps/mobile/
├── src/
│   ├── components/             # Reusable React Native components
│   │   ├── common/            # Common UI components
│   │   ├── search/            # Search-related components
│   │   ├── contacts/          # Contact-related components
│   │   └── messages/          # Message-related components
│   │
│   ├── screens/               # Screen components
│   │   ├── auth/              # Authentication screens
│   │   ├── dashboard/         # Dashboard screen
│   │   ├── search/            # Search screens
│   │   ├── contacts/          # Contact screens
│   │   ├── messages/          # Message screens
│   │   └── settings/          # Settings screens
│   │
│   ├── navigation/            # Navigation configuration
│   │   ├── AppNavigator.tsx   # Main navigation
│   │   ├── AuthNavigator.tsx  # Auth navigation
│   │   └── TabNavigator.tsx   # Bottom tab navigation
│   │
│   ├── services/              # Business logic and API services
│   │   ├── api/               # API client and endpoints
│   │   ├── auth/              # Authentication service
│   │   ├── contacts/          # Contact management
│   │   ├── search/            # Search functionality
│   │   ├── sync/              # Real-time synchronization
│   │   └── storage/           # Local storage management
│   │
│   ├── hooks/                 # Custom React hooks
│   │   ├── useAuth.ts         # Authentication hook
│   │   ├── useContacts.ts     # Contact management hook
│   │   ├── useSearch.ts       # Search functionality hook
│   │   └── useSync.ts         # Synchronization hook
│   │
│   ├── utils/                 # Utility functions
│   │   ├── api.ts             # API utilities
│   │   ├── storage.ts         # Storage utilities
│   │   ├── security.ts        # Security utilities
│   │   └── helpers.ts         # General helpers
│   │
│   ├── types/                 # TypeScript type definitions
│   │   ├── api.ts             # API types
│   │   ├── contacts.ts        # Contact types
│   │   ├── messages.ts        # Message types
│   │   └── navigation.ts      # Navigation types
│   │
│   └── constants/             # App constants
│       ├── api.ts             # API endpoints
│       ├── colors.ts          # Color palette
│       └── dimensions.ts      # Screen dimensions
│
├── android/                   # Android-specific code
├── ios/                       # iOS-specific code
├── __tests__/                 # Test files
├── docs/                      # Documentation
├── .github/                   # GitHub Actions workflows
└── package.json
```

## Development Setup

### Prerequisites

1. **Node.js 18+** and **npm/yarn**
2. **React Native CLI**: `npm install -g @react-native-community/cli`
3. **iOS Development** (macOS only):
   - Xcode 14+
   - iOS Simulator
   - CocoaPods: `sudo gem install cocoapods`
4. **Android Development**:
   - Android Studio
   - Android SDK (API 31+)
   - Android Emulator or physical device

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/remi-mobile.git
cd remi-mobile

# Install dependencies
npm install

# Install iOS dependencies (macOS only)
cd ios && pod install && cd ..

# Start Metro bundler
npm start

# Run on iOS (in another terminal)
npm run ios

# Run on Android (in another terminal)
npm run android
```

## Core Features Implementation

### 1. Contact Intelligence System

**Contact Manager Service:**
```typescript
// src/services/contacts/ContactManager.ts
import { UnifiedContact, ContactIdentity, ContactInsights } from '../../types/contacts';

export class ContactManager {
  async searchContacts(query: string): Promise<UnifiedContact[]> {
    // Implement fuzzy search with real-time suggestions
    const response = await this.apiClient.get('/api/v1/participants/', {
      params: { search: query, limit: 20 }
    });
    
    return response.data.map(this.mapToUnifiedContact);
  }
  
  async getContactInsights(contactId: string): Promise<ContactInsights> {
    const response = await this.apiClient.get(`/api/v1/contacts/dossiers/${contactId}`);
    return response.data;
  }
  
  async mergeContactIdentities(identities: ContactIdentity[]): Promise<UnifiedContact> {
    // Merge contacts across platforms
    const response = await this.apiClient.post('/api/v1/contacts/merge', {
      identities
    });
    return response.data;
  }
  
  private mapToUnifiedContact(participant: any): UnifiedContact {
    return {
      id: participant.id,
      primaryName: participant.display_name,
      displayName: participant.display_name,
      profilePhoto: participant.avatar_url,
      identities: [{
        platform: participant.platform,
        platformUserId: participant.platform_user_id,
        displayName: participant.display_name,
        verified: true
      }],
      emails: participant.email ? [participant.email] : [],
      phoneNumbers: participant.phone ? [participant.phone] : [],
      lastInteraction: new Date(participant.updated_at),
      platforms: [participant.platform],
      createdAt: new Date(participant.created_at),
      updatedAt: new Date(participant.updated_at)
    };
  }
}
```

### 2. Contact-Based Auto-Search Component

```typescript
// src/components/search/ContactSearchBar.tsx
import React, { useState, useEffect } from 'react';
import { View, TextInput, FlatList, TouchableOpacity, Text, Image } from 'react-native';
import Voice from '@react-native-voice/voice';
import { useContacts } from '../../hooks/useContacts';
import { UnifiedContact } from '../../types/contacts';

interface ContactSearchBarProps {
  onContactSelect: (contact: UnifiedContact) => void;
  placeholder?: string;
}

export const ContactSearchBar: React.FC<ContactSearchBarProps> = ({
  onContactSelect,
  placeholder = "Search contacts..."
}) => {
  const [query, setQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const { searchContacts, contactSuggestions, isLoading } = useContacts();

  useEffect(() => {
    if (query.length > 1) {
      searchContacts(query);
    }
  }, [query]);

  useEffect(() => {
    Voice.onSpeechResults = (event) => {
      if (event.value && event.value[0]) {
        setQuery(event.value[0]);
        setIsListening(false);
      }
    };

    return () => {
      Voice.destroy().then(Voice.removeAllListeners);
    };
  }, []);

  const startVoiceSearch = async () => {
    try {
      setIsListening(true);
      await Voice.start('en-US');
    } catch (error) {
      console.error('Voice search error:', error);
      setIsListening(false);
    }
  };

  const renderContactSuggestion = ({ item }: { item: UnifiedContact }) => (
    <TouchableOpacity
      style={styles.suggestionItem}
      onPress={() => onContactSelect(item)}
    >
      <Image
        source={{ uri: item.profilePhoto || 'default-avatar-url' }}
        style={styles.avatar}
      />
      <View style={styles.contactInfo}>
        <Text style={styles.contactName}>{item.displayName}</Text>
        <Text style={styles.contactDetails}>
          {item.platforms.join(', ')} • Last: {item.lastInteraction.toLocaleDateString()}
        </Text>
      </View>
      <View style={styles.platformBadges}>
        {item.platforms.map(platform => (
          <View key={platform} style={styles.platformBadge}>
            <Text style={styles.platformText}>{platform}</Text>
          </View>
        ))}
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.searchInputContainer}>
        <TextInput
          style={styles.searchInput}
          value={query}
          onChangeText={setQuery}
          placeholder={placeholder}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <TouchableOpacity
          style={[styles.voiceButton, isListening && styles.voiceButtonActive]}
          onPress={startVoiceSearch}
        >
          <Text style={styles.voiceButtonText}>🎤</Text>
        </TouchableOpacity>
      </View>
      
      {contactSuggestions.length > 0 && (
        <FlatList
          data={contactSuggestions}
          renderItem={renderContactSuggestion}
          keyExtractor={(item) => item.id}
          style={styles.suggestionsList}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  searchInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    borderRadius: 10,
    paddingHorizontal: 15,
    marginHorizontal: 20,
    marginVertical: 10,
  },
  searchInput: {
    flex: 1,
    height: 45,
    fontSize: 16,
  },
  voiceButton: {
    padding: 8,
    borderRadius: 20,
  },
  voiceButtonActive: {
    backgroundColor: '#007AFF',
  },
  voiceButtonText: {
    fontSize: 18,
  },
  suggestionsList: {
    maxHeight: 300,
    backgroundColor: 'white',
    marginHorizontal: 20,
    borderRadius: 10,
    elevation: 3,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  suggestionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
  },
  contactInfo: {
    flex: 1,
  },
  contactName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  contactDetails: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  platformBadges: {
    flexDirection: 'row',
  },
  platformBadge: {
    backgroundColor: '#e0e0e0',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 4,
  },
  platformText: {
    fontSize: 10,
    color: '#666',
  },
});
```

### 3. Real-Time Synchronization

```typescript
// src/services/sync/SyncService.ts
import { WebSocket } from 'react-native';
import NetInfo from '@react-native-netinfo';
import { DataUpdate, SyncResult } from '../../types/sync';

export class SyncService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectInterval = 5000;

  async connect(): Promise<void> {
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      throw new Error('No internet connection');
    }

    const token = await this.getAuthToken();
    this.ws = new WebSocket(`${WS_CONFIG.url}?token=${token}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const update: DataUpdate = JSON.parse(event.data);
      this.handleRealTimeUpdate(update);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleRealTimeUpdate(update: DataUpdate): void {
    switch (update.type) {
      case 'contact':
        this.updateContactCache(update.data);
        break;
      case 'message':
        this.updateMessageCache(update.data);
        break;
      case 'insight':
        this.showProactiveNotification(update.data);
        break;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.reconnectInterval * Math.pow(2, this.reconnectAttempts));
    }
  }
}
```

### 4. Offline Storage

```typescript
// src/services/storage/OfflineStorage.ts
import SQLite from 'react-native-sqlite-storage';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { UnifiedContact } from '../../types/contacts';

export class OfflineStorage {
  private db: SQLite.SQLiteDatabase | null = null;

  async initialize(): Promise<void> {
    this.db = await SQLite.openDatabase({
      name: 'remi.db',
      location: 'default',
    });

    await this.createTables();
  }

  private async createTables(): Promise<void> {
    if (!this.db) return;

    const createContactsTable = `
      CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        search_text TEXT NOT NULL,
        last_interaction INTEGER,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
      );
    `;

    const createContactsFTS = `
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

    const createSearchCache = `
      CREATE TABLE IF NOT EXISTS search_cache (
        query_hash TEXT PRIMARY KEY,
        query_text TEXT NOT NULL,
        results TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        expires_at INTEGER NOT NULL
      );
    `;

    await this.db.executeSql(createContactsTable);
    await this.db.executeSql(createContactsFTS);
    await this.db.executeSql(createSearchCache);
  }

  async cacheContacts(contacts: UnifiedContact[]): Promise<void> {
    if (!this.db) return;

    const insertContact = `
      INSERT OR REPLACE INTO contacts (id, data, search_text, last_interaction)
      VALUES (?, ?, ?, ?)
    `;

    for (const contact of contacts) {
      const searchText = [
        contact.primaryName,
        contact.displayName,
        ...contact.emails,
        ...contact.phoneNumbers,
        ...contact.platforms
      ].join(' ').toLowerCase();

      await this.db.executeSql(insertContact, [
        contact.id,
        JSON.stringify(contact),
        searchText,
        contact.lastInteraction.getTime()
      ]);
    }
  }

  async searchCachedContacts(query: string, limit = 20): Promise<UnifiedContact[]> {
    if (!this.db) return [];

    const searchQuery = `
      SELECT data FROM contacts 
      WHERE search_text LIKE ? 
      ORDER BY last_interaction DESC 
      LIMIT ?
    `;

    const [results] = await this.db.executeSql(searchQuery, [`%${query.toLowerCase()}%`, limit]);
    
    const contacts: UnifiedContact[] = [];
    for (let i = 0; i < results.rows.length; i++) {
      const row = results.rows.item(i);
      contacts.push(JSON.parse(row.data));
    }

    return contacts;
  }
}
```

## API Integration

### API Client Configuration

```typescript
// src/services/api/client.ts
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000' 
  : 'https://api.remi.com';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          await AsyncStorage.setItem('auth_token', access_token);
          await AsyncStorage.setItem('refresh_token', newRefreshToken);
          
          // Retry original request
          error.config.headers.Authorization = `Bearer ${access_token}`;
          return apiClient.request(error.config);
        } catch (refreshError) {
          // Redirect to login
          await AsyncStorage.multiRemove(['auth_token', 'refresh_token']);
          // Navigate to login screen
        }
      }
    }
    return Promise.reject(error);
  }
);
```

## Testing

### Unit Tests with Jest

```typescript
// __tests__/services/ContactManager.test.ts
import { ContactManager } from '../../src/services/contacts/ContactManager';

describe('ContactManager', () => {
  let contactManager: ContactManager;

  beforeEach(() => {
    contactManager = new ContactManager();
  });

  test('should search contacts with fuzzy matching', async () => {
    const results = await contactManager.searchContacts('jon smith');
    
    expect(results).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          primaryName: expect.stringContaining('John')
        })
      ])
    );
  });

  test('should merge duplicate contacts correctly', async () => {
    const identities = [
      { platform: 'gmail', platformUserId: 'john@gmail.com' },
      { platform: 'slack', platformUserId: 'john.smith' }
    ];

    const merged = await contactManager.mergeContactIdentities(identities);
    
    expect(merged.identities).toHaveLength(2);
    expect(merged.platforms).toEqual(['gmail', 'slack']);
  });
});
```

### E2E Tests with Detox

```typescript
// e2e/contactSearch.e2e.ts
describe('Contact Search', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should search for contacts and display results', async () => {
    // Navigate to search screen
    await element(by.id('search-tab')).tap();
    
    // Type in search bar
    await element(by.id('contact-search-input')).typeText('John');
    
    // Wait for results
    await waitFor(element(by.id('contact-suggestions')))
      .toBeVisible()
      .withTimeout(5000);
    
    // Verify results are displayed
    await expect(element(by.id('contact-suggestion-0'))).toBeVisible();
  });

  it('should select contact and navigate to profile', async () => {
    await element(by.id('search-tab')).tap();
    await element(by.id('contact-search-input')).typeText('John');
    await waitFor(element(by.id('contact-suggestions'))).toBeVisible();
    
    // Tap first result
    await element(by.id('contact-suggestion-0')).tap();
    
    // Verify navigation to contact profile
    await expect(element(by.id('contact-profile-screen'))).toBeVisible();
  });
});
```

## Build and Deployment

### Development Scripts

```json
{
  "scripts": {
    "start": "react-native start",
    "ios": "react-native run-ios",
    "android": "react-native run-android",
    "test": "jest",
    "test:watch": "jest --watch",
    "e2e:ios": "detox test --configuration ios.sim.debug",
    "e2e:android": "detox test --configuration android.emu.debug",
    "build:ios": "react-native run-ios --configuration Release",
    "build:android": "cd android && ./gradlew assembleRelease",
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "type-check": "tsc --noEmit"
  }
}
```

### Deployment Configuration

**iOS Deployment (Fastlane):**
```ruby
# ios/fastlane/Fastfile
default_platform(:ios)

platform :ios do
  desc "Build and upload to TestFlight"
  lane :beta do
    build_app(scheme: "RemiMobile")
    upload_to_testflight
  end

  desc "Build and upload to App Store"
  lane :release do
    build_app(scheme: "RemiMobile")
    upload_to_app_store
  end
end
```

**Android Deployment:**
```bash
# Build release APK
cd android && ./gradlew assembleRelease

# Build release AAB for Play Store
cd android && ./gradlew bundleRelease
```

## Environment Configuration

### Development Environment

```bash
# .env.development
API_BASE_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
ENVIRONMENT=development
ENABLE_FLIPPER=true
```

### Production Environment

```bash
# .env.production
API_BASE_URL=https://api.remi.com
WS_URL=wss://api.remi.com/ws
ENVIRONMENT=production
ENABLE_FLIPPER=false
```

## Getting Started Checklist

- [ ] Clone repository and install dependencies
- [ ] Set up React Native development environment
- [ ] Configure iOS and Android development tools
- [ ] Set up environment variables
- [ ] Run the app on iOS simulator and Android emulator
- [ ] Test contact search functionality
- [ ] Verify API connectivity with backend
- [ ] Test voice search and biometric authentication
- [ ] Run unit tests and E2E tests

This mobile app development guide provides everything needed to build a production-ready React Native application with advanced contact-based auto-search capabilities that integrates seamlessly with the R.E.M.I backend system.