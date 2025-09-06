import React, { useState, useRef, useCallback } from 'react';
import {
  TextInput,
  View,
  Text,
  StyleSheet,
  TextInputProps,
  ViewStyle,
  TextStyle,
  AccessibilityRole,
} from 'react-native';
import { useAccessibility } from '../hooks/useAccessibility';
import { useI18n } from '../hooks/useI18n';

interface AccessibleTextInputProps extends Omit<TextInputProps, 'style'> {
  label?: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  containerStyle?: ViewStyle;
  inputStyle?: TextStyle;
  labelStyle?: TextStyle;
  errorStyle?: TextStyle;
  helperStyle?: TextStyle;
  accessibilityRole?: AccessibilityRole;
  testID?: string;
}

export const AccessibleTextInput: React.FC<AccessibleTextInputProps> = ({
  label,
  error,
  helperText,
  required = false,
  containerStyle,
  inputStyle,
  labelStyle,
  errorStyle,
  helperStyle,
  accessibilityRole = 'none',
  testID,
  placeholder,
  value,
  onChangeText,
  onFocus,
  onBlur,
  ...textInputProps
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<TextInput>(null);
  
  const { 
    getAccessibleTextSize, 
    getAccessibleColors,
    generateAccessibilityLabel,
    announceForAccessibility,
  } = useAccessibility();
  const { t, isRTL } = useI18n();

  const colors = getAccessibleColors();
  const isRTLLayout = isRTL();

  // Handle focus events
  const handleFocus = useCallback((e: any) => {
    setIsFocused(true);
    onFocus?.(e);
    
    // Announce focus for screen readers
    if (label) {
      announceForAccessibility(`${label} ${t('accessibility.textInput.focused')}`, 'low');
    }
  }, [onFocus, label, announceForAccessibility, t]);

  const handleBlur = useCallback((e: any) => {
    setIsFocused(false);
    onBlur?.(e);
  }, [onBlur]);

  // Generate accessibility properties
  const accessibilityLabel = generateAccessibilityLabel([
    label || '',
    required ? t('accessibility.required') : '',
    error ? `${t('accessibility.error')}: ${error}` : '',
    helperText || '',
  ]);

  const accessibilityHint = placeholder || t('accessibility.textInput.hint');

  // Get dynamic styles
  const labelTextSize = getAccessibleTextSize(14);
  const inputTextSize = getAccessibleTextSize(16);
  const helperTextSize = getAccessibleTextSize(12);

  const getBorderColor = () => {
    if (error) return colors.error;
    if (isFocused) return colors.primary;
    return colors.border;
  };

  const getLabelColor = () => {
    if (error) return colors.error;
    if (isFocused) return colors.primary;
    return colors.textSecondary;
  };

  return (
    <View style={[styles.container, containerStyle]} testID={testID}>
      {/* Label */}
      {label && (
        <Text
          style={[
            styles.label,
            {
              fontSize: labelTextSize,
              color: getLabelColor(),
              textAlign: isRTLLayout ? 'right' : 'left',
            },
            labelStyle,
          ]}
          accessible={false} // Handled by input's accessibilityLabel
        >
          {label}
          {required && (
            <Text style={[styles.required, { color: colors.error }]}>
              {' *'}
            </Text>
          )}
        </Text>
      )}

      {/* Input Container */}
      <View
        style={[
          styles.inputContainer,
          {
            borderColor: getBorderColor(),
            backgroundColor: colors.surface,
            borderWidth: 2,
          },
        ]}
      >
        <TextInput
          ref={inputRef}
          style={[
            styles.input,
            {
              fontSize: inputTextSize,
              color: colors.text,
              textAlign: isRTLLayout ? 'right' : 'left',
              writingDirection: isRTLLayout ? 'rtl' : 'ltr',
            },
            inputStyle,
          ]}
          placeholder={placeholder}
          placeholderTextColor={colors.textSecondary}
          value={value}
          onChangeText={onChangeText}
          onFocus={handleFocus}
          onBlur={handleBlur}
          accessible={true}
          accessibilityRole={accessibilityRole}
          accessibilityLabel={accessibilityLabel}
          accessibilityHint={accessibilityHint}
          accessibilityState={{
            disabled: textInputProps.editable === false,
          }}
          {...textInputProps}
        />
      </View>

      {/* Error Message */}
      {error && (
        <Text
          style={[
            styles.errorText,
            {
              fontSize: helperTextSize,
              color: colors.error,
              textAlign: isRTLLayout ? 'right' : 'left',
            },
            errorStyle,
          ]}
          accessible={true}
          accessibilityRole="alert"
          accessibilityLiveRegion="polite"
        >
          {error}
        </Text>
      )}

      {/* Helper Text */}
      {helperText && !error && (
        <Text
          style={[
            styles.helperText,
            {
              fontSize: helperTextSize,
              color: colors.textSecondary,
              textAlign: isRTLLayout ? 'right' : 'left',
            },
            helperStyle,
          ]}
          accessible={false} // Handled by input's accessibilityLabel
        >
          {helperText}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 8,
  },
  label: {
    fontWeight: '600',
    marginBottom: 4,
  },
  required: {
    fontWeight: 'bold',
  },
  inputContainer: {
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  input: {
    minHeight: 44, // WCAG minimum touch target
    paddingVertical: 8,
    paddingHorizontal: 0,
  },
  errorText: {
    marginTop: 4,
    fontWeight: '500',
  },
  helperText: {
    marginTop: 4,
  },
});