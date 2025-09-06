/**
 * EmptyState Component
 * 
 * Reusable empty state display with customizable content and actions
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';

interface EmptyStateProps {
  icon?: string;
  title: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
  style?: any;
  iconSize?: number;
  showIcon?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = 'document-outline',
  title,
  message,
  actionText,
  onAction,
  style,
  iconSize,
  showIcon = true,
}) => {
  const { theme } = useTheme();
  const { width: screenWidth } = Dimensions.get('window');
  const isTablet = screenWidth >= 768;

  const getIconSize = () => {
    if (iconSize) return iconSize;
    return isTablet ? 80 : 64;
  };

  const containerStyle = [
    styles.container,
    isTablet && styles.tabletContainer,
    style,
  ];

  const iconStyle = [
    styles.icon,
    { color: theme.colors.textSecondary },
  ];

  const titleStyle = [
    styles.title,
    {
      color: theme.colors.text,
      fontSize: isTablet ? 24 : 20,
    },
  ];

  const messageStyle = [
    styles.message,
    {
      color: theme.colors.textSecondary,
      fontSize: isTablet ? 18 : 16,
    },
  ];

  const actionButtonStyle = [
    styles.actionButton,
    {
      backgroundColor: theme.colors.primary,
    },
    isTablet && styles.tabletActionButton,
  ];

  const actionTextStyle = [
    styles.actionText,
    {
      color: theme.colors.surface,
      fontSize: isTablet ? 18 : 16,
    },
  ];

  return (
    <View style={containerStyle}>
      {showIcon && (
        <Icon
          name={icon}
          size={getIconSize()}
          style={iconStyle}
        />
      )}
      
      <Text style={titleStyle}>
        {title}
      </Text>
      
      {message && (
        <Text style={messageStyle}>
          {message}
        </Text>
      )}
      
      {actionText && onAction && (
        <TouchableOpacity
          style={actionButtonStyle}
          onPress={onAction}
        >
          <Text style={actionTextStyle}>
            {actionText}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    flex: 1,
  },
  tabletContainer: {
    padding: 48,
  },
  icon: {
    marginBottom: 16,
  },
  title: {
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 8,
  },
  message: {
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
    maxWidth: 300,
  },
  actionButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  tabletActionButton: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 16,
  },
  actionText: {
    fontWeight: '600',
  },
});