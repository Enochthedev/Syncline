/**
 * ResponsiveLayout Component
 * 
 * Adaptive layout that responds to different screen sizes
 * Provides consistent spacing and layout patterns across devices
 */

import React from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Dimensions,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../hooks/useTheme';

interface ResponsiveLayoutProps {
  children: React.ReactNode;
  style?: any;
  contentContainerStyle?: any;
  scrollable?: boolean;
  showsVerticalScrollIndicator?: boolean;
  refreshControl?: React.ReactElement;
  keyboardShouldPersistTaps?: 'always' | 'never' | 'handled';
  padding?: boolean;
  safeArea?: boolean;
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({
  children,
  style,
  contentContainerStyle,
  scrollable = false,
  showsVerticalScrollIndicator = false,
  refreshControl,
  keyboardShouldPersistTaps = 'handled',
  padding = true,
  safeArea = true,
}) => {
  const { theme } = useTheme();
  const insets = useSafeAreaInsets();
  const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

  // Responsive breakpoints
  const isPhone = screenWidth < 768;
  const isTablet = screenWidth >= 768 && screenWidth < 1024;
  const isDesktop = screenWidth >= 1024;

  // Calculate responsive padding
  const getHorizontalPadding = () => {
    if (!padding) return 0;
    
    if (isDesktop) {
      // Desktop: Center content with max width
      const maxContentWidth = 1200;
      const sideMargin = Math.max((screenWidth - maxContentWidth) / 2, 32);
      return sideMargin;
    } else if (isTablet) {
      return 24;
    } else {
      return 16;
    }
  };

  const getVerticalPadding = () => {
    if (!padding) return 0;
    
    if (isTablet) {
      return 24;
    } else {
      return 16;
    }
  };

  const containerStyle = [
    styles.container,
    {
      backgroundColor: theme.colors.background,
      paddingTop: safeArea ? insets.top : 0,
      paddingBottom: safeArea ? insets.bottom : 0,
      paddingLeft: safeArea ? insets.left : 0,
      paddingRight: safeArea ? insets.right : 0,
    },
    style,
  ];

  const contentStyle = [
    styles.content,
    {
      paddingHorizontal: getHorizontalPadding(),
      paddingVertical: getVerticalPadding(),
    },
    isDesktop && styles.desktopContent,
    contentContainerStyle,
  ];

  if (scrollable) {
    return (
      <ScrollView
        style={containerStyle}
        contentContainerStyle={contentStyle}
        showsVerticalScrollIndicator={showsVerticalScrollIndicator}
        refreshControl={refreshControl}
        keyboardShouldPersistTaps={keyboardShouldPersistTaps}
        bounces={Platform.OS === 'ios'}
      >
        {children}
      </ScrollView>
    );
  }

  return (
    <View style={containerStyle}>
      <View style={contentStyle}>
        {children}
      </View>
    </View>
  );
};

// Hook for responsive values
export const useResponsiveValue = <T,>(
  phoneValue: T,
  tabletValue?: T,
  desktopValue?: T
): T => {
  const { width: screenWidth } = Dimensions.get('window');
  
  if (screenWidth >= 1024 && desktopValue !== undefined) {
    return desktopValue;
  } else if (screenWidth >= 768 && tabletValue !== undefined) {
    return tabletValue;
  } else {
    return phoneValue;
  }
};

// Hook for responsive dimensions
export const useResponsiveDimensions = () => {
  const { width: screenWidth, height: screenHeight } = Dimensions.get('window');
  
  const isPhone = screenWidth < 768;
  const isTablet = screenWidth >= 768 && screenWidth < 1024;
  const isDesktop = screenWidth >= 1024;
  
  const isLandscape = screenWidth > screenHeight;
  const isPortrait = screenHeight > screenWidth;
  
  return {
    screenWidth,
    screenHeight,
    isPhone,
    isTablet,
    isDesktop,
    isLandscape,
    isPortrait,
  };
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  desktopContent: {
    maxWidth: 1200,
    alignSelf: 'center',
    width: '100%',
  },
});