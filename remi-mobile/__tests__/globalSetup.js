/**
 * Global Jest Setup
 * Runs once before all tests
 */

module.exports = async () => {
    // Set test environment variables
    process.env.NODE_ENV = 'test';
    process.env.REACT_NATIVE_TEST = 'true';

    // Mock console methods to reduce noise
    global.console = {
        ...console,
        // Keep error and warn for debugging
        log: jest.fn(),
        debug: jest.fn(),
        info: jest.fn(),
    };

    // Set up global test utilities
    global.testUtils = {
        mockApiResponse: (data, status = 200) => ({
            ok: status >= 200 && status < 300,
            status,
            json: () => Promise.resolve(data),
            text: () => Promise.resolve(JSON.stringify(data)),
        }),

        createMockContact: (overrides = {}) => ({
            id: 'test-contact-1',
            name: 'John Doe',
            email: 'john@example.com',
            platforms: ['email'],
            lastInteraction: new Date().toISOString(),
            ...overrides,
        }),

        createMockMessage: (overrides = {}) => ({
            id: 'test-message-1',
            content: 'Test message content',
            sender: 'John Doe',
            timestamp: new Date().toISOString(),
            platform: 'email',
            ...overrides,
        }),

        waitFor: (condition, timeout = 5000) => {
            return new Promise((resolve, reject) => {
                const startTime = Date.now();
                const check = () => {
                    if (condition()) {
                        resolve(true);
                    } else if (Date.now() - startTime > timeout) {
                        reject(new Error('Timeout waiting for condition'));
                    } else {
                        setTimeout(check, 100);
                    }
                };
                check();
            });
        },
    };

    console.log('🧪 Global test setup completed');
};