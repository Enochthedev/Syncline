import { renderHook, act } from '@testing-library/react';
import { useKeyboardShortcuts, shortcutManager } from '@/hooks/useKeyboardShortcuts';

// Mock next/navigation
jest.mock('next/navigation', () => ({
    useRouter: () => ({
        push: jest.fn(),
    }),
}));

describe('Keyboard Shortcuts', () => {
    beforeEach(() => {
        // Clear any existing shortcuts
        shortcutManager['shortcuts'].clear();

        // Mock localStorage
        Object.defineProperty(window, 'localStorage', {
            value: {
                getItem: jest.fn(),
                setItem: jest.fn(),
                removeItem: jest.fn(),
            },
            writable: true,
        });

        // Mock document.addEventListener
        jest.spyOn(document, 'addEventListener');
        jest.spyOn(document, 'removeEventListener');
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('ShortcutManager', () => {
        it('should register shortcuts', () => {
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action: jest.fn(),
            };

            shortcutManager.register(shortcut);

            const shortcuts = shortcutManager.getShortcuts();
            expect(shortcuts).toContainEqual(shortcut);
        });

        it('should unregister shortcuts', () => {
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action: jest.fn(),
            };

            shortcutManager.register(shortcut);
            shortcutManager.unregister('test-shortcut');

            const shortcuts = shortcutManager.getShortcuts();
            expect(shortcuts).not.toContainEqual(shortcut);
        });

        it('should update existing shortcuts', () => {
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action: jest.fn(),
            };

            shortcutManager.register(shortcut);
            shortcutManager.updateShortcut('test-shortcut', { description: 'Updated description' });

            const shortcuts = shortcutManager.getShortcuts();
            const updatedShortcut = shortcuts.find(s => s.id === 'test-shortcut');
            expect(updatedShortcut?.description).toBe('Updated description');
        });

        it('should set custom key bindings', () => {
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action: jest.fn(),
            };

            shortcutManager.register(shortcut);
            shortcutManager.setCustomBinding('test-shortcut', 'ctrl+shift+k');

            const shortcuts = shortcutManager.getShortcuts();
            const updatedShortcut = shortcuts.find(s => s.id === 'test-shortcut');
            expect(updatedShortcut?.shiftKey).toBe(true);
            expect(localStorage.setItem).toHaveBeenCalledWith(
                'keyboard-shortcuts',
                expect.stringContaining('test-shortcut')
            );
        });

        it('should parse key bindings correctly', () => {
            const result = shortcutManager['parseKeyBinding']('ctrl+shift+alt+k');

            expect(result).toEqual({
                ctrlKey: true,
                altKey: true,
                shiftKey: true,
                metaKey: false,
                key: 'k',
            });
        });

        it('should format shortcuts for display', () => {
            const shortcut = {
                id: 'test',
                key: 'k',
                ctrlKey: true,
                shiftKey: true,
                description: 'Test',
                category: 'Test',
                action: jest.fn(),
            };

            const formatted = shortcutManager.formatShortcut(shortcut);
            expect(formatted).toBe('Ctrl + Shift + K');
        });

        it('should group shortcuts by category', () => {
            const shortcuts = [
                {
                    id: 'nav-1',
                    key: 'h',
                    description: 'Home',
                    category: 'Navigation',
                    action: jest.fn(),
                },
                {
                    id: 'nav-2',
                    key: 'k',
                    description: 'Search',
                    category: 'Navigation',
                    action: jest.fn(),
                },
                {
                    id: 'edit-1',
                    key: 'e',
                    description: 'Edit',
                    category: 'Editing',
                    action: jest.fn(),
                },
            ];

            shortcuts.forEach(s => shortcutManager.register(s));

            const categories = shortcutManager.getShortcutsByCategory();

            expect(categories).toHaveLength(2);
            expect(categories.find(c => c.name === 'Navigation')?.shortcuts).toHaveLength(2);
            expect(categories.find(c => c.name === 'Editing')?.shortcuts).toHaveLength(1);
        });

        it('should reset to defaults', () => {
            const customShortcut = {
                id: 'custom',
                key: 'x',
                description: 'Custom',
                category: 'Custom',
                action: jest.fn(),
            };

            shortcutManager.register(customShortcut);
            shortcutManager.setCustomBinding('custom', 'ctrl+x');

            shortcutManager.resetToDefaults();

            expect(localStorage.removeItem).toHaveBeenCalled();
            expect(localStorage.setItem).toHaveBeenCalledWith('keyboard-shortcuts', '{}');
        });
    });

    describe('Keyboard Event Handling', () => {
        it('should match keyboard events to shortcuts', () => {
            const action = jest.fn();
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action,
            };

            shortcutManager.register(shortcut);

            const event = new KeyboardEvent('keydown', {
                key: 'k',
                ctrlKey: true,
                altKey: false,
                shiftKey: false,
                metaKey: false,
            });

            Object.defineProperty(event, 'target', {
                value: document.body,
                writable: true,
            });

            shortcutManager.handleKeyDown(event);

            expect(action).toHaveBeenCalled();
        });

        it('should not trigger shortcuts in input fields', () => {
            const action = jest.fn();
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action,
            };

            shortcutManager.register(shortcut);

            const input = document.createElement('input');
            const event = new KeyboardEvent('keydown', {
                key: 'k',
                ctrlKey: true,
            });

            Object.defineProperty(event, 'target', {
                value: input,
                writable: true,
            });

            shortcutManager.handleKeyDown(event);

            expect(action).not.toHaveBeenCalled();
        });

        it('should trigger global shortcuts in input fields', () => {
            const action = jest.fn();
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action,
                global: true,
            };

            shortcutManager.register(shortcut);

            const input = document.createElement('input');
            const event = new KeyboardEvent('keydown', {
                key: 'k',
                ctrlKey: true,
            });

            Object.defineProperty(event, 'target', {
                value: input,
                writable: true,
            });

            // Mock preventDefault
            event.preventDefault = jest.fn();

            shortcutManager.handleKeyDown(event);

            expect(action).toHaveBeenCalled();
            expect(event.preventDefault).toHaveBeenCalled();
        });

        it('should not trigger disabled shortcuts', () => {
            const action = jest.fn();
            const shortcut = {
                id: 'test-shortcut',
                key: 'k',
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action,
                disabled: true,
            };

            shortcutManager.register(shortcut);

            const event = new KeyboardEvent('keydown', {
                key: 'k',
                ctrlKey: true,
            });

            Object.defineProperty(event, 'target', {
                value: document.body,
                writable: true,
            });

            shortcutManager.handleKeyDown(event);

            expect(action).not.toHaveBeenCalled();
        });

        it('should handle case-insensitive key matching', () => {
            const action = jest.fn();
            const shortcut = {
                id: 'test-shortcut',
                key: 'K', // Uppercase
                ctrlKey: true,
                description: 'Test shortcut',
                category: 'Test',
                action,
            };

            shortcutManager.register(shortcut);

            const event = new KeyboardEvent('keydown', {
                key: 'k', // Lowercase
                ctrlKey: true,
            });

            Object.defineProperty(event, 'target', {
                value: document.body,
                writable: true,
            });

            shortcutManager.handleKeyDown(event);

            expect(action).toHaveBeenCalled();
        });
    });

    describe('useKeyboardShortcuts Hook', () => {
        it('should register and cleanup shortcuts', () => {
            const shortcuts = [
                {
                    id: 'hook-shortcut',
                    key: 'h',
                    description: 'Hook shortcut',
                    category: 'Test',
                    action: jest.fn(),
                },
            ];

            const { unmount } = renderHook(() => useKeyboardShortcuts(shortcuts));

            // Should register shortcuts
            const registeredShortcuts = shortcutManager.getShortcuts();
            expect(registeredShortcuts).toContainEqual(shortcuts[0]);

            // Should add event listener
            expect(document.addEventListener).toHaveBeenCalledWith('keydown', expect.any(Function));

            // Should cleanup on unmount
            unmount();
            expect(document.removeEventListener).toHaveBeenCalledWith('keydown', expect.any(Function));
        });

        it('should provide shortcut management functions', () => {
            const { result } = renderHook(() => useKeyboardShortcuts());

            expect(result.current.registerShortcut).toBeInstanceOf(Function);
            expect(result.current.unregisterShortcut).toBeInstanceOf(Function);
            expect(result.current.getShortcuts).toBeInstanceOf(Function);
            expect(result.current.getShortcutsByCategory).toBeInstanceOf(Function);
        });

        it('should register navigation shortcuts', () => {
            renderHook(() => useKeyboardShortcuts());

            const shortcuts = shortcutManager.getShortcuts();
            const navShortcuts = shortcuts.filter(s => s.category === 'Navigation');

            expect(navShortcuts.length).toBeGreaterThan(0);
            expect(navShortcuts.some(s => s.id === 'nav-home')).toBe(true);
            expect(navShortcuts.some(s => s.id === 'nav-search')).toBe(true);
        });
    });

    describe('Custom Bindings Persistence', () => {
        it('should load custom bindings from localStorage', () => {
            const customBindings = {
                'test-shortcut': 'ctrl+shift+k',
            };

            (localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(customBindings));

            // Create new instance to trigger loading
            const newManager = new (shortcutManager.constructor as any)();

            expect(localStorage.getItem).toHaveBeenCalledWith('keyboard-shortcuts');
        });

        it('should handle invalid localStorage data gracefully', () => {
            (localStorage.getItem as jest.Mock).mockReturnValue('invalid json');

            const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

            // Create new instance to trigger loading
            const newManager = new (shortcutManager.constructor as any)();

            expect(consoleSpy).toHaveBeenCalledWith(
                'Failed to load custom keyboard shortcuts:',
                expect.any(Error)
            );

            consoleSpy.mockRestore();
        });

        it('should save custom bindings to localStorage', () => {
            shortcutManager.setCustomBinding('test', 'ctrl+k');

            expect(localStorage.setItem).toHaveBeenCalledWith(
                'keyboard-shortcuts',
                expect.stringContaining('test')
            );
        });

        it('should handle localStorage save errors gracefully', () => {
            (localStorage.setItem as jest.Mock).mockImplementation(() => {
                throw new Error('Storage full');
            });

            const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

            shortcutManager.setCustomBinding('test', 'ctrl+k');

            expect(consoleSpy).toHaveBeenCalledWith(
                'Failed to save custom keyboard shortcuts:',
                expect.any(Error)
            );

            consoleSpy.mockRestore();
        });
    });
});