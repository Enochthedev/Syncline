export interface WebTranslationKeys {
    // Navigation
    'nav.contacts': string;
    'nav.search': string;
    'nav.messages': string;
    'nav.settings': string;
    'nav.dashboard': string;

    // Search
    'search.placeholder': string;
    'search.noResults': string;
    'search.searching': string;
    'search.voiceSearch': string;
    'search.advancedSearch': string;
    'search.filters': string;
    'search.results': string;

    // Contacts
    'contacts.title': string;
    'contacts.searchPlaceholder': string;
    'contacts.noContacts': string;
    'contacts.lastInteraction': string;
    'contacts.platforms': string;
    'contacts.messageCount': string;
    'contacts.addContact': string;
    'contacts.editContact': string;
    'contacts.deleteContact': string;

    // Messages
    'messages.title': string;
    'messages.noMessages': string;
    'messages.compose': string;
    'messages.send': string;
    'messages.reply': string;
    'messages.forward': string;
    'messages.delete': string;

    // Accessibility
    'accessibility.skipToContent': string;
    'accessibility.skipToNavigation': string;
    'accessibility.skipToSearch': string;
    'accessibility.openMenu': string;
    'accessibility.closeMenu': string;
    'accessibility.loading': string;
    'accessibility.error': string;
    'accessibility.required': string;
    'accessibility.optional': string;

    // Keyboard shortcuts
    'shortcuts.title': string;
    'shortcuts.navigation': string;
    'shortcuts.search': string;
    'shortcuts.accessibility': string;
    'shortcuts.general': string;

    // Common
    'common.loading': string;
    'common.error': string;
    'common.success': string;
    'common.warning': string;
    'common.info': string;
    'common.retry': string;
    'common.cancel': string;
    'common.save': string;
    'common.delete': string;
    'common.edit': string;
    'common.add': string;
    'common.remove': string;
    'common.close': string;
    'common.open': string;
    'common.yes': string;
    'common.no': string;
    'common.ok': string;

    // Time and dates
    'time.now': string;
    'time.today': string;
    'time.yesterday': string;
    'time.tomorrow': string;
    'time.thisWeek': string;
    'time.lastWeek': string;
    'time.thisMonth': string;
    'time.lastMonth': string;
    'time.thisYear': string;
    'time.lastYear': string;

    // Settings
    'settings.title': string;
    'settings.general': string;
    'settings.accessibility': string;
    'settings.language': string;
    'settings.theme': string;
    'settings.notifications': string;
    'settings.privacy': string;
    'settings.account': string;
}

export interface LocaleConfig {
    code: string;
    name: string;
    nativeName: string;
    rtl: boolean;
    dateFormat: string;
    timeFormat: string;
    currency: string;
    numberFormat: {
        decimal: string;
        thousands: string;
    };
}

const SUPPORTED_LOCALES: LocaleConfig[] = [
    {
        code: 'en',
        name: 'English',
        nativeName: 'English',
        rtl: false,
        dateFormat: 'MM/dd/yyyy',
        timeFormat: 'h:mm a',
        currency: 'USD',
        numberFormat: { decimal: '.', thousands: ',' },
    },
    {
        code: 'es',
        name: 'Spanish',
        nativeName: 'Español',
        rtl: false,
        dateFormat: 'dd/MM/yyyy',
        timeFormat: 'HH:mm',
        currency: 'EUR',
        numberFormat: { decimal: ',', thousands: '.' },
    },
    {
        code: 'fr',
        name: 'French',
        nativeName: 'Français',
        rtl: false,
        dateFormat: 'dd/MM/yyyy',
        timeFormat: 'HH:mm',
        currency: 'EUR',
        numberFormat: { decimal: ',', thousands: ' ' },
    },
    {
        code: 'de',
        name: 'German',
        nativeName: 'Deutsch',
        rtl: false,
        dateFormat: 'dd.MM.yyyy',
        timeFormat: 'HH:mm',
        currency: 'EUR',
        numberFormat: { decimal: ',', thousands: '.' },
    },
    {
        code: 'ja',
        name: 'Japanese',
        nativeName: '日本語',
        rtl: false,
        dateFormat: 'yyyy/MM/dd',
        timeFormat: 'HH:mm',
        currency: 'JPY',
        numberFormat: { decimal: '.', thousands: ',' },
    },
    {
        code: 'zh',
        name: 'Chinese (Simplified)',
        nativeName: '简体中文',
        rtl: false,
        dateFormat: 'yyyy/MM/dd',
        timeFormat: 'HH:mm',
        currency: 'CNY',
        numberFormat: { decimal: '.', thousands: ',' },
    },
    {
        code: 'ar',
        name: 'Arabic',
        nativeName: 'العربية',
        rtl: true,
        dateFormat: 'dd/MM/yyyy',
        timeFormat: 'HH:mm',
        currency: 'USD',
        numberFormat: { decimal: '.', thousands: ',' },
    },
    {
        code: 'he',
        name: 'Hebrew',
        nativeName: 'עברית',
        rtl: true,
        dateFormat: 'dd/MM/yyyy',
        timeFormat: 'HH:mm',
        currency: 'ILS',
        numberFormat: { decimal: '.', thousands: ',' },
    },
];

// English translations (default)
const EN_TRANSLATIONS: WebTranslationKeys = {
    // Navigation
    'nav.contacts': 'Contacts',
    'nav.search': 'Search',
    'nav.messages': 'Messages',
    'nav.settings': 'Settings',
    'nav.dashboard': 'Dashboard',

    // Search
    'search.placeholder': 'Search contacts, messages, files...',
    'search.noResults': 'No results found',
    'search.searching': 'Searching...',
    'search.voiceSearch': 'Voice Search',
    'search.advancedSearch': 'Advanced Search',
    'search.filters': 'Filters',
    'search.results': 'Search Results',

    // Contacts
    'contacts.title': 'Contacts',
    'contacts.searchPlaceholder': 'Search contacts...',
    'contacts.noContacts': 'No contacts found',
    'contacts.lastInteraction': 'Last interaction',
    'contacts.platforms': 'Platforms',
    'contacts.messageCount': 'messages',
    'contacts.addContact': 'Add Contact',
    'contacts.editContact': 'Edit Contact',
    'contacts.deleteContact': 'Delete Contact',

    // Messages
    'messages.title': 'Messages',
    'messages.noMessages': 'No messages found',
    'messages.compose': 'Compose',
    'messages.send': 'Send',
    'messages.reply': 'Reply',
    'messages.forward': 'Forward',
    'messages.delete': 'Delete',

    // Accessibility
    'accessibility.skipToContent': 'Skip to main content',
    'accessibility.skipToNavigation': 'Skip to navigation',
    'accessibility.skipToSearch': 'Skip to search',
    'accessibility.openMenu': 'Open menu',
    'accessibility.closeMenu': 'Close menu',
    'accessibility.loading': 'Loading content',
    'accessibility.error': 'Error occurred',
    'accessibility.required': 'Required field',
    'accessibility.optional': 'Optional field',

    // Keyboard shortcuts
    'shortcuts.title': 'Keyboard Shortcuts',
    'shortcuts.navigation': 'Navigation',
    'shortcuts.search': 'Search',
    'shortcuts.accessibility': 'Accessibility',
    'shortcuts.general': 'General',

    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.warning': 'Warning',
    'common.info': 'Information',
    'common.retry': 'Retry',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.add': 'Add',
    'common.remove': 'Remove',
    'common.close': 'Close',
    'common.open': 'Open',
    'common.yes': 'Yes',
    'common.no': 'No',
    'common.ok': 'OK',

    // Time and dates
    'time.now': 'now',
    'time.today': 'today',
    'time.yesterday': 'yesterday',
    'time.tomorrow': 'tomorrow',
    'time.thisWeek': 'this week',
    'time.lastWeek': 'last week',
    'time.thisMonth': 'this month',
    'time.lastMonth': 'last month',
    'time.thisYear': 'this year',
    'time.lastYear': 'last year',

    // Settings
    'settings.title': 'Settings',
    'settings.general': 'General',
    'settings.accessibility': 'Accessibility',
    'settings.language': 'Language',
    'settings.theme': 'Theme',
    'settings.notifications': 'Notifications',
    'settings.privacy': 'Privacy',
    'settings.account': 'Account',
};

class WebInternationalizationService {
    private currentLocale: string = 'en';
    private translations: Map<string, Partial<WebTranslationKeys>> = new Map();
    private listeners: Array<(locale: string) => void> = [];
    private fallbackLocale: string = 'en';

    async initialize(): Promise<void> {
        try {
            // Detect browser locale
            const browserLocale = this.detectBrowserLocale();

            // Load saved locale preference
            const savedLocale = localStorage.getItem('user_locale');

            // Set initial locale
            const initialLocale = savedLocale || browserLocale || 'en';

            // Load default translations
            this.translations.set('en', EN_TRANSLATIONS);

            // Load additional translations
            await this.loadTranslations();

            // Set current locale
            await this.setLocale(initialLocale);

            // Set up document attributes
            this.updateDocumentAttributes();
        } catch (error) {
            console.error('Failed to initialize web i18n service:', error);
            this.currentLocale = 'en';
        }
    }

    private detectBrowserLocale(): string {
        // Get browser language preference
        const browserLang = navigator.language || (navigator as any).userLanguage;

        // Extract language code (e.g., 'en-US' -> 'en')
        const langCode = browserLang.split('-')[0].toLowerCase();

        // Check if we support this language
        const supported = SUPPORTED_LOCALES.find(locale => locale.code === langCode);
        return supported ? langCode : 'en';
    }

    private async loadTranslations(): Promise<void> {
        // In a real application, these would be loaded from separate files or API
        // For demonstration, adding a few key translations

        const spanishTranslations: Partial<WebTranslationKeys> = {
            'nav.contacts': 'Contactos',
            'nav.search': 'Buscar',
            'nav.messages': 'Mensajes',
            'nav.settings': 'Configuración',
            'nav.dashboard': 'Panel de Control',
            'search.placeholder': 'Buscar contactos, mensajes, archivos...',
            'search.noResults': 'No se encontraron resultados',
            'search.searching': 'Buscando...',
            'contacts.title': 'Contactos',
            'contacts.noContacts': 'No se encontraron contactos',
            'messages.title': 'Mensajes',
            'messages.noMessages': 'No se encontraron mensajes',
            'common.loading': 'Cargando...',
            'common.error': 'Error',
            'common.save': 'Guardar',
            'common.cancel': 'Cancelar',
            'common.delete': 'Eliminar',
            'settings.title': 'Configuración',
            'settings.language': 'Idioma',
            'settings.accessibility': 'Accesibilidad',
        };

        const frenchTranslations: Partial<WebTranslationKeys> = {
            'nav.contacts': 'Contacts',
            'nav.search': 'Rechercher',
            'nav.messages': 'Messages',
            'nav.settings': 'Paramètres',
            'nav.dashboard': 'Tableau de Bord',
            'search.placeholder': 'Rechercher contacts, messages, fichiers...',
            'search.noResults': 'Aucun résultat trouvé',
            'search.searching': 'Recherche en cours...',
            'contacts.title': 'Contacts',
            'contacts.noContacts': 'Aucun contact trouvé',
            'messages.title': 'Messages',
            'messages.noMessages': 'Aucun message trouvé',
            'common.loading': 'Chargement...',
            'common.error': 'Erreur',
            'common.save': 'Enregistrer',
            'common.cancel': 'Annuler',
            'common.delete': 'Supprimer',
            'settings.title': 'Paramètres',
            'settings.language': 'Langue',
            'settings.accessibility': 'Accessibilité',
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
            localStorage.setItem('user_locale', supportedLocale);

            // Update document attributes
            this.updateDocumentAttributes();

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

    private updateDocumentAttributes(): void {
        const localeConfig = this.getLocaleConfig();

        if (localeConfig) {
            document.documentElement.lang = localeConfig.code;
            document.documentElement.dir = localeConfig.rtl ? 'rtl' : 'ltr';

            // Update CSS custom properties for RTL support
            document.documentElement.style.setProperty(
                '--text-direction',
                localeConfig.rtl ? 'rtl' : 'ltr'
            );
            document.documentElement.style.setProperty(
                '--start-direction',
                localeConfig.rtl ? 'right' : 'left'
            );
            document.documentElement.style.setProperty(
                '--end-direction',
                localeConfig.rtl ? 'left' : 'right'
            );
        }
    }

    getCurrentLocale(): string {
        return this.currentLocale;
    }

    getSupportedLocales(): LocaleConfig[] {
        return [...SUPPORTED_LOCALES];
    }

    getLocaleConfig(locale?: string): LocaleConfig | undefined {
        const targetLocale = locale || this.currentLocale;
        return SUPPORTED_LOCALES.find(l => l.code === targetLocale);
    }

    isRTL(locale?: string): boolean {
        const config = this.getLocaleConfig(locale);
        return config?.rtl || false;
    }

    translate(key: keyof WebTranslationKeys, params?: Record<string, any>): string {
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

    // Enhanced formatting methods for web
    formatNumber(
        number: number,
        options?: Intl.NumberFormatOptions & { useLocaleFormat?: boolean }
    ): string {
        try {
            const config = this.getLocaleConfig();
            const locale = config?.code || 'en';

            if (options?.useLocaleFormat && config) {
                // Use custom locale formatting
                const formatted = new Intl.NumberFormat(locale, options).format(number);
                return formatted
                    .replace(/\./g, '|||DECIMAL|||')
                    .replace(/,/g, config.numberFormat.thousands)
                    .replace(/\|\|\|DECIMAL\|\|\|/g, config.numberFormat.decimal);
            }

            return new Intl.NumberFormat(locale, options).format(number);
        } catch (error) {
            return number.toString();
        }
    }

    formatDate(
        date: Date,
        options?: Intl.DateTimeFormatOptions & { useLocaleFormat?: boolean }
    ): string {
        try {
            const config = this.getLocaleConfig();
            const locale = config?.code || 'en';

            if (options?.useLocaleFormat && config) {
                // Use custom date format
                const day = date.getDate().toString().padStart(2, '0');
                const month = (date.getMonth() + 1).toString().padStart(2, '0');
                const year = date.getFullYear().toString();

                return config.dateFormat
                    .replace('dd', day)
                    .replace('MM', month)
                    .replace('yyyy', year);
            }

            return new Intl.DateTimeFormat(locale, options).format(date);
        } catch (error) {
            return date.toLocaleDateString();
        }
    }

    formatTime(
        date: Date,
        options?: Intl.DateTimeFormatOptions & { useLocaleFormat?: boolean }
    ): string {
        try {
            const config = this.getLocaleConfig();
            const locale = config?.code || 'en';

            if (options?.useLocaleFormat && config) {
                // Use custom time format
                const hours = date.getHours();
                const minutes = date.getMinutes().toString().padStart(2, '0');

                if (config.timeFormat.includes('a')) {
                    // 12-hour format
                    const displayHours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
                    const ampm = hours >= 12 ? 'PM' : 'AM';
                    return `${displayHours}:${minutes} ${ampm}`;
                } else {
                    // 24-hour format
                    return `${hours.toString().padStart(2, '0')}:${minutes}`;
                }
            }

            return new Intl.DateTimeFormat(locale, {
                hour: 'numeric',
                minute: '2-digit',
                ...options,
            }).format(date);
        } catch (error) {
            return date.toLocaleTimeString();
        }
    }

    formatRelativeTime(date: Date): string {
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMinutes < 1) {
            return this.translate('time.now');
        } else if (diffDays === 0) {
            return this.formatTime(date);
        } else if (diffDays === 1) {
            return this.translate('time.yesterday');
        } else if (diffDays < 7) {
            return this.formatDate(date, { weekday: 'long' });
        } else {
            return this.formatDate(date, {
                month: 'short',
                day: 'numeric',
                year: diffDays > 365 ? 'numeric' : undefined,
            });
        }
    }

    formatCurrency(amount: number, currency?: string): string {
        try {
            const config = this.getLocaleConfig();
            const locale = config?.code || 'en';
            const currencyCode = currency || config?.currency || 'USD';

            return new Intl.NumberFormat(locale, {
                style: 'currency',
                currency: currencyCode,
            }).format(amount);
        } catch (error) {
            return `${currency || '$'} ${amount}`;
        }
    }

    // Pluralization support
    pluralize(
        count: number,
        singular: keyof WebTranslationKeys,
        plural?: keyof WebTranslationKeys,
        zero?: keyof WebTranslationKeys
    ): string {
        if (count === 0 && zero) {
            return this.translate(zero);
        } else if (count === 1) {
            return this.translate(singular);
        } else if (plural) {
            return this.translate(plural);
        } else {
            // Simple English pluralization
            return this.translate(singular) + 's';
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

    // Utility methods for web-specific features
    getTextDirection(): 'ltr' | 'rtl' {
        return this.isRTL() ? 'rtl' : 'ltr';
    }

    getStartDirection(): 'left' | 'right' {
        return this.isRTL() ? 'right' : 'left';
    }

    getEndDirection(): 'left' | 'right' {
        return this.isRTL() ? 'left' : 'right';
    }

    // Load translations dynamically (for code splitting)
    async loadLocaleTranslations(locale: string): Promise<void> {
        try {
            // In a real app, this would load from separate files
            // const translations = await import(`./translations/${locale}.json`);
            // this.translations.set(locale, translations.default);
            console.log(`Loading translations for ${locale}`);
        } catch (error) {
            console.error(`Failed to load translations for ${locale}:`, error);
        }
    }
}

export const webI18nService = new WebInternationalizationService();