/**
 * Test setup configuration for React Native tests
 */

import 'react-native-gesture-handler/jestSetup';

// Mock React Native modules
jest.mock('react-native-reanimated', () => {
    const Reanimated = require('react-native-reanimated/mock');
    Reanimated.default.call = () => { };
    return Reanimated;
});

// Mock React Native Keychain
jest.mock('react-native-keychain', () => ({
    setInternetCredentials: jest.fn(() => Promise.resolve()),
    getInternetCredentials: jest.fn(() => Promise.resolve({ password: '{}' })),
    resetInternetCredentials: jest.fn(() => Promise.resolve()),
}));

// Mock React Native Biometrics
jest.mock('react-native-biometrics', () => ({
    __esModule: true,
    default: jest.fn().mockImplementation(() => ({
        isSensorAvailable: jest.fn(() => Promise.resolve({ available: true, biometryType: 'TouchID' })),
        createKeys: jest.fn(() => Promise.resolve({ success: true })),
        createSignature: jest.fn(() => Promise.resolve({ success: true, signature: 'mock-signature' })),
        deleteKeys: jest.fn(() => Promise.resolve({ success: true })),
    })),
}));

// Mock React Native Device Info
jest.mock('react-native-device-info', () => ({
    getUniqueId: jest.fn(() => Promise.resolve('mock-device-id')),
    getDeviceName: jest.fn(() => Promise.resolve('Mock Device')),
    getSystemName: jest.fn(() => Promise.resolve('iOS')),
    getSystemVersion: jest.fn(() => Promise.resolve('15.0')),
    getVersion: jest.fn(() => '1.0.0'),
}));

// Mock React Native NetInfo
jest.mock('@react-native-community/netinfo', () => ({
    fetch: jest.fn(() => Promise.resolve({ isConnected: true, type: 'wifi' })),
    addEventListener: jest.fn(() => jest.fn()),
}));

// Mock React Native Vector Icons
jest.mock('react-native-vector-icons/MaterialIcons', () => 'Icon');
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');

// Mock React Navigation
jest.mock('@react-navigation/native', () => ({
    useNavigation: () => ({
        navigate: jest.fn(),
        goBack: jest.fn(),
        dispatch: jest.fn(),
    }),
    useRoute: () => ({
        params: {},
    }),
    useFocusEffect: jest.fn(),
}));

// Mock React Native Safe Area Context
jest.mock('react-native-safe-area-context', () => ({
    SafeAreaProvider: ({ children }: any) => children,
    SafeAreaView: ({ children }: any) => children,
    useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
}));

// Global test utilities
global.__DEV__ = true;

// Silence console warnings in tests
const originalWarn = console.warn;
const originalError = console.error;

beforeEach(() => {
    console.warn = jest.fn();
    console.error = jest.fn();
});

afterEach(() => {
    console.warn = originalWarn;
    console.error = originalError;
});

// Mock timers for testing
jest.useFakeTimers();