import React from 'react';
import { render } from '@testing-library/react-native';
import { AccessibleButton } from '../../src/components/AccessibleButton';
import { AccessibleTextInput } from '../../src/components/AccessibleTextInput';
import { AccessibilityTestUtils, toBeAccessible } from './accessibilityTestUtils';

// Extend Jest matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeAccessible(options?: any): R;
    }
  }
}

expect.extend({ toBeAccessible });

// Mock the accessibility and i18n services
jest.mock('../../src/hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    getAccessibleTextSize: (size: number) => size,
    getAccessibleColors: () => ({
      primary: '#2196F3',
      background: '#FFFFFF',
      text: '#212121',
      textSecondary: '#757575',
      border: '#E0E0E0',
      error: '#F44336',
      surface: '#F5F5F5',
    }),
    getAccessibleTouchTarget: () => ({ minWidth: 44, minHeight: 44 }),
    generateAccessibilityLabel: (parts: string[]) => parts.filter(Boolean).join(', '),
    generateAccessibilityHint: (action: string) => `Double tap to ${action}`,
    shouldReduceMotion: () => false,
  }),
}));

jest.mock('../../src/hooks/useI18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
    isRTL: () => false,
  }),
}));

describe('AccessibleButton', () => {
  it('should render with proper accessibility properties', () => {
    const { getByRole } = render(
      <AccessibleButton
        title="Test Button"
        onPress={() => {}}
        accessibilityLabel="Custom test button"
        accessibilityHint="Performs a test action"
      />
    );

    const button = getByRole('button');
    expect(button).toBeTruthy();
    expect(button.props.accessibilityLabel).toBe('Custom test button');
    expect(button.props.accessibilityHint).toBe('Performs a test action');
  });

  it('should meet WCAG accessibility standards', () => {
    const component = render(
      <AccessibleButton
        title="Accessible Button"
        onPress={() => {}}
        accessibilityLabel="Accessible button for testing"
      />
    );

    expect(component.toJSON()).toBeAccessible({
      level: 'AA',
      checkTouchTargets: true,
      checkLabels: true,
    });
  });

  it('should have minimum touch target size', () => {
    const { getByRole } = render(
      <AccessibleButton
        title="Small Button"
        onPress={() => {}}
        size="small"
      />
    );

    const button = getByRole('button');
    const style = button.props.style;
    
    // Check that minimum dimensions are enforced
    expect(style.minWidth).toBeGreaterThanOrEqual(44);
    expect(style.minHeight).toBeGreaterThanOrEqual(44);
  });

  it('should handle disabled state properly', () => {
    const { getByRole } = render(
      <AccessibleButton
        title="Disabled Button"
        onPress={() => {}}
        disabled={true}
      />
    );

    const button = getByRole('button');
    expect(button.props.accessibilityState.disabled).toBe(true);
  });

  it('should handle loading state properly', () => {
    const { getByRole } = render(
      <AccessibleButton
        title="Loading Button"
        onPress={() => {}}
        loading={true}
      />
    );

    const button = getByRole('button');
    expect(button.props.accessibilityState.busy).toBe(true);
  });

  it('should generate meaningful accessibility labels', () => {
    const { getByRole } = render(
      <AccessibleButton
        title="Save Document"
        onPress={() => {}}
        loading={true}
      />
    );

    const button = getByRole('button');
    expect(button.props.accessibilityLabel).toContain('common.loading');
  });

  it('should support different variants with proper contrast', () => {
    const variants = ['primary', 'secondary', 'outline', 'text'] as const;
    
    variants.forEach(variant => {
      const { getByRole } = render(
        <AccessibleButton
          title={`${variant} Button`}
          onPress={() => {}}
          variant={variant}
        />
      );

      const button = getByRole('button');
      expect(button).toBeTruthy();
      
      // Each variant should have appropriate styling
      const style = button.props.style;
      expect(style).toBeDefined();
    });
  });
});

describe('AccessibleTextInput', () => {
  it('should render with proper accessibility properties', () => {
    const { getByDisplayValue } = render(
      <AccessibleTextInput
        label="Email Address"
        value="test@example.com"
        onChangeText={() => {}}
        accessibilityRole="none"
        placeholder="Enter your email"
      />
    );

    const input = getByDisplayValue('test@example.com');
    expect(input).toBeTruthy();
    expect(input.props.accessibilityLabel).toContain('Email Address');
  });

  it('should meet WCAG accessibility standards', () => {
    const component = render(
      <AccessibleTextInput
        label="Accessible Input"
        value=""
        onChangeText={() => {}}
        placeholder="Enter text here"
      />
    );

    expect(component.toJSON()).toBeAccessible({
      level: 'AA',
      checkLabels: true,
      checkTouchTargets: true,
    });
  });

  it('should handle required fields properly', () => {
    const { getByText, getByDisplayValue } = render(
      <AccessibleTextInput
        label="Required Field"
        value=""
        onChangeText={() => {}}
        required={true}
      />
    );

    const label = getByText('Required Field *');
    expect(label).toBeTruthy();

    const input = getByDisplayValue('');
    expect(input.props.accessibilityLabel).toContain('accessibility.required');
  });

  it('should display error messages accessibly', () => {
    const { getByText, getByDisplayValue } = render(
      <AccessibleTextInput
        label="Email"
        value="invalid-email"
        onChangeText={() => {}}
        error="Please enter a valid email address"
      />
    );

    const errorText = getByText('Please enter a valid email address');
    expect(errorText.props.accessibilityRole).toBe('alert');
    expect(errorText.props.accessibilityLiveRegion).toBe('polite');

    const input = getByDisplayValue('invalid-email');
    expect(input.props.accessibilityLabel).toContain('Please enter a valid email address');
  });

  it('should support helper text', () => {
    const { getByText, getByDisplayValue } = render(
      <AccessibleTextInput
        label="Password"
        value=""
        onChangeText={() => {}}
        helperText="Must be at least 8 characters"
        secureTextEntry={true}
      />
    );

    const helperText = getByText('Must be at least 8 characters');
    expect(helperText).toBeTruthy();

    const input = getByDisplayValue('');
    expect(input.props.accessibilityLabel).toContain('Must be at least 8 characters');
  });

  it('should handle focus states properly', () => {
    const mockOnFocus = jest.fn();
    const mockOnBlur = jest.fn();

    const { getByDisplayValue } = render(
      <AccessibleTextInput
        label="Focus Test"
        value=""
        onChangeText={() => {}}
        onFocus={mockOnFocus}
        onBlur={mockOnBlur}
      />
    );

    const input = getByDisplayValue('');
    
    // Simulate focus events
    input.props.onFocus({});
    expect(mockOnFocus).toHaveBeenCalled();

    input.props.onBlur({});
    expect(mockOnBlur).toHaveBeenCalled();
  });

  it('should support RTL layouts', () => {
    // Mock RTL layout
    jest.mocked(require('../../src/hooks/useI18n').useI18n).mockReturnValue({
      t: (key: string) => key,
      isRTL: () => true,
    });

    const { getByDisplayValue } = render(
      <AccessibleTextInput
        label="RTL Input"
        value="RTL text"
        onChangeText={() => {}}
      />
    );

    const input = getByDisplayValue('RTL text');
    expect(input.props.style.textAlign).toBe('right');
    expect(input.props.style.writingDirection).toBe('rtl');
  });
});

describe('Accessibility Test Utils', () => {
  it('should detect missing accessibility labels', () => {
    const component = render(
      <AccessibleButton
        title="Button"
        onPress={() => {}}
        // Missing accessibilityLabel
      />
    );

    const result = AccessibilityTestUtils.testAccessibility(component.toJSON() as any);
    expect(result.passed).toBe(false);
    expect(result.errors.some(error => error.includes('missing accessibilityLabel'))).toBe(true);
  });

  it('should detect insufficient touch target sizes', () => {
    const component = render(
      <AccessibleButton
        title="Tiny Button"
        onPress={() => {}}
        style={{ width: 20, height: 20 }}
      />
    );

    const result = AccessibilityTestUtils.testAccessibility(component.toJSON() as any, {
      checkTouchTargets: true,
    });
    
    expect(result.passed).toBe(false);
    expect(result.errors.some(error => error.includes('width 20px'))).toBe(true);
    expect(result.errors.some(error => error.includes('height 20px'))).toBe(true);
  });

  it('should provide helpful suggestions', () => {
    const component = render(
      <AccessibleButton
        title="Complex Button"
        onPress={() => {}}
        accessibilityLabel="Complex button"
        // Missing accessibilityHint for complex interaction
      />
    );

    const result = AccessibilityTestUtils.testAccessibility(component.toJSON() as any);
    expect(result.suggestions.some(suggestion => 
      suggestion.includes('Consider adding accessibilityHint')
    )).toBe(true);
  });

  it('should validate WCAG compliance levels', () => {
    const component = render(
      <AccessibleButton
        title="WCAG Test"
        onPress={() => {}}
        accessibilityLabel="WCAG compliant button"
        accessibilityHint="Double tap to test WCAG compliance"
      />
    );

    const resultAA = AccessibilityTestUtils.testAccessibility(component.toJSON() as any, {
      level: 'AA',
    });
    
    const resultAAA = AccessibilityTestUtils.testAccessibility(component.toJSON() as any, {
      level: 'AAA',
    });

    expect(resultAA.passed).toBe(true);
    expect(resultAAA.passed).toBe(true);
  });
});