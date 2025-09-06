/**
 * ContactSearchResults Component (Web Version)
 * 
 * Displays contact search results with contact cards and interaction indicators
 */

'use client'

import React from 'react';
import { UnifiedContact } from '@/types';
import { cn } from '@/utils/cn';

interface ContactSearchResultsProps {
  results: UnifiedContact[];
  query: string;
  isLoading: boolean;
  error?: string | null;
  onContactSelect: (contact: UnifiedContact) => void;
  showDetails?: boolean;
  emptyMessage?: string;
  className?: string;
}

export const ContactSearchResults: React.FC<ContactSearchResultsProps> = ({
  results,
  query,
  isLoading,
  error,
  onContactSelect,
  showDetails = true,
  emptyMessage,
  className,
}) => {
  // Render individual contact result
  const renderContactResult = (contact: UnifiedContact) => (
    <button
      key={contact.id}
      onClick={() => onContactSelect(contact)}
      className="w-full p-4 text-left hover:bg-accent transition-colors focus:bg-accent focus:outline-none rounded-lg border border-border mb-2"
    >
      <div className="flex items-start space-x-4">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {contact.profilePhoto ? (
            <img
              src={contact.profilePhoto}
              alt={contact.displayName}
              className="h-12 w-12 rounded-full object-cover"
            />
          ) : (
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-lg font-semibold text-primary">
                {contact.displayName.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
        </div>

        {/* Contact Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-foreground truncate">
              {contact.displayName}
            </h3>
            <div className="flex items-center space-x-2">
              {/* Recent activity indicator */}
              {contact.lastInteraction && 
               new Date(contact.lastInteraction).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000 && (
                <div className="h-2 w-2 bg-green-500 rounded-full" />
              )}
            </div>
          </div>

          {/* Contact Details */}
          <div className="space-y-1">
            {contact.emails.length > 0 && (
              <p className="text-sm text-muted-foreground">
                📧 {contact.emails[0]}
              </p>
            )}
            {contact.phoneNumbers.length > 0 && (
              <p className="text-sm text-muted-foreground">
                📱 {contact.phoneNumbers[0]}
              </p>
            )}
          </div>

          {/* Platform Indicators */}
          <div className="flex flex-wrap gap-1 mt-2">
            {contact.platforms.map((platform) => (
              <span
                key={platform}
                className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-secondary text-secondary-foreground"
              >
                {platform.toUpperCase()}
              </span>
            ))}
          </div>

          {/* Additional Details */}
          {showDetails && (
            <div className="flex items-center space-x-4 mt-3 text-xs text-muted-foreground">
              <span>{contact.totalMessages} messages</span>
              <span>
                Last: {new Date(contact.lastInteraction).toLocaleDateString()}
              </span>
              <div className="flex items-center space-x-1">
                <div
                  className={cn(
                    'h-2 w-2 rounded-full',
                    contact.communicationFrequency === 'high' && 'bg-green-500',
                    contact.communicationFrequency === 'medium' && 'bg-yellow-500',
                    contact.communicationFrequency === 'low' && 'bg-red-500'
                  )}
                />
                <span className="capitalize">
                  {contact.communicationFrequency} frequency
                </span>
              </div>
              <div className="flex items-center space-x-1">
                <span>Strength:</span>
                <div className="w-12 h-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${contact.relationshipStrength * 100}%` }}
                  />
                </div>
                <span>{Math.round(contact.relationshipStrength * 100)}%</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex-shrink-0 flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle quick message action
            }}
            className="p-2 rounded-md hover:bg-accent transition-colors"
            title="Send message"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              // Handle view profile action
            }}
            className="p-2 rounded-md hover:bg-accent transition-colors"
            title="View profile"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </button>
        </div>
      </div>
    </button>
  );

  // Render empty state
  const renderEmptyState = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Searching contacts...</p>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h3 className="text-lg font-semibold text-destructive mb-2">Search Error</h3>
            <p className="text-muted-foreground">{error}</p>
          </div>
        </div>
      );
    }

    if (query.length >= 2) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold mb-2">No contacts found</h3>
            <p className="text-muted-foreground">
              {emptyMessage || `No contacts match "${query}"`}
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="text-4xl mb-4">👥</div>
          <h3 className="text-lg font-semibold mb-2">Search Contacts</h3>
          <p className="text-muted-foreground">
            Type at least 2 characters to search for contacts
          </p>
        </div>
      </div>
    );
  };

  // Render header with result count
  const renderHeader = () => {
    if (!query || results.length === 0) {
      return null;
    }

    return (
      <div className="mb-4 px-1">
        <p className="text-sm text-muted-foreground">
          {results.length} contact{results.length !== 1 ? 's' : ''} found for "{query}"
        </p>
      </div>
    );
  };

  return (
    <div className={cn('space-y-2', className)}>
      {renderHeader()}
      
      {results.length > 0 ? (
        <div className="space-y-2">
          {results.map(renderContactResult)}
        </div>
      ) : (
        renderEmptyState()
      )}
    </div>
  );
};