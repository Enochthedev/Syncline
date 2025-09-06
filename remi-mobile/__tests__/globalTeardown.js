/**
 * Global Jest Teardown
 * Runs once after all tests
 */

module.exports = async () => {
    // Clean up global mocks
    if (global.testUtils) {
        delete global.testUtils;
    }

    // Clean up any remaining timers
    jest.clearAllTimers();

    console.log('🧹 Global test teardown completed');
};