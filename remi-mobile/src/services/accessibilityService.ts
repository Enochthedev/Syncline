import { AccessibilityInfo, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface AccessibilitySettings {
    screenReaderEnabled: boolean;
    reduceMotion: boolean;
    highContrast: boolean;
    textScaling: number;
    voiceControlEnabled: boolean;
    hapticFeedback: boolean;
}

export interface AccessibilityAnnouncement {
    message: string;
    priority: 'low' | 'medium' | 'high';
    delay?: number;
}

class AccessibilityService {
    private settings: AccessibilitySettings = {
        screenReaderEnabled: false,
        reduceMotion: false,
        highContrast: false,
        textScaling: 1.0,
        voiceControlEnabled: false,
        hapticFeedback: true,
    };

    private listeners: Array<(settings: AccessibilitySettings) => void> = [];

    async initialize(): Promise<void> {
        try {
            // Load saved settings
            await this.loadSettings();

            // Check system accessibility settings
            await this.checkSystemAccessibility();

            // Set up accessibility listeners
            this.setupAccessibilityListeners();
        } catch (error) {
            console.error('Failed to initialize accessibility service:', error);
        }
    }

    private async loadSettings(): Promise<void> {
        try {
            const savedSettings = await AsyncStorage.getItem('accessibility_settings');
            if (savedSettings) {
                this.settings = { ...this.settings, ...JSON.parse(savedSettings) };
            }
        } catch (error) {
            console.error('Failed to load accessibility settings:', error);
        }
    }

    private async saveSettings(): Promise<void> {
        try {
            await AsyncStorage.setItem('accessibility_settings', JSON.stringify(this.settings));
        } catch (error) {
            console.error('Failed to save accessibility settings:', error);
        }
    }

    private async checkSystemAccessibility(): Promise<void> {
        try {
            // Check if screen reader is enabled
            const screenReaderEnabled = await AccessibilityInfo.isScreenReaderEnabled();

            // Check if reduce motion is enabled
            const reduceMotionEnabled = await AccessibilityInfo.isReduceMotionEnabled();

            // Check if reduce transparency is enabled (high contrast indicator)
            const reduceTransparencyEnabled = Platform.OS === 'ios'
                ? await AccessibilityInfo.isReduceTransparencyEnabled()
                : false;

            this.settings = {
                ...this.settings,
                screenReaderEnabled,
                reduceMotion: reduceMotionEnabled,
                highContrast: reduceTransparencyEnabled,
            };

            this.notifyListeners();
        } catch (error) {
            console.error('Failed to check system accessibility:', error);
        }
    }

    private setupAccessibilityListeners(): void {
        // Listen for screen reader changes
        AccessibilityInfo.addEventListener('screenReaderChanged', (enabled) => {
            this.settings.screenReaderEnabled = enabled;
            this.notifyListeners();
        });

        // Listen for reduce motion changes
        AccessibilityInfo.addEventListener('reduceMotionChanged', (enabled) => {
            this.settings.reduceMotion = enabled;
            this.notifyListeners();
        });

        // Listen for reduce transparency changes (iOS only)
        if (Platform.OS === 'ios') {
            AccessibilityInfo.addEventListener('reduceTransparencyChanged', (enabled) => {
                this.settings.highContrast = enabled;
                this.notifyListeners();
            });
        }
    }

    getSettings(): AccessibilitySettings {
        return { ...this.settings };
    }

    async updateSettings(updates: Partial<AccessibilitySettings>): Promise<void> {
        this.settings = { ...this.settings, ...updates };
        await this.saveSettings();
        this.notifyListeners();
    }

    subscribeToChanges(callback: (settings: AccessibilitySettings) => void): () => void {
        this.listeners.push(callback);

        // Return unsubscribe function
        return () => {
            const index = this.listeners.indexOf(callback);
            if (index > -1) {
                this.listeners.splice(index, 1);
            }
        };
    }

    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.settings));
    }

    // Announce message to screen reader
    announceForAccessibility(announcement: AccessibilityAnnouncement): void {
        if (!this.settings.screenReaderEnabled) return;

        const delay = announcement.delay || 0;

        setTimeout(() => {
            AccessibilityInfo.announceForAccessibility(announcement.message);
        }, delay);
    }

    // Set accessibility focus to element
    setAccessibilityFocus(elementRef: any): void {
        if (!this.settings.screenReaderEnabled) return;

        if (elementRef?.current) {
            AccessibilityInfo.setAccessibilityFocus(elementRef.current);
        }
    }

    // Get recommended text size based on accessibility settings
    getAccessibleTextSize(baseSize: number): number {
        return baseSize * this.settings.textScaling;
    }

    // Get accessible color scheme
    getAccessibleColors() {
        if (this.settings.highContrast) {
            return {
                primary: '#000000',
                secondary: '#FFFFFF',
                background: '#FFFFFF',
                surface: '#F5F5F5',
                text: '#000000',
                textSecondary: '#333333',
                border: '#000000',
                error: '#D32F2F',
                success: '#2E7D32',
                warning: '#F57C00',
            };
        }

        // Return default colors for normal contrast
        return {
            primary: '#2196F3',
            secondary: '#03DAC6',
            background: '#FFFFFF',
            surface: '#F5F5F5',
            text: '#212121',
            textSecondary: '#757575',
            border: '#E0E0E0',
            error: '#F44336',
            success: '#4CAF50',
            warning: '#FF9800',
        };
    }

    // Check if animations should be reduced
    shouldReduceMotion(): boolean {
        return this.settings.reduceMotion;
    }

    // Get accessible touch target size
    getAccessibleTouchTarget(): { minWidth: number; minHeight: number } {
        return {
            minWidth: 44, // iOS HIG minimum
            minHeight: 44,
        };
    }

    // Generate accessibility label for complex components
    generateAccessibilityLabel(parts: string[]): string {
        return parts.filter(Boolean).join(', ');
    }

    // Generate accessibility hint for actions
    generateAccessibilityHint(action: string, context?: string): string {
        const base = `Double tap to ${action}`;
        return context ? `${base}. ${context}` : base;
    }
}

export const accessibilityService = new AccessibilityService();