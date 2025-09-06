import { webAccessibilityService } from '../../src/services/accessibilityService';

// Mock localStorage
const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
});

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
});

// Mock speechSynthesis
Object.defineProperty(window, 'speechSynthesis', {
    writable: true,
    value: {
        speak: jest.fn(),
        cancel: jest.fn(),
        pause: jest.fn(),
        resume: jest.fn(),
        getVoices: jest.fn(() => []),
    },
});

describe('WebAccessibilityService', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = '';
        document.head.innerHTML = '';
    });

    describe('initialization', () => {
        it('should initialize with default settings', async () => {
            await webAccessibilityService.initialize();

            const settings = webAccessibilityService.getSettings();
            expect(settings.screenReaderEnabled).toBeDefined();
            expect(settings.keyboardNavigation).toBe(true);
            expect(settings.focusVisible).toBe(true);
        });

        it('should create announcement region', async () => {
            await webAccessibilityService.initialize();

            const announcer = document.querySelector('[aria-live="polite"]');
            expect(announcer).toBeTruthy();
            expect(announcer?.getAttribute('aria-atomic')).toBe('true');
        });

        it('should create skip links', async () => {
            await webAccessibilityService.initialize();

            const skipLinks = document.querySelector('.skip-links');
            expect(skipLinks).toBeTruthy();

            const mainContentLink = document.querySelector('a[href="#main-content"]');
            expect(mainContentLink).toBeTruthy();
        });

        it('should apply accessibility styles', async () => {
            await webAccessibilityService.initialize();

            const styles = document.querySelector('style');
            expect(styles).toBeTruthy();
            expect(styles?.textContent).toContain('.skip-link');
            expect(styles?.textContent).toContain('prefers-reduced-motion');
        });
    });

    describe('settings management', () => {
        it('should update settings and notify listeners', async () => {
            await webAccessibilityService.initialize();

            const mockListener = jest.fn();
            const unsubscribe = webAccessibilityService.subscribeToChanges(mockListener);

            await webAccessibilityService.updateSettings({
                textScaling: 1.5,
                highContrast: true,
            });

            expect(mockListener).toHaveBeenCalledWith(
                expect.objectContaining({
                    textScaling: 1.5,
                    highContrast: true,
                })
            );

            unsubscribe();
        });

        it('should save settings to localStorage', async () => {
            await webAccessibilityService.initialize();

            await webAccessibilityService.updateSettings({
                textScaling: 2.0,
            });

            expect(localStorageMock.setItem).toHaveBeenCalledWith(
                'web_accessibility_settings',
                expect.stringContaining('"textScaling":2')
            );
        });

        it('should load settings from localStorage', async () => {
            localStorageMock.getItem.mockReturnValue(
                JSON.stringify({ textScaling: 1.8, highContrast: true })
            );

            await webAccessibilityService.initialize();

            const settings = webAccessibilityService.getSettings();
            expect(settings.textScaling).toBe(1.8);
            expect(settings.highContrast).toBe(true);
        });
    });

    describe('announcements', () => {
        it('should announce messages to screen readers', async () => {
            await webAccessibilityService.initialize();

            webAccessibilityService.announce('Test announcement');

            const announcer = document.querySelector('[aria-live="polite"]');
            expect(announcer?.textContent).toBe('Test announcement');
        });

        it('should support different announcement priorities', async () => {
            await webAccessibilityService.initialize();

            webAccessibilityService.announce('Urgent message', 'assertive');

            const announcer = document.querySelector('[aria-live]');
            expect(announcer?.getAttribute('aria-live')).toBe('assertive');
        });

        it('should clear announcements after timeout', (done) => {
            webAccessibilityService.initialize().then(() => {
                webAccessibilityService.announce('Temporary message');

                const announcer = document.querySelector('[aria-live]');
                expect(announcer?.textContent).toBe('Temporary message');

                setTimeout(() => {
                    expect(announcer?.textContent).toBe('');
                    done();
                }, 1100);
            });
        });
    });

    describe('keyboard shortcuts', () => {
        it('should register and execute keyboard shortcuts', async () => {
            await webAccessibilityService.initialize();

            const mockAction = jest.fn();
            window.addEventListener('accessibility-shortcut', mockAction);

            webAccessibilityService.registerShortcut({
                key: 't',
                ctrlKey: true,
                action: 'test-action',
                description: 'Test shortcut',
            });

            // Simulate Ctrl+T
            const event = new KeyboardEvent('keydown', {
                key: 't',
                ctrlKey: true,
            });
            document.dispatchEvent(event);

            expect(mockAction).toHaveBeenCalled();
        });

        it('should handle text size adjustment shortcuts', async () => {
            await webAccessibilityService.initialize();

            // Simulate Ctrl+=
            const increaseEvent = new KeyboardEvent('keydown', {
                key: '=',
                ctrlKey: true,
            });
            document.dispatchEvent(increaseEvent);

            const settings = webAccessibilityService.getSettings();
            expect(settings.textScaling).toBeGreaterThan(1.0);
        });

        it('should handle search focus shortcut', async () => {
            await webAccessibilityService.initialize();

            // Create a search input
            const searchInput = document.createElement('input');
            searchInput.type = 'search';
            document.body.appendChild(searchInput);

            const focusSpy = jest.spyOn(searchInput, 'focus');

            // Simulate Ctrl+S
            const event = new KeyboardEvent('keydown', {
                key: 's',
                ctrlKey: true,
            });
            document.dispatchEvent(event);

            expect(focusSpy).toHaveBeenCalled();
        });
    });

    describe('focus management', () => {
        it('should trap focus within container', async () => {
            await webAccessibilityService.initialize();

            // Create a container with focusable elements
            const container = document.createElement('div');
            const button1 = document.createElement('button');
            const button2 = document.createElement('button');
            const button3 = document.createElement('button');

            container.appendChild(button1);
            container.appendChild(button2);
            container.appendChild(button3);
            document.body.appendChild(container);

            const cleanup = webAccessibilityService.trapFocus(container);

            // First element should be focused
            expect(document.activeElement).toBe(button1);

            cleanup();
        });

        it('should handle escape key for modals', async () => {
            await webAccessibilityService.initialize();

            // Create a modal
            const modal = document.createElement('div');
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');

            const closeButton = document.createElement('button');
            closeButton.setAttribute('aria-label', 'Close modal');
            modal.appendChild(closeButton);
            document.body.appendChild(modal);

            const clickSpy = jest.spyOn(closeButton, 'click');

            // Simulate Escape key
            const event = new KeyboardEvent('keydown', {
                key: 'Escape',
            });
            document.dispatchEvent(event);

            expect(clickSpy).toHaveBeenCalled();
        });
    });

    describe('live regions', () => {
        it('should create live regions with proper attributes', async () => {
            await webAccessibilityService.initialize();

            const region = webAccessibilityService.createLiveRegion('test-region', 'assertive');

            expect(region.id).toBe('test-region');
            expect(region.getAttribute('aria-live')).toBe('assertive');
            expect(region.getAttribute('aria-atomic')).toBe('true');
        });

        it('should announce to specific live regions', async () => {
            await webAccessibilityService.initialize();

            const region = webAccessibilityService.createLiveRegion('custom-region');

            webAccessibilityService.announceToRegion('custom-region', 'Custom message');

            expect(region.textContent).toBe('Custom message');
        });
    });

    describe('text scaling', () => {
        it('should apply text scaling to document', async () => {
            await webAccessibilityService.initialize();

            await webAccessibilityService.updateSettings({ textScaling: 1.5 });

            expect(document.documentElement.style.fontSize).toBe('24px');
        });

        it('should respect text scaling limits', async () => {
            await webAccessibilityService.initialize();

            // Try to set scaling beyond maximum
            await webAccessibilityService.updateSettings({ textScaling: 5.0 });

            const settings = webAccessibilityService.getSettings();
            expect(settings.textScaling).toBeLessThanOrEqual(3.0);
        });
    });

    describe('speech synthesis', () => {
        it('should read page content when available', async () => {
            await webAccessibilityService.initialize();

            document.body.innerHTML = '<p>Test content to read</p>';

            // Simulate Alt+R shortcut
            const event = new KeyboardEvent('keydown', {
                key: 'r',
                altKey: true,
            });
            document.dispatchEvent(event);

            expect(window.speechSynthesis.speak).toHaveBeenCalled();
        });
    });

    describe('system preferences detection', () => {
        it('should detect reduced motion preference', async () => {
            // Mock reduced motion preference
            (window.matchMedia as jest.Mock).mockImplementation(query => {
                if (query === '(prefers-reduced-motion: reduce)') {
                    return {
                        matches: true,
                        addEventListener: jest.fn(),
                        removeEventListener: jest.fn(),
                    };
                }
                return {
                    matches: false,
                    addEventListener: jest.fn(),
                    removeEventListener: jest.fn(),
                };
            });

            await webAccessibilityService.initialize();

            const settings = webAccessibilityService.getSettings();
            expect(settings.reduceMotion).toBe(true);
        });

        it('should detect high contrast preference', async () => {
            // Mock high contrast preference
            (window.matchMedia as jest.Mock).mockImplementation(query => {
                if (query === '(prefers-contrast: high)') {
                    return {
                        matches: true,
                        addEventListener: jest.fn(),
                        removeEventListener: jest.fn(),
                    };
                }
                return {
                    matches: false,
                    addEventListener: jest.fn(),
                    removeEventListener: jest.fn(),
                };
            });

            await webAccessibilityService.initialize();

            const settings = webAccessibilityService.getSettings();
            expect(settings.highContrast).toBe(true);
        });
    });

    describe('keyboard navigation', () => {
        it('should add keyboard navigation class on tab key', async () => {
            await webAccessibilityService.initialize();

            const event = new KeyboardEvent('keydown', { key: 'Tab' });
            document.dispatchEvent(event);

            expect(document.body.classList.contains('keyboard-navigation')).toBe(true);
        });

        it('should remove keyboard navigation class on mouse down', async () => {
            await webAccessibilityService.initialize();

            // First add the class
            document.body.classList.add('keyboard-navigation');

            const event = new MouseEvent('mousedown');
            document.dispatchEvent(event);

            expect(document.body.classList.contains('keyboard-navigation')).toBe(false);
        });
    });
});