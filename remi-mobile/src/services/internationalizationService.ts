import AsyncStorage from '@react-native-async-storage/async-storage';
import { NativeModules, Platform } from 'react-native';

export interface LocaleInfo {
    code: string;
    name: string;
    nativeName: string;
    rtl: boolean;
}

export interface TranslationKeys {
    // Navigation
    'nav.contacts': string;
    'nav.search': string;
    'nav.messages': string;
    'nav.settings': string;

    // Search
    'search.placeholder': string;
    'search.noResults': string;
    'search.searching': string;
    'search.voiceSearch': string;
    'search.naturalLanguage.placeholder': string;

    // Contacts
    'contacts.title': string;
    'contacts.searchPlaceholder': string;
    'contacts.noContacts': string;
    'contacts.lastInteraction': string;
    'contacts.platforms': string;
    'contacts.messageCount': string;

    // Messages
    'messages.title': string;
    'messages.noMessages': string;
    'messages.sending': string;
    'messages.sent': string;
    'messages.failed': string;
    'messages.retry': string;

    // Accessibility
    'accessibility.contact.button': string;
    'accessibility.search.button': string;
    'accessibility.message.button': string;
    'accessibility.back.button': string;
    'accessibility.menu.button': string;
    'accessibility.close.button': string;
    'accessibility.loading': string;
    'accessibility.error': string;

    // Common
    'common.loading': string;
    'common.error': string;
    'common.retry': string;
    'common.cancel': string;
    'common.save': string;
    'common.delete': string;
    'common.edit': string;
    'common.done': string;
    'common.yes': string;
    'common.no': string;

    // Time formatting
    'time.now': string;
    'time.minutesAgo': string;
    'time.hoursAgo': string;
    'time.daysAgo': string;
    'time.weeksAgo': string;
    'time.monthsAgo': string;
    'time.yearsAgo': string;
}

const SUPPORTED_LOCALES: LocaleInfo[] = [
    { code: 'en', name: 'English', nativeName: 'English', rtl: false },
    { code: 'es', name: 'Spanish', nativeName: 'Español', rtl: false },
    { code: 'fr', name: 'French', nativeName: 'Français', rtl: false },
    { code: 'de', name: 'German', nativeName: 'Deutsch', rtl: false },
    { code: 'it', name: 'Italian', nativeName: 'Italiano', rtl: false },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', rtl: false },
    { code: 'ru', name: 'Russian', nativeName: 'Русский', rtl: false },
    { code: 'ja', name: 'Japanese', nativeName: '日本語', rtl: false },
    { code: 'ko', name: 'Korean', nativeName: '한국어', rtl: false },
    { code: 'zh', name: 'Chinese', nativeName: '中文', rtl: false },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية', rtl: true },
    { code: 'he', name: 'Hebrew', nativeName: 'עברית', rtl: true },
];

// English translations (default)
const EN_TRANSLATIONS: TranslationKeys = {
    // Navigation
    'nav.contacts': 'Contacts',
    'nav.search': 'Search',
    'nav.messages': 'Messages',
    'nav.settings': 'Settings',

    // Search
    'search.placeholder': 'Search contacts, messages...',
    'search.noResults': 'No results found',
    'search.searching': 'Searching...',
    'search.voiceSearch': 'Voice Search',
    'search.naturalLanguage.placeholder': 'Try "messages from John last week"',

    // Contacts
    'contacts.title': 'Contacts',
    'contacts.searchPlaceholder': 'Search contacts...',
    'contacts.noContacts': 'No contacts found',
    'contacts.lastInteraction': 'Last interaction',
    'contacts.platforms': 'Platforms',
    'contacts.messageCount': 'messages',

    // Messages
    'messages.title': 'Messages',
    'messages.noMessages': 'No messages found',
    'messages.sending': 'Sending...',
    'messages.sent': 'Sent',
    'messages.failed': 'Failed to send',
    'messages.retry': 'Retry',

    // Accessibility
    'accessibility.contact.button': 'Contact button',
    'accessibility.search.button': 'Search button',
    'accessibility.message.button': 'Message button',
    'accessibility.back.button': 'Go back',
    'accessibility.menu.button': 'Open menu',
    'accessibility.close.button': 'Close',
    'accessibility.loading': 'Loading content',
    'accessibility.error': 'Error occurred',

    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.retry': 'Retry',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.done': 'Done',
    'common.yes': 'Yes',
    'common.no': 'No',

    // Time formatting
    'time.now': 'now',
    'time.minutesAgo': '{count} minutes ago',
    'time.hoursAgo': '{count} hours ago',
    'time.daysAgo': '{count} days ago',
    'time.weeksAgo': '{count} weeks ago',
    'time.monthsAgo': '{count} months ago',
    'time.yearsAgo': '{count} years ago',
};

class InternationalizationService {
    private currentLocale: string = 'en';
    private translations: Map<string, Partial<TranslationKeys>> = new Map();
    private listeners: Array<(locale: string) => void> = [];
    private fallbackLocale: string = 'en';

    async initialize(): Promise<void> {
        try {
            // Load saved locale preference
            const savedLocale = await AsyncStorage.getItem('user_locale');

            // Get device locale if no saved preference
            const deviceLocale = this.getDeviceLocale();

            // Set initial locale
            const initialLocale = savedLocale || deviceLocale || 'en';

            // Load default translations
            this.translations.set('en', EN_TRANSLATIONS);

            // Set current locale
            await this.setLocale(initialLocale);

            // Load additional translations
            await this.loadTranslations();
        } catch (error) {
            console.error('Failed to initialize i18n service:', error);
            this.currentLocale = 'en';
        }
    }

    private getDeviceLocale(): string {
        try {
            let locale = 'en';

            if (Platform.OS === 'ios') {
                locale = NativeModules.SettingsManager?.settings?.AppleLocale ||
                    NativeModules.SettingsManager?.settings?.AppleLanguages?.[0] ||
                    'en';
            } else {
                locale = NativeModules.I18nManager?.localeIdentifier || 'en';
            }

            // Extract language code (e.g., 'en-US' -> 'en')
            return locale.split('-')[0].split('_')[0];
        } catch (error) {
            console.error('Failed to get device locale:', error);
            return 'en';
        }
    }

    private async loadTranslations(): Promise<void> {
        // In a real app, these would be loaded from files or API
        // For now, we'll add a few sample translations

        const spanishTranslations: Partial<TranslationKeys> = {
            'nav.contacts': 'Contactos',
            'nav.search': 'Buscar',
            'nav.messages': 'Mensajes',
            'nav.settings': 'Configuración',
            'search.placeholder': 'Buscar contactos, mensajes...',
            'search.noResults': 'No se encontraron resultados',
            'search.searching': 'Buscando...',
            'contacts.title': 'Contactos',
            'contacts.noContacts': 'No se encontraron contactos',
            'messages.title': 'Mensajes',
            'messages.noMessages': 'No se encontraron mensajes',
            'common.loading': 'Cargando...',
            'common.error': 'Error',
            'common.retry': 'Reintentar',
            'common.cancel': 'Cancelar',
            'common.save': 'Guardar',
            'common.delete': 'Eliminar',
        };

        const frenchTranslations: Partial<TranslationKeys> = {
            'nav.contacts': 'Contacts',
            'nav.search': 'Rechercher',
            'nav.messages': 'Messages',
            'nav.settings': 'Paramètres',
            'search.placeholder': 'Rechercher contacts, messages...',
            'search.noResults': 'Aucun résultat trouvé',
            'search.searching': 'Recherche...',
            'contacts.title': 'Contacts',
            'contacts.noContacts': 'Aucun contact trouvé',
            'messages.title': 'Messages',
            'messages.noMessages': 'Aucun message trouvé',
            'common.loading': 'Chargement...',
            'common.error': 'Erreur',
            'common.retry': 'Réessayer',
            'common.cancel': 'Annuler',
            'common.save': 'Enregistrer',
            'common.delete': 'Supprimer',
        };

        this.translations.set('es', spanishTranslations);
        this.translations.set('fr', frenchTranslations);
    }

    async setLocale(locale: string): Promise<void> {
        try {
            // Validate locale
            const supportedLocale = this.getSupportedLocale(locale);

            this.currentLocale = supportedLocale;

            // Save preference
            await AsyncStorage.setItem('user_locale', supportedLocale);

            // Notify listeners
            this.notifyListeners();
        } catch (error) {
            console.error('Failed to set locale:', error);
        }
    }

    private getSupportedLocale(locale: string): string {
        const supported = SUPPORTED_LOCALES.find(l => l.code === locale);
        return supported ? locale : this.fallbackLocale;
    }

    getCurrentLocale(): string {
        return this.currentLocale;
    }

    getSupportedLocales(): LocaleInfo[] {
        return [...SUPPORTED_LOCALES];
    }

    getLocaleInfo(locale?: string): LocaleInfo | undefined {
        const targetLocale = locale || this.currentLocale;
        return SUPPORTED_LOCALES.find(l => l.code === targetLocale);
    }

    isRTL(locale?: string): boolean {
        const localeInfo = this.getLocaleInfo(locale);
        return localeInfo?.rtl || false;
    }

    translate(key: keyof TranslationKeys, params?: Record<string, any>): string {
        // Get translation from current locale
        const currentTranslations = this.translations.get(this.currentLocale);
        let translation = currentTranslations?.[key];

        // Fallback to default locale if not found
        if (!translation) {
            const fallbackTranslations = this.translations.get(this.fallbackLocale);
            translation = fallbackTranslations?.[key];
        }

        // Fallback to key if no translation found
        if (!translation) {
            console.warn(`Missing translation for key: ${key}`);
            return key;
        }

        // Replace parameters
        if (params) {
            return this.replaceParams(translation, params);
        }

        return translation;
    }

    private replaceParams(text: string, params: Record<string, any>): string {
        return text.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key]?.toString() || match;
        });
    }

    // Format numbers according to locale
    formatNumber(number: number, options?: Intl.NumberFormatOptions): string {
        try {
            const locale = this.getLocaleInfo()?.code || 'en';
            return new Intl.NumberFormat(locale, options).format(number);
        } catch (error) {
            return number.toString();
        }
    }

    // Format dates according to locale
    formatDate(date: Date, options?: Intl.DateTimeFormatOptions): string {
        try {
            const locale = this.getLocaleInfo()?.code || 'en';
            return new Intl.DateTimeFormat(locale, options).format(date);
        } catch (error) {
            return date.toLocaleDateString();
        }
    }

    // Format relative time (e.g., "2 hours ago")
    formatRelativeTime(date: Date): string {
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
        const diffWeeks = Math.floor(diffDays / 7);
        const diffMonths = Math.floor(diffDays / 30);
        const diffYears = Math.floor(diffDays / 365);

        if (diffMinutes < 1) {
            return this.translate('time.now');
        } else if (diffMinutes < 60) {
            return this.translate('time.minutesAgo', { count: diffMinutes });
        } else if (diffHours < 24) {
            return this.translate('time.hoursAgo', { count: diffHours });
        } else if (diffDays < 7) {
            return this.translate('time.daysAgo', { count: diffDays });
        } else if (diffWeeks < 4) {
            return this.translate('time.weeksAgo', { count: diffWeeks });
        } else if (diffMonths < 12) {
            return this.translate('time.monthsAgo', { count: diffMonths });
        } else {
            return this.translate('time.yearsAgo', { count: diffYears });
        }
    }

    // Format currency according to locale
    formatCurrency(amount: number, currency: string = 'USD'): string {
        try {
            const locale = this.getLocaleInfo()?.code || 'en';
            return new Intl.NumberFormat(locale, {
                style: 'currency',
                currency,
            }).format(amount);
        } catch (error) {
            return `${currency} ${amount}`;
        }
    }

    subscribeToChanges(callback: (locale: string) => void): () => void {
        this.listeners.push(callback);

        return () => {
            const index = this.listeners.indexOf(callback);
            if (index > -1) {
                this.listeners.splice(index, 1);
            }
        };
    }

    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.currentLocale));
    }
}

export const i18nService = new InternationalizationService();