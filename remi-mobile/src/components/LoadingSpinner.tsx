/**
 * LoadingSpinner Component
 * 
 * Reusable loading spinner with different sizes and styles
 */

import React from 'react';
import {
  View,
  ActivityIndicator,
  Text,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { useTheme } from '../hooks/useTheme';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
  color?: string;
  style?: any;
  overlay?: boolean;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  message,
  color,
  style,
  overlay = false,
  fullScreen = false,
}) => {
  const { theme } = useTheme();
  const { width: screenWidth } = Dimensions.get('window');
  const isTablet = screenWidth >= 768;

  const getSpinnerSize = () => {
    switch (size) {
      case 'small':
        return isTablet ? 'small' : 'small';
      case 'large':
        return isTablet ? 'large' : 'large';
      default:
        return isTablet ? 'large' : 'small';
    }
  };

  const getIconSize = () => {
    switch (size) {
      case 'small':
        return isTablet ? 24 : 20;
      case 'large':
        return isTablet ? 48 : 40;
      default:
        return isTablet ? 36 : 30;
    }
  };

  const containerStyle = [
    styles.container,
    fullScreen && styles.fullScreen,
    overlay && [styles.overlay, { backgroundColor: `${theme.colors.background}CC` }],
    { backgroundColor: overlay ? undefined : theme.colors.background },
    style,
  ];

  const messageStyle = [
    styles.message,
    {
      color: theme.colors.text,
      fontSize: isTablet ? 18 : 16,
      marginTop: size === 'large' ? 16 : 12,
    },
  ];

  return (
    <View style={containerStyle}>
      <ActivityIndicator
        size={getSpinnerSize()}
        color={color || theme.colors.primary}
      />
      {message && (
        <Text style={messageStyle}>
          {message}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  fullScreen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 999,
  },
  message: {
    textAlign: 'center',
    fontWeight: '500',
  },
});