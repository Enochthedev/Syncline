/**
 * ContactSuggestion Component
 * 
 * Displays individual contact search suggestions with appropriate styling
 */

import React from 'react';
import { TouchableOpacity, Text, StyleSheet, View } from 'react-native';
import { useTheme } from '../hooks/useTheme';

interface ContactSuggestionProps {
  suggestion: {
    type: string;
    text: string;
    contact_id?: string;
    contact_name?: string;
    platform?: string;
    suggestion_type: string;
  };
  onSelect: (suggestion: any) => void;
}

export const ContactSuggestion: React.FC<ContactSuggestionProps> = ({
  suggestion,
  onSelect,
}) => {
  const { theme } = useTheme();

  const getSuggestionIcon = () => {
    switch (suggestion.type) {
      case 'name':
        return '👤';
      case 'handle':
        return '@';
      case 'recent':
        return '🕒';
      case 'email':
        return '📧';
      default:
        return '🔍';
    }
  };

  const getSuggestionColor = () => {
    switch (suggestion.type) {
      case 'name':
        return theme.colors.primary;
      case 'handle':
        return theme.colors.secondary;
      case 'recent':
        return theme.colors.warning;
      case 'email':
        return theme.colors.info;
      default:
        return theme.colors.textSecondary;
    }
  };

  return (
    <TouchableOpacity
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.surface,
          borderColor: getSuggestionColor(),
        },
      ]}
      onPress={() => onSelect(suggestion)}
    >
      <View style={styles.content}>
        <Text style={styles.icon}>{getSuggestionIcon()}</Text>
        <Text
          style={[styles.text, { color: theme.colors.text }]}
          numberOfLines={1}
        >
          {suggestion.text}
        </Text>
        {suggestion.platform && (
          <Text style={[styles.platform, { color: getSuggestionColor() }]}>
            {suggestion.platform}
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 20,
    borderWidth: 1,
    marginRight: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    fontSize: 12,
    marginRight: 4,
  },
  text: {
    fontSize: 14,
    fontWeight: '500',
    maxWidth: 120,
  },
  platform: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginLeft: 4,
  },
});