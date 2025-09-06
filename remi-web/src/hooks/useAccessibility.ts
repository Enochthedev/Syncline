import { useEffect, useState, useCallback, useRef } from 'react';
import { webAccessibilityService, WebAccessibilitySettings, KeyboardShortcut } from '../services/accessibilityService';

export const useAccessibility = () => {
    const [settings, setSettings] = useState<WebAccessibilitySettings>(
        webAccessibilityService.getSettings()
    );

    useEffect(() => {
        const unsubscribe = webAccessibilityService.subscribeToChanges(setSettings);
        return unsubscribe;
    }, []);

    const updateSettings = useCallback(async (updates: Partial<WebAccessibilitySettings>) => {
        await webAccessibilityService.updateSettings(updates);
    }, []);

    const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
        webAccessibilityService.announce(message, priority);
    }, []);

    const registerShortcut = useCallback((shortcut: KeyboardShortcut) => {
        webAccessibilityService.registerShortcut(shortcut);
    }, []);

    const getKeyboardShortcuts = useCallback(() => {
        return webAccessibilityService.getKeyboardShortcuts();
    }, []);

    return {
        settings,
        updateSettings,
        announce,
        registerShortcut,
        getKeyboardShortcuts,
    };
};

export const useFocusTrap = (isActive: boolean = true) => {
    const containerRef = useRef<HTMLElement>(null);
    const cleanupRef = useRef<(() => void) | null>(null);

    useEffect(() => {
        if (isActive && containerRef.current) {
            cleanupRef.current = webAccessibilityService.trapFocus(containerRef.current);
        }

        return () => {
            if (cleanupRef.current) {
                cleanupRef.current();
                cleanupRef.current = null;
            }
        };
    }, [isActive]);

    return containerRef;
};

export const useLiveRegion = (id: string, level: 'polite' | 'assertive' = 'polite') => {
    const regionRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        regionRef.current = webAccessibilityService.createLiveRegion(id, level);

        return () => {
            // Cleanup is handled by the service
        };
    }, [id, level]);

    const announce = useCallback((message: string) => {
        webAccessibilityService.announceToRegion(id, message);
    }, [id]);

    return { announce };
};

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]) => {
    useEffect(() => {
        shortcuts.forEach(shortcut => {
            webAccessibilityService.registerShortcut(shortcut);
        });

        // Listen for shortcut events
        const handleShortcut = (event: CustomEvent) => {
            const shortcut = event.detail as KeyboardShortcut;
            console.log('Shortcut executed:', shortcut);
        };

        window.addEventListener('accessibility-shortcut', handleShortcut as EventListener);

        return () => {
            window.removeEventListener('accessibility-shortcut', handleShortcut as EventListener);
        };
    }, [shortcuts]);
};

export const useReducedMotion = () => {
    const { settings } = useAccessibility();
    return settings.reduceMotion;
};

export const useHighContrast = () => {
    const { settings } = useAccessibility();
    return settings.highContrast;
};

export const useTextScaling = () => {
    const { settings } = useAccessibility();
    return settings.textScaling;
};