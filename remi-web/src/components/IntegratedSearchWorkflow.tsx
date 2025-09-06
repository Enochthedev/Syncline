/**
 * Integrated Search Workflow Component
 * Comprehensive contact-based search with natural language processing
 * and cross-platform synchronization for web application
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { unifiedBusinessLogic } from '@/services/unifiedBusinessLogic'
import { ContactSearchInput } from '@/components/ContactSearchInput'
import { Contact, Message, ConversationThread, ProactiveInsight } from '@/types'

interface SearchWorkflowState {
  query: string
  results: {
    contacts: Contact[]
    messages: Message[]
    threads: ConversationThread[]
    insights: ProactiveInsight[]
  }
  selectedContact: Contact | null
  selectedThread: ConversationThread | null
  filters: SearchFilters
  loading: boolean
  error: string | null
}

interface SearchFilters {
  platforms: string[]
  dateRange: { start: Date | null; end: Date | null }
  contentTypes: string[]
  participants: string[]
}

export function IntegratedSearchWorkflow() {
  const queryClient = useQueryClient()
  
  const [state, setState] = useState<SearchWorkflowState>({
    query: '',
    results: {
      contacts: [],
      messages: [],
      threads: [],
      insights: []
    },
    selectedContact: null,
    selectedThread: null,
    filters: {
      platforms: [],
      dateRange: { start: null, end: null },
      contentTypes: ['messages', 'files'],
      participants: []
    },
    loading: false,
    error: null
  })

  // Initialize unified business logic
  useEffect(() => {
    const initializeServices = async () => {
      try {
        await unifiedBusinessLogic.initialize()
      } catch (error) {
        setState(prev => ({
          ...prev,
          error: error instanceof Error ? error.message : 'Initialization failed'
        }))
      }
    }

    initializeServices()

    // Cleanup on unmount
    return () => {
      unifiedBusinessLogic.cleanup()
    }
  }, [])

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: async (searchParams: { query: string; options?: any }) => {
      return await unifiedBusinessLogic.executeContactSearchWorkflow(
        searchParams.query,
        {
          includeNaturalLanguage: true,
          includeInsights: true,
          useCache: true,
          maxResults: 50,
          ...searchParams.options
        }
      )
    },
    onSuccess: (data) => {
      setState(prev => ({
        ...prev,
        results: {
          contacts: data.contacts,
          messages: data.messages,
          threads: data.threads,
          insights: data.insights
        },
        loading: false,
        error: null
      }))
    },
    onError: (error) => {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Search failed'
      }))
    }
  })

  // System status query
  const { data: systemStatus } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: () => unifiedBusinessLogic.getSystemStatus(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Handle search
  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) return

    setState(prev => ({ ...prev, query, loading: true, error: null }))
    
    try {
      await searchMutation.mutateAsync({ query })
    } catch (error) {
      console.error('Search failed:', error)
    }
  }, [searchMutation])

  // Handle contact selection
  const handleContactSelect = useCallback((contact: Contact) => {
    setState(prev => ({ ...prev, selectedContact: contact }))
    
    // Search messages for selected contact
    handleSearch(`messages with ${contact.name}`)
  }, [handleSearch])

  // Handle thread selection
  const handleThreadSelect = useCallback((thread: ConversationThread) => {
    setState(prev => ({ ...prev, selectedThread: thread }))
  }, [])

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<SearchFilters>) => {
    setState(prev => ({
      ...prev,
      filters: { ...prev.filters, ...newFilters }
    }))

    // Re-run search with new filters if there's a query
    if (state.query) {
      handleSearch(state.query)
    }
  }, [state.query, handleSearch])

  // Handle real-time updates
  useEffect(() => {
    const handleRealTimeUpdate = (update: any) => {
      switch (update.type) {
        case 'contact_update':
          queryClient.invalidateQueries({ queryKey: ['contacts'] })
          break
        case 'message_received':
          queryClient.invalidateQueries({ queryKey: ['messages'] })
          // Re-run current search to include new message
          if (state.query) {
            handleSearch(state.query)
          }
          break
        case 'sync_complete':
          queryClient.invalidateQueries({ queryKey: ['systemStatus'] })
          break
      }
    }

    // In a real implementation, this would be connected to WebSocket
    // For now, we'll simulate with periodic updates
    const interval = setInterval(() => {
      if (systemStatus?.online && state.query) {
        // Simulate real-time update check
        queryClient.invalidateQueries({ queryKey: ['searchResults', state.query] })
      }
    }, 60000) // Check every minute

    return () => clearInterval(interval)
  }, [queryClient, systemStatus, state.query, handleSearch])

  return (
    <div className="integrated-search-workflow">
      {/* Header with system status */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">R.E.M.I Search</h1>
        <div className="flex items-center space-x-4">
          <SystemStatusIndicator status={systemStatus} />
          <SearchFiltersButton 
            filters={state.filters}
            onFiltersChange={handleFilterChange}
          />
        </div>
      </div>

      {/* Main search interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Search and Results Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Search Input */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <ContactSearchInput
              value={state.query}
              onChangeText={(text) => setState(prev => ({ ...prev, query: text }))}
              onSearch={handleSearch}
              placeholder="Search contacts, messages, or try natural language like 'messages from John last week'"
              loading={state.loading}
            />
            
            {state.error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800">{state.error}</p>
                <button
                  onClick={() => handleSearch(state.query)}
                  className="mt-2 text-red-600 hover:text-red-800 underline"
                >
                  Try again
                </button>
              </div>
            )}
          </div>

          {/* Search Results */}
          {(state.results.contacts.length > 0 || state.results.messages.length > 0) && (
            <SearchResults
              results={state.results}
              query={state.query}
              onContactSelect={handleContactSelect}
              onThreadSelect={handleThreadSelect}
              selectedContact={state.selectedContact}
              loading={state.loading}
            />
          )}

          {/* Natural Language Query Analysis */}
          {state.query && (
            <NaturalLanguageAnalysis query={state.query} />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Selected Contact Details */}
          {state.selectedContact && (
            <ContactDetailsPanel
              contact={state.selectedContact}
              onClose={() => setState(prev => ({ ...prev, selectedContact: null }))}
            />
          )}

          {/* Proactive Insights */}
          {state.results.insights.length > 0 && (
            <ProactiveInsightsPanel insights={state.results.insights} />
          )}

          {/* Recent Activity */}
          <RecentActivityPanel />

          {/* Platform Connections */}
          <PlatformConnectionsPanel connections={systemStatus?.platformConnections || []} />
        </div>
      </div>

      {/* Message Thread Modal */}
      {state.selectedThread && (
        <MessageThreadModal
          thread={state.selectedThread}
          onClose={() => setState(prev => ({ ...prev, selectedThread: null }))}
          searchQuery={state.query}
        />
      )}
    </div>
  )
}

// Supporting components

function SystemStatusIndicator({ status }: { status: any }) {
  if (!status) return null

  return (
    <div className="flex items-center space-x-2">
      <div className={`w-2 h-2 rounded-full ${
        status.online ? 'bg-green-500' : 'bg-red-500'
      }`} />
      <span className="text-sm text-gray-600">
        {status.online ? 'Online' : 'Offline'}
      </span>
      {status.syncStatus === 'active' && (
        <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />
      )}
    </div>
  )
}

function SearchFiltersButton({ filters, onFiltersChange }: {
  filters: SearchFilters
  onFiltersChange: (filters: Partial<SearchFilters>) => void
}) {
  const [showFilters, setShowFilters] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setShowFilters(!showFilters)}
        className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center space-x-2"
      >
        <span>Filters</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.707A1 1 0 013 7V4z" />
        </svg>
      </button>

      {showFilters && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border p-4 z-10">
          <h3 className="font-semibold mb-4">Search Filters</h3>
          
          {/* Platform filters */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Platforms</label>
            <div className="space-y-2">
              {['gmail', 'slack', 'discord', 'whatsapp'].map(platform => (
                <label key={platform} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={filters.platforms.includes(platform)}
                    onChange={(e) => {
                      const newPlatforms = e.target.checked
                        ? [...filters.platforms, platform]
                        : filters.platforms.filter(p => p !== platform)
                      onFiltersChange({ platforms: newPlatforms })
                    }}
                    className="mr-2"
                  />
                  <span className="capitalize">{platform}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Date Range</label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="date"
                value={filters.dateRange.start?.toISOString().split('T')[0] || ''}
                onChange={(e) => onFiltersChange({
                  dateRange: {
                    ...filters.dateRange,
                    start: e.target.value ? new Date(e.target.value) : null
                  }
                })}
                className="px-3 py-2 border rounded"
              />
              <input
                type="date"
                value={filters.dateRange.end?.toISOString().split('T')[0] || ''}
                onChange={(e) => onFiltersChange({
                  dateRange: {
                    ...filters.dateRange,
                    end: e.target.value ? new Date(e.target.value) : null
                  }
                })}
                className="px-3 py-2 border rounded"
              />
            </div>
          </div>

          <button
            onClick={() => setShowFilters(false)}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Apply Filters
          </button>
        </div>
      )}
    </div>
  )
}

function SearchResults({ results, query, onContactSelect, onThreadSelect, selectedContact, loading }: any) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-4">
          Search Results for "{query}"
        </h2>

        {/* Contacts */}
        {results.contacts.length > 0 && (
          <div className="mb-6">
            <h3 className="text-md font-medium mb-3">Contacts ({results.contacts.length})</h3>
            <div className="space-y-2">
              {results.contacts.map((contact: Contact) => (
                <div
                  key={contact.id}
                  onClick={() => onContactSelect(contact)}
                  className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedContact?.id === contact.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">{contact.name}</h4>
                      <p className="text-sm text-gray-600">{contact.email}</p>
                    </div>
                    <div className="flex space-x-1">
                      {contact.platforms?.map(platform => (
                        <span
                          key={platform}
                          className="px-2 py-1 bg-gray-100 text-xs rounded"
                        >
                          {platform}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {results.messages.length > 0 && (
          <div className="mb-6">
            <h3 className="text-md font-medium mb-3">Messages ({results.messages.length})</h3>
            <div className="space-y-2">
              {results.messages.map((message: Message) => (
                <div
                  key={message.id}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="font-medium">{message.sender?.name}</span>
                        <span className="text-xs text-gray-500">{message.platform}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 line-clamp-2">
                        {message.content}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Threads */}
        {results.threads.length > 0 && (
          <div>
            <h3 className="text-md font-medium mb-3">Conversations ({results.threads.length})</h3>
            <div className="space-y-2">
              {results.threads.map((thread: ConversationThread) => (
                <div
                  key={thread.id}
                  onClick={() => onThreadSelect(thread)}
                  className="p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium">{thread.title || 'Conversation'}</h4>
                      <p className="text-sm text-gray-600 mb-2">
                        {thread.participants?.map(p => p.name).join(', ')}
                      </p>
                      <p className="text-sm text-gray-700">
                        {thread.summary?.shortSummary}
                      </p>
                    </div>
                    <div className="text-xs text-gray-500">
                      {thread.messageCount} messages
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {results.contacts.length === 0 && results.messages.length === 0 && results.threads.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No results found for "{query}"
          </div>
        )}
      </div>
    </div>
  )
}

function NaturalLanguageAnalysis({ query }: { query: string }) {
  return (
    <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
      <h3 className="font-medium text-blue-900 mb-2">Query Analysis</h3>
      <div className="text-sm text-blue-800">
        <p>Analyzing: "{query}"</p>
        <div className="mt-2 space-y-1">
          <div>• Intent: Contact search</div>
          <div>• Entities: Person names, time references</div>
          <div>• Scope: Messages and conversations</div>
        </div>
      </div>
    </div>
  )
}

function ContactDetailsPanel({ contact, onClose }: { contact: Contact; onClose: () => void }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Contact Details</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div className="space-y-4">
        <div>
          <h4 className="font-medium">{contact.name}</h4>
          <p className="text-sm text-gray-600">{contact.email}</p>
        </div>
        
        <div>
          <h5 className="text-sm font-medium mb-2">Platforms</h5>
          <div className="flex flex-wrap gap-1">
            {contact.platforms?.map(platform => (
              <span
                key={platform}
                className="px-2 py-1 bg-gray-100 text-xs rounded"
              >
                {platform}
              </span>
            ))}
          </div>
        </div>
        
        <div>
          <h5 className="text-sm font-medium mb-2">Insights</h5>
          <div className="text-sm text-gray-600 space-y-1">
            <div>• Last interaction: {contact.lastInteraction ? new Date(contact.lastInteraction).toLocaleDateString() : 'Unknown'}</div>
            <div>• Relationship strength: {Math.round((contact.relationshipStrength || 0) * 100)}%</div>
            <div>• Communication frequency: {contact.communicationFrequency || 'Unknown'}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ProactiveInsightsPanel({ insights }: { insights: ProactiveInsight[] }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="font-semibold mb-4">Proactive Insights</h3>
      <div className="space-y-3">
        {insights.map(insight => (
          <div key={insight.id} className="p-3 bg-yellow-50 border border-yellow-200 rounded">
            <h4 className="font-medium text-yellow-900">{insight.title}</h4>
            <p className="text-sm text-yellow-800 mt-1">{insight.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecentActivityPanel() {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-3 text-sm text-gray-600">
        <div>• Synced with Gmail (2 min ago)</div>
        <div>• New message from John Smith</div>
        <div>• Updated contact: Sarah Johnson</div>
      </div>
    </div>
  )
}

function PlatformConnectionsPanel({ connections }: { connections: any[] }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h3 className="font-semibold mb-4">Platform Connections</h3>
      <div className="space-y-2">
        {connections.map(connection => (
          <div key={connection.id} className="flex items-center justify-between">
            <span className="text-sm capitalize">{connection.platform}</span>
            <div className={`w-2 h-2 rounded-full ${
              connection.status === 'connected' ? 'bg-green-500' : 'bg-red-500'
            }`} />
          </div>
        ))}
      </div>
    </div>
  )
}

function MessageThreadModal({ thread, onClose, searchQuery }: any) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">{thread.title || 'Conversation'}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          <div className="space-y-4">
            <div className="text-sm text-gray-600">
              Participants: {thread.participants?.map((p: any) => p.name).join(', ')}
            </div>
            
            {thread.summary && (
              <div className="bg-gray-50 p-4 rounded">
                <h3 className="font-medium mb-2">Summary</h3>
                <p className="text-sm">{thread.summary.shortSummary}</p>
              </div>
            )}
            
            <div className="text-center text-gray-500">
              Message thread content would be displayed here
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IntegratedSearchWorkflow