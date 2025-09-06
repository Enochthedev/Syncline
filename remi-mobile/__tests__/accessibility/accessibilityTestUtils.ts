import { ReactTestInstance } from 'react-test-renderer';
import { AccessibilityRole } from 'react-native';

export interface AccessibilityTestResult {
    passed: boolean;
    errors: string[];
    warnings: string[];
    suggestions: string[];
}

export interface WCAGTestOptions {
    level: 'A' | 'AA' | 'AAA';
    includeWarnings: boolean;
    checkColorContrast: boolean;
    checkTouchTargets: boolean;
    checkLabels: boolean;
    checkFocus: boolean;
}

export class AccessibilityTestUtils {
    private static readonly MIN_TOUCH_TARGET_SIZE = 44;
    private static readonly MIN_CONTRAST_RATIO_AA = 4.5;
    private static readonly MIN_CONTRAST_RATIO_AAA = 7.0;

    /**
     * Comprehensive accessibility test for React Native components
     */
    static testAccessibility(
        component: ReactTestInstance,
        options: Partial<WCAGTestOptions> = {}
    ): AccessibilityTestResult {
        const opts: WCAGTestOptions = {
            level: 'AA',
            includeWarnings: true,
            checkColorContrast: true,
            checkTouchTargets: true,
            checkLabels: true,
            checkFocus: true,
            ...options,
        };

        const result: AccessibilityTestResult = {
            passed: true,
            errors: [],
            warnings: [],
            suggestions: [],
        };

        // Test accessibility labels and roles
        if (opts.checkLabels) {
            this.testAccessibilityLabels(component, result);
        }

        // Test touch target sizes
        if (opts.checkTouchTargets) {
            this.testTouchTargets(component, result);
        }

        // Test focus management
        if (opts.checkFocus) {
            this.testFocusManagement(component, result);
        }

        // Test semantic structure
        this.testSemanticStructure(component, result);

        // Test keyboard navigation
        this.testKeyboardNavigation(component, result);

        // Determine overall pass/fail
        result.passed = result.errors.length === 0;

        return result;
    }

    /**
     * Test accessibility labels and descriptions
     */
    private static testAccessibilityLabels(
        component: ReactTestInstance,
        result: AccessibilityTestResult
    ): void {
        const interactiveElements = this.findInteractiveElements(component);

        interactiveElements.forEach((element, index) => {
            const props = element.props;
            const accessibilityLabel = props.accessibilityLabel;
            const accessibilityRole = props.accessibilityRole;

            // Check for missing accessibility labels on interactive elements
            if (!accessibilityLabel && this.requiresAccessibilityLabel(accessibilityRole)) {
                result.errors.push(
                    `Interactive element at index ${index} (role: ${accessibilityRole}) is missing accessibilityLabel`
                );
            }

            // Check for empty or meaningless labels
            if (accessibilityLabel && this.isMeaninglessLabel(accessibilityLabel)) {
                result.warnings.push(
                    `Element at index ${index} has a potentially meaningless accessibility label: "${accessibilityLabel}"`
                );
            }

            // Check for missing accessibility hints on complex interactions
            if (this.requiresAccessibilityHint(accessibilityRole) && !props.accessibilityHint) {
                result.suggestions.push(
                    `Consider adding accessibilityHint to element at index ${index} for better user guidance`
                );
            }
        });
    }

    /**
     * Test touch target sizes for WCAG compliance
     */
    private static testTouchTargets(
        component: ReactTestInstance,
        result: AccessibilityTestResult
    ): void {
        const touchableElements = this.findTouchableElements(component);

        touchableElements.forEach((element, index) => {
            const style = this.extractStyle(element);
            const width = style.width || style.minWidth;
            const height = style.height || style.minHeight;

            if (width && width < this.MIN_TOUCH_TARGET_SIZE) {
                result.errors.push(
                    `Touchable element at index ${index} has width ${width}px, minimum is ${this.MIN_TOUCH_TARGET_SIZE}px`
                );
            }

            if (height && height < this.MIN_TOUCH_TARGET_SIZE) {
                result.errors.push(
                    `Touchable element at index ${index} has height ${height}px, minimum is ${this.MIN_TOUCH_TARGET_SIZE}px`
                );
            }

            // Check for adequate spacing between touch targets
            const padding = style.padding || style.paddingVertical || style.paddingHorizontal || 0;
            if (padding < 8) {
                result.warnings.push(
                    `Touchable element at index ${index} may need more padding for easier touch interaction`
                );
            }
        });
    }

    /**
     * Test focus management and keyboard navigation
     */
    private static testFocusManagement(
        component: ReactTestInstance,
        result: AccessibilityTestResult
    ): void {
        const focusableElements = this.findFocusableElements(component);

        // Check for proper focus indicators
        focusableElements.forEach((element, index) => {
            const props = element.props;

            if (!props.accessible && !props.accessibilityRole) {
                result.warnings.push(
                    `Focusable element at index ${index} should have accessible=true or accessibilityRole`
                );
            }

            // Check for focus trap in modals
            if (this.isModal(element) && !this.hasFocusTrap(element)) {
                result.errors.push(
                    `Modal at index ${index} should implement focus trapping for keyboard users`
                );
            }
        });

        // Check for logical tab order
        if (!this.hasLogicalTabOrder(focusableElements)) {
            result.warnings.push(
                'Focus order may not be logical - consider using accessibilityViewIsModal or adjusting component order'
            );
        }
    }

    /**
     * Test semantic structure and hierarchy
     */
    private static testSemanticStructure(
        component: ReactTestInstance,
        result: AccessibilityTestResult
    ): void {
        const headings = this.findElementsByRole(component, 'header');

        // Check for proper heading hierarchy
        if (headings.length > 1 && !this.hasProperHeadingHierarchy(headings)) {
            result.warnings.push(
                'Heading hierarchy may not be logical - ensure headings follow a proper structure'
            );
        }

        // Check for landmark roles
        const landmarks = this.findLandmarkElements(component);
        if (landmarks.length === 0) {
            result.suggestions.push(
                'Consider adding landmark roles (navigation, main, etc.) for better screen reader navigation'
            );
        }

        // Check for list structure
        const lists = this.findElementsByRole(component, 'list');
        lists.forEach((list, index) => {
            const listItems = this.findChildElementsByRole(list, 'listitem');
            if (listItems.length === 0) {
                result.warnings.push(
                    `List at index ${index} should contain elements with role="listitem"`
                );
            }
        });
    }

    /**
     * Test keyboard navigation support
     */
    private static testKeyboardNavigation(
        component: ReactTestInstance,
        result: AccessibilityTestResult
    ): void {
        const interactiveElements = this.findInteractiveElements(component);

        interactiveElements.forEach((element, index) => {
            const props = element.props;

            // Check for keyboard event handlers
            if (!props.onPress && !props.onKeyPress && !props.onSubmitEditing) {
                result.warnings.push(
                    `Interactive element at index ${index} may not be keyboard accessible`
                );
            }

            // Check for proper ARIA states
            if (this.isToggleable(element) && props.accessibilityState?.checked === undefined) {
                result.warnings.push(
                    `Toggleable element at index ${index} should have accessibilityState.checked`
                );
            }

            if (this.isExpandable(element) && props.accessibilityState?.expanded === undefined) {
                result.warnings.push(
                    `Expandable element at index ${index} should have accessibilityState.expanded`
                );
            }
        });
    }

    // Helper methods

    private static findInteractiveElements(component: ReactTestInstance): ReactTestInstance[] {
        const interactiveRoles: AccessibilityRole[] = [
            'button',
            'link',
            'search',
            'tab',
            'switch',
            'checkbox',
            'radio',
            'combobox',
            'menu',
            'menuitem',
            'tablist',
        ];

        return component.findAll((node) => {
            if (typeof node === 'string') return false;
            const role = node.props?.accessibilityRole;
            return interactiveRoles.includes(role) ||
                node.type === 'TouchableOpacity' ||
                node.type === 'TouchableHighlight' ||
                node.type === 'TouchableWithoutFeedback' ||
                node.type === 'Pressable';
        });
    }

    private static findTouchableElements(component: ReactTestInstance): ReactTestInstance[] {
        return component.findAll((node) => {
            if (typeof node === 'string') return false;
            return node.type === 'TouchableOpacity' ||
                node.type === 'TouchableHighlight' ||
                node.type === 'TouchableWithoutFeedback' ||
                node.type === 'Pressable' ||
                node.props?.onPress;
        });
    }

    private static findFocusableElements(component: ReactTestInstance): ReactTestInstance[] {
        return component.findAll((node) => {
            if (typeof node === 'string') return false;
            return node.props?.accessible === true ||
                node.props?.accessibilityRole ||
                node.props?.focusable === true;
        });
    }

    private static findElementsByRole(
        component: ReactTestInstance,
        role: AccessibilityRole
    ): ReactTestInstance[] {
        return component.findAll((node) => {
            if (typeof node === 'string') return false;
            return node.props?.accessibilityRole === role;
        });
    }

    private static findChildElementsByRole(
        parent: ReactTestInstance,
        role: AccessibilityRole
    ): ReactTestInstance[] {
        return parent.findAll((node) => {
            if (typeof node === 'string') return false;
            return node.props?.accessibilityRole === role;
        });
    }

    private static findLandmarkElements(component: ReactTestInstance): ReactTestInstance[] {
        const landmarkRoles: AccessibilityRole[] = [
            'navigation',
            'main',
            'banner',
            'contentinfo',
            'complementary',
            'region',
        ];

        return component.findAll((node) => {
            if (typeof node === 'string') return false;
            return landmarkRoles.includes(node.props?.accessibilityRole);
        });
    }

    private static requiresAccessibilityLabel(role?: AccessibilityRole): boolean {
        const rolesRequiringLabels: AccessibilityRole[] = [
            'button',
            'link',
            'search',
            'tab',
            'switch',
            'checkbox',
            'radio',
            'combobox',
            'menu',
            'menuitem',
        ];
        return role ? rolesRequiringLabels.includes(role) : false;
    }

    private static requiresAccessibilityHint(role?: AccessibilityRole): boolean {
        const rolesRequiringHints: AccessibilityRole[] = [
            'button',
            'link',
            'tab',
            'combobox',
            'menu',
        ];
        return role ? rolesRequiringHints.includes(role) : false;
    }

    private static isMeaninglessLabel(label: string): boolean {
        const meaninglessLabels = [
            'button',
            'click here',
            'tap here',
            'link',
            'image',
            'icon',
            'more',
            'continue',
        ];
        return meaninglessLabels.includes(label.toLowerCase().trim());
    }

    private static extractStyle(element: ReactTestInstance): any {
        const style = element.props?.style;
        if (Array.isArray(style)) {
            return Object.assign({}, ...style);
        }
        return style || {};
    }

    private static isModal(element: ReactTestInstance): boolean {
        return element.props?.accessibilityViewIsModal === true ||
            element.type === 'Modal';
    }

    private static hasFocusTrap(element: ReactTestInstance): boolean {
        // This would need to be implemented based on the specific modal implementation
        return element.props?.accessibilityViewIsModal === true;
    }

    private static hasLogicalTabOrder(elements: ReactTestInstance[]): boolean {
        // This is a simplified check - in practice, you'd need to analyze the actual layout
        return elements.length <= 1 || elements.every(el => el.props?.accessible !== false);
    }

    private static hasProperHeadingHierarchy(headings: ReactTestInstance[]): boolean {
        // This would need to be implemented based on heading level analysis
        return true; // Simplified for this example
    }

    private static isToggleable(element: ReactTestInstance): boolean {
        const role = element.props?.accessibilityRole;
        return role === 'switch' || role === 'checkbox' || role === 'radio';
    }

    private static isExpandable(element: ReactTestInstance): boolean {
        const role = element.props?.accessibilityRole;
        return role === 'button' && element.props?.accessibilityHint?.includes('expand');
    }
}

/**
 * Jest matcher for accessibility testing
 */
export const toBeAccessible = (
    component: ReactTestInstance,
    options?: Partial<WCAGTestOptions>
) => {
    const result = AccessibilityTestUtils.testAccessibility(component, options);

    return {
        pass: result.passed,
        message: () => {
            if (result.passed) {
                return 'Component passes accessibility tests';
            }

            const messages = [
                'Component failed accessibility tests:',
                ...result.errors.map(error => `  ❌ ${error}`),
                ...result.warnings.map(warning => `  ⚠️  ${warning}`),
                ...result.suggestions.map(suggestion => `  💡 ${suggestion}`),
            ];

            return messages.join('\n');
        },
    };
};