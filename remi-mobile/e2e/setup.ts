/**
 * Detox E2E Test Setup
 * Global setup for end-to-end testing
 */

import { device, expect, element, by, waitFor } from 'detox';

// Extend Jest matchers with Detox
declare global {
    namespace jest {
        interface Matchers<R> {
            toBeVisible(): R;
            toExist(): R;
            toHaveText(text: string): R;
            toHaveValue(value: string): R;
        }
    }
}

// Global test utilities for E2E tests
(global as any).e2eUtils = {
    // Wait for app to be ready
    waitForAppReady: async () => {
        await waitFor(element(by.id('app-container')))
            .toBeVisible()
            .withTimeout(10000);
    },

    // Login helper
    loginUser: async (email: string = 'test@example.com', password: string = 'password123') => {
        await element(by.id('email-input')).typeText(email);
        await element(by.id('password-input')).typeText(password);
        await element(by.id('login-button')).tap();

        // Wait for login to complete
        await waitFor(element(by.id('main-navigation')))
            .toBeVisible()
            .withTimeout(5000);
    },

    // Logout helper
    logoutUser: async () => {
        await element(by.id('settings-tab')).tap();
        await element(by.id('logout-button')).tap();
        await element(by.text('Confirm')).tap();

        // Wait for logout to complete
        await waitFor(element(by.id('login-screen')))
            .toBeVisible()
            .withTimeout(5000);
    },

    // Search helper
    performSearch: async (query: string) => {
        await element(by.id('search-tab')).tap();
        await element(by.id('search-input')).typeText(query);
        await element(by.id('search-button')).tap();
    },

    // Contact selection helper
    selectContact: async (contactName: string) => {
        await element(by.text(contactName)).tap();
        await waitFor(element(by.id('contact-profile')))
            .toBeVisible()
            .withTimeout(3000);
    },

    // Message thread helper
    openMessageThread: async (threadTitle: string) => {
        await element(by.text(threadTitle)).tap();
        await waitFor(element(by.id('message-thread')))
            .toBeVisible()
            .withTimeout(3000);
    },

    // Scroll helpers
    scrollToElement: async (elementId: string, direction: 'up' | 'down' = 'down') => {
        await waitFor(element(by.id(elementId)))
            .toBeVisible()
            .whileElement(by.id('scroll-view'))
            .scroll(200, direction);
    },

    // Screenshot helper
    takeScreenshot: async (name: string) => {
        await device.takeScreenshot(name);
    },

    // Device helpers
    reloadApp: async () => {
        await device.reloadReactNative();
        await global.e2eUtils.waitForAppReady();
    },

    backgroundApp: async (duration: number = 2000) => {
        await device.sendToHome();
        await new Promise(resolve => setTimeout(resolve, duration));
        await device.launchApp({ newInstance: false });
    },

    // Network helpers
    goOffline: async () => {
        await device.setURLBlacklist(['.*']);
    },

    goOnline: async () => {
        await device.setURLBlacklist([]);
    },

    // Biometric helpers
    simulateBiometricAuth: async (success: boolean = true) => {
        if (device.getPlatform() === 'ios') {
            if (success) {
                await device.matchFace();
            } else {
                await device.unmatchedFace();
            }
        } else {
            if (success) {
                await device.matchFinger();
            } else {
                await device.unmatchedFinger();
            }
        }
    },

    // Permission helpers
    grantPermissions: async () => {
        if (device.getPlatform() === 'ios') {
            await device.setPermissions({
                notifications: 'YES',
                contacts: 'YES',
                microphone: 'YES',
            });
        }
    },

    // Data helpers
    clearAppData: async () => {
        await device.clearKeychain();
        // Clear AsyncStorage and other local data
        await device.reloadReactNative();
    },

    // Wait helpers
    waitForText: async (text: string, timeout: number = 5000) => {
        await waitFor(element(by.text(text)))
            .toBeVisible()
            .withTimeout(timeout);
    },

    waitForId: async (id: string, timeout: number = 5000) => {
        await waitFor(element(by.id(id)))
            .toBeVisible()
            .withTimeout(timeout);
    },

    // Assertion helpers
    expectVisible: async (id: string) => {
        await expect(element(by.id(id))).toBeVisible();
    },

    expectText: async (id: string, text: string) => {
        await expect(element(by.id(id))).toHaveText(text);
    },

    expectNotVisible: async (id: string) => {
        await expect(element(by.id(id))).not.toBeVisible();
    },
};

// Setup before each test
beforeEach(async () => {
    // Grant necessary permissions
    await global.e2eUtils.grantPermissions();

    // Ensure app is ready
    await global.e2eUtils.waitForAppReady();
});

// Cleanup after each test
afterEach(async () => {
    // Take screenshot on failure
    if (jasmine.currentSpec && jasmine.currentSpec.failedExpectations.length > 0) {
        const specName = jasmine.currentSpec.fullName.replace(/\s+/g, '_');
        await global.e2eUtils.takeScreenshot(`failed_${specName}`);
    }
});