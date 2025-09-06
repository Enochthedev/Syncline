# R.E.M.I Frontend Development Guide

## Overview

This document provides comprehensive guidance for building mobile and web frontend applications that integrate with the R.E.M.I (Real-time External Memory Interface) backend system. It includes API endpoints, page structures, user flows, and implementation examples.

## Table of Contents

1. [API Integration](#api-integration)
2. [Authentication & Authorization](#authentication--authorization)
3. [Core Application Pages](#core-application-pages)
4. [Mobile App Structure](#mobile-app-structure)
5. [Web App Structure](#web-app-structure)
6. [Real-time Features](#real-time-features)
7. [State Management](#state-management)
8. [Error Handling](#error-handling)
9. [Performance Optimization](#performance-optimization)
10. [Testing Strategy](#testing-strategy)

## API Integration

### Base Configuration

```typescript
// API Configuration
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

### Core API Endpoints

#### Authentication Endpoints
```typescript
// Authentication API
const authAPI = {
  // Login with email/password
  login: 'POST /api/v1/auth/login',
  
  // Register new user
  register: 'POST /api/v1/auth/register',
  
  // Refresh JWT token
  refresh: 'POST /api/v1/auth/refresh',
  
  // Logout
  logout: 'POST /api/v1/auth/logout',
  
  // Get current user profile
  profile: 'GET /api/v1/auth/me',
  
  // Update user profile
  updateProfile: 'PUT /api/v1/auth/me'
};
```

#### Platform Connection Endpoints
```typescript
// Platform Integration API
const platformAPI = {
  // List connected platforms
  listConnections: 'GET /api/v1/platforms/',
  
  // Connect Gmail
  connectGmail: 'POST /api/v1/platforms/gmail/connect',
  gmailCallback: 'GET /api/v1/platforms/gmail/callback',
  
  // Connect Yahoo Mail
  connectYahoo: 'POST /api/v1/platforms/yahoo/connect',
  
  // Connect Slack
  connectSlack: 'POST /api/v1/platforms/slack/connect',
  slackCallback: 'GET /api/v1/platforms/slack/callback',
  
  // Connect Discord
  connectDiscord: 'POST /api/v1/platforms/discord/connect',
  
  // Connect WhatsApp (via Matrix)
  connectWhatsApp: 'POST /api/v1/platforms/whatsapp/connect',
  whatsappQR: 'GET /api/v1/platforms/whatsapp/qr',
  
  // Disconnect platform
  disconnect: 'DELETE /api/v1/platforms/{platform}',
  
  // Get platform status
  status: 'GET /api/v1/platforms/{platform}/status'
};
```

#### Message & Search Endpoints
```typescript
// Message and Search API
const messageAPI = {
  // Search messages across platforms
  search: 'POST /api/v1/search/',
  
  // Get message threads
  getThreads: 'GET /api/v1/threads/',
  getThread: 'GET /api/v1/threads/{thread_id}',
  
  // Get messages
  getMessages: 'GET /api/v1/messages/',
  getMessage: 'GET /api/v1/messages/{message_id}',
  
  // Get participants/contacts
  getParticipants: 'GET /api/v1/participants/',
  getParticipant: 'GET /api/v1/participants/{participant_id}',
  
  // Get contact dossiers
  getContactDossiers: 'GET /api/v1/contacts/dossiers/',
  getContactDossier: 'GET /api/v1/contacts/dossiers/{contact_id}',
  
  // Get summaries
  getSummaries: 'GET /api/v1/summaries/',
  getSummary: 'GET /api/v1/summaries/{summary_id}',
  
  // Get proactive insights
  getInsights: 'GET /api/v1/insights/',
  getNudges: 'GET /api/v1/insights/nudges/',
  
  // File tracking
  getSharedFiles: 'GET /api/v1/files/shared/',
  getFilesByContact: 'GET /api/v1/files/shared/{contact_id}'
};
```

#### System & Health Endpoints
```typescript
// System API
const systemAPI = {
  // Health check
  health: 'GET /api/v1/health/',
  
  // System statistics
  stats: 'GET /api/v1/stats/',
  
  // Platform statistics
  platformStats: 'GET /api/v1/stats/platforms/',
  
  // User settings
  getSettings: 'GET /api/v1/settings/',
  updateSettings: 'PUT /api/v1/settings/'
};
```

## Authentication & Authorization

### JWT Token Management

```typescript
// Token Management Service
class TokenService {
  private static readonly ACCESS_TOKEN_KEY = 'remi_access_token';
  private static readonly REFRESH_TOKEN_KEY = 'remi_refresh_token';

  static setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
  }

  static getAccessToken(): string | null {
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  static clearTokens(): void {
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
  }

  static isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }
}
```

### Authentication Flow

```typescript
// Authentication Service
class AuthService {
  async login(email: string, password: string): Promise<User> {
    const response = await fetch(`${API_CONFIG.baseURL}/api/v1/auth/login`, {
      method: 'POST',
      headers: API_CONFIG.headers,
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    TokenService.setTokens(data.access_token, data.refresh_token);
    
    return data.user;
  }

  async refreshToken(): Promise<string> {
    const refreshToken = TokenService.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${API_CONFIG.baseURL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: API_CONFIG.headers,
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (!response.ok) {
      TokenService.clearTokens();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    TokenService.setTokens(data.access_token, data.refresh_token);
    
    return data.access_token;
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_CONFIG.baseURL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          ...API_CONFIG.headers,
          'Authorization': `Bearer ${TokenService.getAccessToken()}`
        }
      });
    } finally {
      TokenService.clearTokens();
    }
  }
}
```

## Core Application Pages

### 1. Dashboard Page

**Purpose**: Main overview of user's communication activity and insights

**Key Components**:
- Platform connection status
- Recent message summary
- Proactive nudges and reminders
- Quick search bar
- Activity timeline

**API Calls**:
```typescript
// Dashboard Data Loading
const loadDashboardData = async () => {
  const [platforms, insights, recentMessages, stats] = await Promise.all([
    fetch('/api/v1/platforms/'),
    fetch('/api/v1/insights/'),
    fetch('/api/v1/messages/?limit=10&sort=recent'),
    fetch('/api/v1/stats/')
  ]);
  
  return {
    platforms: await platforms.json(),
    insights: await insights.json(),
    recentMessages: await recentMessages.json(),
    stats: await stats.json()
  };
};
```

**Page Actions**:
- Connect new platforms
- View recent activity
- Act on nudges/reminders
- Quick search
- Navigate to detailed views

### 2. Search Page

**Purpose**: Advanced search across all connected platforms

**Key Components**:
- Search input with filters
- Platform selector
- Date range picker
- Search results list
- Faceted search filters
- Search suggestions

**API Calls**:
```typescript
// Search Implementation
const performSearch = async (query: string, filters: SearchFilters) => {
  const searchRequest = {
    query,
    platforms: filters.platforms,
    date_range: filters.dateRange,
    limit: filters.limit || 20,
    offset: filters.offset || 0,
    sort: filters.sort || 'relevance'
  };

  const response = await fetch('/api/v1/search/', {
    method: 'POST',
    headers: {
      ...API_CONFIG.headers,
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    },
    body: JSON.stringify(searchRequest)
  });

  return await response.json();
};
```

**Page Actions**:
- Enter search queries
- Apply filters
- View search results
- Navigate to message details
- Save searches
- Export results

### 3. Messages Page

**Purpose**: Browse and manage messages by thread or platform

**Key Components**:
- Message thread list
- Message detail view
- Platform filter tabs
- Thread participants
- Message attachments
- AI-generated summaries

**API Calls**:
```typescript
// Message Thread Loading
const loadMessageThreads = async (platform?: string, limit = 50) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    ...(platform && { platform })
  });

  const response = await fetch(`/api/v1/threads/?${params}`, {
    headers: {
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    }
  });

  return await response.json();
};

// Individual Thread Loading
const loadThread = async (threadId: string) => {
  const response = await fetch(`/api/v1/threads/${threadId}`, {
    headers: {
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    }
  });

  return await response.json();
};
```

**Page Actions**:
- Browse message threads
- Filter by platform
- View thread details
- Read AI summaries
- Download attachments
- Mark as important

### 4. Contacts Page

**Purpose**: Manage contacts and view relationship insights

**Key Components**:
- Contact list with search
- Contact detail cards
- Communication history
- AI-generated dossiers
- Relationship insights
- Shared files tracking

**API Calls**:
```typescript
// Contact Management
const loadContacts = async () => {
  const response = await fetch('/api/v1/participants/', {
    headers: {
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    }
  });

  return await response.json();
};

const loadContactDossier = async (contactId: string) => {
  const response = await fetch(`/api/v1/contacts/dossiers/${contactId}`, {
    headers: {
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    }
  });

  return await response.json();
};
```

**Page Actions**:
- Browse contacts
- View contact details
- Read AI dossiers
- See communication patterns
- Track shared files
- Set contact preferences

### 5. Insights Page

**Purpose**: AI-powered insights and proactive suggestions

**Key Components**:
- Proactive nudges list
- Follow-up reminders
- Communication patterns
- Relationship insights
- Action item tracking
- Weekly/monthly summaries

**API Calls**:
```typescript
// Insights Loading
const loadInsights = async () => {
  const [nudges, summaries, patterns] = await Promise.all([
    fetch('/api/v1/insights/nudges/'),
    fetch('/api/v1/summaries/?type=weekly'),
    fetch('/api/v1/insights/patterns/')
  ]);

  return {
    nudges: await nudges.json(),
    summaries: await summaries.json(),
    patterns: await patterns.json()
  };
};
```

**Page Actions**:
- Review nudges
- Act on reminders
- View summaries
- Analyze patterns
- Configure insight preferences

### 6. Settings Page

**Purpose**: Configure platforms, preferences, and account settings

**Key Components**:
- Platform connections management
- Notification preferences
- Privacy settings
- Data retention options
- AI processing preferences
- Account management

**API Calls**:
```typescript
// Settings Management
const loadSettings = async () => {
  const response = await fetch('/api/v1/settings/', {
    headers: {
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    }
  });

  return await response.json();
};

const updateSettings = async (settings: UserSettings) => {
  const response = await fetch('/api/v1/settings/', {
    method: 'PUT',
    headers: {
      ...API_CONFIG.headers,
      'Authorization': `Bearer ${TokenService.getAccessToken()}`
    },
    body: JSON.stringify(settings)
  });

  return await response.json();
};
```

**Page Actions**:
- Connect/disconnect platforms
- Update preferences
- Manage privacy settings
- Configure notifications
- Export data
- Delete account

## Mobile App Structure

### React Native Implementation

```typescript
// App.tsx - Main App Structure
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';

// Screens
import DashboardScreen from './screens/DashboardScreen';
import SearchScreen from './screens/SearchScreen';
import MessagesScreen from './screens/MessagesScreen';
import ContactsScreen from './screens/ContactsScreen';
import InsightsScreen from './screens/InsightsScreen';
import SettingsScreen from './screens/SettingsScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

const MainTabs = () => (
  <Tab.Navigator>
    <Tab.Screen name="Dashboard" component={DashboardScreen} />
    <Tab.Screen name="Search" component={SearchScreen} />
    <Tab.Screen name="Messages" component={MessagesScreen} />
    <Tab.Screen name="Contacts" component={ContactsScreen} />
    <Tab.Screen name="Insights" component={InsightsScreen} />
    <Tab.Screen name="Settings" component={SettingsScreen} />
  </Tab.Navigator>
);

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Main" component={MainTabs} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

### Key Mobile Features

1. **Push Notifications**
   - New message alerts
   - Proactive nudges
   - System status updates

2. **Offline Support**
   - Cache recent messages
   - Queue search queries
   - Sync when online

3. **Biometric Authentication**
   - Fingerprint/Face ID
   - Secure token storage

4. **Background Sync**
   - Periodic data refresh
   - Real-time updates

## Web App Structure

### React Implementation

```typescript
// App.tsx - Web App Structure
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';

// Pages
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Messages from './pages/Messages';
import Contacts from './pages/Contacts';
import Insights from './pages/Insights';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<Search />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/messages/:threadId" element={<MessageThread />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/contacts/:contactId" element={<ContactDetail />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  );
}
```

### Key Web Features

1. **Responsive Design**
   - Desktop, tablet, mobile layouts
   - Progressive Web App (PWA)

2. **Keyboard Shortcuts**
   - Quick search (Ctrl+K)
   - Navigation shortcuts
   - Accessibility support

3. **Advanced Search**
   - Complex query builder
   - Saved searches
   - Export functionality

4. **Multi-tab Support**
   - Persistent state
   - Cross-tab communication

## Real-time Features

### WebSocket Integration

```typescript
// WebSocket Service
class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private listeners: Map<string, Function[]> = new Map();

  connect(): void {
    const token = TokenService.getAccessToken();
    this.ws = new WebSocket(`${WS_CONFIG.url}?token=${token}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.reconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleMessage(data: any): void {
    const { type, payload } = data;
    const listeners = this.listeners.get(type) || [];
    listeners.forEach(listener => listener(payload));
  }

  subscribe(eventType: string, callback: Function): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  private reconnect(): void {
    if (this.reconnectAttempts < WS_CONFIG.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, WS_CONFIG.reconnectInterval);
    }
  }
}
```

### Real-time Event Types

```typescript
// WebSocket Event Types
interface WebSocketEvents {
  // New message received
  'message.new': {
    messageId: string;
    platform: string;
    sender: string;
    preview: string;
    threadId: string;
  };

  // Search results streaming
  'search.result': {
    queryId: string;
    result: SearchResult;
    isComplete: boolean;
  };

  // Proactive nudge
  'insight.nudge': {
    type: 'follow_up' | 'reminder' | 'suggestion';
    title: string;
    description: string;
    actionUrl?: string;
  };

  // Platform status update
  'platform.status': {
    platform: string;
    status: 'connected' | 'disconnected' | 'error';
    message?: string;
  };

  // Processing status
  'processing.status': {
    type: 'message_processing' | 'ai_analysis' | 'indexing';
    status: 'started' | 'completed' | 'failed';
    progress?: number;
  };
}
```

## State Management

### Redux Toolkit Implementation

```typescript
// store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import messagesSlice from './slices/messagesSlice';
import searchSlice from './slices/searchSlice';
import platformsSlice from './slices/platformsSlice';
import insightsSlice from './slices/insightsSlice';

export const store = configureStore({
  reducer: {
    auth: authSlice,
    messages: messagesSlice,
    search: searchSlice,
    platforms: platformsSlice,
    insights: insightsSlice,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### Auth Slice Example

```typescript
// store/slices/authSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

export const loginUser = createAsyncThunk(
  'auth/login',
  async ({ email, password }: { email: string; password: string }) => {
    const authService = new AuthService();
    return await authService.login(email, password);
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    isAuthenticated: false,
    loading: false,
    error: null,
  } as AuthState,
  reducers: {
    logout: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      TokenService.clearTokens();
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Login failed';
      });
  },
});

export const { logout, clearError } = authSlice.actions;
export default authSlice.reducer;
```

## Error Handling

### Global Error Handler

```typescript
// utils/errorHandler.ts
export class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public code?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export const handleAPIError = (error: any): APIError => {
  if (error.response) {
    // Server responded with error status
    return new APIError(
      error.response.status,
      error.response.data?.message || 'Server error',
      error.response.data?.code
    );
  } else if (error.request) {
    // Network error
    return new APIError(0, 'Network error - please check your connection');
  } else {
    // Other error
    return new APIError(0, error.message || 'Unknown error occurred');
  }
};

// Global error boundary component
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Log to error reporting service
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>Please refresh the page or contact support if the problem persists.</p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## Performance Optimization

### Data Fetching Strategies

```typescript
// hooks/useInfiniteScroll.ts
import { useState, useEffect, useCallback } from 'react';

export const useInfiniteScroll = <T>(
  fetchFunction: (offset: number, limit: number) => Promise<T[]>,
  limit = 20
) => {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    try {
      const newData = await fetchFunction(offset, limit);
      
      if (newData.length < limit) {
        setHasMore(false);
      }

      setData(prev => [...prev, ...newData]);
      setOffset(prev => prev + limit);
    } catch (error) {
      console.error('Error loading more data:', error);
    } finally {
      setLoading(false);
    }
  }, [fetchFunction, offset, limit, loading, hasMore]);

  return { data, loading, hasMore, loadMore };
};
```

### Caching Strategy

```typescript
// utils/cache.ts
class CacheManager {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>();

  set(key: string, data: any, ttl = 300000): void { // 5 minutes default
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    });
  }

  get(key: string): any | null {
    const item = this.cache.get(key);
    
    if (!item) return null;
    
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  clear(): void {
    this.cache.clear();
  }

  delete(key: string): void {
    this.cache.delete(key);
  }
}

export const cacheManager = new CacheManager();
```

## Testing Strategy

### Component Testing

```typescript
// __tests__/components/SearchBar.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SearchBar } from '../components/SearchBar';

describe('SearchBar', () => {
  const mockOnSearch = jest.fn();

  beforeEach(() => {
    mockOnSearch.mockClear();
  });

  test('renders search input', () => {
    render(<SearchBar onSearch={mockOnSearch} />);
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  test('calls onSearch when form is submitted', async () => {
    render(<SearchBar onSearch={mockOnSearch} />);
    
    const input = screen.getByPlaceholderText(/search/i);
    const submitButton = screen.getByRole('button', { name: /search/i });

    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('test query');
    });
  });
});
```

### API Testing

```typescript
// __tests__/services/authService.test.ts
import { AuthService } from '../services/authService';
import { TokenService } from '../services/tokenService';

// Mock fetch
global.fetch = jest.fn();

describe('AuthService', () => {
  const authService = new AuthService();

  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
    TokenService.clearTokens();
  });

  test('login success', async () => {
    const mockResponse = {
      user: { id: '1', email: 'test@example.com' },
      access_token: 'access_token',
      refresh_token: 'refresh_token'
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    const user = await authService.login('test@example.com', 'password');

    expect(user).toEqual(mockResponse.user);
    expect(TokenService.getAccessToken()).toBe('access_token');
    expect(TokenService.getRefreshToken()).toBe('refresh_token');
  });
});
```

### E2E Testing

```typescript
// e2e/search.spec.ts (Playwright)
import { test, expect } from '@playwright/test';

test.describe('Search functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[data-testid=email]', 'test@example.com');
    await page.fill('[data-testid=password]', 'password');
    await page.click('[data-testid=login-button]');
    await page.waitForURL('/dashboard');
  });

  test('should perform search and display results', async ({ page }) => {
    await page.goto('/search');
    
    await page.fill('[data-testid=search-input]', 'test query');
    await page.click('[data-testid=search-button]');
    
    await expect(page.locator('[data-testid=search-results]')).toBeVisible();
    await expect(page.locator('[data-testid=search-result-item]')).toHaveCount.greaterThan(0);
  });
});
```

## Deployment Considerations

### Environment Configuration

```typescript
// config/environment.ts
export const config = {
  development: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws',
    enableDevTools: true,
    logLevel: 'debug'
  },
  staging: {
    apiUrl: 'https://staging-api.remi.com',
    wsUrl: 'wss://staging-api.remi.com/ws',
    enableDevTools: false,
    logLevel: 'info'
  },
  production: {
    apiUrl: 'https://api.remi.com',
    wsUrl: 'wss://api.remi.com/ws',
    enableDevTools: false,
    logLevel: 'error'
  }
};
```

### Build Optimization

```json
// package.json build scripts
{
  "scripts": {
    "build": "react-scripts build",
    "build:analyze": "npm run build && npx webpack-bundle-analyzer build/static/js/*.js",
    "build:staging": "REACT_APP_ENV=staging npm run build",
    "build:production": "REACT_APP_ENV=production npm run build"
  }
}
```

This comprehensive frontend guide provides the foundation for building robust mobile and web applications that integrate seamlessly with the R.E.M.I backend system. The modular architecture, comprehensive error handling, and performance optimizations ensure a scalable and maintainable codebase.