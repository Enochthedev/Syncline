/**
 * ErrorMessage Component
 * 
 * Reusable error display component with retry functionality
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

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryText?: string;
  showIcon?: boolean;
  style?: any;
  type?: 'error' | 'warning' | 'info';
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title,
  message,
  onRetry,
  retryText = 'Try Again',
  showIcon = true,
  style,
  type = 'error',
}) => {
  const { theme } = useTheme();
  const { width: screenWidth } = Dimensions.get('window');
  const isTablet = screenWidth >= 768;

  const getIconName = () => {
    switch (type) {
      case 'warning':
        return 'warning';
      case 'info':
        return 'information-circle';
      default:
        return 'alert-circle';
    }
  };

  const getIconColor = () => {
    switch (type) {
      case 'warning':
        return theme.colors.warning;
      case 'info':
        return theme.colors.primary;
      default:
        return theme.colors.error;
    }
  };

  const containerStyle = [
    styles.container,
    {
      backgroundColor: theme.colors.surface,
      borderColor: getIconColor(),
    },
    isTablet && styles.tabletContainer,
    style,
  ];

  const titleStyle = [
    styles.title,
    {
      color: theme.colors.text,
      fontSize: isTablet ? 20 : 18,
    },
  ];

  const messageStyle = [
    styles.message,
    {
      color: theme.colors.textSecondary,
      fontSize: isTablet ? 16 : 14,
    },
  ];

  const retryButtonStyle = [
    styles.retryButton,
    {
      backgroundColor: getIconColor(),
    },
    isTablet && styles.tabletRetryButton,
  ];

  const retryTextStyle = [
    styles.retryText,
    {
      color: theme.colors.surface,
      fontSize: isTablet ? 16 : 14,
    },
  ];

  return (
    <View style={containerStyle}>
      {showIcon && (
        <Icon
          name={getIconName()}
          size={isTablet ? 48 : 40}
          color={getIconColor()}
          style={styles.icon}
        />
      )}
      
      <View style={styles.content}>
        {title && (
          <Text style={titleStyle}>
            {title}
          </Text>
        )}
        
        <Text style={messageStyle}>
          {message}
        </Text>
        
        {onRetry && (
          <TouchableOpacity
            style={retryButtonStyle}
            onPress={onRetry}
          >
            <Icon
              name="refresh"
              size={isTablet ? 20 : 16}
              color={theme.colors.surface}
              style={styles.retryIcon}
            />
            <Text style={retryTextStyle}>
              {retryText}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    margin: 16,
  },
  tabletContainer: {
    padding: 20,
    borderRadius: 16,
    margin: 20,
  },
  icon: {
    marginRight: 16,
  },
  content: {
    flex: 1,
  },
  title: {
    fontWeight: '600',
    marginBottom: 4,
  },
  message: {
    lineHeight: 20,
    marginBottom: 12,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  tabletRetryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 10,
  },
  retryIcon: {
    marginRight: 8,
  },
  retryText: {
    fontWeight: '600',
  },
});