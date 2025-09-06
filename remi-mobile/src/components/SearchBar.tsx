/**
 * SearchBar Component
 * 
 * Platform-appropriate search input with responsive styling
 * Supports both mobile and web platforms with adaptive behavior
 */

import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  Platform,
  Dimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useTheme } from '../hooks/useTheme';

interface SearchBarProps {
  value: string;
  onChangeText: (text: string) => void;
  onSubmit?: (text: string) => void;
  onClear?: () => void;
  onFocus?: () => void;
  onBlur?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
  isLoading?: boolean;
  disabled?: boolean;
  showClearButton?: boolean;
  showSearchIcon?: boolean;
  showVoiceButton?: boolean;
  onVoicePress?: () => void;
  style?: any;
  inputStyle?: any;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChangeText,
  onSubmit,
  onClear,
  onFocus,
  onBlur,
  placeholder = "Search...",
  autoFocus = false,
  isLoading = false,
  disabled = false,
  showClearButton = true,
  showSearchIcon = true,
  showVoiceButton = false,
  onVoicePress,
  style,
  inputStyle,
}) => {
  const { theme } = useTheme();
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<TextInput>(null);
  const { width: screenWidth } = Dimensions.get('window');

  // Responsive sizing
  const isTablet = screenWidth >= 768;
  const isDesktop = screenWidth >= 1024;

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    onFocus?.();
  }, [onFocus]);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    onBlur?.();
  }, [onBlur]);

  const handleClear = useCallback(() => {
    onChangeText('');
    onClear?.();
    inputRef.current?.focus();
  }, [onChangeText, onClear]);

  const handleSubmit = useCallback(() => {
    if (value.trim()) {
      onSubmit?.(value.trim());
    }
  }, [value, onSubmit]);

  const handleVoicePress = useCallback(() => {
    onVoicePress?.();
  }, [onVoicePress]);

  // Dynamic styles based on platform and state
  const containerStyle = [
    styles.container,
    {
      backgroundColor: theme.colors.surface,
      borderColor: isFocused ? theme.colors.primary : theme.colors.border,
      borderWidth: isFocused ? 2 : 1,
    },
    isTablet && styles.tabletContainer,
    isDesktop && styles.desktopContainer,
    disabled && { opacity: 0.6 },
    style,
  ];

  const textInputStyle = [
    styles.input,
    {
      color: theme.colors.text,
      fontSize: isTablet ? 18 : 16,
    },
    inputStyle,
  ];

  return (
    <View style={containerStyle}>
      {/* Search Icon */}
      {showSearchIcon && (
        <Icon
          name="search"
          size={isTablet ? 24 : 20}
          color={isFocused ? theme.colors.primary : theme.colors.textSecondary}
          style={styles.searchIcon}
        />
      )}

      {/* Text Input */}
      <TextInput
        ref={inputRef}
        style={textInputStyle}
        value={value}
        onChangeText={onChangeText}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onSubmitEditing={handleSubmit}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textSecondary}
        autoFocus={autoFocus}
        editable={!disabled}
        autoCorrect={false}
        autoCapitalize="none"
        returnKeyType="search"
        clearButtonMode={Platform.OS === 'ios' ? 'while-editing' : 'never'}
        selectTextOnFocus={Platform.OS === 'web'}
      />

      {/* Action Buttons Container */}
      <View style={styles.actionsContainer}>
        {/* Loading Indicator */}
        {isLoading && (
          <ActivityIndicator
            size={isTablet ? 'small' : 'small'}
            color={theme.colors.primary}
            style={styles.loadingIndicator}
          />
        )}

        {/* Voice Button */}
        {showVoiceButton && !isLoading && (
          <TouchableOpacity
            onPress={handleVoicePress}
            style={[styles.actionButton, { backgroundColor: theme.colors.primary }]}
            disabled={disabled}
          >
            <Icon
              name="mic"
              size={isTablet ? 20 : 16}
              color={theme.colors.surface}
            />
          </TouchableOpacity>
        )}

        {/* Clear Button */}
        {showClearButton && value.length > 0 && !isLoading && Platform.OS !== 'ios' && (
          <TouchableOpacity
            onPress={handleClear}
            style={styles.clearButton}
            disabled={disabled}
          >
            <Icon
              name="close-circle"
              size={isTablet ? 24 : 20}
              color={theme.colors.textSecondary}
            />
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
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: Platform.OS === 'web' ? 12 : 10,
    elevation: Platform.OS === 'android' ? 2 : 0,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    minHeight: 48,
  },
  tabletContainer: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 16,
    minHeight: 56,
  },
  desktopContainer: {
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 20,
    minHeight: 64,
  },
  searchIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: '400',
    paddingVertical: 0, // Remove default padding
    ...Platform.select({
      web: {
        outline: 'none',
      },
    }),
  },
  actionsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  loadingIndicator: {
    marginRight: 8,
  },
  actionButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  clearButton: {
    padding: 4,
    marginLeft: 4,
  },
});