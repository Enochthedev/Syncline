---
inclusion: manual
---

# Frontend Integration Guidelines

## Overview

This document provides guidance on integrating backend API endpoints with the frontend applications (web and mobile) as they are developed. Each backend endpoint should be documented with frontend integration notes.

## Integration Pattern

For each backend API endpoint implemented, document:

1. **API Endpoint Details**
   - HTTP method and path
   - Request/response schemas
   - Authentication requirements
   - Rate limits

2. **Frontend Integration**
   - React Query hook pattern
   - State management approach
   - UI component suggestions
   - Error handling strategy

3. **Mobile-Specific Considerations**
   - Native module requirements
   - Offline sync strategy
   - Platform-specific behavior (iOS/Android)
   - Performance optimizations

## Example Integration Documentation

### Backend Endpoint: GET /api/v1/participants/

**Purpose**: Search and list participants (contacts) across platforms

**Request Parameters**:
```typescript
{
  search?: string;      // Search query
  platform?: string;    // Filter by platform
  limit?: number;       // Results limit (default: 20)
  offset?: number;      // Pagination offset
}
```

**Response**:
```typescript
{
  items: Participant[];
  total: number;
  limit: number;
  offset: number;
}
```

### Web Frontend Integration

**React Query Hook** (`apps/web/src/hooks/useParticipants.ts`):
```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api/client';

export const useParticipants = (filters: ParticipantFilters) => {
  return useQuery({
    queryKey: ['participants', filters],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/participants/', {
        params: filters
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });
};
```

**Component Usage** (`apps/web/src/components/contacts/ContactList.tsx`):
```typescript
import { useParticipants } from '../../hooks/useParticipants';

export const ContactList = () => {
  const { data, isLoading, error } = useParticipants({
    search: searchQuery,
    limit: 50
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="contact-list">
      {data.items.map(contact => (
        <ContactCard key={contact.id} contact={contact} />
      ))}
    </div>
  );
};
```

### Mobile Frontend Integration

**React Native Hook** (`apps/mobile/src/hooks/useParticipants.ts`):
```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api/client';
import { OfflineStorage } from '../services/storage/OfflineStorage';

export const useParticipants = (filters: ParticipantFilters) => {
  const offlineStorage = new OfflineStorage();

  return useQuery({
    queryKey: ['participants', filters],
    queryFn: async () => {
      try {
        // Try online first
        const response = await apiClient.get('/api/v1/participants/', {
          params: filters
        });
        
        // Cache for offline use
        await offlineStorage.cacheContacts(response.data.items);
        
        return response.data;
      } catch (error) {
        // Fallback to offline cache
        const cached = await offlineStorage.searchCachedContacts(
          filters.search || '',
          filters.limit || 20
        );
        return { items: cached, total: cached.length, offline: true };
      }
    },
    staleTime: 5 * 60 * 1000,
  });
};
```

**Component Usage** (`apps/mobile/src/components/contacts/ContactList.tsx`):
```typescript
import React from 'react';
import { FlatList, View, Text } from 'react-native';
import { useParticipants } from '../../hooks/useParticipants';
import { ContactCard } from './ContactCard';

export const ContactList = ({ searchQuery }) => {
  const { data, isLoading, error } = useParticipants({
    search: searchQuery,
    limit: 50
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <FlatList
      data={data.items}
      renderItem={({ item }) => <ContactCard contact={item} />}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={
        data.offline && (
          <View style={styles.offlineBanner}>
            <Text>Showing cached results (offline)</Text>
          </View>
        )
      }
    />
  );
};
```

### Mobile-Specific Notes

**Offline Sync Strategy**:
- Cache all fetched participants in SQLite
- Use cached data when offline
- Show offline indicator in UI
- Sync changes when connection restored

**Platform Differences**:
- **iOS**: Use native contact picker integration
- **Android**: Request READ_CONTACTS permission
- Both: Implement biometric auth for sensitive data

**Performance**:
- Implement virtual scrolling for large lists
- Use React Native's FlatList with `windowSize` optimization
- Lazy load contact avatars
- Debounce search queries (300ms)

## API Endpoint Checklist

When implementing a backend endpoint, ensure:

- [ ] OpenAPI/Swagger documentation is complete
- [ ] Request/response schemas are defined
- [ ] Authentication requirements are documented
- [ ] Rate limits are specified
- [ ] Error responses are documented
- [ ] Frontend integration notes are added to this doc
- [ ] React Query hook pattern is documented
- [ ] Mobile offline strategy is defined
- [ ] Platform-specific considerations are noted

## Common Patterns

### Authentication

**Web**:
```typescript
// Store tokens in localStorage
localStorage.setItem('auth_token', token);
localStorage.setItem('refresh_token', refreshToken);
```

**Mobile**:
```typescript
// Store tokens in secure storage
import * as Keychain from 'react-native-keychain';

await Keychain.setGenericPassword('auth_token', token);
await Keychain.setGenericPassword('refresh_token', refreshToken);
```

### Real-Time Updates

**Web** (WebSocket):
```typescript
const { isConnected, lastMessage } = useWebSocket();

useEffect(() => {
  if (lastMessage?.type === 'contact_update') {
    queryClient.invalidateQueries(['participants']);
  }
}, [lastMessage]);
```

**Mobile** (WebSocket + Push Notifications):
```typescript
import messaging from '@react-native-firebase/messaging';

// WebSocket for real-time when app is active
const { isConnected } = useWebSocket();

// Push notifications for background updates
useEffect(() => {
  const unsubscribe = messaging().onMessage(async remoteMessage => {
    if (remoteMessage.data?.type === 'contact_update') {
      queryClient.invalidateQueries(['participants']);
    }
  });

  return unsubscribe;
}, []);
```

### Error Handling

**Web**:
```typescript
const { error } = useParticipants(filters);

if (error) {
  if (error.response?.status === 401) {
    // Redirect to login
    navigate('/login');
  } else if (error.response?.status === 429) {
    // Show rate limit message
    toast.error('Too many requests. Please try again later.');
  } else {
    // Generic error
    toast.error('Failed to load contacts');
  }
}
```

**Mobile**:
```typescript
const { error } = useParticipants(filters);

if (error) {
  if (error.response?.status === 401) {
    // Navigate to login
    navigation.navigate('Login');
  } else if (error.response?.status === 429) {
    // Show rate limit alert
    Alert.alert('Rate Limit', 'Too many requests. Please try again later.');
  } else {
    // Generic error with retry option
    Alert.alert(
      'Error',
      'Failed to load contacts',
      [
        { text: 'Retry', onPress: () => refetch() },
        { text: 'Cancel', style: 'cancel' }
      ]
    );
  }
}
```

## Testing Integration

### Web E2E Tests
```typescript
// tests/e2e/participants.spec.ts
test('should load and display participants', async ({ page }) => {
  await page.goto('/contacts');
  await expect(page.locator('[data-testid=contact-list]')).toBeVisible();
  await expect(page.locator('[data-testid=contact-card]').first()).toBeVisible();
});
```

### Mobile E2E Tests
```typescript
// e2e/participants.e2e.ts
describe('Participants', () => {
  it('should load and display participants', async () => {
    await element(by.id('contacts-tab')).tap();
    await expect(element(by.id('contact-list'))).toBeVisible();
    await expect(element(by.id('contact-card')).atIndex(0)).toBeVisible();
  });
});
```

## Future Enhancements

As the backend evolves, consider:

1. **GraphQL Layer**: Add GraphQL for more flexible queries
2. **Optimistic Updates**: Update UI before server confirms
3. **Infinite Scroll**: Implement cursor-based pagination
4. **Advanced Caching**: Use service workers (web) and SQLite (mobile)
5. **Offline Queue**: Queue mutations when offline, sync when online

## Questions to Answer for Each Endpoint

1. **Does this endpoint need offline support?**
   - If yes, what data should be cached?
   - How long should cache be valid?

2. **Does this endpoint need real-time updates?**
   - If yes, via WebSocket or polling?
   - What triggers invalidation?

3. **Are there platform-specific requirements?**
   - iOS-specific features?
   - Android-specific features?
   - Web-specific features?

4. **What are the performance considerations?**
   - Large datasets requiring pagination?
   - Heavy computations requiring loading states?
   - Frequent updates requiring debouncing?

5. **What are the security considerations?**
   - Sensitive data requiring encryption?
   - Biometric auth required?
   - Token refresh strategy?
