export interface WebAccessibilitySettings {
    screenReaderEnabled: boolean;
    reduceMotion: boolean;
    highContrast: boolean;
    textScaling: number;
    keyboardNavigation: boolean;
    focusVisible: boolean;
    announcements: boolean;
}

export interface KeyboardShortcut {
    key: string;
    ctrlKey?: boolean;
    metaKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
    action: string;
    description: string;
}

class WebAccessibilityService {
    private settings: WebAccessibilitySettings = {
        screenReaderEnabled: false,
        reduceMotion: false,
        highContrast: false,
        textScaling: 1.0,
        keyboardNavigation: true,
        focusVisible: true,
        announcements: true,
    };

    private listeners: Array<(settings: WebAccessibilitySettings) => void> = [];
    private keyboardShortcuts: Map<string, KeyboardShortcut> = new Map();
    private announcer: HTMLElement | null = null;

    async initialize(): Promise<void> {
        try {
            // Load saved settings
            await this.loadSettings();

            // Check system preferences
            this.checkSystemPreferences();

            // Set up accessibility features
            this.setupAccessibilityFeatures();

            // Register default keyboard shortcuts
            this.registerDefaultShortcuts();

            // Set up event listeners
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize web accessibility service:', error);
        }
    }

    private checkSystemPreferences(): void {
        // Check for reduced motion preference
        if (window.matchMedia) {
            const reduceMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
            this.settings.reduceMotion = reduceMotionQuery.matches;

            reduceMotionQuery.addEventListener('change', (e) => {
                this.settings.reduceMotion = e.matches;
                this.notifyListeners();
            });

            // Check for high contrast preference
            const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
            this.settings.highContrast = highContrastQuery.matches;

            highContrastQuery.addEventListener('change', (e) => {
                this.settings.highContrast = e.matches;
                this.notifyListeners();
            });

            // Check for color scheme preference
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', () => {
                this.notifyListeners();
            });
        }

        // Detect screen reader usage
        this.detectScreenReader();
    }

    private detectScreenReader(): void {
        // Check for common screen reader indicators
        const hasScreenReader =
            navigator.userAgent.includes('NVDA') ||
            navigator.userAgent.includes('JAWS') ||
            navigator.userAgent.includes('VoiceOver') ||
            window.speechSynthesis !== undefined;

        this.settings.screenReaderEnabled = hasScreenReader;
    }

    private setupAccessibilityFeatures(): void {
        // Create live region for announcements
        this.createAnnouncementRegion();

        // Set up focus management
        this.setupFocusManagement();

        // Apply accessibility styles
        this.applyAccessibilityStyles();
    }

    private createAnnouncementRegion(): void {
        this.announcer = document.createElement('div');
        this.announcer.setAttribute('aria-live', 'polite');
        this.announcer.setAttribute('aria-atomic', 'true');
        this.announcer.setAttribute('aria-relevant', 'text');
        this.announcer.style.position = 'absolute';
        this.announcer.style.left = '-10000px';
        this.announcer.style.width = '1px';
        this.announcer.style.height = '1px';
        this.announcer.style.overflow = 'hidden';
        document.body.appendChild(this.announcer);
    }

    private setupFocusManagement(): void {
        // Add focus-visible polyfill behavior
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Skip links for keyboard navigation
        this.createSkipLinks();
    }

    private createSkipLinks(): void {
        const skipLinks = document.createElement('div');
        skipLinks.className = 'skip-links';
        skipLinks.innerHTML = `
      <a href="#main-content" class="skip-link">Skip to main content</a>
      <a href="#navigation" class="skip-link">Skip to navigation</a>
      <a href="#search" class="skip-link">Skip to search</a>
    `;
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    private applyAccessibilityStyles(): void {
        const style = document.createElement('style');
        style.textContent = `
      .skip-links {
        position: absolute;
        top: -40px;
        left: 6px;
        z-index: 1000;
      }
      
      .skip-link {
        position: absolute;
        top: -40px;
        left: 6px;
        background: #000;
        color: #fff;
        padding: 8px;
        text-decoration: none;
        border-radius: 4px;
        z-index: 1001;
      }
      
      .skip-link:focus {
        top: 6px;
      }
      
      .keyboard-navigation *:focus {
        outline: 2px solid #2196F3 !important;
        outline-offset: 2px !important;
      }
      
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }
      }
      
      @media (prefers-contrast: high) {
        * {
          border-color: #000 !important;
        }
      }
    `;
        document.head.appendChild(style);
    }

    private registerDefaultShortcuts(): void {
        // Navigation shortcuts
        this.registerShortcut({
            key: 'h',
            altKey: true,
            action: 'navigate-home',
            description: 'Navigate to home page',
        });

        this.registerShortcut({
            key: 's',
            ctrlKey: true,
            action: 'focus-search',
            description: 'Focus search input',
        });

        this.registerShortcut({
            key: 'k',
            ctrlKey: true,
            action: 'open-command-palette',
            description: 'Open command palette',
        });

        // Accessibility shortcuts
        this.registerShortcut({
            key: '=',
            ctrlKey: true,
            action: 'increase-text-size',
            description: 'Increase text size',
        });

        this.registerShortcut({
            key: '-',
            ctrlKey: true,
            action: 'decrease-text-size',
            description: 'Decrease text size',
        });

        this.registerShortcut({
            key: '0',
            ctrlKey: true,
            action: 'reset-text-size',
            description: 'Reset text size',
        });

        // Screen reader shortcuts
        this.registerShortcut({
            key: 'r',
            altKey: true,
            action: 'read-page',
            description: 'Read current page',
        });
    }

    private setupEventListeners(): void {
        // Keyboard shortcut handler
        document.addEventListener('keydown', (e) => {
            const shortcutKey = this.getShortcutKey(e);
            const shortcut = this.keyboardShortcuts.get(shortcutKey);

            if (shortcut) {
                e.preventDefault();
                this.executeShortcut(shortcut);
            }
        });

        // Focus trap for modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.handleEscapeKey();
            }
        });
    }

    private getShortcutKey(e: KeyboardEvent): string {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.metaKey) parts.push('meta');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }

    private executeShortcut(shortcut: KeyboardShortcut): void {
        switch (shortcut.action) {
            case 'focus-search':
                this.focusSearchInput();
                break;
            case 'increase-text-size':
                this.adjustTextSize(0.1);
                break;
            case 'decrease-text-size':
                this.adjustTextSize(-0.1);
                break;
            case 'reset-text-size':
                this.resetTextSize();
                break;
            case 'read-page':
                this.readCurrentPage();
                break;
            default:
                // Emit custom event for application-specific shortcuts
                window.dispatchEvent(new CustomEvent('accessibility-shortcut', {
                    detail: shortcut,
                }));
        }
    }

    private focusSearchInput(): void {
        const searchInput = document.querySelector('[role="search"] input, input[type="search"]') as HTMLElement;
        if (searchInput) {
            searchInput.focus();
            this.announce('Search input focused');
        }
    }

    private adjustTextSize(delta: number): void {
        this.settings.textScaling = Math.max(0.5, Math.min(3.0, this.settings.textScaling + delta));
        this.applyTextScaling();
        this.announce(`Text size ${delta > 0 ? 'increased' : 'decreased'} to ${Math.round(this.settings.textScaling * 100)}%`);
    }

    private resetTextSize(): void {
        this.settings.textScaling = 1.0;
        this.applyTextScaling();
        this.announce('Text size reset to 100%');
    }

    private applyTextScaling(): void {
        document.documentElement.style.fontSize = `${this.settings.textScaling * 16}px`;
        this.notifyListeners();
    }

    private readCurrentPage(): void {
        if ('speechSynthesis' in window) {
            const text = document.body.innerText;
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.8;
            utterance.pitch = 1.0;
            speechSynthesis.speak(utterance);
        }
    }

    private handleEscapeKey(): void {
        // Close modals, dropdowns, etc.
        const modal = document.querySelector('[role="dialog"][aria-modal="true"]') as HTMLElement;
        if (modal) {
            const closeButton = modal.querySelector('[aria-label*="close"], [aria-label*="Close"]') as HTMLElement;
            if (closeButton) {
                closeButton.click();
            }
        }
    }

    registerShortcut(shortcut: KeyboardShortcut): void {
        const key = this.getShortcutKeyFromShortcut(shortcut);
        this.keyboardShortcuts.set(key, shortcut);
    }

    private getShortcutKeyFromShortcut(shortcut: KeyboardShortcut): string {
        const parts = [];
        if (shortcut.ctrlKey) parts.push('ctrl');
        if (shortcut.metaKey) parts.push('meta');
        if (shortcut.altKey) parts.push('alt');
        if (shortcut.shiftKey) parts.push('shift');
        parts.push(shortcut.key.toLowerCase());
        return parts.join('+');
    }

    announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
        if (!this.settings.announcements || !this.announcer) return;

        this.announcer.setAttribute('aria-live', priority);
        this.announcer.textContent = message;

        // Clear after announcement
        setTimeout(() => {
            if (this.announcer) {
                this.announcer.textContent = '';
            }
        }, 1000);
    }

    getSettings(): WebAccessibilitySettings {
        return { ...this.settings };
    }

    async updateSettings(updates: Partial<WebAccessibilitySettings>): Promise<void> {
        this.settings = { ...this.settings, ...updates };

        if (updates.textScaling !== undefined) {
            this.applyTextScaling();
        }

        await this.saveSettings();
        this.notifyListeners();
    }

    subscribeToChanges(callback: (settings: WebAccessibilitySettings) => void): () => void {
        this.listeners.push(callback);

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

    private async loadSettings(): Promise<void> {
        try {
            const saved = localStorage.getItem('web_accessibility_settings');
            if (saved) {
                this.settings = { ...this.settings, ...JSON.parse(saved) };
            }
        } catch (error) {
            console.error('Failed to load accessibility settings:', error);
        }
    }

    private async saveSettings(): Promise<void> {
        try {
            localStorage.setItem('web_accessibility_settings', JSON.stringify(this.settings));
        } catch (error) {
            console.error('Failed to save accessibility settings:', error);
        }
    }

    getKeyboardShortcuts(): KeyboardShortcut[] {
        return Array.from(this.keyboardShortcuts.values());
    }

    // Focus management utilities
    trapFocus(container: HTMLElement): () => void {
        const focusableElements = container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        const handleTabKey = (e: KeyboardEvent) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
            }
        };

        container.addEventListener('keydown', handleTabKey);

        // Focus first element
        if (firstElement) {
            firstElement.focus();
        }

        // Return cleanup function
        return () => {
            container.removeEventListener('keydown', handleTabKey);
        };
    }

    // ARIA live region management
    createLiveRegion(id: string, level: 'polite' | 'assertive' = 'polite'): HTMLElement {
        let region = document.getElementById(id);

        if (!region) {
            region = document.createElement('div');
            region.id = id;
            region.setAttribute('aria-live', level);
            region.setAttribute('aria-atomic', 'true');
            region.style.position = 'absolute';
            region.style.left = '-10000px';
            region.style.width = '1px';
            region.style.height = '1px';
            region.style.overflow = 'hidden';
            document.body.appendChild(region);
        }

        return region;
    }

    announceToRegion(regionId: string, message: string): void {
        const region = document.getElementById(regionId);
        if (region) {
            region.textContent = message;
            setTimeout(() => {
                region.textContent = '';
            }, 1000);
        }
    }
}

export const webAccessibilityService = new WebAccessibilityService();