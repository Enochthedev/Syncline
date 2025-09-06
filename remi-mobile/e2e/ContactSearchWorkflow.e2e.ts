/**
 * End-to-End Tests for Contact Search Workflow
 * Complete user journey testing with Detox
 */

import { device, expect, element, by, waitFor } from 'detox';

describe('Contact Search Workflow', () => {
    beforeAll(async () => {
        await device.launchApp();
        await global.e2eUtils.waitForAppReady();
    });

    beforeEach(async () => {
        await global.e2eUtils.clearAppData();
        await global.e2eUtils.reloadApp();
    });

    describe('Authentication Flow', () => {
        it('should complete login flow successfully', async () => {
            // Should start on login screen
            await global.e2eUtils.expectVisible('login-screen');

            // Enter credentials
            await element(by.id('email-input')).typeText('test@example.com');
            await element(by.id('password-input')).typeText('password123');

            // Tap login button
            await element(by.id('login-button')).tap();

            // Should navigate to main app
            await global.e2eUtils.waitForId('main-navigation', 10000);
            await global.e2eUtils.expectVisible('main-navigation');

            // Should show contacts tab by default
            await global.e2eUtils.expectVisible('contacts-tab');
        });

        it('should handle biometric authentication', async () => {
            // Login first
            await global.e2eUtils.loginUser();

            // Enable biometric auth in settings
            await element(by.id('settings-tab')).tap();
            await element(by.id('biometric-toggle')).tap();

            // Simulate biometric prompt
            await global.e2eUtils.simulateBiometricAuth(true);

            // Should show success message
            await global.e2eUtils.waitForText('Biometric authentication enabled');

            // Logout and try biometric login
            await global.e2eUtils.logoutUser();

            await element(by.id('biometric-login-button')).tap();
            await global.e2eUtils.simulateBiometricAuth(true);

            // Should login successfully
            await global.e2eUtils.waitForId('main-navigation');
        });

        it('should handle login errors gracefully', async () => {
            await element(by.id('email-input')).typeText('invalid@example.com');
            await element(by.id('password-input')).typeText('wrongpassword');
            await element(by.id('login-button')).tap();

            // Should show error message
            await global.e2eUtils.waitForText('Invalid credentials');

            // Should remain on login screen
            await global.e2eUtils.expectVisible('login-screen');
        });
    });

    describe('Contact Search Journey', () => {
        beforeEach(async () => {
            await global.e2eUtils.loginUser();
        });

        it('should complete full contact search workflow', async () => {
            // Navigate to search tab
            await element(by.id('search-tab')).tap();
            await global.e2eUtils.expectVisible('search-screen');

            // Perform contact search
            await element(by.id('search-input')).typeText('John');

            // Should show search suggestions
            await global.e2eUtils.waitForId('search-suggestions');
            await global.e2eUtils.expectVisible('search-suggestions');

            // Tap search button
            await element(by.id('search-button')).tap();

            // Should show search results
            await global.e2eUtils.waitForId('search-results');
            await global.e2eUtils.expectVisible('search-results');

            // Select first contact result
            await element(by.id('contact-result-0')).tap();

            // Should navigate to contact profile
            await global.e2eUtils.waitForId('contact-profile');
            await global.e2eUtils.expectVisible('contact-profile');

            // Verify contact information is displayed
            await global.e2eUtils.expectVisible('contact-name');
            await global.e2eUtils.expectVisible('contact-platforms');
            await global.e2eUtils.expectVisible('contact-last-interaction');
        });

        it('should handle natural language search', async () => {
            await element(by.id('search-tab')).tap();

            // Type natural language query
            await element(by.id('search-input')).typeText('messages from Sarah about project');

            // Should show natural language indicator
            await global.e2eUtils.waitForId('nl-search-indicator');

            await element(by.id('search-button')).tap();

            // Should show parsed query explanation
            await global.e2eUtils.waitForId('query-explanation');
            await global.e2eUtils.expectVisible('query-explanation');

            // Should show filtered results
            await global.e2eUtils.waitForId('search-results');

            // Results should be filtered by contact and topic
            await global.e2eUtils.expectVisible('search-filters-applied');
        });

        it('should support voice search', async () => {
            await element(by.id('search-tab')).tap();

            // Tap voice search button
            await element(by.id('voice-search-button')).tap();

            // Should show voice recording UI
            await global.e2eUtils.waitForId('voice-recording-ui');
            await global.e2eUtils.expectVisible('voice-recording-ui');

            // Simulate voice input (mock)
            await element(by.id('simulate-voice-input')).tap();

            // Should show transcription
            await global.e2eUtils.waitForId('voice-transcription');
            await global.e2eUtils.expectText('voice-transcription', 'find messages from John');

            // Should automatically perform search
            await global.e2eUtils.waitForId('search-results');
            await global.e2eUtils.expectVisible('search-results');
        });

        it('should handle search with filters', async () => {
            await element(by.id('search-tab')).tap();

            // Open advanced search
            await element(by.id('advanced-search-button')).tap();
            await global.e2eUtils.waitForId('search-filters');

            // Apply platform filter
            await element(by.id('platform-filter-email')).tap();
            await element(by.id('platform-filter-slack')).tap();

            // Apply date range filter
            await element(by.id('date-range-filter')).tap();
            await element(by.text('Last 7 days')).tap();

            // Apply content type filter
            await element(by.id('content-type-filter')).tap();
            await element(by.text('Messages')).tap();

            // Perform search with filters
            await element(by.id('search-input')).typeText('project update');
            await element(by.id('search-button')).tap();

            // Should show filtered results
            await global.e2eUtils.waitForId('search-results');

            // Should show active filters
            await global.e2eUtils.expectVisible('active-filters');
            await global.e2eUtils.expectVisible('filter-email');
            await global.e2eUtils.expectVisible('filter-slack');
        });
    });

    describe('Contact Profile and Messages', () => {
        beforeEach(async () => {
            await global.e2eUtils.loginUser();
            await global.e2eUtils.performSearch('John');
            await global.e2eUtils.selectContact('John Doe');
        });

        it('should display comprehensive contact profile', async () => {
            // Should show contact header
            await global.e2eUtils.expectVisible('contact-header');
            await global.e2eUtils.expectVisible('contact-photo');
            await global.e2eUtils.expectVisible('contact-name');

            // Should show platform identities
            await global.e2eUtils.expectVisible('platform-identities');

            // Should show communication stats
            await global.e2eUtils.expectVisible('communication-stats');
            await global.e2eUtils.expectVisible('last-interaction');
            await global.e2eUtils.expectVisible('message-count');

            // Should show relationship insights
            await global.e2eUtils.scrollToElement('relationship-insights');
            await global.e2eUtils.expectVisible('relationship-insights');
            await global.e2eUtils.expectVisible('communication-frequency');
            await global.e2eUtils.expectVisible('relationship-strength');
        });

        it('should navigate to message threads', async () => {
            // Tap on messages section
            await element(by.id('contact-messages-section')).tap();

            // Should show message threads
            await global.e2eUtils.waitForId('message-threads');
            await global.e2eUtils.expectVisible('message-threads');

            // Tap on first thread
            await element(by.id('message-thread-0')).tap();

            // Should open message thread view
            await global.e2eUtils.waitForId('message-thread-view');
            await global.e2eUtils.expectVisible('message-thread-view');

            // Should show messages
            await global.e2eUtils.expectVisible('message-list');

            // Should show thread header with participants
            await global.e2eUtils.expectVisible('thread-header');
            await global.e2eUtils.expectVisible('thread-participants');
        });

        it('should display shared content', async () => {
            // Navigate to shared content tab
            await element(by.id('shared-content-tab')).tap();

            // Should show content categories
            await global.e2eUtils.waitForId('content-categories');
            await global.e2eUtils.expectVisible('files-category');
            await global.e2eUtils.expectVisible('links-category');
            await global.e2eUtils.expectVisible('media-category');

            // Tap on files category
            await element(by.id('files-category')).tap();

            // Should show shared files
            await global.e2eUtils.waitForId('shared-files-list');
            await global.e2eUtils.expectVisible('shared-files-list');

            // Should be able to preview file
            await element(by.id('file-item-0')).tap();
            await global.e2eUtils.waitForId('file-preview');
            await global.e2eUtils.expectVisible('file-preview');
        });

        it('should handle contact actions', async () => {
            // Tap contact actions menu
            await element(by.id('contact-actions-menu')).tap();

            // Should show action options
            await global.e2eUtils.waitForId('contact-actions');
            await global.e2eUtils.expectVisible('add-note-action');
            await global.e2eUtils.expectVisible('edit-contact-action');
            await global.e2eUtils.expectVisible('merge-contact-action');

            // Test add note
            await element(by.id('add-note-action')).tap();
            await global.e2eUtils.waitForId('add-note-modal');

            await element(by.id('note-input')).typeText('Important client contact');
            await element(by.id('save-note-button')).tap();

            // Should show note in contact profile
            await global.e2eUtils.waitForId('contact-notes');
            await global.e2eUtils.expectVisible('contact-notes');
        });
    });

    describe('Real-time Updates', () => {
        beforeEach(async () => {
            await global.e2eUtils.loginUser();
        });

        it('should receive real-time message notifications', async () => {
            // Navigate to messages tab
            await element(by.id('messages-tab')).tap();

            // Simulate incoming message (via test API)
            await device.sendUserNotification({
                trigger: {
                    type: 'push',
                },
                title: 'New Message',
                subtitle: 'John Doe',
                body: 'Hey, how are you?',
                badge: 1,
                payload: {
                    messageId: 'test-message-123',
                    senderId: 'john-doe',
                },
            });

            // Should show notification
            await global.e2eUtils.waitForText('New Message');

            // Tap notification to open message
            await element(by.text('New Message')).tap();

            // Should navigate to message thread
            await global.e2eUtils.waitForId('message-thread-view');
            await global.e2eUtils.expectVisible('message-thread-view');
        });

        it('should sync data in real-time', async () => {
            // Start on contacts tab
            await element(by.id('contacts-tab')).tap();

            // Get initial contact count
            const initialCount = await element(by.id('contacts-count')).getAttributes();

            // Simulate contact added on another device (via WebSocket mock)
            await device.sendUserActivity({
                type: 'contact_added',
                data: {
                    id: 'new-contact-123',
                    name: 'Jane Smith',
                    email: 'jane@example.com',
                },
            });

            // Should update contact list
            await global.e2eUtils.waitForText('Jane Smith');
            await global.e2eUtils.expectVisible('contact-jane-smith');

            // Contact count should increase
            await waitFor(element(by.id('contacts-count')))
                .not.toHaveText(initialCount.text)
                .withTimeout(5000);
        });
    });

    describe('Offline Functionality', () => {
        beforeEach(async () => {
            await global.e2eUtils.loginUser();
        });

        it('should work offline with cached data', async () => {
            // Load some data while online
            await global.e2eUtils.performSearch('John');
            await global.e2eUtils.waitForId('search-results');

            // Go offline
            await global.e2eUtils.goOffline();

            // Should show offline indicator
            await global.e2eUtils.waitForId('offline-indicator');
            await global.e2eUtils.expectVisible('offline-indicator');

            // Should still be able to search cached data
            await element(by.id('search-input')).clearText();
            await element(by.id('search-input')).typeText('John');
            await element(by.id('search-button')).tap();

            // Should show cached results
            await global.e2eUtils.waitForId('search-results');
            await global.e2eUtils.expectVisible('cached-results-indicator');

            // Should be able to view contact profile
            await element(by.id('contact-result-0')).tap();
            await global.e2eUtils.waitForId('contact-profile');
            await global.e2eUtils.expectVisible('contact-profile');
        });

        it('should sync when coming back online', async () => {
            // Go offline
            await global.e2eUtils.goOffline();

            // Make changes while offline
            await global.e2eUtils.performSearch('John');
            await global.e2eUtils.selectContact('John Doe');

            await element(by.id('contact-actions-menu')).tap();
            await element(by.id('add-note-action')).tap();
            await element(by.id('note-input')).typeText('Added while offline');
            await element(by.id('save-note-button')).tap();

            // Should show pending sync indicator
            await global.e2eUtils.waitForId('pending-sync-indicator');

            // Go back online
            await global.e2eUtils.goOnline();

            // Should show syncing indicator
            await global.e2eUtils.waitForId('syncing-indicator');

            // Should complete sync
            await waitFor(element(by.id('syncing-indicator')))
                .not.toBeVisible()
                .withTimeout(10000);

            // Changes should be synced
            await global.e2eUtils.expectVisible('contact-notes');
        });
    });

    describe('Performance and Edge Cases', () => {
        beforeEach(async () => {
            await global.e2eUtils.loginUser();
        });

        it('should handle large search result sets', async () => {
            // Perform broad search that returns many results
            await global.e2eUtils.performSearch('a'); // Single letter to get many results

            // Should show results with pagination
            await global.e2eUtils.waitForId('search-results');
            await global.e2eUtils.expectVisible('search-results');

            // Should be able to scroll through results smoothly
            await element(by.id('search-results-list')).scroll(1000, 'down');
            await element(by.id('search-results-list')).scroll(1000, 'down');

            // Should load more results
            await global.e2eUtils.waitForId('load-more-results');
            await element(by.id('load-more-results')).tap();

            // Should show additional results
            await global.e2eUtils.waitForText('Showing more results');
        });

        it('should handle app backgrounding and foregrounding', async () => {
            // Navigate to contact profile
            await global.e2eUtils.performSearch('John');
            await global.e2eUtils.selectContact('John Doe');

            // Background the app
            await global.e2eUtils.backgroundApp(5000);

            // Should return to same screen
            await global.e2eUtils.expectVisible('contact-profile');

            // Should maintain scroll position and state
            await global.e2eUtils.expectVisible('contact-name');
        });

        it('should handle memory pressure gracefully', async () => {
            // Simulate memory pressure by loading many contacts
            for (let i = 0; i < 10; i++) {
                await global.e2eUtils.performSearch(`contact${i}`);
                await global.e2eUtils.waitForId('search-results');

                if (i < 9) {
                    await element(by.id('search-input')).clearText();
                }
            }

            // App should remain responsive
            await global.e2eUtils.expectVisible('search-screen');

            // Should be able to navigate normally
            await element(by.id('contacts-tab')).tap();
            await global.e2eUtils.expectVisible('contacts-screen');
        });

        it('should handle rapid user interactions', async () => {
            // Rapidly tap between tabs
            for (let i = 0; i < 5; i++) {
                await element(by.id('search-tab')).tap();
                await element(by.id('contacts-tab')).tap();
                await element(by.id('messages-tab')).tap();
                await element(by.id('settings-tab')).tap();
            }

            // Should end up on settings tab
            await global.e2eUtils.expectVisible('settings-screen');

            // App should remain stable
            await element(by.id('contacts-tab')).tap();
            await global.e2eUtils.expectVisible('contacts-screen');
        });
    });
});