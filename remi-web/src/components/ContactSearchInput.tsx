/**
 * ContactSearchInput Component (Web Version)
 * 
 * Real-time contact search input with fuzzy matching and suggestions for web
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import { contactSearchService } from '../services/contactSearchService';

interface ContactSearchInputProps {
  onContactSelect: (contact: any) => void;
  onSearchResults: (results: any[]) => void;
  placeholder?: string;
  autoFocus?: boolean;
  showSuggestions?: boolean;
  className?: string;
}

export const ContactSearchInput: React.FC<ContactSearchInputProps> = ({
  onContactSelect,
  onSearchResults,
  placeholder = "Search contacts...",
  autoFocus = false,
  showSuggestions = true,
  className = "",
}) => {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  // Real-time contact search
  const { data: searchResults, isLoading, error } = useQuery({
    queryKey: ['contactSearch', debouncedQuery],
    queryFn: () => contactSearchService.searchContactsRealtime(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30000,
  });

  // Update parent with search results
  useEffect(() => {
    if (searchResults?.contacts) {
      onSearchResults(searchResults.contacts);
    }
  }, [searchResults, onSearchResults]);

  // Handle text input changes
  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setQuery(text);
    setShowResults(text.length >= 2);
  }, []);

  // Handle contact selection
  const handleContactSelect = useCallback((contact: any) => {
    setQuery(contact.primary_name || contact.display_name);
    setShowResults(false);
    onContactSelect(contact);
  }, [onContactSelect]);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: any) => {
    if (suggestion.contact_id) {
      const contact = searchResults?.contacts?.find(
        (c: any) => c.id === suggestion.contact_id
      );
      if (contact) {
        handleContactSelect(contact);
      }
    } else {
      setQuery(suggestion.text);
    }
  }, [searchResults, handleContactSelect]);

  // Clear search
  const handleClear = useCallback(() => {
    setQuery('');
    setShowResults(false);
    onSearchResults([]);
  }, [onSearchResults]);

  return (
    <div className={`relative ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={handleQueryChange}
          placeholder={placeholder}
          autoFocus={autoFocus}
          autoComplete="off"
          className="w-full px-4 py-3 pr-12 text-gray-900 bg-white border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        
        {isLoading && (
          <div className="absolute right-10 top-1/2 transform -translate-y-1/2">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
          </div>
        )}
        
        {query.length > 0 && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Search Results */}
      {showResults && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
          {error && (
            <div className="p-4 text-center text-red-600">
              Search failed. Please try again.
            </div>
          )}

          {searchResults?.contacts && searchResults.contacts.length > 0 && (
            <div className="py-2">
              {searchResults.contacts.map((contact: any) => (
                <button
                  key={contact.id}
                  onClick={() => handleContactSelect(contact)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">
                        {contact.primary_name || contact.display_name}
                      </div>
                      {contact.primary_email && (
                        <div className="text-sm text-gray-500">
                          {contact.primary_email}
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1 mt-1">
                        {contact.platforms?.map((platform: string) => (
                          <span
                            key={platform}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {platform.toUpperCase()}
                          </span>
                        ))}
                      </div>
                    </div>
                    {contact.interaction_indicators?.has_recent_messages && (
                      <div className="w-2 h-2 bg-green-400 rounded-full ml-2"></div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {showSuggestions && searchResults?.suggestions && searchResults.suggestions.length > 0 && (
            <div className="border-t border-gray-100 p-3">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Suggestions
              </div>
              <div className="flex flex-wrap gap-2">
                {searchResults.suggestions.map((suggestion: any, index: number) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionSelect(suggestion)}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {suggestion.type === 'name' && '👤'}
                    {suggestion.type === 'handle' && '@'}
                    {suggestion.type === 'recent' && '🕒'}
                    {suggestion.type === 'email' && '📧'}
                    <span className="ml-1">{suggestion.text}</span>
                    {suggestion.platform && (
                      <span className="ml-1 text-xs text-blue-600">
                        {suggestion.platform}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {debouncedQuery.length >= 2 && 
           !isLoading && 
           (!searchResults?.contacts || searchResults.contacts.length === 0) && (
            <div className="p-4 text-center text-gray-500">
              No contacts found for "{debouncedQuery}"
            </div>
          )}
        </div>
      )}
    </div>
  );
};