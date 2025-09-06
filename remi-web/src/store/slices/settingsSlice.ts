import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface NotificationSettings {
    enabled: boolean
    proactiveInsights: boolean
    commitmentReminders: boolean
    relationshipOpportunities: boolean
    quietHours: {
        enabled: boolean
        start: string // HH:MM format
        end: string // HH:MM format
    }
}

interface PrivacySettings {
    piiRedaction: boolean
    dataMinimization: boolean
    analyticsOptOut: boolean
    shareUsageData: boolean
}

interface SyncSettings {
    realTimeSync: boolean
    backgroundSync: boolean
    syncFrequency: 'immediate' | 'hourly' | 'daily'
    platforms: Record<string, boolean>
}

interface UISettings {
    theme: 'light' | 'dark' | 'system'
    language: string
    timezone: string
    dateFormat: string
    compactMode: boolean
    showPlatformIcons: boolean
}

interface SettingsState {
    notifications: NotificationSettings
    privacy: PrivacySettings
    sync: SyncSettings
    ui: UISettings
    isLoading: boolean
    error: string | null
}

const initialState: SettingsState = {
    notifications: {
        enabled: true,
        proactiveInsights: true,
        commitmentReminders: true,
        relationshipOpportunities: true,
        quietHours: {
            enabled: false,
            start: '22:00',
            end: '08:00',
        },
    },
    privacy: {
        piiRedaction: true,
        dataMinimization: true,
        analyticsOptOut: false,
        shareUsageData: false,
    },
    sync: {
        realTimeSync: true,
        backgroundSync: true,
        syncFrequency: 'immediate',
        platforms: {},
    },
    ui: {
        theme: 'system',
        language: 'en',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        dateFormat: 'MM/dd/yyyy',
        compactMode: false,
        showPlatformIcons: true,
    },
    isLoading: false,
    error: null,
}

const settingsSlice = createSlice({
    name: 'settings',
    initialState,
    reducers: {
        updateNotificationSettings: (state, action: PayloadAction<Partial<NotificationSettings>>) => {
            state.notifications = { ...state.notifications, ...action.payload }
        },
        updatePrivacySettings: (state, action: PayloadAction<Partial<PrivacySettings>>) => {
            state.privacy = { ...state.privacy, ...action.payload }
        },
        updateSyncSettings: (state, action: PayloadAction<Partial<SyncSettings>>) => {
            state.sync = { ...state.sync, ...action.payload }
        },
        updateUISettings: (state, action: PayloadAction<Partial<UISettings>>) => {
            state.ui = { ...state.ui, ...action.payload }
        },
        setPlatformSync: (state, action: PayloadAction<{ platform: string; enabled: boolean }>) => {
            state.sync.platforms[action.payload.platform] = action.payload.enabled
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.isLoading = action.payload
        },
        setError: (state, action: PayloadAction<string | null>) => {
            state.error = action.payload
            state.isLoading = false
        },
        resetSettings: () => initialState,
    },
})

export const {
    updateNotificationSettings,
    updatePrivacySettings,
    updateSyncSettings,
    updateUISettings,
    setPlatformSync,
    setLoading,
    setError,
    resetSettings,
} = settingsSlice.actions

export default settingsSlice.reducer