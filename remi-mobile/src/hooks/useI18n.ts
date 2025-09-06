import { useEffect, useState, useCallback } from 'react';
import { i18nService, TranslationKeys, LocaleInfo } from '../services/internationalizationService';

export const useI18n = () => {
    const [currentLocale, setCurrentLocale] = useState<string>(i18nService.getCurrentLocale());

    useEffect(() => {
        const unsubscribe = i18nService.subscribeToChanges(setCurrentLocale);
        return unsubscribe;
    }, []);

    const translate = useCallback((key: keyof TranslationKeys, params?: Record<string, any>) => {
        return i18nService.translate(key, params);
    }, [currentLocale]);

    const setLocale = useCallback(async (locale: string) => {
        await i18nService.setLocale(locale);
    }, []);

    const getSupportedLocales = useCallback((): LocaleInfo[] => {
        return i18nService.getSupportedLocales();
    }, []);

    const getLocaleInfo = useCallback((locale?: string): LocaleInfo | undefined => {
        return i18nService.getLocaleInfo(locale);
    }, []);

    const isRTL = useCallback((locale?: string): boolean => {
        return i18nService.isRTL(locale);
    }, [currentLocale]);

    const formatNumber = useCallback((number: number, options?: Intl.NumberFormatOptions) => {
        return i18nService.formatNumber(number, options);
    }, [currentLocale]);

    const formatDate = useCallback((date: Date, options?: Intl.DateTimeFormatOptions) => {
        return i18nService.formatDate(date, options);
    }, [currentLocale]);

    const formatRelativeTime = useCallback((date: Date) => {
        return i18nService.formatRelativeTime(date);
    }, [currentLocale]);

    const formatCurrency = useCallback((amount: number, currency?: string) => {
        return i18nService.formatCurrency(amount, currency);
    }, [currentLocale]);

    // Shorthand for translate function
    const t = translate;

    return {
        currentLocale,
        setLocale,
        translate,
        t, // Shorthand
        getSupportedLocales,
        getLocaleInfo,
        isRTL,
        formatNumber,
        formatDate,
        formatRelativeTime,
        formatCurrency,
    };
};