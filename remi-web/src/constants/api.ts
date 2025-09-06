// API Configuration and Endpoints for R.E.M.I Web App

export const API_CONFIG = {
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    }
};

export const WS_CONFIG = {
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
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
        ADVANCED: '/api/v1/search/advanced',
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
        RELATIONSHIP_MAP: '/api/v1/contacts/{id}/relationships',
    },

    // Messages and threads
    MESSAGES: {
        LIST: '/api/v1/messages/',
        DETAIL: '/api/v1/messages/{id}',
        THREADS: '/api/v1/threads/',
        THREAD_DETAIL: '/api/v1/threads/{id}',
        THREAD_MESSAGES: '/api/v1/threads/{id}/messages',
        THREAD_SUMMARY: '/api/v1/threads/{id}/summary',
    },

    // Platform connections
    PLATFORMS: {
        LIST: '/api/v1/platforms/',
        CONNECT: '/api/v1/platforms/{platform}/connect',
        STATUS: '/api/v1/platforms/{platform}/status',
        DISCONNECT: '/api/v1/platforms/{platform}',
        SYNC: '/api/v1/platforms/{platform}/sync',
        HEALTH: '/api/v1/platforms/{platform}/health',
    },

    // Insights and notifications
    INSIGHTS: {
        LIST: '/api/v1/insights/',
        PROACTIVE: '/api/v1/insights/proactive',
        MARK_READ: '/api/v1/insights/{id}/read',
        FEEDBACK: '/api/v1/insights/{id}/feedback',
        ANALYTICS: '/api/v1/insights/analytics',
    },

    // User preferences and settings
    USER: {
        PROFILE: '/api/v1/user/profile',
        PREFERENCES: '/api/v1/user/preferences',
        NOTIFICATIONS: '/api/v1/user/notifications',
        PRIVACY: '/api/v1/user/privacy',
        EXPORT_DATA: '/api/v1/user/export',
        DELETE_ACCOUNT: '/api/v1/user/delete',
    },

    // Analytics and reporting
    ANALYTICS: {
        DASHBOARD: '/api/v1/analytics/dashboard',
        COMMUNICATION_PATTERNS: '/api/v1/analytics/communication-patterns',
        RELATIONSHIP_INSIGHTS: '/api/v1/analytics/relationship-insights',
        PLATFORM_USAGE: '/api/v1/analytics/platform-usage',
        EXPORT_REPORT: '/api/v1/analytics/export',
    },

    // Real-time WebSocket
    WEBSOCKET: '/ws',

    // Health and monitoring
    HEALTH: '/api/v1/health',
    STATUS: '/api/v1/status',
    METRICS: '/api/v1/metrics',
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
    FACEBOOK: 'facebook',
    INSTAGRAM: 'instagram',
} as const;

// Search configuration
export const SEARCH_CONFIG = {
    DEBOUNCE_DELAY: 300,
    MIN_QUERY_LENGTH: 2,
    MAX_SUGGESTIONS: 20,
    DEFAULT_LIMIT: 50,
    MAX_LIMIT: 500,
    FACET_LIMIT: 10,
} as const;

// Cache configuration
export const CACHE_CONFIG = {
    CONTACT_TTL: 5 * 60 * 1000, // 5 minutes
    SEARCH_TTL: 2 * 60 * 1000, // 2 minutes
    MESSAGE_TTL: 10 * 60 * 1000, // 10 minutes
    ANALYTICS_TTL: 30 * 60 * 1000, // 30 minutes
    MAX_CACHE_SIZE: 100 * 1024 * 1024, // 100MB
    INDEXEDDB_VERSION: 1,
} as const;

// PWA configuration
export const PWA_CONFIG = {
    CACHE_NAME: 'remi-web-v1',
    OFFLINE_URL: '/offline',
    INSTALL_PROMPT_DELAY: 3000,
    UPDATE_CHECK_INTERVAL: 60000, // 1 minute
} as const;

// WebSocket message types
export const WS_MESSAGE_TYPES = {
    CONTACT_UPDATE: 'contact_update',
    MESSAGE_RECEIVED: 'message_received',
    THREAD_UPDATE: 'thread_update',
    INSIGHT_NOTIFICATION: 'insight_notification',
    PLATFORM_STATUS: 'platform_status',
    SYNC_STATUS: 'sync_status',
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
    OFFLINE_ERROR: 'OFFLINE_ERROR',
    STORAGE_ERROR: 'STORAGE_ERROR',
} as const;

// Keyboard shortcuts
export const KEYBOARD_SHORTCUTS = {
    SEARCH: 'cmd+k,ctrl+k',
    NEW_MESSAGE: 'cmd+n,ctrl+n',
    SETTINGS: 'cmd+comma,ctrl+comma',
    HELP: 'cmd+shift+slash,ctrl+shift+slash',
    TOGGLE_SIDEBAR: 'cmd+b,ctrl+b',
    FOCUS_SEARCH: 'cmd+f,ctrl+f',
} as const;

// Feature flags
export const FEATURE_FLAGS = {
    VOICE_SEARCH: process.env.REACT_APP_VOICE_SEARCH_ENABLED === 'true',
    ADVANCED_SEARCH: process.env.REACT_APP_ADVANCED_SEARCH_ENABLED === 'true',
    REAL_TIME_SYNC: process.env.REACT_APP_REAL_TIME_SYNC_ENABLED === 'true',
    ANALYTICS: process.env.REACT_APP_ANALYTICS_ENABLED === 'true',
    PWA_FEATURES: process.env.REACT_APP_PWA_ENABLED === 'true',
    OFFLINE_MODE: process.env.REACT_APP_OFFLINE_ENABLED === 'true',
} as const;