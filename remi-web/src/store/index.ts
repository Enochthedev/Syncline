import { configureStore } from '@reduxjs/toolkit'
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux'
import authSlice from './slices/authSlice'
import contactsSlice from './slices/contactsSlice'
import searchSlice from './slices/searchSlice'
import settingsSlice from './slices/settingsSlice'

export const store = configureStore({
    reducer: {
        auth: authSlice,
        contacts: contactsSlice,
        search: searchSlice,
        settings: settingsSlice,
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: {
                ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
            },
        }),
    devTools: process.env.NODE_ENV !== 'production',
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector