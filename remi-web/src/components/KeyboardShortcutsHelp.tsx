'use client';

import React, { useState, useEffect } from 'react';
import { useKeyboardShortcuts, ShortcutCategory, KeyboardShortcut } from '@/hooks/useKeyboardShortcuts';

interface KeyboardShortcutsHelpProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  const { getShortcutsByCategory, shortcutManager } = useKeyboardShortcuts();
  const [categories, setCategories] = useState<ShortcutCategory[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingShortcut, setEditingShortcut] = useState<string | null>(null);
  const [newBinding, setNewBinding] = useState('');

  useEffect(() => {
    if (isOpen) {
      setCategories(getShortcutsByCategory());
    }
  }, [isOpen, getShortcutsByCategory]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const filteredCategories = categories.map(category => ({
    ...category,
    shortcuts: category.shortcuts.filter(shortcut =>
      shortcut.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      shortcut.key.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter(category => category.shortcuts.length > 0);

  const formatShortcut = (shortcut: KeyboardShortcut): string => {
    return shortcutManager.formatShortcut(shortcut);
  };

  const handleEditShortcut = (shortcutId: string) => {
    setEditingShortcut(shortcutId);
    const shortcut = categories
      .flatMap(c => c.shortcuts)
      .find(s => s.id === shortcutId);
    if (shortcut) {
      setNewBinding(formatShortcut(shortcut));
    }
  };

  const handleSaveShortcut = () => {
    if (editingShortcut && newBinding) {
      shortcutManager.setCustomBinding(editingShortcut, newBinding);
      setCategories(getShortcutsByCategory());
      setEditingShortcut(null);
      setNewBinding('');
    }
  };

  const handleCancelEdit = () => {
    setEditingShortcut(null);
    setNewBinding('');
  };

  const handleResetDefaults = () => {
    if (confirm('Reset all keyboard shortcuts to defaults? This cannot be undone.')) {
      shortcutManager.resetToDefaults();
      setCategories(getShortcutsByCategory());
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Keyboard Shortcuts</h2>
            <p className="text-sm text-gray-600 mt-1">
              Customize your keyboard shortcuts for faster navigation
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleResetDefaults}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded hover:bg-gray-50"
            >
              Reset to Defaults
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <input
              type="text"
              placeholder="Search shortcuts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <svg
              className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[60vh]">
          {filteredCategories.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>No shortcuts found matching "{searchQuery}"</p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {filteredCategories.map((category) => (
                <div key={category.id}>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">
                    {category.name}
                  </h3>
                  <div className="space-y-2">
                    {category.shortcuts.map((shortcut) => (
                      <div
                        key={shortcut.id}
                        className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 group"
                      >
                        <div className="flex-1">
                          <span className="text-sm text-gray-900">
                            {shortcut.description}
                          </span>
                          {shortcut.disabled && (
                            <span className="ml-2 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                              Disabled
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {editingShortcut === shortcut.id ? (
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={newBinding}
                                onChange={(e) => setNewBinding(e.target.value)}
                                placeholder="e.g., Ctrl+K"
                                className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    handleSaveShortcut();
                                  } else if (e.key === 'Escape') {
                                    handleCancelEdit();
                                  }
                                }}
                                autoFocus
                              />
                              <button
                                onClick={handleSaveShortcut}
                                className="p-1 text-green-600 hover:text-green-800"
                                title="Save"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="p-1 text-red-600 hover:text-red-800"
                                title="Cancel"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </div>
                          ) : (
                            <>
                              <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 border border-gray-300 rounded">
                                {formatShortcut(shortcut)}
                              </kbd>
                              <button
                                onClick={() => handleEditShortcut(shortcut.id)}
                                className="p-1 text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Edit shortcut"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center space-x-4">
              <span>Press <kbd className="px-1 py-0.5 bg-white border border-gray-300 rounded text-xs">?</kbd> to open this help</span>
              <span>Press <kbd className="px-1 py-0.5 bg-white border border-gray-300 rounded text-xs">Esc</kbd> to close</span>
            </div>
            <div>
              {filteredCategories.reduce((total, cat) => total + cat.shortcuts.length, 0)} shortcuts available
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Hook to manage the help overlay
export function useKeyboardShortcutsHelp() {
  const [isOpen, setIsOpen] = useState(false);
  const { registerShortcut, unregisterShortcut } = useKeyboardShortcuts();

  useEffect(() => {
    const helpShortcut = {
      id: 'help-shortcuts',
      key: '?',
      description: 'Show Keyboard Shortcuts Help',
      category: 'Help',
      action: () => setIsOpen(true),
      global: true,
    };

    registerShortcut(helpShortcut);

    return () => {
      unregisterShortcut('help-shortcuts');
    };
  }, [registerShortcut, unregisterShortcut]);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
  };
}