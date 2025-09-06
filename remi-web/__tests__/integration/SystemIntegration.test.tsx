/**
 * Comprehensive System Integration Tests for Web Application
 * Tests end-to-end workflows and cross-platform synchronization
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { unifiedBusinessLogic } from '@/services/unifiedBusinessLogic'
import { apiClient } from '@/services/apiClient'
import HomePage from '@/app/page'
import { contactSearchSlice } from '@/store/slices/contactSearchSlice'

// Mock API responses
const mockContacts = [
  {
    id: '1',
    name: 'John Smith',
    email: 'john@example.com',
    platforms: ['gmail', 'slack'],
    lastInteraction: new Date('2024-01-15'),
    relationshipStrength: 0.8
  },
  {
    id: '2',
    name: 'Sarah Johnson',
    email: 'sarah@example.com',
    platforms: ['gmail', 'discord'],
    lastInteraction: new Date('2024-01-14'),
    relationshipStrength: 0.9
  }
]

const mockMessages = [
  {
    id: '1',
    content: 'Project update meeting scheduled for tomorrow',
    sender: mockContacts[0],
    timestamp: new Date('2024-01-15T10:00:00Z'),
    platform: 'gmail',
    threadId: 'thread-1'
  },
  {
    id: '2',
    content: 'Can you review the latest design mockups?',
    sender: mockContacts[1],
    timestamp: new Date('2024-01-14T15:30:00Z'),
    platform: 'slack',
    threadId: 'thread-2'
  }
]

const mockInsights = [
  {
    id: '1',
    type: 'follow_up_reminder',
    title: 'Follow up with John Smith',
    description: 'No response to project update from 3 days ago',
    priority: 'medium',
    relatedContacts: [mockContacts[0]],
    createdAt: new Date('2024-01-15T09:00:00Z')
  }
]

// Test setup helpers
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

function createTestStore() {
  return configureStore({
    reducer: {
      contactSearch: contactSearchSlice.reducer,
    },
  })
}

function renderWithProviders(component: React.ReactElement) {
  const queryClient = createTestQueryClient()
  const store = createTestStore()

  return render(
    <QueryClientProvider client={queryClient}>
      <Provider store={store}>
        {component}
      </Provider>
    </QueryClientProvider>
  )
}

// Mock API client
jest.mock('@/services/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    initialize: jest.fn(),
  },
}))

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
}

global.WebSocket = jest.fn(() => mockWebSocket) as any

// Mock IndexedDB
const mockIndexedDB = {
  open: jest.fn(() => ({
    result: {
      transaction: jest.fn(() => ({
        objectStore: jest.fn(() => ({
          get: jest.fn(),
          put: jest.fn(),
          delete: jest.fn(),
          getAll: jest.fn(),
        })),
      })),
    },
  })),
}

global.indexedDB = mockIndexedDB as any

describe('System Integration Tests', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    user = userEvent.setup()
    jest.clearAllMocks()
    
    // Setup default API responses
    ;(apiClient.get as jest.Mock).mockImplementation((url) => {
      if (url.includes('/contacts/search')) {
        return Promise.resolve({ data: { contacts: mockContacts } })
      }
      if (url.includes('/messages/search')) {
        return Promise.resolve({ data: { messages: mockMessages } })
      }
      if (url.includes('/insights/proactive')) {
        return Promise.resolve({ data: { insights: mockInsights } })
      }
      return Promise.resolve({ data: {} })
    })

    ;(apiClient.post as jest.Mock).mockImplementation((url) => {
      if (url.includes('/search/parse')) {
        return Promise.resolve({
          data: {
            text: 'messages from John',
            intent: 'person_search',
            entities: [{ type: 'person', value: 'John' }]
          }
        })
      }
      return Promise.resolve({ data: {} })
    })
  })

  describe('End-to-End Contact Search Workflow', () => {
    it('should complete full contact search workflow with natural language processing', async () => {
      renderWithProviders(<HomePage />)

      // Step 1: Verify initial page load
      expect(screen.getByText('Find conversations with anyone, instantly')).toBeInTheDocument()
      
      const searchInput = screen.getByPlaceholderText(/Search for messages with John/i)
      expect(searchInput).toBeInTheDocument()

      // Step 2: Enter natural language search query
      await user.type(searchInput, 'messages from John last week')

      // Step 3: Wait for query parsing
      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/api/search/parse', {
          query: 'messages from John last week'
        })
      })

      // Step 4: Verify contact suggestions appear
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      // Step 5: Click on contact suggestion
      const contactSuggestion = screen.getByText('John Smith')
      await user.click(contactSuggestion)

      // Step 6: Verify contact profile information
      await waitFor(() => {
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
        expect(screen.getByText('gmail')).toBeInTheDocument()
        expect(screen.getByText('slack')).toBeInTheDocument()
      })

      // Step 7: Search messages with contact
      const searchMessagesButton = screen.getByRole('button', { name: /search messages/i })
      await user.click(searchMessagesButton)

      // Step 8: Verify message search results
      await waitFor(() => {
        expect(screen.getByText('Project update meeting scheduled')).toBeInTheDocument()
      })

      // Step 9: Verify platform indicators
      expect(screen.getByText('gmail')).toBeInTheDocument()

      // Step 10: Click on message to view thread
      const messageResult = screen.getByText('Project update meeting scheduled')
      await user.click(messageResult)

      // Step 11: Verify message thread view
      await waitFor(() => {
        expect(screen.getByText('Message Thread')).toBeInTheDocument()
        expect(screen.getByText('Project update meeting scheduled for tomorrow')).toBeInTheDocument()
      })
    })

    it('should handle cross-platform search and filtering', async () => {
      renderWithProviders(<HomePage />)

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      
      // Search across all platforms
      await user.type(searchInput, 'project')

      // Wait for results
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
        expect(screen.getByText('Sarah Johnson')).toBeInTheDocument()
      })

      // Apply platform filter
      const filterButton = screen.getByRole('button', { name: /filter/i })
      await user.click(filterButton)

      // Select Gmail only
      const gmailFilter = screen.getByLabelText('Gmail')
      await user.click(gmailFilter)

      const applyFiltersButton = screen.getByRole('button', { name: /apply filters/i })
      await user.click(applyFiltersButton)

      // Verify filtered results
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
        // Sarah should be filtered out if she doesn't have Gmail
      })
    })

    it('should handle real-time updates and synchronization', async () => {
      renderWithProviders(<HomePage />)

      // Initialize WebSocket connection
      await act(async () => {
        await unifiedBusinessLogic.initialize()
      })

      // Simulate real-time message update
      const mockUpdate = {
        type: 'message_received',
        data: {
          id: '3',
          content: 'New real-time message',
          sender: mockContacts[0],
          timestamp: new Date(),
          platform: 'slack'
        }
      }

      // Trigger WebSocket message
      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls
          .find(call => call[0] === 'message')?.[1]
        
        if (messageHandler) {
          messageHandler({ data: JSON.stringify(mockUpdate) })
        }
      })

      // Verify real-time update appears
      await waitFor(() => {
        expect(screen.getByText('New real-time message')).toBeInTheDocument()
      })

      // Verify sync indicator updates
      expect(screen.getByText(/synced/i)).toBeInTheDocument()
    })
  })

  describe('Offline Support and Caching', () => {
    it('should handle offline mode gracefully', async () => {
      renderWithProviders(<HomePage />)

      // Simulate offline mode
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false,
      })

      // Trigger offline event
      act(() => {
        window.dispatchEvent(new Event('offline'))
      })

      // Verify offline indicator
      await waitFor(() => {
        expect(screen.getByText(/offline/i)).toBeInTheDocument()
      })

      // Attempt search in offline mode
      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      await user.type(searchInput, 'cached search')

      // Verify cached results are shown
      await waitFor(() => {
        expect(screen.getByText(/cached results/i)).toBeInTheDocument()
      })

      // Simulate going back online
      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: true,
      })

      act(() => {
        window.dispatchEvent(new Event('online'))
      })

      // Verify online indicator and sync
      await waitFor(() => {
        expect(screen.getByText(/online/i)).toBeInTheDocument()
        expect(screen.getByText(/syncing/i)).toBeInTheDocument()
      })
    })

    it('should cache search results and manage cache lifecycle', async () => {
      renderWithProviders(<HomePage />)

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)

      // Perform initial search
      await user.type(searchInput, 'cache test')

      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/api/contacts/search', expect.any(Object))
      })

      // Clear search and search again with same query
      await user.clear(searchInput)
      await user.type(searchInput, 'cache test')

      // Verify cached results are used (no additional API call)
      expect(apiClient.get).toHaveBeenCalledTimes(1)

      // Wait for cache expiration (simulate)
      act(() => {
        jest.advanceTimersByTime(5 * 60 * 1000) // 5 minutes
      })

      // Search again after cache expiration
      await user.clear(searchInput)
      await user.type(searchInput, 'cache test')

      // Verify new API call is made
      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Progressive Web App Features', () => {
    it('should handle PWA installation and service worker', async () => {
      // Mock service worker registration
      const mockServiceWorker = {
        register: jest.fn(() => Promise.resolve({
          installing: null,
          waiting: null,
          active: { state: 'activated' },
          addEventListener: jest.fn(),
          update: jest.fn(),
        })),
        ready: Promise.resolve({
          active: { state: 'activated' },
          sync: { register: jest.fn() },
        }),
      }

      Object.defineProperty(navigator, 'serviceWorker', {
        value: mockServiceWorker,
        writable: true,
      })

      renderWithProviders(<HomePage />)

      // Initialize service worker
      await act(async () => {
        await unifiedBusinessLogic.initialize()
      })

      // Verify service worker registration
      expect(mockServiceWorker.register).toHaveBeenCalledWith('/sw.js')

      // Simulate PWA install prompt
      const mockInstallPrompt = {
        prompt: jest.fn(),
        userChoice: Promise.resolve({ outcome: 'accepted' }),
      }

      act(() => {
        window.dispatchEvent(
          Object.assign(new Event('beforeinstallprompt'), mockInstallPrompt)
        )
      })

      // Verify install prompt appears
      await waitFor(() => {
        expect(screen.getByText(/install app/i)).toBeInTheDocument()
      })

      // Click install button
      const installButton = screen.getByRole('button', { name: /install/i })
      await user.click(installButton)

      // Verify install prompt is triggered
      expect(mockInstallPrompt.prompt).toHaveBeenCalled()
    })

    it('should handle keyboard shortcuts and accessibility', async () => {
      renderWithProviders(<HomePage />)

      // Test global search shortcut (Ctrl+K)
      await user.keyboard('{Control>}k{/Control}')

      // Verify search input is focused
      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      expect(searchInput).toHaveFocus()

      // Test escape to clear search
      await user.type(searchInput, 'test query')
      await user.keyboard('{Escape}')

      // Verify search is cleared
      expect(searchInput).toHaveValue('')

      // Test tab navigation
      await user.tab()
      expect(screen.getByRole('button', { name: /search/i })).toHaveFocus()

      // Test enter to execute search
      await user.type(searchInput, 'keyboard test')
      await user.keyboard('{Enter}')

      // Verify search is executed
      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/api/contacts/search', expect.any(Object))
      })
    })
  })

  describe('Performance and Error Handling', () => {
    it('should handle large datasets efficiently', async () => {
      // Mock large dataset
      const largeContactList = Array.from({ length: 1000 }, (_, i) => ({
        id: `contact-${i}`,
        name: `Contact ${i}`,
        email: `contact${i}@example.com`,
        platforms: ['gmail'],
        lastInteraction: new Date(),
        relationshipStrength: Math.random()
      }))

      ;(apiClient.get as jest.Mock).mockResolvedValueOnce({
        data: { contacts: largeContactList }
      })

      renderWithProviders(<HomePage />)

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)

      // Measure search performance
      const startTime = performance.now()
      
      await user.type(searchInput, 'performance test')

      await waitFor(() => {
        expect(screen.getByText('Contact 0')).toBeInTheDocument()
      })

      const endTime = performance.now()
      const searchTime = endTime - startTime

      // Verify reasonable performance (< 2 seconds)
      expect(searchTime).toBeLessThan(2000)

      // Test virtual scrolling with large list
      const contactsList = screen.getByRole('list')
      
      // Scroll down
      fireEvent.scroll(contactsList, { target: { scrollTop: 1000 } })

      // Verify virtualization (not all items rendered)
      const renderedContacts = screen.getAllByText(/Contact \d+/)
      expect(renderedContacts.length).toBeLessThan(largeContactList.length)
    })

    it('should handle API errors gracefully', async () => {
      ;(apiClient.get as jest.Mock).mockRejectedValueOnce(
        new Error('Network error')
      )

      renderWithProviders(<HomePage />)

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      await user.type(searchInput, 'error test')

      // Verify error handling
      await waitFor(() => {
        expect(screen.getByText(/error occurred/i)).toBeInTheDocument()
      })

      // Verify retry functionality
      const retryButton = screen.getByRole('button', { name: /retry/i })
      
      // Mock successful retry
      ;(apiClient.get as jest.Mock).mockResolvedValueOnce({
        data: { contacts: mockContacts }
      })

      await user.click(retryButton)

      // Verify successful retry
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })
    })

    it('should handle concurrent operations safely', async () => {
      renderWithProviders(<HomePage />)

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)

      // Simulate rapid typing (concurrent searches)
      await user.type(searchInput, 'concurrent')
      await user.type(searchInput, ' test')
      await user.type(searchInput, ' query')

      // Verify only the latest search is processed
      await waitFor(() => {
        const apiCalls = (apiClient.get as jest.Mock).mock.calls
        const searchCalls = apiCalls.filter(call => 
          call[0].includes('/contacts/search')
        )
        
        // Should debounce and only make one call for final query
        expect(searchCalls.length).toBe(1)
        expect(searchCalls[0][1].params.q).toBe('concurrent test query')
      })
    })
  })

  describe('Cross-Platform Integration', () => {
    it('should handle platform connection management', async () => {
      renderWithProviders(<HomePage />)

      // Navigate to platform connections
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await user.click(settingsButton)

      const platformsButton = screen.getByRole('button', { name: /platforms/i })
      await user.click(platformsButton)

      // Verify platform connection interface
      expect(screen.getByText('Gmail')).toBeInTheDocument()
      expect(screen.getByText('Slack')).toBeInTheDocument()
      expect(screen.getByText('Discord')).toBeInTheDocument()

      // Test platform connection
      const connectGmailButton = screen.getByRole('button', { name: /connect gmail/i })
      
      ;(apiClient.post as jest.Mock).mockResolvedValueOnce({
        data: {
          id: 'gmail-connection-1',
          platform: 'gmail',
          status: 'connected',
          lastSync: new Date(),
          capabilities: ['read', 'search']
        }
      })

      await user.click(connectGmailButton)

      // Verify OAuth flow initiation
      await waitFor(() => {
        expect(screen.getByText(/connecting to gmail/i)).toBeInTheDocument()
      })

      // Simulate successful connection
      act(() => {
        // Simulate OAuth callback
        window.postMessage({
          type: 'oauth_success',
          platform: 'gmail',
          credentials: { access_token: 'test-token' }
        }, '*')
      })

      // Verify connection success
      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument()
      })
    })

    it('should validate data synchronization across platforms', async () => {
      renderWithProviders(<HomePage />)

      // Mock multi-platform search results
      ;(apiClient.get as jest.Mock).mockResolvedValueOnce({
        data: {
          contacts: mockContacts,
          messages: mockMessages,
          threads: [
            {
              id: 'thread-1',
              platform: 'gmail',
              participants: [mockContacts[0]],
              messageCount: 5,
              lastMessage: mockMessages[0]
            },
            {
              id: 'thread-2',
              platform: 'slack',
              participants: [mockContacts[1]],
              messageCount: 3,
              lastMessage: mockMessages[1]
            }
          ]
        }
      })

      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      await user.type(searchInput, 'cross platform')

      // Verify results from multiple platforms
      await waitFor(() => {
        expect(screen.getByText('gmail')).toBeInTheDocument()
        expect(screen.getByText('slack')).toBeInTheDocument()
      })

      // Test platform-specific filtering
      const platformFilter = screen.getByRole('button', { name: /filter by platform/i })
      await user.click(platformFilter)

      const gmailCheckbox = screen.getByLabelText('Gmail')
      await user.click(gmailCheckbox)

      // Verify filtered results
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
        expect(screen.queryByText('Sarah Johnson')).not.toBeInTheDocument()
      })
    })
  })

  describe('User Acceptance Scenarios', () => {
    it('should support complete user workflow from onboarding to daily use', async () => {
      renderWithProviders(<HomePage />)

      // Simulate new user onboarding
      const getStartedButton = screen.getByRole('button', { name: /get started/i })
      await user.click(getStartedButton)

      // Complete onboarding steps
      await waitFor(() => {
        expect(screen.getByText(/welcome to remi/i)).toBeInTheDocument()
      })

      // Skip through onboarding for test
      const skipButton = screen.getByRole('button', { name: /skip/i })
      await user.click(skipButton)

      // Verify main interface
      expect(screen.getByText('Find conversations with anyone, instantly')).toBeInTheDocument()

      // Perform first search
      const searchInput = screen.getByPlaceholderText(/Search for messages/i)
      await user.type(searchInput, 'first search')

      // Verify search works
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      // Test contact interaction
      const contactCard = screen.getByText('John Smith')
      await user.click(contactCard)

      // Verify contact details
      await waitFor(() => {
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
      })

      // Test message search within contact
      const messageSearchInput = screen.getByPlaceholderText(/search messages/i)
      await user.type(messageSearchInput, 'project')

      // Verify message results
      await waitFor(() => {
        expect(screen.getByText('Project update meeting')).toBeInTheDocument()
      })
    })

    it('should handle power user workflows efficiently', async () => {
      renderWithProviders(<HomePage />)

      // Test advanced search features
      const advancedSearchButton = screen.getByRole('button', { name: /advanced search/i })
      await user.click(advancedSearchButton)

      // Configure complex search filters
      const dateFromInput = screen.getByLabelText(/from date/i)
      await user.type(dateFromInput, '2024-01-01')

      const dateToInput = screen.getByLabelText(/to date/i)
      await user.type(dateToInput, '2024-01-31')

      const platformSelect = screen.getByLabelText(/platforms/i)
      await user.selectOptions(platformSelect, ['gmail', 'slack'])

      const contentTypeSelect = screen.getByLabelText(/content type/i)
      await user.selectOptions(contentTypeSelect, 'messages')

      // Execute advanced search
      const executeSearchButton = screen.getByRole('button', { name: /search/i })
      await user.click(executeSearchButton)

      // Verify advanced search results
      await waitFor(() => {
        expect(apiClient.get).toHaveBeenCalledWith('/api/search/advanced', {
          params: expect.objectContaining({
            dateFrom: '2024-01-01',
            dateTo: '2024-01-31',
            platforms: ['gmail', 'slack'],
            contentType: 'messages'
          })
        })
      })

      // Test bulk operations
      const selectAllCheckbox = screen.getByLabelText(/select all/i)
      await user.click(selectAllCheckbox)

      const bulkActionsButton = screen.getByRole('button', { name: /bulk actions/i })
      await user.click(bulkActionsButton)

      const exportButton = screen.getByRole('button', { name: /export/i })
      await user.click(exportButton)

      // Verify export functionality
      await waitFor(() => {
        expect(apiClient.post).toHaveBeenCalledWith('/api/export', expect.any(Object))
      })
    })
  })
})

// Cleanup
afterEach(() => {
  jest.clearAllTimers()
  jest.useRealTimers()
})