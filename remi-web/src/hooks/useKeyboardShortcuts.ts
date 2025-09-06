import { useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

export interface KeyboardShortcut {
    id: string;
    key: string;
    ctrlKey?: boolean;
    altKey?: boolean;
    shiftKey?: boolean;
    metaKey?: boolean;
    description: string;
    category: string;
    action: () => void;
    disabled?: boolean;
    global?: boolean; // Can be triggered from anywhere
}

export interface ShortcutCategory {
    id: string;
    name: string;
    shortcuts: KeyboardShortcut[];
}

const DEFAULT_SHORTCUTS: KeyboardShortcut[] = [
    // Navigation shortcuts
    {
        id: 'nav-home',
        key: 'h',
        ctrlKey: true,
        description: 'Go to Home',
        category: 'Navigation',
        action: () => { },
        global: true,
    },
    {
        id: 'nav-search',
        key: 'k',
        ctrlKey: true,
        description: 'Open Search',
        category: 'Navigation',
        action: () => { },
        global: true,
    },
    {
        id: 'nav-contacts',
        key: 'c',
        ctrlKey: true,
        shiftKey: true,
        description: 'Go to Contacts',
        category: 'Navigation',
        action: () => { },
        global: true,
    },
    {
        id: 'nav-messages',
        key: 'm',
        ctrlKey: true,
        shiftKey: true,
        description: 'Go to Messages',
        category: 'Navigation',
        action: () => { },
        global: true,
    },
    {
        id: 'nav-analytics',
        key: 'a',
        ctrlKey: true,
        shiftKey: true,
        description: 'Go to Analytics',
        category: 'Navigation',
        action: () => { },
        global: true,
    },
    {
        id: 'nav-settings',
        key: ',',
        ctrlKey: true,
        description: 'Open Settings',
        category: 'Navigation',
        action: () => { },
        global: true,
    },

    // Search shortcuts
    {
        id: 'search-focus',
        key: '/',
        description: 'Focus Search Input',
        category: 'Search',
        action: () => { },
        global: true,
    },
    {
        id: 'search-clear',
        key: 'Escape',
        description: 'Clear Search',
        category: 'Search',
        action: () => { },
    },
    {
        id: 'search-next',
        key: 'n',
        ctrlKey: true,
        description: 'Next Search Result',
        category: 'Search',
        action: () => { },
    },
    {
        id: 'search-prev',
        key: 'p',
        ctrlKey: true,
        description: 'Previous Search Result',
        category: 'Search',
        action: () => { },
    },

    // Contact shortcuts
    {
        id: 'contact-new',
        key: 'n',
        ctrlKey: true,
        altKey: true,
        description: 'New Contact',
        category: 'Contacts',
        action: () => { },
    },
    {
        id: 'contact-edit',
        key: 'e',
        description: 'Edit Contact',
        category: 'Contacts',
        action: () => { },
    },
    {
        id: 'contact-delete',
        key: 'Delete',
        description: 'Delete Contact',
        category: 'Contacts',
        action: () => { },
    },

    // Message shortcuts
    {
        id: 'message-reply',
        key: 'r',
        description: 'Reply to Message',
        category: 'Messages',
        action: () => { },
    },
    {
        id: 'message-forward',
        key: 'f',
        description: 'Forward Message',
        category: 'Messages',
        action: () => { },
    },
    {
        id: 'message-archive',
        key: 'a',
        description: 'Archive Message',
        category: 'Messages',
        action: () => { },
    },

    // Application shortcuts
    {
        id: 'app-help',
        key: '?',
        description: 'Show Help',
        category: 'Application',
        action: () => { },
        global: true,
    },
    {
        id: 'app-refresh',
        key: 'r',
        ctrlKey: true,
        description: 'Refresh Page',
        category: 'Application',
        action: () => { },
        global: true,
    },
    {
        id: 'app-fullscreen',
        key: 'F11',
        description: 'Toggle Fullscreen',
        category: 'Application',
        action: () => { },
        global: true,
    },

    // Accessibility shortcuts
    {
        id: 'a11y-skip-nav',
        key: 'Tab',
        description: 'Skip to Main Content',
        category: 'Accessibility',
        action: () => { },
        global: true,
    },
    {
        id: 'a11y-focus-search',
        key: 's',
        altKey: true,
        description: 'Focus Search (Screen Reader)',
        category: 'Accessibility',
        action: () => { },
        global: true,
    },
];

class KeyboardShortcutManager {
    private shortcuts: Map<string, KeyboardShortcut> = new Map();
    private listeners: Set<(event: KeyboardEvent) => void> = new Set();
    private customBindings: Map<string, string> = new Map();

    constructor() {
        this.loadCustomBindings();
        this.initializeDefaults();
    }

    private loadCustomBindings(): void {
        try {
            const saved = localStorage.getItem('keyboard-shortcuts');
            if (saved) {
                const bindings = JSON.parse(saved);
                this.customBindings = new Map(Object.entries(bindings));
            }
        } catch (error) {
            console.error('Failed to load custom keyboard shortcuts:', error);
        }
    }

    private saveCustomBindings(): void {
        try {
            const bindings = Object.fromEntries(this.customBindings);
            localStorage.setItem('keyboard-shortcuts', JSON.stringify(bindings));
        } catch (error) {
            console.error('Failed to save custom keyboard shortcuts:', error);
        }
    }

    private initializeDefaults(): void {
        DEFAULT_SHORTCUTS.forEach(shortcut => {
            this.shortcuts.set(shortcut.id, { ...shortcut });
        });
    }

    register(shortcut: KeyboardShortcut): void {
        this.shortcuts.set(shortcut.id, shortcut);
    }

    unregister(id: string): void {
        this.shortcuts.delete(id);
    }

    updateShortcut(id: string, updates: Partial<KeyboardShortcut>): void {
        const existing = this.shortcuts.get(id);
        if (existing) {
            this.shortcuts.set(id, { ...existing, ...updates });
        }
    }

    setCustomBinding(shortcutId: string, keyBinding: string): void {
        this.customBindings.set(shortcutId, keyBinding);
        this.saveCustomBindings();

        // Update the shortcut with new binding
        const shortcut = this.shortcuts.get(shortcutId);
        if (shortcut) {
            const binding = this.parseKeyBinding(keyBinding);
            this.shortcuts.set(shortcutId, { ...shortcut, ...binding });
        }
    }

    private parseKeyBinding(binding: string): Partial<KeyboardShortcut> {
        const parts = binding.toLowerCase().split('+');
        const result: Partial<KeyboardShortcut> = {
            ctrlKey: false,
            altKey: false,
            shiftKey: false,
            metaKey: false,
        };

        parts.forEach(part => {
            switch (part) {
                case 'ctrl':
                case 'control':
                    result.ctrlKey = true;
                    break;
                case 'alt':
                    result.altKey = true;
                    break;
                case 'shift':
                    result.shiftKey = true;
                    break;
                case 'meta':
                case 'cmd':
                    result.metaKey = true;
                    break;
                default:
                    result.key = part;
            }
        });

        return result;
    }

    private matchesShortcut(event: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
        return (
            event.key.toLowerCase() === shortcut.key.toLowerCase() &&
            !!event.ctrlKey === !!shortcut.ctrlKey &&
            !!event.altKey === !!shortcut.altKey &&
            !!event.shiftKey === !!shortcut.shiftKey &&
            !!event.metaKey === !!shortcut.metaKey
        );
    }

    handleKeyDown = (event: KeyboardEvent): void => {
        // Don't trigger shortcuts when typing in inputs
        const target = event.target as HTMLElement;
        if (
            target.tagName === 'INPUT' ||
            target.tagName === 'TEXTAREA' ||
            target.contentEditable === 'true'
        ) {
            // Only allow global shortcuts in input fields
            const globalShortcuts = Array.from(this.shortcuts.values()).filter(s => s.global);
            for (const shortcut of globalShortcuts) {
                if (!shortcut.disabled && this.matchesShortcut(event, shortcut)) {
                    event.preventDefault();
                    shortcut.action();
                    return;
                }
            }
            return;
        }

        // Check all shortcuts
        for (const shortcut of this.shortcuts.values()) {
            if (!shortcut.disabled && this.matchesShortcut(event, shortcut)) {
                event.preventDefault();
                shortcut.action();
                return;
            }
        }
    };

    getShortcuts(): KeyboardShortcut[] {
        return Array.from(this.shortcuts.values());
    }

    getShortcutsByCategory(): ShortcutCategory[] {
        const categories = new Map<string, KeyboardShortcut[]>();

        this.shortcuts.forEach(shortcut => {
            if (!categories.has(shortcut.category)) {
                categories.set(shortcut.category, []);
            }
            categories.get(shortcut.category)!.push(shortcut);
        });

        return Array.from(categories.entries()).map(([name, shortcuts]) => ({
            id: name.toLowerCase().replace(/\s+/g, '-'),
            name,
            shortcuts: shortcuts.sort((a, b) => a.description.localeCompare(b.description)),
        }));
    }

    formatShortcut(shortcut: KeyboardShortcut): string {
        const parts: string[] = [];

        if (shortcut.ctrlKey) parts.push('Ctrl');
        if (shortcut.altKey) parts.push('Alt');
        if (shortcut.shiftKey) parts.push('Shift');
        if (shortcut.metaKey) parts.push('Cmd');

        parts.push(shortcut.key.toUpperCase());

        return parts.join(' + ');
    }

    resetToDefaults(): void {
        this.customBindings.clear();
        this.saveCustomBindings();
        this.shortcuts.clear();
        this.initializeDefaults();
    }
}

const shortcutManager = new KeyboardShortcutManager();

export function useKeyboardShortcuts(shortcuts?: KeyboardShortcut[]) {
    const router = useRouter();
    const shortcutsRef = useRef<KeyboardShortcut[]>([]);

    // Register navigation shortcuts
    useEffect(() => {
        const navigationShortcuts: KeyboardShortcut[] = [
            {
                id: 'nav-home',
                key: 'h',
                ctrlKey: true,
                description: 'Go to Home',
                category: 'Navigation',
                action: () => router.push('/'),
                global: true,
            },
            {
                id: 'nav-search',
                key: 'k',
                ctrlKey: true,
                description: 'Open Search',
                category: 'Navigation',
                action: () => {
                    const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement;
                    if (searchInput) {
                        searchInput.focus();
                    } else {
                        router.push('/search');
                    }
                },
                global: true,
            },
            {
                id: 'nav-contacts',
                key: 'c',
                ctrlKey: true,
                shiftKey: true,
                description: 'Go to Contacts',
                category: 'Navigation',
                action: () => router.push('/contacts'),
                global: true,
            },
            {
                id: 'nav-messages',
                key: 'm',
                ctrlKey: true,
                shiftKey: true,
                description: 'Go to Messages',
                category: 'Navigation',
                action: () => router.push('/messages'),
                global: true,
            },
            {
                id: 'nav-analytics',
                key: 'a',
                ctrlKey: true,
                shiftKey: true,
                description: 'Go to Analytics',
                category: 'Navigation',
                action: () => router.push('/analytics'),
                global: true,
            },
        ];

        navigationShortcuts.forEach(shortcut => {
            shortcutManager.register(shortcut);
        });

        return () => {
            navigationShortcuts.forEach(shortcut => {
                shortcutManager.unregister(shortcut.id);
            });
        };
    }, [router]);

    // Register custom shortcuts
    useEffect(() => {
        if (shortcuts) {
            shortcuts.forEach(shortcut => {
                shortcutManager.register(shortcut);
            });
            shortcutsRef.current = shortcuts;
        }

        return () => {
            shortcutsRef.current.forEach(shortcut => {
                shortcutManager.unregister(shortcut.id);
            });
        };
    }, [shortcuts]);

    // Add event listener
    useEffect(() => {
        document.addEventListener('keydown', shortcutManager.handleKeyDown);

        return () => {
            document.removeEventListener('keydown', shortcutManager.handleKeyDown);
        };
    }, []);

    const registerShortcut = useCallback((shortcut: KeyboardShortcut) => {
        shortcutManager.register(shortcut);
    }, []);

    const unregisterShortcut = useCallback((id: string) => {
        shortcutManager.unregister(id);
    }, []);

    const getShortcuts = useCallback(() => {
        return shortcutManager.getShortcuts();
    }, []);

    const getShortcutsByCategory = useCallback(() => {
        return shortcutManager.getShortcutsByCategory();
    }, []);

    return {
        registerShortcut,
        unregisterShortcut,
        getShortcuts,
        getShortcutsByCategory,
        shortcutManager,
    };
}

export { shortcutManager };