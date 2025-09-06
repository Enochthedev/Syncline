/**
 * ResponsiveUIDemo Screen
 * 
 * Demonstrates responsive UI components and navigation
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { SearchBar } from '../components/SearchBar';
import { ContactCard } from '../components/ContactCard';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { ResponsiveLayout, useResponsiveDimensions } from '../components/ResponsiveLayout';
import { useTheme } from '../hooks/useTheme';

export const ResponsiveUIDemoScreen: React.FC = () => {
  const { theme } = useTheme();
  const { isPhone, isTablet, isDesktop, screenWidth } = useResponsiveDimensions();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [showLoading, setShowLoading] = useState(false);
  const [showError, setShowError] = useState(false);
  const [showEmpty, setShowEmpty] = useState(false);

  // Mock contact data
  const mockContact = {
    id: '1',
    primary_name: 'John Doe',
    display_name: 'John Doe',
    primary_email: 'john@example.com',
    primary_phone: '+1234567890',
    profile_photo_url: undefined,
    platforms: ['gmail', 'slack'],
    total_messages: 42,
    last_interaction: '2024-01-15T10:30:00Z',
    relationship_strength: 0.8,
    communication_frequency: 'high',
    is_favorite: true,
    interaction_indicators: {
      has_recent_messages: true,
      is_frequent_contact: true,
      has_unread_messages: false,
    },
    recent_interaction: {
      has_recent: true,
      days_since: 2,
      interaction_level: 'this_week',
    },
  };

  const handleContactPress = (contact: any) => {
    console.log('Contact pressed:', contact.primary_name);
  };

  const handleRetry = () => {
    setShowError(false);
    setShowLoading(true);
    setTimeout(() => setShowLoading(false), 2000);
  };

  const handleAddContact = () => {
    console.log('Add contact pressed');
  };

  const deviceInfo = `${isPhone ? 'Phone' : isTablet ? 'Tablet' : isDesktop ? 'Desktop' : 'Unknown'} (${screenWidth}px)`;

  return (
    <ResponsiveLayout scrollable>
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Responsive UI Demo
        </Text>
        <Text style={[styles.deviceInfo, { color: theme.colors.textSecondary }]}>
          Device: {deviceInfo}
        </Text>
      </View>

      {/* Search Bar Section */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Search Bar
        </Text>
        <SearchBar
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search contacts..."
          showVoiceButton={true}
          onVoicePress={() => console.log('Voice pressed')}
          isLoading={showLoading}
        />
      </View>

      {/* Contact Card Section */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Contact Card
        </Text>
        <ContactCard
          contact={mockContact}
          onPress={handleContactPress}
          showDetails={true}
        />
      </View>

      {/* Loading States Section */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Loading States
        </Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.demoButton, { backgroundColor: theme.colors.primary }]}
            onPress={() => setShowLoading(!showLoading)}
          >
            <Text style={[styles.buttonText, { color: theme.colors.surface }]}>
              Toggle Loading
            </Text>
          </TouchableOpacity>
        </View>
        {showLoading && (
          <LoadingSpinner
            size="medium"
            message="Loading contacts..."
          />
        )}
      </View>

      {/* Error States Section */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Error States
        </Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.demoButton, { backgroundColor: theme.colors.error }]}
            onPress={() => setShowError(!showError)}
          >
            <Text style={[styles.buttonText, { color: theme.colors.surface }]}>
              Toggle Error
            </Text>
          </TouchableOpacity>
        </View>
        {showError && (
          <ErrorMessage
            title="Connection Error"
            message="Unable to load contacts. Please check your internet connection and try again."
            onRetry={handleRetry}
            type="error"
          />
        )}
      </View>

      {/* Empty States Section */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Empty States
        </Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.demoButton, { backgroundColor: theme.colors.secondary }]}
            onPress={() => setShowEmpty(!showEmpty)}
          >
            <Text style={[styles.buttonText, { color: theme.colors.surface }]}>
              Toggle Empty
            </Text>
          </TouchableOpacity>
        </View>
        {showEmpty && (
          <EmptyState
            icon="people-outline"
            title="No Contacts Found"
            message="You haven't added any contacts yet. Start by connecting your communication platforms."
            actionText="Add Contact"
            onAction={handleAddContact}
          />
        )}
      </View>

      {/* Component Variations */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Component Variations
        </Text>
        
        {/* Different sized loading spinners */}
        <View style={styles.variationRow}>
          <LoadingSpinner size="small" />
          <LoadingSpinner size="medium" />
          <LoadingSpinner size="large" />
        </View>

        {/* Different error types */}
        <ErrorMessage
          message="This is a warning message"
          type="warning"
          style={styles.marginTop}
        />
        
        <ErrorMessage
          message="This is an info message"
          type="info"
          style={styles.marginTop}
        />
      </View>

      {/* Responsive Behavior */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
          Responsive Behavior
        </Text>
        <View style={[styles.responsiveDemo, { backgroundColor: theme.colors.surface }]}>
          <Text style={[styles.responsiveText, { color: theme.colors.text }]}>
            Screen Width: {screenWidth}px
          </Text>
          <Text style={[styles.responsiveText, { color: theme.colors.text }]}>
            Device Type: {isPhone ? 'Phone' : isTablet ? 'Tablet' : 'Desktop'}
          </Text>
          <Text style={[styles.responsiveText, { color: theme.colors.text }]}>
            Layout: {isPhone ? 'Mobile Layout' : isTablet ? 'Tablet Layout' : 'Desktop Layout'}
          </Text>
        </View>
      </View>
    </ResponsiveLayout>
  );
};

const styles = StyleSheet.create({
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  deviceInfo: {
    fontSize: 14,
    marginBottom: 16,
    fontStyle: 'italic',
  },
  buttonRow: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  demoButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    marginRight: 12,
  },
  buttonText: {
    fontWeight: '600',
  },
  variationRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 16,
  },
  marginTop: {
    marginTop: 12,
  },
  responsiveDemo: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  responsiveText: {
    fontSize: 14,
    marginBottom: 4,
  },
});