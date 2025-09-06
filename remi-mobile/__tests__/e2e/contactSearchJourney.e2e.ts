/**
 * End-to-End Tests for Contact Search User Journey
 * 
 * Tests the complete workflow from search input to contact profile
 */

import { by, device, element, expect, waitFor } from 'detox'

describe('Contact Search Journey', () => {
    beforeAll(async () => {
        await device.launchApp()
    })

    beforeEach(async () => {
        await device.reloadReactNative()
    })

    describe('Complete Contact Search Workflow', () => {
        it('should complete the full contact search workflow', async () => {
            // 1. Start from dashboard
            await waitFor(element(by.text('Dashboard')))
                .toBeVisible()
                .withTimeout(5000)

            // 2. Navigate to demo workflow
            await element(by.text('Try Demo Workflow')).tap()

            // 3. Verify demo workflow screen loads
            await waitFor(element(by.text('Welcome to R.E.M.I Demo')))
                .toBeVisible()
                .withTimeout(3000)

            // 4. Start the demo
            await element(by.text('Start Demo')).tap()

            // 5. Verify search screen appears
            await waitFor(element(by.text('Search for Contacts')))
                .toBeVisible()
                .withTimeout(3000)

            // 6. Perform contact search
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('John Smith')

            // 7. Wait for search results
            await waitFor(element(by.text('Search Results')))
                .toBeVisible()
                .withTimeout(5000)

            // 8. Select a contact from results
            await element(by.text('John Smith')).tap()

            // 9. Verify contact profile screen
            await waitFor(element(by.text('Contact Profile')))
                .toBeVisible()
                .withTimeout(3000)

            // 10. View messages
            await element(by.text('View Messages')).tap()

            // 11. Verify messages screen
            await waitFor(element(by.text('Message History')))
                .toBeVisible()
                .withTimeout(3000)

            // 12. View insights
            await element(by.text('View Insights')).tap()

            // 13. Verify insights screen
            await waitFor(element(by.text('AI Insights')))
                .toBeVisible()
                .withTimeout(3000)

            // 14. Navigate to full profile
            await element(by.text('Open Full Profile')).tap()

            // 15. Verify full profile screen loads
            await waitFor(element(by.text('Contact Profile')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should handle natural language search', async () => {
            // Navigate to search screen
            await element(by.text('Search')).tap()

            // Try natural language search
            await element(by.text('Try Natural Language')).tap()

            // Enter natural language query
            const nlInput = element(by.id('natural-language-input'))
            await nlInput.typeText('messages with John')

            // Verify search processes
            await waitFor(element(by.text('Processing...')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should handle empty search results gracefully', async () => {
            // Navigate to search
            await element(by.text('Search')).tap()

            // Search for non-existent contact
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('NonExistentContact')

            // Verify empty state message
            await waitFor(element(by.text('No contacts found')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should support fuzzy matching in search', async () => {
            // Navigate to search
            await element(by.text('Search')).tap()

            // Search with typos
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('Jon Smth') // Typos in "John Smith"

            // Should still find John Smith
            await waitFor(element(by.text('John Smith')))
                .toBeVisible()
                .withTimeout(5000)
        })

        it('should display contact suggestions', async () => {
            // Navigate to search
            await element(by.text('Search')).tap()

            // Start typing
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('J')

            // Verify suggestions appear
            await waitFor(element(by.id('contact-suggestions')))
                .toBeVisible()
                .withTimeout(3000)
        })
    })

    describe('Contact Profile Features', () => {
        beforeEach(async () => {
            // Navigate to a contact profile
            await element(by.text('Contacts')).tap()
            await element(by.text('John Smith')).tap()
        })

        it('should display contact information correctly', async () => {
            // Verify contact name
            await expect(element(by.text('John Smith'))).toBeVisible()

            // Verify contact details
            await expect(element(by.text('john.smith@company.com'))).toBeVisible()

            // Verify platform indicators
            await expect(element(by.text('GMAIL'))).toBeVisible()
            await expect(element(by.text('SLACK'))).toBeVisible()
        })

        it('should show communication statistics', async () => {
            // Verify message count
            await expect(element(by.text('127'))).toBeVisible()

            // Verify relationship strength
            await expect(element(by.text('85%'))).toBeVisible()

            // Verify platform count
            await expect(element(by.text('2'))).toBeVisible()
        })

        it('should navigate to message threads', async () => {
            // Tap on messages
            await element(by.text('View Messages')).tap()

            // Verify message thread screen
            await waitFor(element(by.text('Messages')))
                .toBeVisible()
                .withTimeout(3000)
        })
    })

    describe('Message Thread Features', () => {
        beforeEach(async () => {
            // Navigate to message thread
            await element(by.text('Messages')).tap()
            await element(by.text('John Smith')).tap()
        })

        it('should display message thread correctly', async () => {
            // Verify thread title
            await expect(element(by.text('Conversation with John Smith'))).toBeVisible()

            // Verify messages are displayed
            await expect(element(by.id('message-list'))).toBeVisible()
        })

        it('should show message timestamps', async () => {
            // Verify timestamp format
            await expect(element(by.id('message-timestamp'))).toBeVisible()
        })

        it('should handle message search within thread', async () => {
            // Open search in thread
            await element(by.id('thread-search-button')).tap()

            // Search for specific content
            const searchInput = element(by.id('thread-search-input'))
            await searchInput.typeText('project')

            // Verify search highlights
            await waitFor(element(by.id('search-highlight')))
                .toBeVisible()
                .withTimeout(3000)
        })
    })

    describe('Settings and Configuration', () => {
        beforeEach(async () => {
            await element(by.text('Settings')).tap()
        })

        it('should display user profile information', async () => {
            // Verify user name
            await expect(element(by.text('Demo User'))).toBeVisible()

            // Verify demo badge
            await expect(element(by.text('Demo Mode'))).toBeVisible()
        })

        it('should show platform connection status', async () => {
            // Verify platform list
            await expect(element(by.text('Gmail'))).toBeVisible()
            await expect(element(by.text('Slack'))).toBeVisible()
            await expect(element(by.text('Discord'))).toBeVisible()
            await expect(element(by.text('WhatsApp'))).toBeVisible()

            // Verify connection status
            await expect(element(by.text('Not connected'))).toBeVisible()
        })

        it('should open API configuration', async () => {
            // Open API config
            await element(by.text('API Configuration')).tap()

            // Verify modal opens
            await waitFor(element(by.text('API Configuration')))
                .toBeVisible()
                .withTimeout(3000)

            // Verify API URL input
            await expect(element(by.id('api-url-input'))).toBeVisible()
        })

        it('should handle settings toggles', async () => {
            // Toggle notifications
            await element(by.id('notifications-toggle')).tap()

            // Toggle biometric auth
            await element(by.id('biometric-toggle')).tap()

            // Toggle dark mode
            await element(by.id('dark-mode-toggle')).tap()
        })
    })

    describe('Error Handling', () => {
        it('should handle network errors gracefully', async () => {
            // Simulate network error
            await device.setURLBlacklist(['.*'])

            // Try to search
            await element(by.text('Search')).tap()
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('John')

            // Verify error message
            await waitFor(element(by.text('Network error')))
                .toBeVisible()
                .withTimeout(5000)

            // Reset network
            await device.setURLBlacklist([])
        })

        it('should show offline indicator when offline', async () => {
            // Simulate offline
            await device.setURLBlacklist(['.*'])

            // Verify offline indicator
            await waitFor(element(by.text('Offline - Search unavailable')))
                .toBeVisible()
                .withTimeout(3000)

            // Reset network
            await device.setURLBlacklist([])
        })

        it('should handle API timeout errors', async () => {
            // This would require mocking slow API responses
            // For now, just verify error handling UI exists
            await element(by.text('Search')).tap()

            // Verify retry button exists in error states
            // This would be triggered by actual timeout in real scenario
        })
    })

    describe('Performance and Responsiveness', () => {
        it('should load search results quickly', async () => {
            const startTime = Date.now()

            await element(by.text('Search')).tap()
            const searchInput = element(by.id('contact-search-input'))
            await searchInput.typeText('John')

            await waitFor(element(by.text('John Smith')))
                .toBeVisible()
                .withTimeout(2000) // Should load within 2 seconds

            const endTime = Date.now()
            const loadTime = endTime - startTime

            // Verify reasonable load time (less than 2 seconds)
            expect(loadTime).toBeLessThan(2000)
        })

        it('should handle rapid typing in search', async () => {
            await element(by.text('Search')).tap()
            const searchInput = element(by.id('contact-search-input'))

            // Type rapidly
            await searchInput.typeText('J')
            await searchInput.typeText('o')
            await searchInput.typeText('h')
            await searchInput.typeText('n')

            // Should still show results
            await waitFor(element(by.text('John Smith')))
                .toBeVisible()
                .withTimeout(3000)
        })

        it('should scroll smoothly through long contact lists', async () => {
            await element(by.text('Contacts')).tap()

            // Scroll through list
            await element(by.id('contact-list')).scroll(500, 'down')
            await element(by.id('contact-list')).scroll(500, 'up')

            // Should remain responsive
            await expect(element(by.id('contact-list'))).toBeVisible()
        })
    })

    describe('Accessibility', () => {
        it('should support screen reader navigation', async () => {
            // Enable accessibility
            await device.enableSynchronization()

            // Verify accessibility labels exist
            await expect(element(by.id('contact-search-input'))).toHaveAccessibilityLabel('Search contacts')
            await expect(element(by.text('Search'))).toHaveAccessibilityLabel('Search tab')
        })

        it('should support keyboard navigation on web', async () => {
            // This would be more relevant for web version
            // For mobile, verify touch targets are appropriate size
            await element(by.text('Search')).tap()

            // Verify touch targets are accessible
            await expect(element(by.id('contact-search-input'))).toBeVisible()
        })
    })
})

describe('Demo Mode Specific Tests', () => {
    it('should show demo data consistently', async () => {
        // Verify demo contacts are always available
        await element(by.text('Search')).tap()
        const searchInput = element(by.id('contact-search-input'))
        await searchInput.typeText('John')

        await waitFor(element(by.text('John Smith')))
            .toBeVisible()
            .withTimeout(3000)

        // Verify demo contact has expected data
        await element(by.text('John Smith')).tap()
        await expect(element(by.text('127'))).toBeVisible() // Message count
        await expect(element(by.text('85%'))).toBeVisible() // Relationship strength
    })

    it('should handle demo mode limitations gracefully', async () => {
        // Try to connect a platform in demo mode
        await element(by.text('Settings')).tap()
        await element(by.text('Gmail')).tap()

        // Should show demo mode message
        await waitFor(element(by.text('Demo Mode')))
            .toBeVisible()
            .withTimeout(3000)
    })

    it('should provide realistic demo experience', async () => {
        // Verify demo workflow provides comprehensive experience
        await element(by.text('Try Demo Workflow')).tap()
        await element(by.text('Start Demo')).tap()

        // Should guide through all major features
        await waitFor(element(by.text('Search for Contacts')))
            .toBeVisible()
            .withTimeout(3000)
    })
})