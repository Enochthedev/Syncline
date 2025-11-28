# 🚀 Platform Connection & Mobile Frontend Guide

**Quick Start Guide for Connecting Social Media Platforms and Building Mobile App**

---

## 📱 Overview: How Platform Connections Work

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Mobile App    │──────▶│  Backend API    │◀─────│  Social Media   │
│   (Expo/RN)     │ HTTP  │  (localhost     │OAuth │  Platforms      │
│                 │       │   :8000)        │      │  (Gmail, Slack) │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                         │                          │
        │   1. User taps          │   2. Backend creates     │
        │   "Connect Gmail"       │   OAuth URL              │
        │                         │                          │
        │   ◀───returns OAuth URL─┤   3. User authorizes    │
        │                         │                          │
        │   4. Opens browser──────┼────────────────────────▶ │
        │                         │                          │
        │   ◀────callback code────┼──────callback URL───────┘
        │                         │
        │   5. Sends code to      │
        │   backend              │
        │                         │
        │   6. Backend exchanges  │
        │   code for tokens      │
        │                         │
        │   7. Platform connected!│
        └─────────────────────────┘
```

---

## 🔌 Step 1: Connect Social Media Platforms

### Platform Connection Flow (Backend API)

The backend provides these endpoints for platform connections:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/connections/{platform}/initiate` | POST | Start OAuth flow |
| `/api/v1/connections/{platform}/callback` | GET | OAuth callback |
| `/api/v1/connections` | GET | List user's connections |
| `/api/v1/connections/{id}/disconnect` | DELETE | Disconnect platform |
| `/api/v1/connections/{id}/health` | GET | Check connection health |

### Supported Platforms

| Platform | Status | Auth Type | Setup Required |
|----------|--------|-----------|----------------|
| **Gmail** | ✅ Ready | OAuth 2.0 | Google Cloud Console |
| **Slack** | ✅ Ready | OAuth 2.0 | Slack App |
| **Discord** | ✅ Ready | Bot Token | Discord Developer Portal |
| **Telegram** | ✅ Ready | Bot Token | @BotFather |
| **Twitter/X** | ✅ Ready | OAuth 2.0 | Twitter Developer Portal |
| **WhatsApp** | ✅ Ready | Matrix Bridge | Matrix Homeserver |
| **Yahoo Mail** | ✅ Ready | IMAP | App Password |

---

## 🔧 Step 2: Get Platform Credentials

### Quick Setup for Each Platform

#### 1️⃣ **Gmail** (Most Common)

```bash
# 1. Go to Google Cloud Console
https://console.cloud.google.com/

# 2. Create/select project → Enable Gmail API

# 3. Create OAuth 2.0 credentials
# - Authorized redirect URI: http://localhost:8000/api/v1/connections/gmail/callback

# 4. Add to .env
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
```

**Detailed Guide**: `apps/backend/API_KEYS_GUIDE.md` (lines 19-44)

---

#### 2️⃣ **Slack**

```bash
# 1. Go to Slack API
https://api.slack.com/apps

# 2. Create New App → From scratch

# 3. Get credentials from "Basic Information"
SLACK_CLIENT_ID=...
SLACK_CLIENT_SECRET=...
SLACK_SIGNING_SECRET=...

# 4. Install to workspace for tokens
SLACK_BOT_TOKEN=xoxb-...
SLACK_USER_TOKEN=xoxp-...
```

**Required Scopes**: `channels:history`, `channels:read`, `chat:write`, `users:read`

---

#### 3️⃣ **Discord**

```bash
# 1. Go to Discord Developer Portal
https://discord.com/developers/applications

# 2. Create Application → Add Bot

# 3. Copy credentials
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret

# 4. Enable intents:
# - Message Content Intent
# - Server Members Intent
```

---

#### 4️⃣ **Telegram** (Simplest!)

```bash
# 1. Open Telegram → Search @BotFather

# 2. Send /newbot command

# 3. Follow prompts and copy token
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

---

#### 5️⃣ **Twitter/X**

```bash
# 1. Go to Twitter Developer Portal
https://developer.twitter.com/en/portal/dashboard

# 2. Create project and app

# 3. Generate keys
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
X_BEARER_TOKEN=...
```

---

## 📲 Step 3: Build Mobile Frontend

### Option A: React Native (Expo) - Recommended

Since there's no existing `apps/mobile/` directory, let's create it:

```bash
# 1. Navigate to apps directory
cd /Users/user/Code/Syncline/apps

# 2. Create Expo app
npx create-expo-app mobile --template blank-typescript

# 3. Navigate to mobile app
cd mobile

# 4. Install dependencies
npm install axios @react-navigation/native @react-navigation/stack
npm install react-native-safe-area-context react-native-screens

# 5. Run on iOS simulator
npm run ios

# OR run on Android
npm run android
```

---

### Mobile App Structure

```
apps/mobile/
├── App.tsx                   # Main app entry
├── app.json                  # Expo config
├── package.json
├── src/
│   ├── api/
│   │   ├── client.ts         # Axios HTTP client
│   │   └── endpoints/
│   │       ├── connections.ts  # Platform connections
│   │       ├── messages.ts     # Message queries
│   │       └── auth.ts         # Authentication
│   ├── screens/
│   │   ├── HomeScreen.tsx
│   │   ├── ConnectionsScreen.tsx
│   │   ├── MessagesScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── components/
│   │   ├── PlatformCard.tsx
│   │   ├── MessageList.tsx
│   │   └── SearchBar.tsx
│   ├── navigation/
│   │   └── AppNavigator.tsx
│   └── types/
│       └── index.ts
└── tsconfig.json
```

---

## 🎨 Step 4: Implement Platform Connection in Mobile App

### 4.1: API Client Setup

Create `src/api/client.ts`:

```typescript
import axios from 'axios';

const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000/api/v1'  // Development
  : 'https://your-production-url.com/api/v1';  // Production

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = getAuthToken(); // Implement token storage
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

### 4.2: Platform Connection Service

Create `src/api/endpoints/connections.ts`:

```typescript
import { apiClient } from '../client';
import { Platform } from '../../types';

export interface InitiateConnectionRequest {
  user_id: string;
  redirect_uri?: string;
}

export interface ConnectionResponse {
  id: string;
  platform: string;
  status: 'active' | 'pending' | 'error';
  authorization_url?: string;
  created_at: string;
}

export const connectionsAPI = {
  // Start OAuth flow
  initiateConnection: async (
    platform: Platform, 
    userId: string
  ): Promise<ConnectionResponse> => {
    const { data } = await apiClient.post(
      `/connections/${platform}/initiate`,
      { user_id: userId }
    );
    return data;
  },

  // List all connections
  listConnections: async (userId: string): Promise<ConnectionResponse[]> => {
    const { data } = await apiClient.get('/connections', {
      params: { user_id: userId }
    });
    return data.connections;
  },

  // Disconnect platform
  disconnectPlatform: async (connectionId: string): Promise<void> => {
    await apiClient.delete(`/connections/${connectionId}/disconnect`);
  },

  // Check connection health
  checkHealth: async (connectionId: string) => {
    const { data } = await apiClient.get(
      `/connections/${connectionId}/health`
    );
    return data;
  },
};
```

---

### 4.3: Connection Screen Component

Create `src/screens/ConnectionsScreen.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking } from 'react-native';
import { connectionsAPI } from '../api/endpoints/connections';

const PLATFORMS = [
  { id: 'gmail', name: 'Gmail', icon: '📧', color: '#EA4335' },
  { id: 'slack', name: 'Slack', icon: '💬', color: '#4A154B' },
  { id: 'discord', name: 'Discord', icon: '🎮', color: '#5865F2' },
  { id: 'telegram', name: 'Telegram', icon: '✈️', color: '#0088CC' },
  { id: 'twitter', name: 'Twitter/X', icon: '🐦', color: '#1DA1F2' },
];

export const ConnectionsScreen = () => {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleConnect = async (platform: string) => {
    try {
      setLoading(true);
      
      // 1. Initiate OAuth flow
      const response = await connectionsAPI.initiateConnection(
        platform,
        'current-user-id' // Replace with actual user ID
      );

      // 2. Open OAuth URL in browser
      if (response.authorization_url) {
        await Linking.openURL(response.authorization_url);
      }

      // 3. Poll for connection status
      // (In production, use deep linking callback)
      setTimeout(() => loadConnections(), 3000);

    } catch (error) {
      console.error('Connection failed:', error);
      alert('Failed to connect. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const loadConnections = async () => {
    try {
      const data = await connectionsAPI.listConnections('current-user-id');
      setConnections(data);
    } catch (error) {
      console.error('Failed to load connections:', error);
    }
  };

  useEffect(() => {
    loadConnections();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Connect Platforms</Text>
      
      {PLATFORMS.map((platform) => {
        const isConnected = connections.some(
          (conn) => conn.platform === platform.id && conn.status === 'active'
        );

        return (
          <TouchableOpacity
            key={platform.id}
            style={[
              styles.platformCard,
              { borderColor: platform.color }
            ]}
            onPress={() => handleConnect(platform.id)}
            disabled={loading || isConnected}
          >
            <Text style={styles.icon}>{platform.icon}</Text>
            <Text style={styles.platformName}>{platform.name}</Text>
            <Text style={styles.status}>
              {isConnected ? '✅ Connected' : '⚪ Connect'}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  platformCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    marginBottom: 12,
    borderRadius: 12,
    borderWidth: 2,
  },
  icon: {
    fontSize: 32,
    marginRight: 12,
  },
  platformName: {
    flex: 1,
    fontSize: 18,
    fontWeight: '600',
  },
  status: {
    fontSize: 14,
    color: '#666',
  },
});
```

---

## 🔄 Step 5: OAuth Deep Linking (Production)

For production mobile apps, implement deep linking to handle OAuth callbacks:

### 5.1: Configure Deep Linking

In `app.json`:

```json
{
  "expo": {
    "scheme": "syncline",
    "ios": {
      "bundleIdentifier": "com.syncline.app"
    },
    "android": {
      "package": "com.syncline.app"
    }
  }
}
```

### 5.2: Handle OAuth Callback

```typescript
import * as Linking from 'expo-linking';

// Listen for deep link
useEffect(() => {
  const subscription = Linking.addEventListener('url', handleDeepLink);
  return () => subscription.remove();
}, []);

const handleDeepLink = ({ url }: { url: string }) => {
  const { queryParams } = Linking.parse(url);
  
  if (queryParams?.code && queryParams?.state) {
    // Send code to backend to complete OAuth
    completeOAuthFlow(queryParams.code, queryParams.state);
  }
};
```

### 5.3: Update Backend Redirect URI

```bash
# In .env, add mobile deep link
GMAIL_REDIRECT_URI=syncline://oauth/callback
SLACK_REDIRECT_URI=syncline://oauth/callback
```

---

## 🧪 Step 6: Test the Flow

### Test Workflow:

1. **Start Backend**:
   ```bash
   cd /Users/user/Code/Syncline
   docker compose -f apps/backend/docker-compose.yml up -d
   cd apps/backend && python main.py
   ```

2. **Create Mobile App** (if not exists):
   ```bash
   cd apps
   npx create-expo-app mobile --template blank-typescript
   cd mobile
   npm install
   ```

3. **Test Connection** (using curl first):
   ```bash
   # Test Gmail connection initiation
   curl -X POST http://localhost:8000/api/v1/connections/gmail/initiate \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test-user-123"}'
   
   # Response will include authorization_url
   # Open URL in browser to complete OAuth
   ```

4. **Build Mobile UI**:
   - Implement ConnectionsScreen
   - Add API client
   - Test on simulator

5. **Connect a Platform**:
   - Tap "Connect Gmail" in mobile app
   - App opens browser with OAuth URL
   - User authorizes app
   - Callback returns to app
   - Connection shows as "Connected"

---

## 📊 Step 7: View Connected Messages

Once platforms are connected, messages will flow automatically:

### Message Query API:

```typescript
// src/api/endpoints/messages.ts
export const messagesAPI = {
  // List messages
  listMessages: async (filters?: {
    platform?: string;
    start_date?: string;
    end_date?: string;
  }) => {
    const { data } = await apiClient.get('/messages', { params: filters });
    return data;
  },

  // Search messages
  searchMessages: async (query: string) => {
    const { data } = await apiClient.get('/messages/search', {
      params: { query }
    });
    return data;
  },

  // AI semantic search
  semanticSearch: async (query: string) => {
    const { data } = await apiClient.post('/ai/search', { query });
    return data;
  },
};
```

---

## 🎯 Complete Example: Minimal Mobile App

Here's a complete minimal mobile app you can scaffold:

```bash
# Generate the app structure
cd /Users/user/Code/Syncline/apps
npx create-expo-app mobile --template blank-typescript

# Then create these files...
```

**Key Files to Create**:

1. `src/api/client.ts` - HTTP client config
2. `src/api/endpoints/connections.ts` - Connection API
3. `src/api/endpoints/messages.ts` - Messages API
4. `src/screens/ConnectionsScreen.tsx` - Connect platforms UI
5. `src/screens/MessagesScreen.tsx` - View messages UI
6. `App.tsx` - Navigation setup

---

## 🚦 Quick Start Commands

```bash
# Terminal 1: Start Backend
cd /Users/user/Code/Syncline
docker compose -f apps/backend/docker-compose.yml up -d
cd apps/backend && python main.py

# Terminal 2: Create & Run Mobile App
cd /Users/user/Code/Syncline/apps
npx create-expo-app mobile --template blank-typescript
cd mobile
npm install axios @react-navigation/native @react-navigation/stack
npm run ios  # or npm run android

# Terminal 3: Test Backend APIs
curl http://localhost:8000/health
curl http://localhost:8000/docs  # View API documentation
```

---

## ✅ Success Checklist

- [ ] Backend running at `http://localhost:8000`
- [ ] Platform credentials added to `.env` file
- [ ] Mobile app scaffolded with Expo
- [ ] API client configured in mobile app
- [ ] ConnectionsScreen implemented
- [ ] Test connection flow works
- [ ] Messages display in mobile app

---

## 🆘 Troubleshooting

### Backend not accessible from mobile
```bash
# Instead of localhost, use your machine's IP
# Find IP: ifconfig | grep "inet "
# Update API_BASE_URL to: http://192.168.x.x:8000
```

### OAuth callback not working
- Make sure redirect URI matches exactly in platform settings
- For mobile, implement deep linking (see Step 5)
- For development, use web-based OAuth flow first

### CORS errors
Backend already has CORS configured in `.env`:
```bash
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
# Add your mobile app origin if needed
```

---

## 📚 Next Steps

1. **Scaffold Mobile App** - Create the Expo app structure
2. **Implement Authentication** - Add JWT login flow
3. **Build Connection UI** - Create platform connection cards
4. **Test with One Platform** - Start with Telegram (simplest)
5. **Add Message Display** - Show connected messages
6. **Enhance with AI** - Add semantic search and insights

---

**Ready to start?** Let me know which platform you want to connect first, or if you want help scaffolding the mobile app!
