import { useEffect, useState, useCallback } from 'react';
import { webI18nService, WebTranslationKeys, LocaleConfig } from '../services/internationalizationService';

export const useI18n = () => {
    const [currentLocale, setCurrentLocale] = useState<string>(webI18nService.getCurrentLocale());

    useEffect(() => {
        const unsubscribe = webI18nService.subscribeToChanges(setCurrentLocale);
        return unsubscribe;
    }, []);

    const translate = useCallback((key: keyof WebTranslationKeys, params?: Record<string, any>) => {
        return webI18nService.translate(key, params);
    }, [currentLocale]);

    const setLocale = useCallback(async (locale: string) => {
        await webI18nService.setLocale(locale);
    }, []);

    const getSupportedLocales = useCallback((): LocaleConfig[] => {
        return webI18nService.getSupportedLocales();
    }, []);

    const getLocaleConfig = useCallback((locale?: string): LocaleConfig | undefined => {
        return webI18nService.getLocaleConfig(locale);
    }, []);

    const isRTL = useCallback((locale?: string): boolean => {
        return webI18nService.isRTL(locale);
    }, [currentLocale]);

    const formatNumber = useCallback((
        number: number,
        options?: Intl.NumberFormatOptions & { useLocaleFormat?: boolean }
    ) => {
        return webI18nService.formatNumber(number, options);
    }, [currentLocale]);

    const formatDate = useCallback((
        date: Date,
        options?: Intl.DateTimeFormatOptions & { useLocaleFormat?: boolean }
    ) => {
        return webI18nService.formatDate(date, options);
    }, [currentLocale]);

    const formatTime = useCallback((
        date: Date,
        options?: Intl.DateTimeFormatOptions & { useLocaleFormat?: boolean }
    ) => {
        return webI18nService.formatTime(date, options);
    }, [currentLocale]);

    const formatRelativeTime = useCallback((date: Date) => {
        return webI18nService.formatRelativeTime(date);
    }, [currentLocale]);

    const formatCurrency = useCallback((amount: number, currency?: string) => {
        return webI18nService.formatCurrency(amount, currency);
    }, [currentLocale]);

    const pluralize = useCallback((
        count: number,
        singular: keyof WebTranslationKeys,
        plural?: keyof WebTranslationKeys,
        zero?: keyof WebTranslationKeys
    ) => {
        return webI18nService.pluralize(count, singular, plural, zero);
    }, [currentLocale]);

    const getTextDirection = useCallback(() => {
        return webI18nService.getTextDirection();
    }, [currentLocale]);

    const getStartDirection = useCallback(() => {
        return webI18nService.getStartDirection();
    }, [currentLocale]);

    const getEndDirection = useCallback(() => {
        return webI18nService.getEndDirection();
    }, [currentLocale]);

    // Shorthand for translate function
    const t = translate;

    return {
        currentLocale,
        setLocale,
        translate,
        t, // Shorthand
        getSupportedLocales,
        getLocaleConfig,
        isRTL,
        formatNumber,
        formatDate,
        formatTime,
        formatRelativeTime,
        formatCurrency,
        pluralize,
        getTextDirection,
        getStartDirection,
        getEndDirection,
    };
};