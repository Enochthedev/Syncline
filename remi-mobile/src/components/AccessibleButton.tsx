import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
  AccessibilityRole,
  GestureResponderEvent,
} from 'react-native';
import { useAccessibility } from '../hooks/useAccessibility';
import { useI18n } from '../hooks/useI18n';

interface AccessibleButtonProps {
  title: string;
  onPress: (event: GestureResponderEvent) => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'outline' | 'text';
  size?: 'small' | 'medium' | 'large';
  accessibilityLabel?: string;
  accessibilityHint?: string;
  accessibilityRole?: AccessibilityRole;
  testID?: string;
  style?: ViewStyle;
  textStyle?: TextStyle;
  icon?: React.ReactNode;
  loading?: boolean;
}

export const AccessibleButton: React.FC<AccessibleButtonProps> = ({
  title,
  onPress,
  disabled = false,
  variant = 'primary',
  size = 'medium',
  accessibilityLabel,
  accessibilityHint,
  accessibilityRole = 'button',
  testID,
  style,
  textStyle,
  icon,
  loading = false,
}) => {
  const { 
    getAccessibleTextSize, 
    getAccessibleColors, 
    getAccessibleTouchTarget,
    generateAccessibilityLabel,
    generateAccessibilityHint,
  } = useAccessibility();
  const { t } = useI18n();

  const colors = getAccessibleColors();
  const touchTarget = getAccessibleTouchTarget();

  // Generate accessibility properties
  const finalAccessibilityLabel = accessibilityLabel || 
    generateAccessibilityLabel([
      title,
      loading ? t('common.loading') : '',
      disabled ? 'disabled' : '',
    ]);

  const finalAccessibilityHint = accessibilityHint || 
    generateAccessibilityHint(title.toLowerCase());

  // Get size-specific styles
  const getSizeStyles = () => {
    const baseTextSize = size === 'small' ? 14 : size === 'large' ? 18 : 16;
    const textSize = getAccessibleTextSize(baseTextSize);
    const padding = size === 'small' ? 8 : size === 'large' ? 16 : 12;

    return {
      fontSize: textSize,
      paddingVertical: padding,
      paddingHorizontal: padding * 1.5,
    };
  };

  // Get variant-specific styles
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return {
          backgroundColor: disabled ? colors.border : colors.primary,
          borderColor: disabled ? colors.border : colors.primary,
        };
      case 'secondary':
        return {
          backgroundColor: disabled ? colors.border : colors.secondary,
          borderColor: disabled ? colors.border : colors.secondary,
        };
      case 'outline':
        return {
          backgroundColor: 'transparent',
          borderColor: disabled ? colors.border : colors.primary,
          borderWidth: 2,
        };
      case 'text':
        return {
          backgroundColor: 'transparent',
          borderColor: 'transparent',
        };
      default:
        return {
          backgroundColor: colors.primary,
          borderColor: colors.primary,
        };
    }
  };

  const getTextColor = () => {
    if (disabled) return colors.textSecondary;
    
    switch (variant) {
      case 'primary':
      case 'secondary':
        return colors.background;
      case 'outline':
      case 'text':
        return colors.primary;
      default:
        return colors.background;
    }
  };

  const sizeStyles = getSizeStyles();
  const variantStyles = getVariantStyles();
  const textColor = getTextColor();

  return (
    <TouchableOpacity
      style={[
        styles.button,
        {
          minWidth: touchTarget.minWidth,
          minHeight: touchTarget.minHeight,
          borderRadius: 8,
          borderWidth: 1,
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'row',
          paddingVertical: sizeStyles.paddingVertical,
          paddingHorizontal: sizeStyles.paddingHorizontal,
        },
        variantStyles,
        style,
      ]}
      onPress={onPress}
      disabled={disabled || loading}
      accessible={true}
      accessibilityRole={accessibilityRole}
      accessibilityLabel={finalAccessibilityLabel}
      accessibilityHint={finalAccessibilityHint}
      accessibilityState={{
        disabled: disabled || loading,
        busy: loading,
      }}
      testID={testID}
    >
      {icon && (
        <Text style={[styles.icon, { marginRight: 8 }]}>
          {icon}
        </Text>
      )}
      <Text
        style={[
          styles.text,
          {
            fontSize: sizeStyles.fontSize,
            color: textColor,
          },
          textStyle,
        ]}
        numberOfLines={1}
        adjustsFontSizeToFit
      >
        {loading ? t('common.loading') : title}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    // Base styles handled dynamically
  },
  text: {
    fontWeight: '600',
    textAlign: 'center',
  },
  icon: {
    fontSize: 16,
  },
});