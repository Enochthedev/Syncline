/**
 * ContactProfile Component
 * 
 * Displays unified contact information and platform identities
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Linking,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';
import { UnifiedContact, ContactIdentity, SocialProfile } from '../types';

interface ContactProfileProps {
  contact: UnifiedContact;
  onMessagePress?: () => void;
  onCallPress?: () => void;
  onEmailPress?: () => void;
  onViewMessagesPress?: () => void;
  onViewSharedContentPress?: () => void;
}

export const ContactProfile: React.FC<ContactProfileProps> = ({
  contact,
  onMessagePress,
  onCallPress,
  onEmailPress,
  onViewMessagesPress,
  onViewSharedContentPress,
}) => {
  const { theme } = useTheme();

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatResponseTime = (minutes: number) => {
    if (minutes < 60) return `${Math.round(minutes)}m`;
    if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
    return `${Math.round(minutes / 1440)}d`;
  };

  const getFrequencyColor = (frequency: string) => {
    switch (frequency) {
      case 'high': return theme.colors.success;
      case 'medium': return theme.colors.warning;
      case 'low': return theme.colors.error;
      default: return theme.colors.textSecondary;
    }
  };

  const getPlatformIcon = (platform: string) => {
    const platformIcons: Record<string, string> = {
      gmail: 'mail',
      slack: 'chatbubbles',
      discord: 'game-controller',
      whatsapp: 'logo-whatsapp',
      twitter: 'logo-twitter',
      linkedin: 'logo-linkedin',
      telegram: 'paper-plane',
    };
    return platformIcons[platform.toLowerCase()] || 'globe';
  };

  const handleSocialProfilePress = (profile: SocialProfile) => {
    Linking.openURL(profile.url);
  };

  const handleEmailPress = (email: string) => {
    Linking.openURL(`mailto:${email}`);
  };

  const handlePhonePress = (phone: string) => {
    Linking.openURL(`tel:${phone}`);
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {/* Header Section */}
      <View style={[styles.header, { backgroundColor: theme.colors.surface }]}>
        <View style={styles.avatarContainer}>
          {contact.profilePhoto ? (
            <Image source={{ uri: contact.profilePhoto }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatarPlaceholder, { backgroundColor: theme.colors.primary }]}>
              <Text style={[styles.avatarText, { color: theme.colors.white }]}>
                {contact.primaryName[0].toUpperCase()}
              </Text>
            </View>
          )}
        </View>

        <View style={styles.headerInfo}>
          <Text style={[styles.primaryName, { color: theme.colors.text }]}>
            {contact.primaryName}
          </Text>
          {contact.displayName !== contact.primaryName && (
            <Text style={[styles.displayName, { color: theme.colors.textSecondary }]}>
              {contact.displayName}
            </Text>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          {onMessagePress && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.primary }]}
              onPress={onMessagePress}
            >
              <Icon name="chatbubble" size={20} color={theme.colors.white} />
            </TouchableOpacity>
          )}
          {contact.phoneNumbers.length > 0 && onCallPress && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.success }]}
              onPress={onCallPress}
            >
              <Icon name="call" size={20} color={theme.colors.white} />
            </TouchableOpacity>
          )}
          {contact.emails.length > 0 && onEmailPress && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: theme.colors.warning }]}
              onPress={onEmailPress}
            >
              <Icon name="mail" size={20} color={theme.colors.white} />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Contact Information */}
      <View style={[styles.section, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>Contact Information</Text>
        
        {contact.emails.map((email, index) => (
          <TouchableOpacity
            key={index}
            style={styles.contactItem}
            onPress={() => handleEmailPress(email)}
          >
            <Icon name="mail" size={16} color={theme.colors.primary} />
            <Text style={[styles.contactText, { color: theme.colors.text }]}>{email}</Text>
          </TouchableOpacity>
        ))}

        {contact.phoneNumbers.map((phone, index) => (
          <TouchableOpacity
            key={index}
            style={styles.contactItem}
            onPress={() => handlePhonePress(phone)}
          >
            <Icon name="call" size={16} color={theme.colors.primary} />
            <Text style={[styles.contactText, { color: theme.colors.text }]}>{phone}</Text>
          </TouchableOpacity>
        ))}

        {contact.socialProfiles.map((profile, index) => (
          <TouchableOpacity
            key={index}
            style={styles.contactItem}
            onPress={() => handleSocialProfilePress(profile)}
          >
            <Icon name={getPlatformIcon(profile.platform)} size={16} color={theme.colors.primary} />
            <Text style={[styles.contactText, { color: theme.colors.text }]}>
              {profile.handle} ({profile.platform})
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Platform Identities */}
      <View style={[styles.section, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>Platform Identities</Text>
        
        {contact.identities.map((identity: ContactIdentity, index) => (
          <View key={index} style={styles.identityItem}>
            <View style={styles.identityHeader}>
              <Icon 
                name={getPlatformIcon(identity.platform)} 
                size={20} 
                color={theme.colors.primary} 
              />
              <Text style={[styles.identityPlatform, { color: theme.colors.text }]}>
                {identity.platform.charAt(0).toUpperCase() + identity.platform.slice(1)}
              </Text>
              {identity.verified && (
                <Icon name="checkmark-circle" size={16} color={theme.colors.success} />
              )}
            </View>
            <Text style={[styles.identityName, { color: theme.colors.textSecondary }]}>
              {identity.displayName}
            </Text>
            {identity.handle && (
              <Text style={[styles.identityHandle, { color: theme.colors.textSecondary }]}>
                @{identity.handle}
              </Text>
            )}
          </View>
        ))}
      </View>

      {/* Communication Insights */}
      <View style={[styles.section, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>Communication Insights</Text>
        
        <View style={styles.insightGrid}>
          <View style={styles.insightItem}>
            <Text style={[styles.insightLabel, { color: theme.colors.textSecondary }]}>
              Total Messages
            </Text>
            <Text style={[styles.insightValue, { color: theme.colors.text }]}>
              {contact.totalMessages.toLocaleString()}
            </Text>
          </View>

          <View style={styles.insightItem}>
            <Text style={[styles.insightLabel, { color: theme.colors.textSecondary }]}>
              Frequency
            </Text>
            <Text style={[styles.insightValue, { color: getFrequencyColor(contact.communicationFrequency) }]}>
              {contact.communicationFrequency.charAt(0).toUpperCase() + contact.communicationFrequency.slice(1)}
            </Text>
          </View>

          <View style={styles.insightItem}>
            <Text style={[styles.insightLabel, { color: theme.colors.textSecondary }]}>
              Relationship Strength
            </Text>
            <Text style={[styles.insightValue, { color: theme.colors.text }]}>
              {Math.round(contact.relationshipStrength * 100)}%
            </Text>
          </View>

          <View style={styles.insightItem}>
            <Text style={[styles.insightLabel, { color: theme.colors.textSecondary }]}>
              Response Time
            </Text>
            <Text style={[styles.insightValue, { color: theme.colors.text }]}>
              {formatResponseTime(contact.responsePattern.averageResponseTime)}
            </Text>
          </View>
        </View>

        <View style={styles.responsePatternContainer}>
          <Text style={[styles.responsePatternLabel, { color: theme.colors.textSecondary }]}>
            Communication Style: {contact.responsePattern.communicationStyle}
          </Text>
          <Text style={[styles.responsePatternLabel, { color: theme.colors.textSecondary }]}>
            Response Rate: {Math.round(contact.responsePattern.responseRate * 100)}%
          </Text>
        </View>
      </View>

      {/* Quick Actions */}
      <View style={[styles.section, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>Quick Actions</Text>
        
        {onViewMessagesPress && (
          <TouchableOpacity
            style={[styles.quickAction, { borderColor: theme.colors.border }]}
            onPress={onViewMessagesPress}
          >
            <Icon name="chatbubbles" size={20} color={theme.colors.primary} />
            <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
              View Messages ({contact.totalMessages})
            </Text>
            <Icon name="chevron-forward" size={16} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        )}

        {onViewSharedContentPress && (
          <TouchableOpacity
            style={[styles.quickAction, { borderColor: theme.colors.border }]}
            onPress={onViewSharedContentPress}
          >
            <Icon name="folder" size={20} color={theme.colors.primary} />
            <Text style={[styles.quickActionText, { color: theme.colors.text }]}>
              Shared Content ({contact.sharedFiles.length + contact.sharedLinks.length})
            </Text>
            <Icon name="chevron-forward" size={16} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Metadata */}
      <View style={[styles.section, { backgroundColor: theme.colors.surface }]}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>Information</Text>
        
        <View style={styles.metadataItem}>
          <Text style={[styles.metadataLabel, { color: theme.colors.textSecondary }]}>
            Last Interaction:
          </Text>
          <Text style={[styles.metadataValue, { color: theme.colors.text }]}>
            {formatDate(contact.lastInteraction)}
          </Text>
        </View>

        <View style={styles.metadataItem}>
          <Text style={[styles.metadataLabel, { color: theme.colors.textSecondary }]}>
            Last Sync:
          </Text>
          <Text style={[styles.metadataValue, { color: theme.colors.text }]}>
            {formatDate(contact.lastSyncAt)}
          </Text>
        </View>

        <View style={styles.metadataItem}>
          <Text style={[styles.metadataLabel, { color: theme.colors.textSecondary }]}>
            Platforms:
          </Text>
          <Text style={[styles.metadataValue, { color: theme.colors.text }]}>
            {contact.platforms.join(', ')}
          </Text>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    marginBottom: 8,
  },
  avatarContainer: {
    marginRight: 16,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
  },
  avatarPlaceholder: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  headerInfo: {
    flex: 1,
  },
  primaryName: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  displayName: {
    fontSize: 16,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  section: {
    marginBottom: 8,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  contactItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    gap: 12,
  },
  contactText: {
    fontSize: 16,
  },
  identityItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  identityHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  identityPlatform: {
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  identityName: {
    fontSize: 14,
    marginLeft: 28,
  },
  identityHandle: {
    fontSize: 14,
    marginLeft: 28,
  },
  insightGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
    marginBottom: 16,
  },
  insightItem: {
    flex: 1,
    minWidth: '45%',
  },
  insightLabel: {
    fontSize: 12,
    marginBottom: 4,
  },
  insightValue: {
    fontSize: 18,
    fontWeight: '600',
  },
  responsePatternContainer: {
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  responsePatternLabel: {
    fontSize: 14,
    marginBottom: 4,
  },
  quickAction: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 4,
    borderBottomWidth: 1,
    gap: 12,
  },
  quickActionText: {
    fontSize: 16,
    flex: 1,
  },
  metadataItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  metadataLabel: {
    fontSize: 14,
  },
  metadataValue: {
    fontSize: 14,
    fontWeight: '500',
  },
});