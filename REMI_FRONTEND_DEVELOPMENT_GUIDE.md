# R.E.M.I Frontend Development Guide

## Project Overview

This repository contains the React Native mobile application and Progressive Web Application for R.E.M.I (Real-time External Memory Interface), providing intelligent contact-based auto-search, real-time synchronization, and cross-platform communication insights.

## Architecture

### Technology Stack

**React Native Mobile App:**
- React Native 0.72+ with TypeScript 5.0+
- React Navigation 6+ for navigation
- Zustand/Redux Toolkit for state management
- React Query for API state management
- React Native libraries for native functionality

**Progressive Web App:**
- React 18+ with TypeScript 5.0+
- Next.js 13+ for SSR and optimization
- React Router for navigation
- Redux Toolkit for state management
- Service Worker for offline functionality

**Shared Libraries:**
- Axios + React Query for API communication
- Shared business logic and utilities
- Common TypeScript interfaces and types

## Project Structure

```
remi-frontend/
├── packages/
│   ├── mobile/                 # React Native app
│   │   ├── src/
│   │   │   ├── components/     # React Native components
│   │   │   ├── screens/        # Screen components
│   │   │   ├── navigation/     # Navigation configuration
│   │   │   ├── services/       # API and business logic
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── utils/          # Utility functions
│   │   │   └── types/          # TypeScript types
│   │   ├── android/            # Android-specific code
│   │   ├── ios/                # iOS-specific code
│   │   └── package.json
│   │
│   ├── web/                    # Progressive Web App
│   │   ├── src/
│   │   │   ├── components/     # React components
│   │   │   ├── pages/          # Page components
│   │   │   ├── services/       # API and business logic
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── utils/          # Utility functions
│   │   │   └── types/          # TypeScript types
│   │   ├── public/             # Static assets
│   │   └── package.json
│   │
│   └── shared/                 # Shared code between mobile and web
│       ├── src/
│       │   ├── api/            # API client and endpoints
│       │   ├── services/       # Business logic services
│       │   ├── types/          # Shared TypeScript interfaces
│       │   ├── utils/          # Shared utility functions
│       │   └── constants/      # Shared constants
│       └── package.json
│
├── docs/                       # Documentation
├── scripts/                    # Build and deployment scripts
├── .github/                    # GitHub Actions workflows
└── package.json               # Root package.json for monorepo
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
git clone https://github.com/your-org/remi-frontend.git
cd remi-frontend

# Install dependencies for all packages
npm install

# Install iOS dependencies (macOS only)
cd packages/mobile/ios && pod install && cd ../../..

# Start Metro bundler for React Native
npm run mobile:start

# Run on iOS (in another terminal)
npm run mobile:ios

# Run on Android (in another terminal)
npm run mobile:android

# Run web application
npm run web:dev
```

## Core Features Implementation

### 1. Contact Intelligence System

**Key Components:**
- `ContactManager`: Unified contact management across platforms
- `ContactSearchService`: Intelligent contact search with fuzzy matching
- `ContactInsightsService`: AI-powered relationship analysis

**Implementation Priority:**
```typescript
// packages/shared/src/services/ContactManager.ts
export class ContactManager {
  async searchContacts(query: string): Promise<UnifiedContact[]> {
    // Implement fuzzy search with real-time suggestions
  }
  
  async getContactInsights(contactId: string): Promise<ContactInsights> {
    // Generate AI-powered relationship insights
  }
  
  async mergeContactIdentities(identities: ContactIdentity[]): Promise<UnifiedContact> {
    // Merge contacts across platforms
  }
}
```

### 2. Advanced Search System

**Key Features:**
- Real-time contact-based auto-search
- Natural language query processing
- Voice search integration
- Hybrid lexical and vector search

**React Native Implementation:**
```typescript
// packages/mobile/src/components/SearchBar.tsx
export const SearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<ContactSuggestion[]>([]);
  
  // Real-time contact suggestions
  const { data: contactSuggestions } = useContactSuggestions(query);
  
  // Voice search integration
  const startVoiceSearch = async () => {
    const result = await Voice.start({
      onSpeechResults: (results) => {
        setQuery(results[0]);
      }
    });
  };
  
  return (
    <View style={styles.searchContainer}>
      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder="Search contacts, messages..."
        style={styles.searchInput}
      />
      <TouchableOpacity onPress={startVoiceSearch}>
        <Icon name="microphone" />
      </TouchableOpacity>
    </View>
  );
};
```

### 3. Real-Time Synchronization

**WebSocket Integration:**
```typescript
// packages/shared/src/services/SyncService.ts
export class SyncService {
  private ws: WebSocket | null = null;
  
  async connect(): Promise<void> {
    this.ws = new WebSocket(WS_CONFIG.url);
    
    this.ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      this.handleRealTimeUpdate(update);
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
    }
  }
}
```

### 4. Offline Capabilities

**React Native Offline Storage:**
```typescript
// packages/mobile/src/services/OfflineStorage.ts
import SQLite from 'react-native-sqlite-storage';
import AsyncStorage from '@react-native-async-storage/async-storage';

export class OfflineStorage {
  private db: SQLite.SQLiteDatabase;
  
  async initializeDatabase(): Promise<void> {
    this.db = await SQLite.openDatabase({
      name: 'remi.db',
      location: 'default',
    });
    
    await this.createTables();
  }
  
  async cacheContacts(contacts: UnifiedContact[]): Promise<void> {
    const query = `INSERT OR REPLACE INTO contacts (id, data) VALUES (?, ?)`;
    
    for (const contact of contacts) {
      await this.db.executeSql(query, [contact.id, JSON.stringify(contact)]);
    }
  }
  
  async searchCachedContacts(query: string): Promise<UnifiedContact[]> {
    const sql = `SELECT data FROM contacts WHERE data MATCH ? LIMIT 20`;
    const [results] = await this.db.executeSql(sql, [query]);
    
    return Array.from({ length: results.rows.length }, (_, i) => 
      JSON.parse(results.rows.item(i).data)
    );
  }
}
```

## API Integration

### Backend Connection

**API Configuration:**
```typescript
// packages/shared/src/api/config.ts
export const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
};

// WebSocket Configuration
export const WS_CONFIG = {
  url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10
};
```

**API Client:**
```typescript
// packages/shared/src/api/client.ts
import axios from 'axios';
import { API_CONFIG } from './config';

export const apiClient = axios.create(API_CONFIG);

// Request interceptor for authentication
apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
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
      await refreshAuthToken();
      return apiClient.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

### Key API Endpoints

```typescript
// packages/shared/src/api/endpoints.ts
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
  },
  
  // Search
  SEARCH: {
    MESSAGES: '/api/v1/search/',
    CONTACTS: '/api/v1/participants/',
    COMMITMENTS: '/api/v1/search/commitments',
    FILES: '/api/v1/search/files',
  },
  
  // Contacts
  CONTACTS: {
    LIST: '/api/v1/participants/',
    DETAIL: '/api/v1/participants/{id}',
    DOSSIER: '/api/v1/contacts/dossiers/{id}',
  },
  
  // Messages
  MESSAGES: {
    LIST: '/api/v1/messages/',
    THREADS: '/api/v1/threads/',
    THREAD_DETAIL: '/api/v1/threads/{id}',
  },
  
  // Platforms
  PLATFORMS: {
    LIST: '/api/v1/platforms/',
    CONNECT: '/api/v1/platforms/{platform}/connect',
    STATUS: '/api/v1/platforms/{platform}/status',
  }
};
```

## Development Workflow

### 1. Feature Development Process

1. **Create Feature Branch**: `git checkout -b feature/contact-search`
2. **Implement Shared Logic**: Start with `packages/shared/`
3. **Add Mobile Components**: Implement in `packages/mobile/`
4. **Add Web Components**: Implement in `packages/web/`
5. **Write Tests**: Add unit and integration tests
6. **Test on Devices**: Test on iOS, Android, and web browsers
7. **Create Pull Request**: Submit for code review

### 2. Testing Strategy

**Unit Tests (Jest):**
```bash
# Run all tests
npm test

# Run mobile tests
npm run mobile:test

# Run web tests
npm run web:test

# Run shared tests
npm run shared:test
```

**E2E Tests (Detox for mobile, Playwright for web):**
```bash
# Mobile E2E tests
npm run mobile:e2e:ios
npm run mobile:e2e:android

# Web E2E tests
npm run web:e2e
```

### 3. Build and Deployment

**Development Builds:**
```bash
# Build mobile app for development
npm run mobile:build:dev

# Build web app for development
npm run web:build:dev
```

**Production Builds:**
```bash
# Build mobile app for production
npm run mobile:build:prod

# Build web app for production
npm run web:build:prod
```

**Deployment:**
```bash
# Deploy to app stores (requires certificates)
npm run mobile:deploy:ios
npm run mobile:deploy:android

# Deploy web app
npm run web:deploy
```

## Key Implementation Tasks

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up monorepo structure with React Native and web packages
- [ ] Configure shared TypeScript interfaces and API client
- [ ] Implement authentication system with biometric support
- [ ] Set up navigation and basic UI components

### Phase 2: Contact Intelligence (Weeks 3-4)
- [ ] Build contact management system with unified profiles
- [ ] Implement contact-based auto-search with fuzzy matching
- [ ] Add contact relationship insights and communication patterns
- [ ] Create contact profile views with interaction history

### Phase 3: Advanced Search (Weeks 5-6)
- [ ] Integrate with backend hybrid search system
- [ ] Add voice search with speech-to-text
- [ ] Implement natural language query processing
- [ ] Build advanced search UI with filters and suggestions

### Phase 4: Real-Time & Offline (Weeks 7-8)
- [ ] Implement WebSocket real-time synchronization
- [ ] Add offline capabilities with SQLite caching
- [ ] Build conflict resolution for offline-online sync
- [ ] Add push notifications and deep linking

### Phase 5: Polish & Deploy (Weeks 9-10)
- [ ] Performance optimization and testing
- [ ] Security implementation and audit
- [ ] App store preparation and deployment
- [ ] User acceptance testing and bug fixes

## Environment Configuration

### Development Environment Variables

Create `.env` files in each package:

**packages/mobile/.env:**
```
API_BASE_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
ENVIRONMENT=development
```

**packages/web/.env:**
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development
```

### Production Configuration

**packages/mobile/.env.production:**
```
API_BASE_URL=https://api.remi.com
WS_URL=wss://api.remi.com/ws
ENVIRONMENT=production
```

**packages/web/.env.production:**
```
REACT_APP_API_URL=https://api.remi.com
REACT_APP_WS_URL=wss://api.remi.com/ws
REACT_APP_ENVIRONMENT=production
```

## Getting Started Checklist

- [ ] Clone repository and install dependencies
- [ ] Set up development environment (Node.js, React Native CLI, Xcode/Android Studio)
- [ ] Configure environment variables
- [ ] Run backend R.E.M.I system locally
- [ ] Start mobile development server and test on simulator/emulator
- [ ] Start web development server and test in browser
- [ ] Verify API connectivity and authentication flow
- [ ] Begin implementing contact-based search functionality

## Support and Resources

- **Backend API Documentation**: Available at `http://localhost:8000/docs` when running locally
- **React Native Documentation**: https://reactnative.dev/docs/getting-started
- **TypeScript Documentation**: https://www.typescriptlang.org/docs/
- **Testing Documentation**: Jest, Detox, and Playwright documentation

This development guide provides everything needed to start building the React Native mobile app and Progressive Web App with advanced contact-based auto-search capabilities that integrate seamlessly with your existing R.E.M.I backend system.