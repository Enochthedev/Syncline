import { accessibilityService } from '../../src/services/accessibilityService';
import { AccessibilityInfo } from 'react-native';

// Mock React Native AccessibilityInfo
jest.mock('react-native', () => ({
    AccessibilityInfo: {
        isScreenReaderEnabled: jest.fn(),
        isReduceMotionEnabled: jest.fn(),
        isReduceTransparencyEnabled: jest.fn(),
        addEventListener: jest.fn(),
        announceForAccessibility: jest.fn(),
        setAccessibilityFocus: jest.fn(),
    },
    Platform: {
        OS: 'ios',
    },
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
    getItem: jest.fn(),
    setItem: jest.fn(),
}));

describe('AccessibilityService', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('initialization', () => {
        it('should initialize with system accessibility settings', async () => {
            (AccessibilityInfo.isScreenReaderEnabled as jest.Mock).mockResolvedValue(true);
            (AccessibilityInfo.isReduceMotionEnabled as jest.Mock).mockResolvedValue(false);
            (AccessibilityInfo.isReduceTransparencyEnabled as jest.Mock).mockResolvedValue(true);

            await accessibilityService.initialize();

            const settings = accessibilityService.getSettings();
            expect(settings.screenReaderEnabled).toBe(true);
            expect(settings.reduceMotion).toBe(false);
            expect(settings.highContrast).toBe(true);
        });

        it('should set up accessibility event listeners', async () => {
            await accessibilityService.initialize();

            expect(AccessibilityInfo.addEventListener).toHaveBeenCalledWith(
                'screenReaderChanged',
                expect.any(Function)
            );
            expect(AccessibilityInfo.addEventListener).toHaveBeenCalledWith(
                'reduceMotionChanged',
                expect.any(Function)
            );
        });
    });

    describe('settings management', () => {
        it('should update accessibility settings', async () => {
            await accessibilityService.initialize();

            await accessibilityService.updateSettings({
                textScaling: 1.5,
                hapticFeedback: false,
            });

            const settings = accessibilityService.getSettings();
            expect(settings.textScaling).toBe(1.5);
            expect(settings.hapticFeedback).toBe(false);
        });

        it('should notify listeners when settings change', async () => {
            await accessibilityService.initialize();

            const mockListener = jest.fn();
            const unsubscribe = accessibilityService.subscribeToChanges(mockListener);

            await accessibilityService.updateSettings({ textScaling: 2.0 });

            expect(mockListener).toHaveBeenCalledWith(
                expect.objectContaining({ textScaling: 2.0 })
            );

            unsubscribe();
        });
    });

    describe('accessibility announcements', () => {
        it('should announce messages for screen readers', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ screenReaderEnabled: true });

            accessibilityService.announceForAccessibility({
                message: 'Test announcement',
                priority: 'high',
            });

            expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
                'Test announcement'
            );
        });

        it('should not announce when screen reader is disabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ screenReaderEnabled: false });

            accessibilityService.announceForAccessibility({
                message: 'Test announcement',
                priority: 'high',
            });

            expect(AccessibilityInfo.announceForAccessibility).not.toHaveBeenCalled();
        });

        it('should support delayed announcements', (done) => {
            accessibilityService.initialize().then(() => {
                accessibilityService.updateSettings({ screenReaderEnabled: true }).then(() => {
                    accessibilityService.announceForAccessibility({
                        message: 'Delayed announcement',
                        priority: 'medium',
                        delay: 100,
                    });

                    setTimeout(() => {
                        expect(AccessibilityInfo.announceForAccessibility).toHaveBeenCalledWith(
                            'Delayed announcement'
                        );
                        done();
                    }, 150);
                });
            });
        });
    });

    describe('accessible text sizing', () => {
        it('should scale text based on accessibility settings', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ textScaling: 1.5 });

            const scaledSize = accessibilityService.getAccessibleTextSize(16);
            expect(scaledSize).toBe(24);
        });

        it('should return original size when scaling is 1.0', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ textScaling: 1.0 });

            const scaledSize = accessibilityService.getAccessibleTextSize(16);
            expect(scaledSize).toBe(16);
        });
    });

    describe('accessible colors', () => {
        it('should return high contrast colors when enabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ highContrast: true });

            const colors = accessibilityService.getAccessibleColors();
            expect(colors.primary).toBe('#000000');
            expect(colors.background).toBe('#FFFFFF');
            expect(colors.text).toBe('#000000');
        });

        it('should return normal colors when high contrast is disabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ highContrast: false });

            const colors = accessibilityService.getAccessibleColors();
            expect(colors.primary).toBe('#2196F3');
            expect(colors.background).toBe('#FFFFFF');
            expect(colors.text).toBe('#212121');
        });
    });

    describe('motion preferences', () => {
        it('should respect reduce motion setting', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ reduceMotion: true });

            expect(accessibilityService.shouldReduceMotion()).toBe(true);
        });

        it('should allow motion when reduce motion is disabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ reduceMotion: false });

            expect(accessibilityService.shouldReduceMotion()).toBe(false);
        });
    });

    describe('touch targets', () => {
        it('should provide minimum touch target size', () => {
            const touchTarget = accessibilityService.getAccessibleTouchTarget();
            expect(touchTarget.minWidth).toBe(44);
            expect(touchTarget.minHeight).toBe(44);
        });
    });

    describe('accessibility label generation', () => {
        it('should generate meaningful accessibility labels', () => {
            const label = accessibilityService.generateAccessibilityLabel([
                'Contact',
                'John Doe',
                '5 messages',
            ]);
            expect(label).toBe('Contact, John Doe, 5 messages');
        });

        it('should filter out empty parts', () => {
            const label = accessibilityService.generateAccessibilityLabel([
                'Contact',
                '',
                'John Doe',
                null as any,
                '5 messages',
            ]);
            expect(label).toBe('Contact, John Doe, 5 messages');
        });
    });

    describe('accessibility hints', () => {
        it('should generate helpful accessibility hints', () => {
            const hint = accessibilityService.generateAccessibilityHint('open contact');
            expect(hint).toBe('Double tap to open contact');
        });

        it('should include context in hints when provided', () => {
            const hint = accessibilityService.generateAccessibilityHint(
                'send message',
                'This will open the message composer'
            );
            expect(hint).toBe('Double tap to send message. This will open the message composer');
        });
    });

    describe('focus management', () => {
        it('should set accessibility focus when screen reader is enabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ screenReaderEnabled: true });

            const mockRef = { current: {} };
            accessibilityService.setAccessibilityFocus(mockRef);

            expect(AccessibilityInfo.setAccessibilityFocus).toHaveBeenCalledWith(mockRef.current);
        });

        it('should not set focus when screen reader is disabled', async () => {
            await accessibilityService.initialize();
            await accessibilityService.updateSettings({ screenReaderEnabled: false });

            const mockRef = { current: {} };
            accessibilityService.setAccessibilityFocus(mockRef);

            expect(AccessibilityInfo.setAccessibilityFocus).not.toHaveBeenCalled();
        });
    });
});