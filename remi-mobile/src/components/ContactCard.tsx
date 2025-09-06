/**
 * ContactCard Component
 * 
 * Displays contact information with platform indicators and interaction status
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  Dimensions,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';
import { useResponsiveDimensions } from './ResponsiveLayout';

interface ContactCardProps {
  contact: {
    id: string;
    primary_name: string;
    display_name?: string;
    primary_email?: string;
    primary_phone?: string;
    profile_photo_url?: string;
    platforms: string[];
    total_messages: number;
    last_interaction?: string;
    relationship_strength: number;
    communication_frequency: string;
    is_favorite: boolean;
    interaction_indicators?: {
      has_recent_messages: boolean;
      is_frequent_contact: boolean;
      has_unread_messages: boolean;
    };
    recent_interaction?: {
      has_recent: boolean;
      days_since: number;
      interaction_level: string;
    };
  };
  onPress: (contact: any) => void;
  showDetails?: boolean;
}

export const ContactCard: React.FC<ContactCardProps> = ({
  contact,
  onPress,
  showDetails = true,
}) => {
  const { theme } = useTheme();
  const { isTablet, isDesktop } = useResponsiveDimensions();

  const getInteractionLevelColor = () => {
    if (!contact.recent_interaction) return theme.colors.textSecondary;
    
    switch (contact.recent_interaction.interaction_level) {
      case 'today':
        return theme.colors.success;
      case 'this_week':
        return theme.colors.primary;
      case 'this_month':
        return theme.colors.warning;
      default:
        return theme.colors.textSecondary;
    }
  };

  const getInteractionLevelText = () => {
    if (!contact.recent_interaction) return 'No recent activity';
    
    switch (contact.recent_interaction.interaction_level) {
      case 'today':
        return 'Active today';
      case 'this_week':
        return 'Active this week';
      case 'this_month':
        return 'Active this month';
      default:
        return `${contact.recent_interaction.days_since} days ago`;
    }
  };

  const getRelationshipStrengthWidth = () => {
    return `${Math.max(contact.relationship_strength * 100, 10)}%`;
  };

  return (
    <TouchableOpacity
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.border,
        },
        isTablet && styles.tabletContainer,
        isDesktop && styles.desktopContainer,
      ]}
      onPress={() => onPress(contact)}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatarContainer}>
          {contact.profile_photo_url ? (
            <Image
              source={{ uri: contact.profile_photo_url }}
              style={[styles.avatar, isTablet && styles.tabletAvatar]}
            />
          ) : (
            <View style={[
              styles.avatarPlaceholder, 
              { backgroundColor: theme.colors.primary },
              isTablet && styles.tabletAvatar
            ]}>
              <Text style={[
                styles.avatarText, 
                { color: theme.colors.white },
                isTablet && styles.tabletAvatarText
              ]}>
                {(contact.primary_name || contact.display_name || '?')[0].toUpperCase()}
              </Text>
            </View>
          )}
          {contact.is_favorite && (
            <View style={[styles.favoriteIndicator, { backgroundColor: theme.colors.warning }]}>
              <Text style={styles.favoriteIcon}>⭐</Text>
            </View>
          )}
        </View>

        <View style={styles.contactInfo}>
          <Text style={[
            styles.name, 
            { color: theme.colors.text },
            isTablet && styles.tabletName
          ]} numberOfLines={1}>
            {contact.primary_name || contact.display_name}
          </Text>
          {contact.primary_email && (
            <Text style={[styles.email, { color: theme.colors.textSecondary }]} numberOfLines={1}>
              {contact.primary_email}
            </Text>
          )}
          {contact.primary_phone && (
            <Text style={[styles.phone, { color: theme.colors.textSecondary }]} numberOfLines={1}>
              {contact.primary_phone}
            </Text>
          )}
        </View>

        <View style={styles.indicators}>
          {contact.interaction_indicators?.has_recent_messages && (
            <View style={[styles.recentIndicator, { backgroundColor: theme.colors.success }]} />
          )}
          {contact.interaction_indicators?.has_unread_messages && (
            <View style={[styles.unreadIndicator, { backgroundColor: theme.colors.error }]} />
          )}
        </View>
      </View>

      {/* Platform Indicators */}
      <View style={styles.platformsContainer}>
        {contact.platforms.map((platform) => (
          <View
            key={platform}
            style={[styles.platformBadge, { backgroundColor: theme.colors.primary }]}
          >
            <Text style={[styles.platformText, { color: theme.colors.white }]}>
              {platform.toUpperCase()}
            </Text>
          </View>
        ))}
      </View>

      {/* Details */}
      {showDetails && (
        <View style={styles.details}>
          {/* Interaction Level */}
          <View style={styles.detailRow}>
            <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
              Last Activity:
            </Text>
            <Text style={[styles.detailValue, { color: getInteractionLevelColor() }]}>
              {getInteractionLevelText()}
            </Text>
          </View>

          {/* Message Count */}
          <View style={styles.detailRow}>
            <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
              Messages:
            </Text>
            <Text style={[styles.detailValue, { color: theme.colors.text }]}>
              {contact.total_messages}
            </Text>
          </View>

          {/* Communication Frequency */}
          <View style={styles.detailRow}>
            <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
              Frequency:
            </Text>
            <Text style={[styles.detailValue, { color: theme.colors.text }]}>
              {contact.communication_frequency}
            </Text>
          </View>

          {/* Relationship Strength */}
          <View style={styles.strengthContainer}>
            <Text style={[styles.detailLabel, { color: theme.colors.textSecondary }]}>
              Relationship Strength:
            </Text>
            <View style={[styles.strengthBar, { backgroundColor: theme.colors.border }]}>
              <View
                style={[
                  styles.strengthFill,
                  {
                    backgroundColor: theme.colors.primary,
                    width: getRelationshipStrengthWidth(),
                  },
                ]}
              />
            </View>
            <Text style={[styles.strengthValue, { color: theme.colors.text }]}>
              {Math.round(contact.relationship_strength * 100)}%
            </Text>
          </View>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginVertical: 4,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  tabletContainer: {
    borderRadius: 16,
    padding: 20,
    marginVertical: 6,
  },
  desktopContainer: {
    borderRadius: 20,
    padding: 24,
    marginVertical: 8,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  avatarContainer: {
    position: 'relative',
    marginRight: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
  },
  tabletAvatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  avatarPlaceholder: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  tabletAvatarText: {
    fontSize: 24,
  },
  favoriteIndicator: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  favoriteIcon: {
    fontSize: 10,
  },
  contactInfo: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  tabletName: {
    fontSize: 18,
  },
  email: {
    fontSize: 14,
    marginBottom: 1,
  },
  phone: {
    fontSize: 14,
  },
  indicators: {
    alignItems: 'center',
  },
  recentIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginBottom: 4,
  },
  unreadIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  platformsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  platformBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginRight: 6,
    marginBottom: 4,
  },
  platformText: {
    fontSize: 10,
    fontWeight: '600',
  },
  details: {
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
    paddingTop: 12,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  detailLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
  detailValue: {
    fontSize: 12,
    fontWeight: '600',
  },
  strengthContainer: {
    marginTop: 4,
  },
  strengthBar: {
    height: 4,
    borderRadius: 2,
    marginTop: 4,
    marginBottom: 2,
  },
  strengthFill: {
    height: '100%',
    borderRadius: 2,
  },
  strengthValue: {
    fontSize: 10,
    textAlign: 'right',
  },
});