import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { SearchResult, SearchFilters, QueryIntent } from '@/types'

interface SearchState {
    query: string
    results: SearchResult[]
    isLoading: boolean
    error: string | null
    totalCount: number
    processingTime: number
    suggestions: string[]
    recentSearches: string[]
    savedSearches: Array<{
        id: string
        name: string
        query: string
        filters?: SearchFilters
    }>
    filters: SearchFilters
    intent: QueryIntent | null
    hasMore: boolean
    page: number
}

const initialState: SearchState = {
    query: '',
    results: [],
    isLoading: false,
    error: null,
    totalCount: 0,
    processingTime: 0,
    suggestions: [],
    recentSearches: [],
    savedSearches: [],
    filters: {},
    intent: null,
    hasMore: false,
    page: 1,
}

const searchSlice = createSlice({
    name: 'search',
    initialState,
    reducers: {
        setQuery: (state, action: PayloadAction<string>) => {
            state.query = action.payload
        },
        searchStart: (state) => {
            state.isLoading = true
            state.error = null
        },
        searchSuccess: (state, action: PayloadAction<{
            results: SearchResult[]
            totalCount: number
            processingTime: number
            suggestions?: string[]
            hasMore: boolean
            page: number
        }>) => {
            state.isLoading = false
            state.results = action.payload.page === 1
                ? action.payload.results
                : [...state.results, ...action.payload.results]
            state.totalCount = action.payload.totalCount
            state.processingTime = action.payload.processingTime
            state.suggestions = action.payload.suggestions || []
            state.hasMore = action.payload.hasMore
            state.page = action.payload.page
            state.error = null
        },
        searchFailure: (state, action: PayloadAction<string>) => {
            state.isLoading = false
            state.error = action.payload
        },
        clearResults: (state) => {
            state.results = []
            state.totalCount = 0
            state.processingTime = 0
            state.suggestions = []
            state.hasMore = false
            state.page = 1
            state.error = null
        },
        setFilters: (state, action: PayloadAction<SearchFilters>) => {
            state.filters = action.payload
        },
        clearFilters: (state) => {
            state.filters = {}
        },
        setIntent: (state, action: PayloadAction<QueryIntent | null>) => {
            state.intent = action.payload
        },
        addRecentSearch: (state, action: PayloadAction<string>) => {
            const query = action.payload.trim()
            if (query && !state.recentSearches.includes(query)) {
                state.recentSearches = [query, ...state.recentSearches.slice(0, 9)]
            }
        },
        removeRecentSearch: (state, action: PayloadAction<string>) => {
            state.recentSearches = state.recentSearches.filter(q => q !== action.payload)
        },
        clearRecentSearches: (state) => {
            state.recentSearches = []
        },
        addSavedSearch: (state, action: PayloadAction<{
            name: string
            query: string
            filters?: SearchFilters
        }>) => {
            const savedSearch = {
                id: Date.now().toString(),
                ...action.payload,
            }
            state.savedSearches.push(savedSearch)
        },
        removeSavedSearch: (state, action: PayloadAction<string>) => {
            state.savedSearches = state.savedSearches.filter(s => s.id !== action.payload)
        },
        setSuggestions: (state, action: PayloadAction<string[]>) => {
            state.suggestions = action.payload
        },
    },
})

export const {
    setQuery,
    searchStart,
    searchSuccess,
    searchFailure,
    clearResults,
    setFilters,
    clearFilters,
    setIntent,
    addRecentSearch,
    removeRecentSearch,
    clearRecentSearches,
    addSavedSearch,
    removeSavedSearch,
    setSuggestions,
} = searchSlice.actions

export default searchSlice.reducer