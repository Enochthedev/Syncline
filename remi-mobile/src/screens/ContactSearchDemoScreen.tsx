/**
 * Contact Search Demo Screen
 * 
 * Demonstrates the contact search functionality with real API integration
 */

import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  Alert,
} from 'react-native';
import { ContactSearchInput } from '../components/ContactSearchInput';
import { ContactCard } from '../components/ContactCard';
import { useTheme } from '../hooks/useTheme';

export const ContactSearchDemoScreen: React.FC = () => {
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedContact, setSelectedContact] = useState<any | null>(null);
  const { theme } = useTheme();

  const handleSearchResults = useCallback((results: any[]) => {
    setSearchResults(results);
  }, []);

  const handleContactSelect = useCallback((contact: any) => {
    setSelectedContact(contact);
    Alert.alert(
      'Contact Selected',
      `You selected ${contact.primary_name || contact.display_name}`,
      [
        {
          text: 'View Profile',
          onPress: () => {
            // Navigate to contact profile
            console.log('Navigate to contact profile:', contact.id);
          },
        },
        {
          text: 'View Messages',
          onPress: () => {
            // Navigate to contact messages
            console.log('Navigate to contact messages:', contact.id);
          },
        },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  }, []);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <ScrollView style={styles.scrollView} keyboardShouldPersistTaps="handled">
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.colors.text }]}>
            Contact Search Demo
          </Text>
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            Try searching for contacts with fuzzy matching and natural language queries
          </Text>
        </View>

        {/* Search Input */}
        <View style={styles.searchSection}>
          <ContactSearchInput
            onContactSelect={handleContactSelect}
            onSearchResults={handleSearchResults}
            placeholder="Search contacts... (try 'John', 'john@example.com', or '@handle')"
            showSuggestions={true}
          />
        </View>

        {/* Example Queries */}
        <View style={styles.examplesSection}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Example Searches:
          </Text>
          <View style={styles.examplesList}>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "John Smith" - Search by name
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "john@company.com" - Search by email
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "+1-555-0123" - Search by phone
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "@johnsmith" - Search by handle
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "Jon Smth" - Fuzzy matching with typos
            </Text>
          </View>
        </View>

        {/* Selected Contact */}
        {selectedContact && (
          <View style={styles.selectedSection}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Selected Contact:
            </Text>
            <ContactCard
              contact={selectedContact}
              onPress={handleContactSelect}
              showDetails={true}
            />
          </View>
        )}

        {/* Search Results */}
        {searchResults.length > 0 && (
          <View style={styles.resultsSection}>
            <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
              Search Results ({searchResults.length}):
            </Text>
            {searchResults.map((contact) => (
              <ContactCard
                key={contact.id}
                contact={contact}
                onPress={handleContactSelect}
                showDetails={false}
              />
            ))}
          </View>
        )}

        {/* Natural Language Examples */}
        <View style={styles.nlSection}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Natural Language Queries:
          </Text>
          <Text style={[styles.nlDescription, { color: theme.colors.textSecondary }]}>
            The system also supports natural language queries for more complex searches:
          </Text>
          <View style={styles.nlExamplesList}>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "messages with John Smith"
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "files shared with Sarah"
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "what did I promise to Mike"
            </Text>
            <Text style={[styles.exampleText, { color: theme.colors.textSecondary }]}>
              • "conversations with team members"
            </Text>
          </View>
        </View>

        {/* API Features */}
        <View style={styles.featuresSection}>
          <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
            Features Demonstrated:
          </Text>
          <View style={styles.featuresList}>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Real-time search with fuzzy matching
            </Text>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Contact suggestions and autocomplete
            </Text>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Platform indicators and interaction status
            </Text>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Relationship strength visualization
            </Text>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Recent activity indicators
            </Text>
            <Text style={[styles.featureText, { color: theme.colors.textSecondary }]}>
              ✓ Multi-platform contact unification
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  header: {
    padding: 20,
    paddingBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    lineHeight: 22,
  },
  searchSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  examplesSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  examplesList: {
    paddingLeft: 8,
  },
  exampleText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 4,
  },
  selectedSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  resultsSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  nlSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  nlDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  nlExamplesList: {
    paddingLeft: 8,
  },
  featuresSection: {
    paddingHorizontal: 20,
    marginBottom: 40,
  },
  featuresList: {
    paddingLeft: 8,
  },
  featureText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 4,
  },
});