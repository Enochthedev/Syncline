// API Configuration and Endpoints for R.E.M.I Mobile App

export const API_CONFIG = {
    baseURL: process.env.API_BASE_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    }
};

export const WS_CONFIG = {
    url: process.env.WS_URL || 'ws://localhost:8000/ws',
    reconnectInterval: 5000,
    maxReconnectAttempts: 10
};

// Core API Endpoints
export const API_ENDPOINTS = {
    // Authentication
    AUTH: {
        LOGIN: '/api/v1/auth/login',
        REFRESH: '/api/v1/auth/refresh',
        LOGOUT: '/api/v1/auth/logout',
        REGISTER: '/api/v1/auth/register',
        FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
        RESET_PASSWORD: '/api/v1/auth/reset-password',
    },

    // Contact-based search (PRIMARY FEATURE)
    SEARCH: {
        MESSAGES: '/api/v1/search/',
        CONTACTS: '/api/v1/participants/',
        COMMITMENTS: '/api/v1/search/commitments',
        FILES: '/api/v1/search/files',
        SUGGESTIONS: '/api/v1/search/suggestions',
        NATURAL_LANGUAGE: '/api/v1/search/natural-language',
    },

    // Contact auto-search (NEW FEATURE)
    CONTACT_SEARCH: {
        REALTIME: '/api/v1/contacts/search/realtime',
        NATURAL_LANGUAGE: '/api/v1/contacts/search/natural-language',
        MESSAGES: '/api/v1/contacts/search/{contactId}/messages',
        SHARED_CONTENT: '/api/v1/contacts/search/{contactId}/shared-content',
        SUGGESTIONS: '/api/v1/contacts/search/suggestions/{query}',
        HEALTH: '/api/v1/contacts/search/health',
        EXAMPLES: '/api/v1/contacts/search/test/natural-language',
    },

    // Contact management
    CONTACTS: {
        LIST: '/api/v1/participants/',
        DETAIL: '/api/v1/participants/{id}',
        DOSSIER: '/api/v1/contacts/dossiers/{id}',
        MERGE: '/api/v1/contacts/merge',
        INSIGHTS: '/api/v1/contacts/{id}/insights',
        ANALYTICS: '/api/v1/contacts/{id}/analytics',
        EXPORT: '/api/v1/contacts/{id}/export',
    },

    // Messages and threads
    MESSAGES: {
        LIST: '/api/v1/messages/',
        DETAIL: '/api/v1/messages/{id}',
        THREADS: '/api/v1/threads/',
        THREAD_DETAIL: '/api/v1/threads/{id}',
        THREAD_MESSAGES: '/api/v1/threads/{id}/messages',
    },

    // Platform connections
    PLATFORMS: {
        LIST: '/api/v1/platforms/',
        CONNECT: '/api/v1/platforms/{platform}/connect',
        STATUS: '/api/v1/platforms/{platform}/status',
        DISCONNECT: '/api/v1/platforms/{platform}',
        SYNC: '/api/v1/platforms/{platform}/sync',
    },

    // Insights and notifications
    INSIGHTS: {
        LIST: '/api/v1/insights/',
        PROACTIVE: '/api/v1/insights/proactive',
        MARK_READ: '/api/v1/insights/{id}/read',
        FEEDBACK: '/api/v1/insights/{id}/feedback',
    },

    // User preferences and settings
    USER: {
        PROFILE: '/api/v1/user/profile',
        PREFERENCES: '/api/v1/user/preferences',
        NOTIFICATIONS: '/api/v1/user/notifications',
        PRIVACY: '/api/v1/user/privacy',
    },

    // Real-time WebSocket
    WEBSOCKET: '/ws',

    // Health and monitoring
    HEALTH: '/api/v1/health',
    STATUS: '/api/v1/status',
} as const;

// Platform identifiers
export const PLATFORMS = {
    GMAIL: 'gmail',
    SLACK: 'slack',
    DISCORD: 'discord',
    WHATSAPP: 'whatsapp',
    TWITTER: 'twitter',
    LINKEDIN: 'linkedin',
    TELEGRAM: 'telegram',
} as const;

// Search configuration
export const SEARCH_CONFIG = {
    DEBOUNCE_DELAY: 300,
    MIN_QUERY_LENGTH: 2,
    MAX_SUGGESTIONS: 10,
    DEFAULT_LIMIT: 20,
    MAX_LIMIT: 100,
} as const;

// Cache configuration
export const CACHE_CONFIG = {
    CONTACT_TTL: 5 * 60 * 1000, // 5 minutes
    SEARCH_TTL: 2 * 60 * 1000, // 2 minutes
    MESSAGE_TTL: 10 * 60 * 1000, // 10 minutes
    MAX_CACHE_SIZE: 50 * 1024 * 1024, // 50MB
} as const;

// Error codes
export const ERROR_CODES = {
    NETWORK_ERROR: 'NETWORK_ERROR',
    TIMEOUT_ERROR: 'TIMEOUT_ERROR',
    AUTH_ERROR: 'AUTH_ERROR',
    VALIDATION_ERROR: 'VALIDATION_ERROR',
    NOT_FOUND: 'NOT_FOUND',
    SERVER_ERROR: 'SERVER_ERROR',
    RATE_LIMITED: 'RATE_LIMITED',
} as const;