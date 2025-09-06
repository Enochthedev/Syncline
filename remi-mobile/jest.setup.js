/**
 * Jest Setup File
 * 
 * Global mocks and setup for React Native testing
 */

import '@testing-library/jest-native/extend-expect';

// Mock React Native modules
jest.mock('react-native', () => {
    const RN = jest.requireActual('react-native');

    // Mock problematic modules
    RN.NativeModules = {
        ...RN.NativeModules,
        SettingsManager: {
            settings: {},
            setValues: jest.fn(),
            getConstants: jest.fn(() => ({})),
        },
        PlatformConstants: {
            getConstants: jest.fn(() => ({
                forceTouchAvailable: false,
                osVersion: '14.0',
                systemName: 'iOS',
            })),
        },
    };

    // Mock TurboModuleRegistry
    RN.TurboModuleRegistry = {
        getEnforcing: jest.fn(() => ({
            getConstants: jest.fn(() => ({})),
        })),
        get: jest.fn(() => null),
    };

    // Mock Dimensions
    RN.Dimensions = {
        get: jest.fn(() => ({ width: 375, height: 812 })),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
    };

    return RN;
});

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage', () => ({
    getItem: jest.fn(() => Promise.resolve(null)),
    setItem: jest.fn(() => Promise.resolve()),
    removeItem: jest.fn(() => Promise.resolve()),
    clear: jest.fn(() => Promise.resolve()),
    getAllKeys: jest.fn(() => Promise.resolve([])),
    multiGet: jest.fn(() => Promise.resolve([])),
    multiSet: jest.fn(() => Promise.resolve()),
    multiRemove: jest.fn(() => Promise.resolve()),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/Ionicons', () => 'Icon');

// Mock react-native-biometrics
jest.mock('react-native-biometrics', () => ({
    isSensorAvailable: jest.fn(() => Promise.resolve({ available: false })),
    createKeys: jest.fn(() => Promise.resolve()),
    biometricKeysExist: jest.fn(() => Promise.resolve({ keysExist: false })),
    createSignature: jest.fn(() => Promise.resolve()),
    simplePrompt: jest.fn(() => Promise.resolve({ success: true })),
}));

// Mock react-native-device-info
jest.mock('react-native-device-info', () => ({
    getUniqueId: jest.fn(() => Promise.resolve('test-device-id')),
    getSystemName: jest.fn(() => 'iOS'),
    getSystemVersion: jest.fn(() => '14.0'),
    getModel: jest.fn(() => 'iPhone'),
    getBrand: jest.fn(() => 'Apple'),
    getDeviceName: jest.fn(() => Promise.resolve('Test Device')),
    getVersion: jest.fn(() => '1.0.0'),
}));

// Mock react-native-keychain
jest.mock('react-native-keychain', () => ({
    setInternetCredentials: jest.fn(() => Promise.resolve()),
    getInternetCredentials: jest.fn(() => Promise.resolve({ password: '{}' })),
    resetInternetCredentials: jest.fn(() => Promise.resolve()),
}));

// Mock @react-native-community/netinfo
jest.mock('@react-native-community/netinfo', () => ({
    fetch: jest.fn(() => Promise.resolve({ isConnected: true, type: 'wifi' })),
    addEventListener: jest.fn(() => jest.fn()),
}));

// Mock @tanstack/react-query
jest.mock('@tanstack/react-query', () => {
    const actualReactQuery = jest.requireActual('@tanstack/react-query');
    return {
        ...actualReactQuery,
        useQuery: jest.fn(() => ({
            data: null,
            isLoading: false,
            error: null,
            refetch: jest.fn(),
            isSuccess: false,
            isError: false,
            isFetching: false,
        })),
        useMutation: jest.fn(() => ({
            mutate: jest.fn(),
            isLoading: false,
            error: null,
            isPending: false,
        })),
        useInfiniteQuery: jest.fn(() => ({
            data: null,
            isLoading: false,
            error: null,
            refetch: jest.fn(),
            fetchNextPage: jest.fn(),
            hasNextPage: false,
        })),
        QueryClient: actualReactQuery.QueryClient,
        QueryClientProvider: actualReactQuery.QueryClientProvider,
    };
});

// Mock react-native-safe-area-context
jest.mock('react-native-safe-area-context', () => ({
    SafeAreaProvider: ({ children }) => children,
    SafeAreaView: ({ children }) => children,
    useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
}));

// Mock react-native-gesture-handler
jest.mock('react-native-gesture-handler', () => ({
    GestureHandlerRootView: ({ children }) => children,
    PanGestureHandler: ({ children }) => children,
    State: {},
}));

// Mock @react-navigation
jest.mock('@react-navigation/native', () => ({
    NavigationContainer: ({ children }) => children,
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

jest.mock('@react-navigation/bottom-tabs', () => ({
    createBottomTabNavigator: () => ({
        Navigator: ({ children }) => children,
        Screen: ({ children }) => children,
    }),
}));

jest.mock('@react-navigation/stack', () => ({
    createStackNavigator: () => ({
        Navigator: ({ children }) => children,
        Screen: ({ children }) => children,
    }),
}));

// Mock console methods to reduce noise in tests
global.console = {
    ...console,
    warn: jest.fn(),
    error: jest.fn(),
    log: jest.fn(),
};

// Mock fetch
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(''),
    })
);

// Mock timers
jest.useFakeTimers();

// Setup test environment
beforeEach(() => {
    jest.clearAllMocks();
});