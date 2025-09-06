/**
 * Jest Configuration for React Native
 * Comprehensive testing setup with high coverage requirements
 */

module.exports = {
    preset: 'react-native',
    setupFilesAfterEnv: [
        '<rootDir>/jest.setup.js',
        '<rootDir>/__tests__/setup.ts'
    ],

    // Transform configuration for React Native modules
    transformIgnorePatterns: [
        'node_modules/(?!(react-native|@react-native|react-native-vector-icons|react-native-reanimated|@react-navigation|@react-native-community|@react-native-firebase|@tanstack|react-native-biometrics|react-native-keychain|react-native-device-info|jail-monkey)/)'
    ],

    // Coverage configuration with high requirements
    collectCoverageFrom: [
        'src/**/*.{js,jsx,ts,tsx}',
        '!src/**/*.d.ts',
        '!src/**/*.stories.{js,jsx,ts,tsx}',
        '!src/**/index.{js,jsx,ts,tsx}',
        '!src/**/__tests__/**',
        '!src/**/__mocks__/**',
        '!src/**/types.ts',
        '!src/**/constants.ts'
    ],

    // High coverage thresholds
    coverageThreshold: {
        global: {
            branches: 85,
            functions: 90,
            lines: 90,
            statements: 90
        },
        // Critical components require higher coverage
        './src/services/': {
            branches: 90,
            functions: 95,
            lines: 95,
            statements: 95
        },
        './src/components/': {
            branches: 85,
            functions: 90,
            lines: 90,
            statements: 90
        },
        './src/hooks/': {
            branches: 90,
            functions: 95,
            lines: 95,
            statements: 95
        }
    },

    // Coverage reporting
    coverageReporters: [
        'text',
        'text-summary',
        'html',
        'lcov',
        'json-summary'
    ],

    coverageDirectory: '<rootDir>/coverage',

    // Module name mapping for path aliases
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
        '^@components/(.*)$': '<rootDir>/src/components/$1',
        '^@services/(.*)$': '<rootDir>/src/services/$1',
        '^@hooks/(.*)$': '<rootDir>/src/hooks/$1',
        '^@utils/(.*)$': '<rootDir>/src/utils/$1',
        '^@types/(.*)$': '<rootDir>/src/types/$1',
        '^@constants/(.*)$': '<rootDir>/src/constants/$1',
        '^@contexts/(.*)$': '<rootDir>/src/contexts/$1',
        '^@screens/(.*)$': '<rootDir>/src/screens/$1',
        '^@navigation/(.*)$': '<rootDir>/src/navigation/$1'
    },

    // Test environment configuration
    testEnvironment: 'jsdom',

    // Test file patterns
    testMatch: [
        '<rootDir>/__tests__/**/*.test.{js,jsx,ts,tsx}',
        '<rootDir>/src/**/__tests__/**/*.test.{js,jsx,ts,tsx}'
    ],

    // Test timeout for async operations
    testTimeout: 10000,

    // Verbose output for debugging
    verbose: true,

    // Clear mocks between tests
    clearMocks: true,

    // Restore mocks after each test
    restoreMocks: true,

    // Error handling
    errorOnDeprecated: true,

    // Performance monitoring
    maxWorkers: '50%',

    // Cache configuration
    cacheDirectory: '<rootDir>/node_modules/.cache/jest',

    // Global setup and teardown
    globalSetup: '<rootDir>/__tests__/globalSetup.js',
    globalTeardown: '<rootDir>/__tests__/globalTeardown.js',

    // Custom reporters for CI/CD
    reporters: [
        'default',
        ['jest-junit', {
            outputDirectory: '<rootDir>/test-results',
            outputName: 'junit.xml',
            classNameTemplate: '{classname}',
            titleTemplate: '{title}',
            ancestorSeparator: ' › ',
            usePathForSuiteName: true
        }]
    ]
};