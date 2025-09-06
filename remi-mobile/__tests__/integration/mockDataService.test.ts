/**
 * Integration Tests for Mock Data Service
 * 
 * Tests the mock data service functionality for demo mode
 */

import { mockDataService } from '@/services/mockDataService'
import { UnifiedContact, SearchResult, ProactiveInsight } from '@/types'

describe('MockDataService Integration Tests', () => {
    beforeEach(() => {
        // Reset service state if needed
        jest.clearAllMocks()
    })

    describe('Contact Search Functionality', () => {
        it('should return contacts for valid search queries', async () => {
            const results = await mockDataService.searchContacts('John')

            expect(results).toBeDefined()
            expect(Array.isArray(results)).toBe(true)
            expect(results.length).toBeGreaterThan(0)

            const johnContact = results.find(c => c.primaryName.includes('John'))
            expect(johnContact).toBeDefined()
            expect(johnContact?.primaryName).toBe('John Smith')
        })

        it('should support fuzzy matching', async () => {
            // Test with typos
            const results = await mockDataService.searchContacts('Jon Smth')

            expect(results.length).toBeGreaterThan(0)
            const johnContact = results.find(c => c.primaryName.includes('John'))
            expect(johnContact).toBeDefined()
        })

        it('should search by email addresses', async () => {
            const results = await mockDataService.searchContacts('john.smith@company.com')

            expect(results.length).toBeGreaterThan(0)
            const contact = results[0]
            expect(contact.emails).toContain('john.smith@company.com')
        })

        it('should search by phone numbers', async () => {
            const results = await mockDataService.searchContacts('+1-555-0123')

            expect(results.length).toBeGreaterThan(0)
            const contact = results[0]
            expect(contact.phoneNumbers).toContain('+1-555-0123')
        })

        it('should search by platform handles', async () => {
            const results = await mockDataService.searchContacts('jsmith')

            expect(results.length).toBeGreaterThan(0)
            const contact = results[0]
            const slackIdentity = contact.identities.find(i => i.platform === 'slack')
            expect(slackIdentity?.handle).toBe('jsmith')
        })

        it('should return empty array for short queries', async () => {
            const results = await mockDataService.searchContacts('J')
            expect(results).toEqual([])
        })

        it('should return empty array for no matches', async () => {
            const results = await mockDataService.searchContacts('NonExistentContact')
            expect(results).toEqual([])
        })
    })

    describe('Contact Retrieval', () => {
        it('should retrieve specific contact by ID', async () => {
            const contact = await mockDataService.getContact('contact-1')

            expect(contact).toBeDefined()
            expect(contact?.id).toBe('contact-1')
            expect(contact?.primaryName).toBe('John Smith')
        })

        it('should return null for non-existent contact ID', async () => {
            const contact = await mockDataService.getContact('non-existent-id')
            expect(contact).toBeNull()
        })

        it('should retrieve all contacts', async () => {
            const contacts = await mockDataService.getContacts()

            expect(Array.isArray(contacts)).toBe(true)
            expect(contacts.length).toBeGreaterThan(0)

            // Verify expected contacts exist
            const contactNames = contacts.map(c => c.primaryName)
            expect(contactNames).toContain('John Smith')
            expect(contactNames).toContain('Sarah Johnson')
            expect(contactNames).toContain('Mike Chen')
        })
    })

    describe('Message and Thread Functionality', () => {
        it('should retrieve threads for a contact', async () => {
            const threads = await mockDataService.getThreadsForContact('contact-1')

            expect(Array.isArray(threads)).toBe(true)
            expect(threads.length).toBeGreaterThan(0)

            const thread = threads[0]
            expect(thread.participants.some(p => p.id === 'contact-1')).toBe(true)
        })

        it('should retrieve messages for a thread', async () => {
            const threads = await mockDataService.getThreadsForContact('contact-1')
            const threadId = threads[0].id

            const messages = await mockDataService.getMessagesForThread(threadId)

            expect(Array.isArray(messages)).toBe(true)
            expect(messages.length).toBeGreaterThan(0)

            messages.forEach(message => {
                expect(message.threadId).toBe(threadId)
            })
        })

        it('should search messages globally', async () => {
            const results = await mockDataService.searchMessages('project')

            expect(Array.isArray(results)).toBe(true)
            expect(results.length).toBeGreaterThan(0)

            results.forEach(result => {
                expect(result.type).toBe('message')
                expect(result.content?.toLowerCase()).toContain('project')
            })
        })

        it('should search messages for specific contact', async () => {
            const results = await mockDataService.searchMessages('project', 'contact-1')

            expect(Array.isArray(results)).toBe(true)

            // All results should be related to contact-1
            results.forEach(result => {
                expect(result.contact?.id).toBe('contact-1')
            })
        })

        it('should return empty results for no message matches', async () => {
            const results = await mockDataService.searchMessages('nonexistentterm')
            expect(results).toEqual([])
        })
    })

    describe('Proactive Insights', () => {
        it('should return proactive insights', async () => {
            const insights = await mockDataService.getProactiveInsights()

            expect(Array.isArray(insights)).toBe(true)
            expect(insights.length).toBeGreaterThan(0)

            insights.forEach(insight => {
                expect(insight).toHaveProperty('id')
                expect(insight).toHaveProperty('type')
                expect(insight).toHaveProperty('title')
                expect(insight).toHaveProperty('description')
                expect(insight).toHaveProperty('priority')
                expect(insight).toHaveProperty('relatedContacts')
                expect(insight).toHaveProperty('suggestedActions')
            })
        })

        it('should include different types of insights', async () => {
            const insights = await mockDataService.getProactiveInsights()

            const insightTypes = insights.map(i => i.type)
            expect(insightTypes.length).toBeGreaterThan(1)

            // Should have variety of insight types
            const uniqueTypes = new Set(insightTypes)
            expect(uniqueTypes.size).toBeGreaterThan(1)
        })
    })

    describe('Contact Suggestions', () => {
        it('should return contact suggestions for partial queries', async () => {
            const suggestions = await mockDataService.getContactSuggestions('John')

            expect(Array.isArray(suggestions)).toBe(true)
            expect(suggestions.length).toBeGreaterThan(0)
            expect(suggestions).toContain('John Smith')
        })

        it('should return email suggestions', async () => {
            const suggestions = await mockDataService.getContactSuggestions('john.smith')

            expect(Array.isArray(suggestions)).toBe(true)
            expect(suggestions.some(s => s.includes('@company.com'))).toBe(true)
        })

        it('should limit suggestion count', async () => {
            const suggestions = await mockDataService.getContactSuggestions('a')

            expect(suggestions.length).toBeLessThanOrEqual(5)
        })

        it('should return empty array for empty query', async () => {
            const suggestions = await mockDataService.getContactSuggestions('')
            expect(suggestions).toEqual([])
        })
    })

    describe('Data Consistency', () => {
        it('should maintain consistent contact data across calls', async () => {
            const contact1 = await mockDataService.getContact('contact-1')
            const contact2 = await mockDataService.getContact('contact-1')

            expect(contact1).toEqual(contact2)
        })

        it('should have valid relationship data', async () => {
            const contacts = await mockDataService.getContacts()

            contacts.forEach(contact => {
                // Verify relationship strength is valid
                expect(contact.relationshipStrength).toBeGreaterThanOrEqual(0)
                expect(contact.relationshipStrength).toBeLessThanOrEqual(1)

                // Verify communication frequency is valid
                expect(['high', 'medium', 'low']).toContain(contact.communicationFrequency)

                // Verify dates are valid
                expect(contact.lastInteraction).toBeInstanceOf(Date)
                expect(contact.createdAt).toBeInstanceOf(Date)
                expect(contact.updatedAt).toBeInstanceOf(Date)
            })
        })

        it('should have valid platform identities', async () => {
            const contacts = await mockDataService.getContacts()

            contacts.forEach(contact => {
                contact.identities.forEach(identity => {
                    expect(identity).toHaveProperty('platform')
                    expect(identity).toHaveProperty('platformUserId')
                    expect(identity).toHaveProperty('displayName')
                    expect(typeof identity.verified).toBe('boolean')
                })
            })
        })

        it('should have consistent thread and message relationships', async () => {
            const contacts = await mockDataService.getContacts()

            for (const contact of contacts) {
                const threads = await mockDataService.getThreadsForContact(contact.id)

                for (const thread of threads) {
                    const messages = await mockDataService.getMessagesForThread(thread.id)

                    messages.forEach(message => {
                        expect(message.threadId).toBe(thread.id)

                        // Message should involve the contact
                        const isFromContact = message.sender.id === contact.id
                        const isToContact = message.recipients.some(r => r.id === contact.id)
                        expect(isFromContact || isToContact).toBe(true)
                    })
                }
            }
        })
    })

    describe('Performance and Reliability', () => {
        it('should handle concurrent requests', async () => {
            const promises = [
                mockDataService.searchContacts('John'),
                mockDataService.searchContacts('Sarah'),
                mockDataService.searchContacts('Mike'),
                mockDataService.getContacts(),
                mockDataService.getProactiveInsights(),
            ]

            const results = await Promise.all(promises)

            expect(results).toHaveLength(5)
            results.forEach(result => {
                expect(result).toBeDefined()
            })
        })

        it('should simulate realistic API delays', async () => {
            const startTime = Date.now()
            await mockDataService.searchContacts('John')
            const endTime = Date.now()

            const duration = endTime - startTime
            expect(duration).toBeGreaterThan(100) // Should have some delay
            expect(duration).toBeLessThan(1000) // But not too long for tests
        })

        it('should handle edge cases gracefully', async () => {
            // Test with special characters
            const results1 = await mockDataService.searchContacts('@#$%')
            expect(results1).toEqual([])

            // Test with very long strings
            const longString = 'a'.repeat(1000)
            const results2 = await mockDataService.searchContacts(longString)
            expect(results2).toEqual([])

            // Test with null/undefined (should be handled by TypeScript, but just in case)
            const results3 = await mockDataService.searchContacts('')
            expect(results3).toEqual([])
        })
    })

    describe('Mock Data Quality', () => {
        it('should have realistic contact data', async () => {
            const contacts = await mockDataService.getContacts()

            contacts.forEach(contact => {
                // Should have realistic names
                expect(contact.primaryName).toMatch(/^[A-Za-z\s]+$/)

                // Should have valid email formats
                contact.emails.forEach(email => {
                    expect(email).toMatch(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)
                })

                // Should have valid phone formats
                contact.phoneNumbers.forEach(phone => {
                    expect(phone).toMatch(/^\+?[\d\s\-\(\)]+$/)
                })

                // Should have reasonable message counts
                expect(contact.totalMessages).toBeGreaterThan(0)
                expect(contact.totalMessages).toBeLessThan(1000)
            })
        })

        it('should have realistic message content', async () => {
            const results = await mockDataService.searchMessages('')

            results.forEach(result => {
                expect(result.content).toBeDefined()
                expect(result.content!.length).toBeGreaterThan(10)
                expect(result.content!.length).toBeLessThan(500)

                // Should have realistic timestamps
                expect(result.timestamp).toBeInstanceOf(Date)
                expect(result.timestamp.getTime()).toBeLessThan(Date.now())
            })
        })

        it('should have diverse platform representation', async () => {
            const contacts = await mockDataService.getContacts()

            const allPlatforms = new Set<string>()
            contacts.forEach(contact => {
                contact.platforms.forEach(platform => {
                    allPlatforms.add(platform)
                })
            })

            expect(allPlatforms.size).toBeGreaterThan(1)
            expect(allPlatforms.has('gmail')).toBe(true)
        })
    })
})