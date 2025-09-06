import { useEffect, useState, useCallback } from 'react';
import { accessibilityService, AccessibilitySettings } from '../services/accessibilityService';

export const useAccessibility = () => {
    const [settings, setSettings] = useState<AccessibilitySettings>(
        accessibilityService.getSettings()
    );

    useEffect(() => {
        const unsubscribe = accessibilityService.subscribeToChanges(setSettings);
        return unsubscribe;
    }, []);

    const updateSettings = useCallback(async (updates: Partial<AccessibilitySettings>) => {
        await accessibilityService.updateSettings(updates);
    }, []);

    const announceForAccessibility = useCallback((message: string, priority: 'low' | 'medium' | 'high' = 'medium') => {
        accessibilityService.announceForAccessibility({ message, priority });
    }, []);

    const setAccessibilityFocus = useCallback((elementRef: any) => {
        accessibilityService.setAccessibilityFocus(elementRef);
    }, []);

    const getAccessibleTextSize = useCallback((baseSize: number) => {
        return accessibilityService.getAccessibleTextSize(baseSize);
    }, [settings.textScaling]);

    const getAccessibleColors = useCallback(() => {
        return accessibilityService.getAccessibleColors();
    }, [settings.highContrast]);

    const shouldReduceMotion = useCallback(() => {
        return accessibilityService.shouldReduceMotion();
    }, [settings.reduceMotion]);

    const getAccessibleTouchTarget = useCallback(() => {
        return accessibilityService.getAccessibleTouchTarget();
    }, []);

    const generateAccessibilityLabel = useCallback((parts: string[]) => {
        return accessibilityService.generateAccessibilityLabel(parts);
    }, []);

    const generateAccessibilityHint = useCallback((action: string, context?: string) => {
        return accessibilityService.generateAccessibilityHint(action, context);
    }, []);

    return {
        settings,
        updateSettings,
        announceForAccessibility,
        setAccessibilityFocus,
        getAccessibleTextSize,
        getAccessibleColors,
        shouldReduceMotion,
        getAccessibleTouchTarget,
        generateAccessibilityLabel,
        generateAccessibilityHint,
    };
};