/**
 * ContactSearchContainer Component (Web Version)
 * 
 * Container component that integrates all contact search functionality
 * with API integration and state management
 */

'use client'

import React, { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ContactSearchInput } from '../ContactSearchInput';
import { ContactSearchResults } from './ContactSearchResults';
import { ContactSuggestions } from './ContactSuggestions';
import { useDebounce } from '@/hooks/useDebounce';
import { contactSearchService } from '@/services/contactSearchService';
import { UnifiedContact } from '@/types';
import { cn } from '@/utils/cn';

interface ContactSearchContainerProps {
  onContactSelect: (contact: UnifiedContact) => void;
  initialQuery?: string;
  autoFocus?: boolean;
  showSuggestions?: boolean;
  showRecentContacts?: boolean;
  placeholder?: string;
  className?: string;
}

export const ContactSearchContainer: React.FC<ContactSearchContainerProps> = ({
  onContactSelect,
  initialQuery = '',
  autoFocus = false,
  showSuggestions = true,
  showRecentContacts = true,
  placeholder = "Search contacts...",
  className,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState<UnifiedContact[]>([]);
  const [showResults, setShowResults] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  // Real-time contact search
  const {
    data: searchData,
    isLoading: isSearchLoading,
    error: searchError,
    refetch: refetchSearch,
  } = useQuery({
    queryKey: ['contactSearch', debouncedQuery],
    queryFn: () => contactSearchService.searchContactsRealtime(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30000,
    retry: 2,
  });

  // Search suggestions
  const {
    data: suggestionsData,
    isLoading: isSuggestionsLoading,
  } = useQuery({
    queryKey: ['contactSuggestions', debouncedQuery],
    queryFn: () => contactSearchService.getSearchSuggestions(debouncedQuery),
    enabled: debouncedQuery.length >= 1 && showSuggestions,
    staleTime: 60000,
  });

  // Recent contacts (mock data for now)
  const {
    data: recentContactsData,
  } = useQuery({
    queryKey: ['recentContacts'],
    queryFn: async () => {
      // This would be replaced with actual API call
      return [];
    },
    enabled: showRecentContacts && query.length === 0,
    staleTime: 300000, // 5 minutes
  });

  // Update search results when data changes
  useEffect(() => {
    if (searchData?.contacts) {
      setSearchResults(searchData.contacts);
      setShowResults(true);
    } else {
      setSearchResults([]);
      setShowResults(debouncedQuery.length >= 2);
    }
  }, [searchData, debouncedQuery]);

  // Handle contact selection
  const handleContactSelect = useCallback((contact: UnifiedContact) => {
    setQuery(contact.displayName);
    setShowResults(false);
    onContactSelect(contact);
  }, [onContactSelect]);

  // Handle search results update
  const handleSearchResults = useCallback((results: UnifiedContact[]) => {
    setSearchResults(results);
  }, []);

  // Handle query changes
  const handleQueryChange = useCallback((newQuery: string) => {
    setQuery(newQuery);
    if (newQuery.length < 2) {
      setShowResults(false);
      setSearchResults([]);
    }
  }, []);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Search Input */}
      <div className="relative">
        <ContactSearchInput
          onContactSelect={handleContactSelect}
          onSearchResults={handleSearchResults}
          placeholder={placeholder}
          autoFocus={autoFocus}
          showSuggestions={showSuggestions}
        />
      </div>

      {/* Show suggestions when not searching */}
      {!showResults && (showSuggestions || showRecentContacts) && (
        <div className="space-y-4">
          {/* Search Suggestions */}
          {showSuggestions && suggestionsData && suggestionsData.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">
                Search Suggestions
              </h3>
              <div className="flex flex-wrap gap-2">
                {suggestionsData.slice(0, 5).map((suggestion: any, index: number) => (
                  <button
                    key={index}
                    onClick={() => setQuery(suggestion.text || suggestion.query)}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                  >
                    <span className="mr-1">
                      {suggestion.type === 'recent' && '🕒'}
                      {suggestion.type === 'frequent' && '⭐'}
                      {suggestion.type === 'suggested' && '💡'}
                      {suggestion.type === 'query' && '🔍'}
                      {!suggestion.type && '👤'}
                    </span>
                    {suggestion.text || suggestion.query}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recent Contacts */}
          {showRecentContacts && recentContactsData && recentContactsData.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">
                Recent Contacts
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {recentContactsData.slice(0, 6).map((contact: UnifiedContact) => (
                  <button
                    key={contact.id}
                    onClick={() => handleContactSelect(contact)}
                    className="flex items-center space-x-3 p-3 rounded-lg border border-border hover:bg-accent transition-colors text-left"
                  >
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
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {contact.displayName}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {contact.totalMessages} messages
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Empty State for Suggestions */}
          {(!suggestionsData || suggestionsData.length === 0) &&
           (!recentContactsData || recentContactsData.length === 0) &&
           !isSuggestionsLoading && (
            <div className="text-center py-8">
              <div className="text-4xl mb-2">👥</div>
              <p className="text-muted-foreground">
                Start typing to search for contacts
              </p>
            </div>
          )}

          {/* Loading State */}
          {isSuggestionsLoading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2"></div>
              <p className="text-muted-foreground">Loading suggestions...</p>
            </div>
          )}
        </div>
      )}

      {/* Show search results when searching */}
      {showResults && (
        <ContactSearchResults
          results={searchResults}
          query={debouncedQuery}
          isLoading={isSearchLoading}
          error={searchError?.message}
          onContactSelect={handleContactSelect}
          showDetails={true}
        />
      )}
    </div>
  );
};