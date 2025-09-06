import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { UnifiedContact } from '@/types'

interface ContactsState {
    contacts: UnifiedContact[]
    selectedContact: UnifiedContact | null
    isLoading: boolean
    error: string | null
    searchQuery: string
    filters: {
        platforms: string[]
        lastInteraction: 'all' | 'today' | 'week' | 'month'
        relationshipStrength: 'all' | 'high' | 'medium' | 'low'
    }
}

const initialState: ContactsState = {
    contacts: [],
    selectedContact: null,
    isLoading: false,
    error: null,
    searchQuery: '',
    filters: {
        platforms: [],
        lastInteraction: 'all',
        relationshipStrength: 'all',
    },
}

const contactsSlice = createSlice({
    name: 'contacts',
    initialState,
    reducers: {
        setContacts: (state, action: PayloadAction<UnifiedContact[]>) => {
            state.contacts = action.payload
            state.isLoading = false
            state.error = null
        },
        addContact: (state, action: PayloadAction<UnifiedContact>) => {
            const existingIndex = state.contacts.findIndex(c => c.id === action.payload.id)
            if (existingIndex >= 0) {
                state.contacts[existingIndex] = action.payload
            } else {
                state.contacts.push(action.payload)
            }
        },
        updateContact: (state, action: PayloadAction<UnifiedContact>) => {
            const index = state.contacts.findIndex(c => c.id === action.payload.id)
            if (index >= 0) {
                state.contacts[index] = action.payload
            }
            if (state.selectedContact?.id === action.payload.id) {
                state.selectedContact = action.payload
            }
        },
        removeContact: (state, action: PayloadAction<string>) => {
            state.contacts = state.contacts.filter(c => c.id !== action.payload)
            if (state.selectedContact?.id === action.payload) {
                state.selectedContact = null
            }
        },
        setSelectedContact: (state, action: PayloadAction<UnifiedContact | null>) => {
            state.selectedContact = action.payload
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.isLoading = action.payload
        },
        setError: (state, action: PayloadAction<string | null>) => {
            state.error = action.payload
            state.isLoading = false
        },
        setSearchQuery: (state, action: PayloadAction<string>) => {
            state.searchQuery = action.payload
        },
        setFilters: (state, action: PayloadAction<Partial<ContactsState['filters']>>) => {
            state.filters = { ...state.filters, ...action.payload }
        },
        clearFilters: (state) => {
            state.filters = initialState.filters
            state.searchQuery = ''
        },
    },
})

export const {
    setContacts,
    addContact,
    updateContact,
    removeContact,
    setSelectedContact,
    setLoading,
    setError,
    setSearchQuery,
    setFilters,
    clearFilters,
} = contactsSlice.actions

export default contactsSlice.reducer