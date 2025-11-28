# 📱 Mobile App Scaffold - Quick Start

**Your Syncline mobile app is being created! Here's what to do next.**

---

## ✅ What's Happening Now

The command `npx create-expo-app mobile --template blank-typescript` is running and will create:

```
apps/mobile/
├── App.tsx              # Main entry point
├── app.json            # Expo configuration
├── package.json        # Dependencies
├── tsconfig.json       # TypeScript config
├── assets/             # Images, fonts
└── node_modules/       # Installed packages
```

---

## 🚀 Next Steps (Once created)

### 1. Install Additional Dependencies

```bash
cd apps/mobile

# Core navigation
npm install @react-navigation/native @react-navigation/stack @react-navigation/bottom-tabs

# Required dependencies for navigation
npm install react-native-screens react-native-safe-area-context

# HTTP client
npm install axios

# State management (optional)
npm install @tanstack/react-query

# UI components (optional but recommended)
npm install react-native-paper
```

---

### 2. Create API Client

**File: `src/api/client.ts`**

```typescript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Get your machine's IP address for local development
// Run: ifconfig | grep "inet " (on Mac)
const API_BASE_URL = __DEV__ 
  ? 'http://192.168.x.x:8000/api/v1'  // Replace with your IP!
  : 'https://your-production-url.com/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      AsyncStorage.removeItem('auth_token');
      // Navigate to login
    }
    return Promise.reject(error);
  }
);
```

---

### 3. Create API Endpoints

**File: `src/api/endpoints/connections.ts`**

```typescript
import { apiClient } from '../client';

export const connectionsAPI = {
  initiateConnection: async (platform: string, userId: string) => {
    const { data } = await apiClient.post(
      `/connections/${platform}/initiate`,
      { user_id: userId }
    );
    return data;
  },

  listConnections: async (userId: string) => {
    const { data } = await apiClient.get('/connections', {
      params: { user_id: userId }
    });
    return data;
  },

  disconnectPlatform: async (connectionId: string) => {
    await apiClient.delete(`/connections/${connectionId}/disconnect`);
  },
};
```

**File: `src/api/endpoints/ai.ts`**

```typescript
import { apiClient } from '../client';

export const aiAPI = {
  summarizeThread: async (
    threadId: string,
    type: 'brief' | 'detailed' | 'bullet_points' = 'brief'
  ) => {
    const { data } = await apiClient.post(`/ai/summarize/${threadId}`, {
      summary_type: type,
      force_regenerate: false
    });
    return data;
  },

  semanticSearch: async (query: string, filters?: any) => {
    const { data } = await apiClient.post('/ai/search', {
      query,
      ...filters,
      limit: 20
    });
    return data;
  },

  askAI: async (question: string) => {
    const { data } = await apiClient.post('/ai/ask', {
      question,
      limit: 10
    });
    return data;
  },

  getInsights: async (contactId: string, days: number = 30) => {
    const { data } = await apiClient.post(
      `/ai/insights/${contactId}`,
      null,
      { params: { days } }
    );
    return data;
  },
};
```

---

### 4. Create Navigation

**File: `src/navigation/AppNavigator.tsx`**

```typescript
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';

import HomeScreen from '../screens/HomeScreen';
import ConnectionsScreen from '../screens/ConnectionsScreen';
import MessagesScreen from '../screens/MessagesScreen';
import SearchScreen from '../screens/SearchScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

export const AppNavigator = () => {
  return (
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen 
          name="Home" 
          component={HomeScreen}
          options={{ tabBarIcon: () => '🏠' }}
        />
        <Tab.Screen 
          name="Connections" 
          component={ConnectionsScreen}
          options={{ tabBarIcon: () => '🔗' }}
        />
        <Tab.Screen 
          name="Messages" 
          component={MessagesScreen}
          options={{ tabBarIcon: () => '💬' }}
        />
        <Tab.Screen 
          name="Search" 
          component={SearchScreen}
          options={{ tabBarIcon: () => '🔍' }}
        />
        <Tab.Screen 
          name="Settings" 
          component={SettingsScreen}
          options={{ tabBarIcon: () => '⚙️' }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
};
```

---

### 5. Update App.tsx

```typescript
import { AppNavigator } from './src/navigation/AppNavigator';

export default function App() {
  return <AppNavigator />;
}
```

---

### 6. Create Basic Screens

Create these files in `src/screens/`:

- `HomeScreen.tsx` - Dashboard with stats
- `ConnectionsScreen.tsx` - Connect platforms (see PLATFORM_CONNECTION_GUIDE.md)
- `MessagesScreen.tsx` - List messages
- `SearchScreen.tsx` - Semantic search
- `SettingsScreen.tsx` - App settings

---

## 📊 How AI Features Work

Check the comprehensive guide: **`AI_FEATURES_GUIDE.md`**

### Quick Summary:

1. **Thread Summaries** 🤖
   - Endpoint: `POST /api/v1/ai/summarize/{thread_id}`
   - Generates: Brief/detailed/bullet summaries of conversations
   - Uses: Local Ollama LLM (llama3.2)
   - Cost: **FREE** (runs locally)

2. **Semantic Search** 🔍
   - Endpoint: `POST /api/v1/ai/search`
   - Finds: Messages by meaning, not just keywords
   - Uses: Vector embeddings in ChromaDB
   - Example: "budget issues" finds "cost overrun", "financial concerns"

3. **Contact Insights** 📊
   - Endpoint: `POST /api/v1/ai/insights/{contact_id}`
   - Analyzes: Communication patterns, trends, sentiment
   - Shows: Topics, frequency, platform preferences

4. **Entity Extraction** 🏷️
   - Endpoint: `GET /api/v1/ai/entities/{message_id}`
   - Extracts: People, dates, locations, organizations, money
   - Automatic: Runs during message ingestion

5. **Natural Language Queries** 💬
   - Endpoint: `POST /api/v1/ai/ask`
   - Ask: "What did Alice say about the budget?"
   - Returns: AI-generated answer with source messages

---

## 🔧 Find Your Local IP (Important!)

For the mobile app to connect to your backend:

```bash
# Mac/Linux
ifconfig | grep "inet "
# Look for something like: 192.168.1.x

# Windows
ipconfig
# Look for IPv4 Address
```

Then update `src/api/client.ts`:
```typescript
const API_BASE_URL = 'http://192.168.1.123:8000/api/v1';  // Your IP here!
```

---

## 🧪 Test Backend API First

```bash
# Test from mobile/browser with your IP
curl http://192.168.x.x:8000/api/v1/health

# Should return:
{
  "status": "healthy",
  "timestamp": "...",
  "version": "1.0.0",
  "environment": "development"
}
```

---

## 📱 Run the Mobile App

```bash
# iOS (requires Xcode)
npm run ios

# Android (requires Android Studio)
npm run android

# Web (for quick testing)
npm run web
```

---

## 🎯 Recommended Build Order

**Week 1: Basic Setup**
1. ✅ Create navigation
2. ✅ Build API client
3. ✅ Create ConnectionsScreen
4. ✅ Test platform connection flow

**Week 2: Core Features**
5. ✅ Build MessagesScreen
6. ✅ Implement message listing
7. ✅ Add pull-to-refresh
8. ✅ Add infinite scroll

**Week 3: AI Features**
9. ✅ Add semantic search
10. ✅ Show thread summaries
11. ✅ Display contact insights
12. ✅ Implement "Ask AI" screen

**Week 4: Polish**
13. ✅ Add authentication
14. ✅ Improve UI/UX
15. ✅ Add notifications
16. ✅ Test thoroughly

---

## 💡 Pro Tips

1. **Use React Query** for data fetching:
   ```typescript
   const { data, isLoading } = useQuery({
     queryKey: ['connections', userId],
     queryFn: () => connectionsAPI.listConnections(userId)
   });
   ```

2. **Test on web first** - Faster than emulators:
   ```bash
   npm run web
   ```

3. **Use Expo Go app** for quick testing on real device

4. **Check backend logs** if API calls fail:
   ```bash
   # In the terminal running the backend
   # You'll see requests in real-time
   ```

---

## 📚 Resources

- **Platform Connection**: `PLATFORM_CONNECTION_GUIDE.md`
- **AI Features**: `AI_FEATURES_GUIDE.md`
- **Backend API Docs**: http://localhost:8000/docs
- **Expo Docs**: https://docs.expo.dev/
- **React Navigation**: https://reactnavigation.org/

---

## ✅ Checklist

Once the mobile app is created:

- [ ] Install dependencies
- [ ] Find your local IP address
- [ ] Create `src/api/client.ts` with correct IP
- [ ] Create API endpoint files
- [ ] Set up navigation
- [ ] Create basic screens
- [ ] Test connection to backend
- [ ] Implement ConnectionsScreen
- [ ] Add AI features
- [ ] Polish UI/UX

---

**The mobile app creation is in progress. Once complete, proceed with the steps above!**

**Need help with any specific screen or feature? Let me know!**
