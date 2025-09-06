/**
 * Enhanced Contact Search Component with Comprehensive Error Handling
 * Demonstrates integration of the error handling and user feedback systems
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator
} from 'react-native';
import ErrorBoundary from './ErrorBoundary';
import ErrorFeedback from './ErrorFeedback';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { ErrorType, AppError } from '../types/errors';
import CrashReporter from '../services/crashReporter';

interface Contact {
  id: string;
  name: string;
  email: string;
  platforms: string[];
}

interface EnhancedContactSearchProps {
  onContactSelect: (contact: Contact) => void;
}

const EnhancedContactSearch: React.FC<EnhancedContactSearchProps> = ({
  onContactSelect
}) => {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showErrorFeedback, setShowErrorFeedback] = useState(false);
  const [currentError, setCurrentError] = useState<AppError | null>(null);

  const crashReporter = CrashReporter.getInstance();

  // Enhanced error handler with comprehensive options
  const {
    error,
    isRetrying,
    retryCount,
    handleError,
    retryLastOperation,
    clearError,
    executeWithRetry
  } = useErrorHandler({
    showUserFeedback: true,
    autoRetry: false, // Manual retry for better UX
    maxRetries: 3,
    onError: (error) => {
      console.log('Search error:', error.type, error.message);
      crashReporter.addBreadcrumb('error', `Search error: ${error.type}`, 'error');
      setCurrentError(error);
    },
    onResolution: (resolution) => {
      console.log('Error resolved:', resolution.action);
      if (resolution.resolved) {
        setCurrentError(null);
      }
    }
  });

  // Simulate contact search API call
  const searchContacts = useCallback(async (searchQuery: string): Promise<Contact[]> => {
    // Add breadcrumb for user action
    crashReporter.recordUserAction('search', 'ContactSearch', 'search_input', {
      query: searchQuery
    });

    // Simulate various failure scenarios for testing
    const random = Math.random();
    
    if (random < 0.1) {
      throw new Error('Network request failed');
    } else if (random < 0.15) {
      throw new Error('Search service unavailable');
    } else if (random < 0.2) {
      throw new Error('Authentication token expired');
    } else if (random < 0.25) {
      throw new Error('Rate limit exceeded');
    }

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));

    // Return mock data
    return [
      {
        id: '1',
        name: `John Doe (${searchQuery})`,
        email: 'john@example.com',
        platforms: ['email', 'slack']
      },
      {
        id: '2',
        name: `Jane Smith (${searchQuery})`,
        email: 'jane@example.com',
        platforms: ['email', 'teams']
      }
    ];
  }, [crashReporter]);

  // Enhanced search with comprehensive error handling
  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setContacts([]);
      return;
    }

    setIsLoading(true);
    crashReporter.addBreadcrumb('user_action', `Searching for: ${searchQuery}`, 'info');

    try {
      const results = await executeWithRetry(
        () => searchContacts(searchQuery),
        ErrorType.SEARCH_TIMEOUT,
        {
          maxRetries: 3,
          baseDelay: 1000,
          backoffMultiplier: 2,
          retryableErrors: [
            ErrorType.NETWORK_UNAVAILABLE,
            ErrorType.API_TIMEOUT,
            ErrorType.SEARCH_TIMEOUT
          ]
        }
      );

      setContacts(results);
      crashReporter.addBreadcrumb('success', `Found ${results.length} contacts`, 'info');
    } catch (error) {
      const resolution = await handleError(error as Error, {
        screenName: 'ContactSearch',
        actionAttempted: 'search_contacts',
        additionalData: {
          query: searchQuery,
          retryCount,
          timestamp: new Date().toISOString()
        }
      });

      // Handle different resolution actions
      if (resolution.action === 'fallback' && resolution.fallbackData) {
        setContacts(resolution.fallbackData);
        Alert.alert('Notice', resolution.message || 'Using cached data');
      } else if (resolution.action === 'user_action') {
        // Show error feedback modal for user action
        setShowErrorFeedback(true);
      }
    } finally {
      setIsLoading(false);
    }
  }, [executeWithRetry, handleError, retryCount, searchContacts, crashReporter]);

  // Handle contact selection with error handling
  const handleContactSelection = useCallback(async (contact: Contact) => {
    crashReporter.recordUserAction('select', 'ContactSearch', 'contact_item', {
      contactId: contact.id,
      contactName: contact.name
    });

    try {
      await executeWithRetry(
        () => Promise.resolve(onContactSelect(contact)),
        ErrorType.CONTACT_NOT_FOUND
      );
    } catch (error) {
      await handleError(error as Error, {
        screenName: 'ContactSearch',
        actionAttempted: 'select_contact',
        additionalData: { contactId: contact.id }
      });
    }
  }, [onContactSelect, executeWithRetry, handleError, crashReporter]);

  // Handle manual retry
  const handleRetry = useCallback(async () => {
    clearError();
    await retryLastOperation();
  }, [clearError, retryLastOperation]);

  // Handle error feedback submission
  const handleErrorFeedbackSubmit = useCallback(async (feedback: string) => {
    if (currentError) {
      try {
        await crashReporter.reportError(currentError.id, feedback);
        Alert.alert('Thank You', 'Your feedback has been submitted.');
      } catch (reportError) {
        Alert.alert('Error', 'Failed to submit feedback. Please try again.');
      }
    }
    setShowErrorFeedback(false);
  }, [currentError, crashReporter]);

  // Simulate different error scenarios for testing
  const simulateError = useCallback(async (errorType: string) => {
    let error: Error;
    
    switch (errorType) {
      case 'network':
        error = new Error('Network connection failed');
        break;
      case 'auth':
        error = new Error('Authentication token expired');
        break;
      case 'storage':
        error = new Error('Device storage full');
        break;
      case 'critical':
        error = new Error('Critical system failure');
        break;
      default:
        error = new Error('Unknown error occurred');
    }

    await handleError(error, {
      screenName: 'ContactSearch',
      actionAttempted: 'simulate_error',
      additionalData: { errorType }
    });
  }, [handleError]);

  return (
    <ErrorBoundary
      onError={(error) => {
        crashReporter.recordUnhandledError(error.originalError || new Error(error.message), 'component_error');
      }}
    >
      <View style={styles.container}>
        <Text style={styles.title}>Enhanced Contact Search</Text>
        
        {/* Search Input */}
        <View style={styles.searchContainer}>
          <TouchableOpacity
            style={styles.searchButton}
            onPress={() => handleSearch('test query')}
            disabled={isLoading || isRetrying}
          >
            {isLoading || isRetrying ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.searchButtonText}>
                {isRetrying ? `Retrying (${retryCount})...` : 'Search Contacts'}
              </Text>
            )}
          </TouchableOpacity>
        </View>

        {/* Error Display */}
        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorTitle}>Error Occurred</Text>
            <Text style={styles.errorMessage}>{error.userMessage}</Text>
            <Text style={styles.errorDetails}>
              Type: {error.type} | Severity: {error.severity}
            </Text>
            
            <View style={styles.errorActions}>
              {error.retryable && (
                <TouchableOpacity
                  style={[styles.actionButton, styles.retryButton]}
                  onPress={handleRetry}
                  disabled={isRetrying}
                >
                  <Text style={styles.actionButtonText}>
                    {isRetrying ? 'Retrying...' : 'Retry'}
                  </Text>
                </TouchableOpacity>
              )}
              
              <TouchableOpacity
                style={[styles.actionButton, styles.feedbackButton]}
                onPress={() => setShowErrorFeedback(true)}
              >
                <Text style={styles.actionButtonText}>Report Issue</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[styles.actionButton, styles.dismissButton]}
                onPress={clearError}
              >
                <Text style={styles.actionButtonText}>Dismiss</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Contact Results */}
        <View style={styles.resultsContainer}>
          <Text style={styles.resultsTitle}>
            Search Results ({contacts.length})
          </Text>
          {contacts.map((contact) => (
            <TouchableOpacity
              key={contact.id}
              style={styles.contactItem}
              onPress={() => handleContactSelection(contact)}
            >
              <Text style={styles.contactName}>{contact.name}</Text>
              <Text style={styles.contactEmail}>{contact.email}</Text>
              <View style={styles.platformTags}>
                {contact.platforms.map((platform) => (
                  <Text key={platform} style={styles.platformTag}>
                    {platform}
                  </Text>
                ))}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Error Simulation Buttons (for testing) */}
        <View style={styles.testContainer}>
          <Text style={styles.testTitle}>Test Error Scenarios:</Text>
          <View style={styles.testButtons}>
            <TouchableOpacity
              style={styles.testButton}
              onPress={() => simulateError('network')}
            >
              <Text style={styles.testButtonText}>Network Error</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.testButton}
              onPress={() => simulateError('auth')}
            >
              <Text style={styles.testButtonText}>Auth Error</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.testButton}
              onPress={() => simulateError('storage')}
            >
              <Text style={styles.testButtonText}>Storage Error</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.testButton}
              onPress={() => simulateError('critical')}
            >
              <Text style={styles.testButtonText}>Critical Error</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Error Feedback Modal */}
        <ErrorFeedback
          visible={showErrorFeedback}
          error={currentError}
          onClose={() => setShowErrorFeedback(false)}
          onSubmit={handleErrorFeedbackSubmit}
        />
      </View>
    </ErrorBoundary>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center'
  },
  searchContainer: {
    marginBottom: 20
  },
  searchButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center'
  },
  searchButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600'
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 16,
    borderRadius: 8,
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#f44336'
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#d32f2f',
    marginBottom: 8
  },
  errorMessage: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8
  },
  errorDetails: {
    fontSize: 12,
    color: '#999',
    marginBottom: 12
  },
  errorActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8
  },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    minWidth: 80
  },
  retryButton: {
    backgroundColor: '#4CAF50'
  },
  feedbackButton: {
    backgroundColor: '#FF9800'
  },
  dismissButton: {
    backgroundColor: '#9E9E9E'
  },
  actionButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center'
  },
  resultsContainer: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 20
  },
  resultsTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12
  },
  contactItem: {
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  contactName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4
  },
  contactEmail: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8
  },
  platformTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4
  },
  platformTag: {
    backgroundColor: '#e3f2fd',
    color: '#1976d2',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    fontSize: 12,
    fontWeight: '500'
  },
  testContainer: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16
  },
  testTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12
  },
  testButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8
  },
  testButton: {
    backgroundColor: '#f44336',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6
  },
  testButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600'
  }
});

export default EnhancedContactSearch;