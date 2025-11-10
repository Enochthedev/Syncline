# R.E.M.I Web Application Development Guide

## Project Overview

This repository contains the Progressive Web Application for R.E.M.I (Real-time External Memory Interface), providing intelligent contact-based auto-search, real-time synchronization, and cross-platform communication insights through a modern web interface.

## Technology Stack

**Progressive Web App:**
- React 18+ with TypeScript 5.0+
- Next.js 13+ for SSR and optimization
- React Router for client-side routing
- Redux Toolkit for state management
- React Query for API state management
- Service Worker for offline functionality

**Key Libraries:**
- `axios` - HTTP client
- `@tanstack/react-query` - Server state management
- `@reduxjs/toolkit` - State management
- `react-hook-form` - Form handling
- `framer-motion` - Animations
- `react-virtualized` - Virtual scrolling
- `workbox` - Service Worker utilities
- `web-speech-api` - Voice recognition

## Project Structure

```
apps/web/
├── src/
│   ├── components/             # Reusable React components
│   │   ├── common/            # Common UI components
│   │   ├── search/            # Search-related components
│   │   ├── contacts/          # Contact-related components
│   │   ├── messages/          # Message-related components
│   │   └── layout/            # Layout components
│   │
│   ├── pages/                 # Page components
│   │   ├── auth/              # Authentication pages
│   │   ├── dashboard/         # Dashboard page
│   │   ├── search/            # Search pages
│   │   ├── contacts/          # Contact pages
│   │   ├── messages/          # Message pages
│   │   └── settings/          # Settings pages
│   │
│   ├── hooks/                 # Custom React hooks
│   │   ├── useAuth.ts         # Authentication hook
│   │   ├── useContacts.ts     # Contact management hook
│   │   ├── useSearch.ts       # Search functionality hook
│   │   ├── useWebSocket.ts    # WebSocket connection hook
│   │   └── useOffline.ts      # Offline functionality hook
│   │
│   ├── services/              # Business logic and API services
│   │   ├── api/               # API client and endpoints
│   │   ├── auth/              # Authentication service
│   │   ├── contacts/          # Contact management
│   │   ├── search/            # Search functionality
│   │   ├── sync/              # Real-time synchronization
│   │   └── storage/           # Local storage management
│   │
│   ├── store/                 # Redux store configuration
│   │   ├── index.ts           # Store setup
│   │   ├── slices/            # Redux slices
│   │   └── middleware/        # Custom middleware
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
│   │   └── common.ts          # Common types
│   │
│   └── constants/             # App constants
│       ├── api.ts             # API endpoints
│       ├── colors.ts          # Color palette
│       └── breakpoints.ts     # Responsive breakpoints
│
├── public/                    # Static assets
│   ├── manifest.json          # PWA manifest
│   ├── sw.js                  # Service Worker
│   └── icons/                 # App icons
│
├── __tests__/                 # Test files
├── docs/                      # Documentation
├── .github/                   # GitHub Actions workflows
└── package.json
```

## Development Setup

### Prerequisites

1. **Node.js 18+** and **npm/yarn**
2. **Modern Browser** (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
3. **Git** for version control

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/remi-web.git
cd remi-web

# Install dependencies
npm install

# Start development server
npm run dev

# Open browser to http://localhost:3000
```

## Core Features Implementation

### 1. Contact Intelligence System

**Contact Manager Service:**
```typescript
// src/services/contacts/ContactManager.ts
import { UnifiedContact, ContactIdentity, ContactInsights } from '../../types/contacts';
import { apiClient } from '../api/client';

export class ContactManager {
  async searchContacts(query: string): Promise<UnifiedContact[]> {
    const response = await apiClient.get('/api/v1/participants/', {
      params: { search: query, limit: 50 }
    });
    
    return response.data.map(this.mapToUnifiedContact);
  }
  
  async getContactInsights(contactId: string): Promise<ContactInsights> {
    const response = await apiClient.get(`/api/v1/contacts/dossiers/${contactId}`);
    return response.data;
  }
  
  async getContactAnalytics(contactId: string): Promise<ContactAnalytics> {
    const response = await apiClient.get(`/api/v1/contacts/${contactId}/analytics`);
    return response.data;
  }
  
  async exportContactData(contactId: string, format: 'json' | 'csv'): Promise<Blob> {
    const response = await apiClient.get(`/api/v1/contacts/${contactId}/export`, {
      params: { format },
      responseType: 'blob'
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

### 2. Advanced Contact Search Component

```typescript
// src/components/search/ContactSearchBar.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash';
import { useContacts } from '../../hooks/useContacts';
import { UnifiedContact } from '../../types/contacts';

interface ContactSearchBarProps {
  onContactSelect: (contact: UnifiedContact) => void;
  placeholder?: string;
  showAdvancedFilters?: boolean;
}

export const ContactSearchBar: React.FC<ContactSearchBarProps> = ({
  onContactSelect,
  placeholder = "Search contacts...",
  showAdvancedFilters = false
}) => {
  const [query, setQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const { searchContacts, contactSuggestions, isLoading } = useContacts();

  // Debounced search to avoid excessive API calls
  const debouncedSearch = useCallback(
    debounce((searchQuery: string) => {
      if (searchQuery.length > 1) {
        searchContacts(searchQuery);
        setShowSuggestions(true);
      } else {
        setShowSuggestions(false);
      }
    }, 300),
    [searchContacts]
  );

  useEffect(() => {
    debouncedSearch(query);
    return () => {
      debouncedSearch.cancel();
    };
  }, [query, debouncedSearch]);

  const startVoiceSearch = async () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Voice search is not supported in this browser');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const handleContactSelect = (contact: UnifiedContact) => {
    setQuery(contact.displayName);
    setShowSuggestions(false);
    onContactSelect(contact);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  return (
    <div className="contact-search-container">
      <div className="search-input-wrapper">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="search-input"
          autoComplete="off"
        />
        
        <button
          onClick={startVoiceSearch}
          className={`voice-button ${isListening ? 'listening' : ''}`}
          title="Voice search"
        >
          🎤
        </button>
        
        {showAdvancedFilters && (
          <button className="filters-button" title="Advanced filters">
            ⚙️
          </button>
        )}
      </div>

      {showSuggestions && contactSuggestions.length > 0 && (
        <div className="suggestions-dropdown">
          {contactSuggestions.map((contact) => (
            <div
              key={contact.id}
              className="suggestion-item"
              onClick={() => handleContactSelect(contact)}
            >
              <img
                src={contact.profilePhoto || '/default-avatar.png'}
                alt={contact.displayName}
                className="contact-avatar"
              />
              <div className="contact-info">
                <div className="contact-name">{contact.displayName}</div>
                <div className="contact-details">
                  {contact.platforms.join(', ')} • Last: {contact.lastInteraction.toLocaleDateString()}
                </div>
              </div>
              <div className="platform-badges">
                {contact.platforms.map(platform => (
                  <span key={platform} className={`platform-badge ${platform}`}>
                    {platform}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {isLoading && (
        <div className="search-loading">
          <div className="spinner"></div>
          Searching...
        </div>
      )}
    </div>
  );
};
```

### 3. Advanced Search Interface

```typescript
// src/components/search/AdvancedSearchBuilder.tsx
import React, { useState } from 'react';
import { SearchFilters, QueryIntent } from '../../types/search';

interface AdvancedSearchBuilderProps {
  onSearch: (filters: SearchFilters) => void;
  initialFilters?: SearchFilters;
}

export const AdvancedSearchBuilder: React.FC<AdvancedSearchBuilderProps> = ({
  onSearch,
  initialFilters
}) => {
  const [filters, setFilters] = useState<SearchFilters>(initialFilters || {});
  const [queryBuilder, setQueryBuilder] = useState('');

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
  };

  const buildNaturalLanguageQuery = () => {
    const parts: string[] = [];
    
    if (filters.participants?.length) {
      parts.push(`messages with ${filters.participants.join(', ')}`);
    }
    
    if (filters.platforms?.length) {
      parts.push(`from ${filters.platforms.join(', ')}`);
    }
    
    if (filters.date_from || filters.date_to) {
      if (filters.date_from && filters.date_to) {
        parts.push(`between ${filters.date_from.toDateString()} and ${filters.date_to.toDateString()}`);
      } else if (filters.date_from) {
        parts.push(`since ${filters.date_from.toDateString()}`);
      } else if (filters.date_to) {
        parts.push(`before ${filters.date_to.toDateString()}`);
      }
    }
    
    if (filters.has_attachments) {
      parts.push('with attachments');
    }
    
    if (filters.entity_types?.length) {
      parts.push(`containing ${filters.entity_types.join(', ')}`);
    }
    
    return parts.join(' ');
  };

  const handleSearch = () => {
    onSearch(filters);
  };

  return (
    <div className="advanced-search-builder">
      <div className="search-section">
        <h3>Search Criteria</h3>
        
        <div className="filter-group">
          <label>Contacts</label>
          <input
            type="text"
            placeholder="Enter contact names..."
            onChange={(e) => handleFilterChange('participants', e.target.value.split(',').map(s => s.trim()))}
          />
        </div>

        <div className="filter-group">
          <label>Platforms</label>
          <div className="checkbox-group">
            {['gmail', 'slack', 'discord', 'whatsapp', 'twitter'].map(platform => (
              <label key={platform} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={filters.platforms?.includes(platform) || false}
                  onChange={(e) => {
                    const platforms = filters.platforms || [];
                    if (e.target.checked) {
                      handleFilterChange('platforms', [...platforms, platform]);
                    } else {
                      handleFilterChange('platforms', platforms.filter(p => p !== platform));
                    }
                  }}
                />
                {platform.charAt(0).toUpperCase() + platform.slice(1)}
              </label>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <label>Date Range</label>
          <div className="date-range">
            <input
              type="date"
              onChange={(e) => handleFilterChange('date_from', new Date(e.target.value))}
            />
            <span>to</span>
            <input
              type="date"
              onChange={(e) => handleFilterChange('date_to', new Date(e.target.value))}
            />
          </div>
        </div>

        <div className="filter-group">
          <label>Content Type</label>
          <div className="checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={filters.has_attachments || false}
                onChange={(e) => handleFilterChange('has_attachments', e.target.checked)}
              />
              Has Attachments
            </label>
          </div>
        </div>

        <div className="filter-group">
          <label>Entity Types</label>
          <div className="checkbox-group">
            {['person', 'organization', 'task', 'commitment', 'file', 'topic'].map(entityType => (
              <label key={entityType} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={filters.entity_types?.includes(entityType) || false}
                  onChange={(e) => {
                    const entityTypes = filters.entity_types || [];
                    if (e.target.checked) {
                      handleFilterChange('entity_types', [...entityTypes, entityType]);
                    } else {
                      handleFilterChange('entity_types', entityTypes.filter(t => t !== entityType));
                    }
                  }}
                />
                {entityType.charAt(0).toUpperCase() + entityType.slice(1)}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="query-preview">
        <h3>Natural Language Query</h3>
        <div className="query-text">
          {buildNaturalLanguageQuery() || 'Build your search criteria above...'}
        </div>
      </div>

      <div className="search-actions">
        <button onClick={handleSearch} className="search-button">
          Search
        </button>
        <button onClick={() => setFilters({})} className="clear-button">
          Clear All
        </button>
      </div>
    </div>
  );
};
```

### 4. Real-Time WebSocket Integration

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';
import { useAuth } from './useAuth';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const { token } = useAuth();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  const connect = () => {
    if (!token) return;

    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
    ws.current = new WebSocket(`${wsUrl}?token=${token}`);

    ws.current.onopen = () => {
      setIsConnected(true);
      reconnectAttempts.current = 0;
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);
      handleMessage(message);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
      
      // Attempt to reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, Math.pow(2, reconnectAttempts.current) * 1000);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'contact_update':
        // Handle contact updates
        window.dispatchEvent(new CustomEvent('contactUpdate', { detail: message.data }));
        break;
      case 'message_received':
        // Handle new messages
        window.dispatchEvent(new CustomEvent('messageReceived', { detail: message.data }));
        break;
      case 'insight_notification':
        // Handle proactive insights
        window.dispatchEvent(new CustomEvent('insightNotification', { detail: message.data }));
        break;
    }
  };

  const sendMessage = (type: string, data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type, data }));
    }
  };

  useEffect(() => {
    if (token) {
      connect();
    }

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  return {
    isConnected,
    lastMessage,
    sendMessage
  };
};
```

### 5. Progressive Web App Features

```typescript
// src/services/pwa/ServiceWorkerManager.ts
export class ServiceWorkerManager {
  async register(): Promise<ServiceWorkerRegistration | null> {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('Service Worker registered:', registration);
        return registration;
      } catch (error) {
        console.error('Service Worker registration failed:', error);
        return null;
      }
    }
    return null;
  }

  async requestNotificationPermission(): Promise<boolean> {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  }

  showNotification(title: string, options: NotificationOptions = {}) {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/badge-72x72.png',
        ...options
      });
    }
  }

  async installPrompt(): Promise<boolean> {
    const deferredPrompt = (window as any).deferredPrompt;
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      return outcome === 'accepted';
    }
    return false;
  }
}
```

### 6. Offline Storage with IndexedDB

```typescript
// src/services/storage/IndexedDBStorage.ts
import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { UnifiedContact } from '../../types/contacts';

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
  messages: {
    key: string;
    value: any;
    indexes: {
      'by-thread': string;
      'by-sender': string;
      'by-timestamp': Date;
    };
  };
  searchCache: {
    key: string;
    value: {
      query: string;
      results: any[];
      timestamp: Date;
      expiresAt: Date;
    };
  };
}

export class IndexedDBStorage {
  private db: IDBPDatabase<REMIDatabase> | null = null;

  async initialize(): Promise<void> {
    this.db = await openDB<REMIDatabase>('remi-db', 1, {
      upgrade(db) {
        // Contacts store
        const contactsStore = db.createObjectStore('contacts', { keyPath: 'id' });
        contactsStore.createIndex('by-name', 'primaryName');
        contactsStore.createIndex('by-platform', 'platforms', { multiEntry: true });
        contactsStore.createIndex('by-last-interaction', 'lastInteraction');

        // Messages store
        const messagesStore = db.createObjectStore('messages', { keyPath: 'id' });
        messagesStore.createIndex('by-thread', 'threadId');
        messagesStore.createIndex('by-sender', 'sender.id');
        messagesStore.createIndex('by-timestamp', 'timestamp');

        // Search cache store
        db.createObjectStore('searchCache', { keyPath: 'query' });
      },
    });
  }

  async cacheContacts(contacts: UnifiedContact[]): Promise<void> {
    if (!this.db) return;

    const tx = this.db.transaction('contacts', 'readwrite');
    const store = tx.objectStore('contacts');

    await Promise.all(contacts.map(contact => store.put(contact)));
    await tx.done;
  }

  async searchCachedContacts(query: string, limit = 50): Promise<UnifiedContact[]> {
    if (!this.db) return [];

    const tx = this.db.transaction('contacts', 'readonly');
    const store = tx.objectStore('contacts');
    const index = store.index('by-name');

    const results: UnifiedContact[] = [];
    const lowerQuery = query.toLowerCase();

    for await (const cursor of index.iterate()) {
      if (cursor.value.primaryName.toLowerCase().includes(lowerQuery) ||
          cursor.value.displayName.toLowerCase().includes(lowerQuery)) {
        results.push(cursor.value);
        if (results.length >= limit) break;
      }
    }

    return results;
  }

  async cacheSearchResults(query: string, results: any[], ttl = 300000): Promise<void> {
    if (!this.db) return;

    const cacheEntry = {
      query,
      results,
      timestamp: new Date(),
      expiresAt: new Date(Date.now() + ttl)
    };

    await this.db.put('searchCache', cacheEntry);
  }

  async getCachedSearchResults(query: string): Promise<any[] | null> {
    if (!this.db) return null;

    const cached = await this.db.get('searchCache', query);
    if (cached && cached.expiresAt > new Date()) {
      return cached.results;
    }

    return null;
  }
}
```

## API Integration

### API Client with Interceptors

```typescript
// src/services/api/client.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('auth_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);
```

## Testing

### Unit Tests with Jest and React Testing Library

```typescript
// src/components/search/__tests__/ContactSearchBar.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContactSearchBar } from '../ContactSearchBar';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('ContactSearchBar', () => {
  const mockOnContactSelect = jest.fn();

  beforeEach(() => {
    mockOnContactSelect.mockClear();
  });

  test('renders search input', () => {
    renderWithProviders(
      <ContactSearchBar onContactSelect={mockOnContactSelect} />
    );
    
    expect(screen.getByPlaceholderText(/search contacts/i)).toBeInTheDocument();
  });

  test('shows suggestions when typing', async () => {
    renderWithProviders(
      <ContactSearchBar onContactSelect={mockOnContactSelect} />
    );
    
    const input = screen.getByPlaceholderText(/search contacts/i);
    fireEvent.change(input, { target: { value: 'John' } });

    await waitFor(() => {
      expect(screen.getByText(/searching/i)).toBeInTheDocument();
    });
  });

  test('calls onContactSelect when suggestion is clicked', async () => {
    const mockContact = {
      id: '1',
      displayName: 'John Smith',
      primaryName: 'John Smith',
      platforms: ['gmail'],
      lastInteraction: new Date()
    };

    // Mock the API response
    jest.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [mockContact],
    } as Response);

    renderWithProviders(
      <ContactSearchBar onContactSelect={mockOnContactSelect} />
    );
    
    const input = screen.getByPlaceholderText(/search contacts/i);
    fireEvent.change(input, { target: { value: 'John' } });

    await waitFor(() => {
      const suggestion = screen.getByText('John Smith');
      fireEvent.click(suggestion);
    });

    expect(mockOnContactSelect).toHaveBeenCalledWith(mockContact);
  });
});
```

### E2E Tests with Playwright

```typescript
// tests/e2e/contact-search.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Contact Search', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[data-testid=email]', 'test@example.com');
    await page.fill('[data-testid=password]', 'password');
    await page.click('[data-testid=login-button]');
    await page.waitForURL('/dashboard');
  });

  test('should search for contacts and display results', async ({ page }) => {
    await page.goto('/search');
    
    await page.fill('[data-testid=contact-search-input]', 'John');
    
    await expect(page.locator('[data-testid=contact-suggestions]')).toBeVisible();
    await expect(page.locator('[data-testid=contact-suggestion]').first()).toBeVisible();
  });

  test('should use voice search', async ({ page }) => {
    await page.goto('/search');
    
    // Grant microphone permission
    await page.context().grantPermissions(['microphone']);
    
    await page.click('[data-testid=voice-search-button]');
    await expect(page.locator('[data-testid=voice-indicator]')).toBeVisible();
  });

  test('should navigate to contact profile', async ({ page }) => {
    await page.goto('/search');
    await page.fill('[data-testid=contact-search-input]', 'John');
    await page.waitForSelector('[data-testid=contact-suggestion]');
    
    await page.click('[data-testid=contact-suggestion]');
    
    await expect(page.locator('[data-testid=contact-profile]')).toBeVisible();
  });
});
```

## Build and Deployment

### Development Scripts

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test",
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "type-check": "tsc --noEmit",
    "analyze": "ANALYZE=true npm run build"
  }
}
```

### Production Build Configuration

```typescript
// next.config.js
const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
});

module.exports = withPWA({
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    appDir: true,
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
});
```

### Deployment to Vercel/Netlify

```bash
# Build for production
npm run build

# Deploy to Vercel
vercel --prod

# Deploy to Netlify
netlify deploy --prod --dir=out
```

## Environment Configuration

### Development Environment

```bash
# .env.local
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENVIRONMENT=development
NEXT_PUBLIC_GA_ID=your-ga-id
```

### Production Environment

```bash
# .env.production
REACT_APP_API_URL=https://api.remi.com
REACT_APP_WS_URL=wss://api.remi.com/ws
REACT_APP_ENVIRONMENT=production
NEXT_PUBLIC_GA_ID=your-production-ga-id
```

## Getting Started Checklist

- [ ] Clone repository and install dependencies
- [ ] Set up development environment
- [ ] Configure environment variables
- [ ] Run the development server
- [ ] Test contact search functionality
- [ ] Verify API connectivity with backend
- [ ] Test voice search and advanced filters
- [ ] Test PWA features (offline, install prompt)
- [ ] Run unit tests and E2E tests

This web application development guide provides everything needed to build a production-ready Progressive Web App with advanced contact-based auto-search capabilities that integrates seamlessly with the R.E.M.I backend system.