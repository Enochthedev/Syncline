import '@testing-library/jest-dom'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
    constructor() { }
    disconnect() { }
    observe() { }
    unobserve() { }
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
    constructor() { }
    disconnect() { }
    observe() { }
    unobserve() { }
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), // deprecated
        removeListener: jest.fn(), // deprecated
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
})

// Mock localStorage
const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
}
global.sessionStorage = sessionStorageMock

// Mock fetch
global.fetch = jest.fn()

// Mock WebSocket
global.WebSocket = class WebSocket {
    constructor(url) {
        this.url = url
        this.readyState = WebSocket.CONNECTING
    }

    static CONNECTING = 0
    static OPEN = 1
    static CLOSING = 2
    static CLOSED = 3

    close() {
        this.readyState = WebSocket.CLOSED
    }

    send() { }

    addEventListener() { }
    removeEventListener() { }
}

// Mock navigator
Object.defineProperty(navigator, 'serviceWorker', {
    value: {
        register: jest.fn(() => Promise.resolve()),
        ready: Promise.resolve({
            unregister: jest.fn(() => Promise.resolve()),
        }),
    },
})

// Mock Notification API
global.Notification = {
    permission: 'default',
    requestPermission: jest.fn(() => Promise.resolve('granted')),
}

// Mock IndexedDB
const indexedDBMock = {
    open: jest.fn(() => ({
        result: {
            createObjectStore: jest.fn(),
            transaction: jest.fn(() => ({
                objectStore: jest.fn(() => ({
                    add: jest.fn(),
                    get: jest.fn(),
                    put: jest.fn(),
                    delete: jest.fn(),
                    clear: jest.fn(),
                })),
            })),
        },
        onsuccess: null,
        onerror: null,
    })),
}
global.indexedDB = indexedDBMock

// Suppress console warnings in tests
const originalWarn = console.warn
beforeAll(() => {
    console.warn = (...args) => {
        if (
            typeof args[0] === 'string' &&
            args[0].includes('componentWillReceiveProps') ||
            args[0].includes('componentWillUpdate')
        ) {
            return
        }
        originalWarn.call(console, ...args)
    }
})

afterAll(() => {
    console.warn = originalWarn
})