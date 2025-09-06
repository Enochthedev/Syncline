'use client';

import React, { useEffect, useState } from 'react';
import { useKeyboardShortcuts, useKeyboardShortcutsHelp } from '@/hooks/useKeyboardShortcuts';
import { KeyboardShortcutsHelp } from '@/components/KeyboardShortcutsHelp';
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt';
import { useMultiWindow } from '@/utils/multiWindow';
import { useExtensionAPI } from '@/utils/extensionAPI';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [isOnline, setIsOnline] = useState(true);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [notifications, setNotifications] = useState<any[]>([]);

  // Keyboard shortcuts
  const { shortcutManager } = useKeyboardShortcuts();
  const keyboardHelp = useKeyboardShortcutsHelp();

  // Multi-window support
  const { activeWindows, syncData, currentWindowId } = useMultiWindow();

  // Extension API
  const { notifyExtensions } = useExtensionAPI();

  // Connection status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial status
    setIsOnline(navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Service worker messages
  useEffect(() => {
    const handleSWMessage = (event: CustomEvent) => {
      const { type, payload } = event.detail;

      switch (type) {
        case 'CONNECTION_STATUS':
          setIsOnline(payload.isOnline);
          break;
        case 'CACHE_UPDATED':
          setSyncStatus('idle');
          notifyExtensions('cache-updated', payload);
          break;
        case 'PUSH_NOTIFICATION':
          setNotifications(prev => [...prev, payload]);
          break;
        case 'UPDATE_AVAILABLE':
          setNotifications(prev => [...prev, {
            id: 'update-available',
            type: 'info',
            title: 'Update Available',
            message: payload.message,
            actions: [
              {
                label: 'Update Now',
                action: () => {
                  // This would trigger the service worker update
                  window.location.reload();
                },
              },
              {
                label: 'Later',
                action: () => {
                  setNotifications(prev => prev.filter(n => n.id !== 'update-available'));
                },
              },
            ],
          }]);
          break;
      }
    };

    window.addEventListener('sw-message', handleSWMessage as EventListener);

    return () => {
      window.removeEventListener('sw-message', handleSWMessage as EventListener);
    };
  }, [notifyExtensions]);

  // Multi-window synchronization
  useEffect(() => {
    const handleMultiWindowMessage = (event: CustomEvent) => {
      const { type, payload } = event.detail;

      switch (type) {
        case 'contacts-synced':
          notifyExtensions('contacts-synced', payload);
          break;
        case 'search-results-synced':
          notifyExtensions('search-results-synced', payload);
          break;
        case 'auth-state-synced':
          notifyExtensions('auth-state-synced', payload);
          break;
      }
    };

    window.addEventListener('multi-window-contacts-synced', handleMultiWindowMessage as EventListener);
    window.addEventListener('multi-window-search-results-synced', handleMultiWindowMessage as EventListener);
    window.addEventListener('multi-window-auth-state-synced', handleMultiWindowMessage as EventListener);

    return () => {
      window.removeEventListener('multi-window-contacts-synced', handleMultiWindowMessage as EventListener);
      window.removeEventListener('multi-window-search-results-synced', handleMultiWindowMessage as EventListener);
      window.removeEventListener('multi-window-auth-state-synced', handleMultiWindowMessage as EventListener);
    };
  }, [notifyExtensions]);

  // Register global keyboard shortcuts
  useEffect(() => {
    const globalShortcuts = [
      {
        id: 'toggle-help',
        key: '?',
        description: 'Show keyboard shortcuts help',
        category: 'Help',
        action: keyboardHelp.open,
        global: true,
      },
      {
        id: 'refresh-page',
        key: 'r',
        ctrlKey: true,
        description: 'Refresh page',
        category: 'Application',
        action: () => window.location.reload(),
        global: true,
      },
      {
        id: 'toggle-fullscreen',
        key: 'F11',
        description: 'Toggle fullscreen',
        category: 'Application',
        action: () => {
          if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
          } else {
            document.exitFullscreen();
          }
        },
        global: true,
      },
    ];

    globalShortcuts.forEach(shortcut => {
      shortcutManager.register(shortcut);
    });

    return () => {
      globalShortcuts.forEach(shortcut => {
        shortcutManager.unregister(shortcut.id);
      });
    };
  }, [shortcutManager, keyboardHelp.open]);

  const dismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Connection Status Bar */}
      {!isOnline && (
        <div className="bg-yellow-500 text-white px-4 py-2 text-center text-sm">
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span>You're offline. Some features may be limited.</span>
          </div>
        </div>
      )}

      {/* Sync Status Bar */}
      {syncStatus === 'syncing' && (
        <div className="bg-blue-500 text-white px-4 py-2 text-center text-sm">
          <div className="flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            <span>Syncing data across windows...</span>
          </div>
        </div>
      )}

      {/* Multi-Window Status */}
      {activeWindows.length > 1 && (
        <div className="bg-green-500 text-white px-4 py-2 text-center text-sm">
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
            </svg>
            <span>{activeWindows.length} windows open - data synced automatically</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="relative">
        {children}
      </main>

      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className="bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-gray-900">
                  {notification.title}
                </h4>
                <p className="text-sm text-gray-600 mt-1">
                  {notification.message}
                </p>
                {notification.actions && (
                  <div className="flex space-x-2 mt-3">
                    {notification.actions.map((action: any, index: number) => (
                      <button
                        key={index}
                        onClick={action.action}
                        className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => dismissNotification(notification.id)}
                className="ml-2 p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* PWA Install Prompt */}
      <PWAInstallPrompt
        onInstall={() => {
          setNotifications(prev => [...prev, {
            id: 'pwa-installed',
            type: 'success',
            title: 'App Installed',
            message: 'R.E.M.I has been installed successfully!',
          }]);
        }}
        onDismiss={() => {
          console.log('PWA install prompt dismissed');
        }}
      />

      {/* Keyboard Shortcuts Help */}
      <KeyboardShortcutsHelp
        isOpen={keyboardHelp.isOpen}
        onClose={keyboardHelp.close}
      />

      {/* Skip to main content link for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded z-50"
      >
        Skip to main content
      </a>

      {/* Screen reader announcements */}
      <div
        id="screen-reader-announcements"
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      >
        {!isOnline && 'Application is now offline'}
        {syncStatus === 'syncing' && 'Syncing data'}
        {activeWindows.length > 1 && `${activeWindows.length} windows are open and synchronized`}
      </div>

      {/* Focus management for keyboard navigation */}
      <div
        id="focus-trap-start"
        tabIndex={0}
        onFocus={(e) => {
          // Move focus to the last focusable element when tabbing backwards from the start
          const focusableElements = document.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
          if (lastElement) {
            lastElement.focus();
          }
        }}
      />

      <div
        id="focus-trap-end"
        tabIndex={0}
        onFocus={(e) => {
          // Move focus to the first focusable element when tabbing forward from the end
          const focusableElements = document.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          const firstElement = focusableElements[0] as HTMLElement;
          if (firstElement) {
            firstElement.focus();
          }
        }}
      />
    </div>
  );
}