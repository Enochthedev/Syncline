'use client'

import { useState, useEffect } from 'react'
import { UnifiedContact } from '@/types'
import { cn } from '@/utils/cn'

interface ContactSuggestionsProps {
  query: string
  onContactSelect: (contact: UnifiedContact) => void
  className?: string
}

// Mock data for demonstration
const mockContacts: UnifiedContact[] = [
  {
    id: '1',
    primaryName: 'John Smith',
    displayName: 'John Smith',
    profilePhoto: undefined,
    identities: [
      {
        platform: 'gmail',
        platformUserId: 'john.smith@example.com',
        displayName: 'John Smith',
        verified: true,
      },
    ],
    emails: ['john.smith@example.com'],
    phoneNumbers: ['+1-555-0123'],
    socialProfiles: [],
    lastInteraction: new Date('2024-01-15'),
    totalMessages: 45,
    platforms: ['gmail', 'slack'],
    relationshipStrength: 0.8,
    communicationFrequency: 'high',
    responsePattern: {
      averageResponseTime: 30,
      responseRate: 0.9,
      preferredTimes: ['09:00-12:00', '14:00-17:00'],
      communicationStyle: 'professional',
    },
    topicAffinity: [],
    sharedFiles: [],
    sharedLinks: [],
    commonContacts: [],
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-15'),
    lastSyncAt: new Date('2024-01-15'),
  },
  {
    id: '2',
    primaryName: 'Sarah Johnson',
    displayName: 'Sarah Johnson',
    profilePhoto: undefined,
    identities: [
      {
        platform: 'gmail',
        platformUserId: 'sarah.johnson@example.com',
        displayName: 'Sarah Johnson',
        verified: true,
      },
    ],
    emails: ['sarah.johnson@example.com'],
    phoneNumbers: [],
    socialProfiles: [],
    lastInteraction: new Date('2024-01-10'),
    totalMessages: 23,
    platforms: ['gmail'],
    relationshipStrength: 0.6,
    communicationFrequency: 'medium',
    responsePattern: {
      averageResponseTime: 120,
      responseRate: 0.7,
      preferredTimes: ['10:00-16:00'],
      communicationStyle: 'casual',
    },
    topicAffinity: [],
    sharedFiles: [],
    sharedLinks: [],
    commonContacts: [],
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-10'),
    lastSyncAt: new Date('2024-01-10'),
  },
]

export function ContactSuggestions({
  query,
  onContactSelect,
  className,
}: ContactSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<UnifiedContact[]>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!query.trim()) {
      setSuggestions([])
      return
    }

    setIsLoading(true)
    
    // Simulate API call with mock data
    const timer = setTimeout(() => {
      const filtered = mockContacts.filter(contact =>
        contact.primaryName.toLowerCase().includes(query.toLowerCase()) ||
        contact.emails.some(email => email.toLowerCase().includes(query.toLowerCase()))
      )
      setSuggestions(filtered)
      setIsLoading(false)
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  if (!query.trim()) {
    return null
  }

  return (
    <div className={cn('relative', className)}>
      <div className="absolute top-0 left-0 right-0 z-50 bg-card border border-border rounded-lg shadow-lg max-h-96 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center">
            <div className="inline-flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
              <span className="text-sm text-muted-foreground">Searching contacts...</span>
            </div>
          </div>
        ) : suggestions.length > 0 ? (
          <div className="py-2">
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Contacts ({suggestions.length})
            </div>
            {suggestions.map((contact) => (
              <button
                key={contact.id}
                onClick={() => onContactSelect(contact)}
                className="w-full px-3 py-3 text-left hover:bg-accent transition-colors focus:bg-accent focus:outline-none"
              >
                <div className="flex items-center space-x-3">
                  {/* Avatar */}
                  <div className="flex-shrink-0">
                    {contact.profilePhoto ? (
                      <img
                        src={contact.profilePhoto}
                        alt={contact.displayName}
                        className="h-8 w-8 rounded-full"
                      />
                    ) : (
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-sm font-medium text-primary">
                          {contact.displayName.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Contact Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-foreground truncate">
                        {contact.displayName}
                      </p>
                      <div className="flex items-center space-x-1">
                        {contact.platforms.map((platform) => (
                          <span
                            key={platform}
                            className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground"
                          >
                            {platform}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center space-x-4 mt-1">
                      <p className="text-xs text-muted-foreground">
                        {contact.totalMessages} messages
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Last: {contact.lastInteraction.toLocaleDateString()}
                      </p>
                      <div className="flex items-center space-x-1">
                        <div
                          className={cn(
                            'h-2 w-2 rounded-full',
                            contact.communicationFrequency === 'high' && 'bg-green-500',
                            contact.communicationFrequency === 'medium' && 'bg-yellow-500',
                            contact.communicationFrequency === 'low' && 'bg-red-500'
                          )}
                        />
                        <span className="text-xs text-muted-foreground capitalize">
                          {contact.communicationFrequency}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="flex-shrink-0">
                    <svg
                      className="h-4 w-4 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-4 text-center">
            <p className="text-sm text-muted-foreground">
              No contacts found for "{query}"
            </p>
          </div>
        )}
      </div>
    </div>
  )
}