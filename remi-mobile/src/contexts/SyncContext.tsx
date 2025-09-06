import React, { createContext, useContext, useState, useEffect } from 'react'
import NetInfo from '@react-native-netinfo'
import { syncService } from '@/services/syncService'

interface SyncState {
  isOnline: boolean
  isSyncing: boolean
  lastSyncTime: Date | null
  pendingActions: number
  error: string | null
}

interface SyncContextType extends SyncState {
  sync: () => Promise<void>
  clearError: () => void
}

const initialState: SyncState = {
  isOnline: true,
  isSyncing: false,
  lastSyncTime: null,
  pendingActions: 0,
  error: null,
}

const SyncContext = createContext<SyncContextType | undefined>(undefined)

export function SyncProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SyncState>(initialState)

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setState(prev => ({ ...prev, isOnline: state.isConnected ?? false }))
    })

    return unsubscribe
  }, [])

  const sync = async () => {
    if (!state.isOnline) return

    try {
      setState(prev => ({ ...prev, isSyncing: true, error: null }))
      await syncService.performSync()
      setState(prev => ({ 
        ...prev, 
        isSyncing: false, 
        lastSyncTime: new Date(),
        pendingActions: 0
      }))
    } catch (error: any) {
      setState(prev => ({ 
        ...prev, 
        isSyncing: false, 
        error: error.message || 'Sync failed' 
      }))
    }
  }

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }))
  }

  const value: SyncContextType = {
    ...state,
    sync,
    clearError,
  }

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>
}

export function useSync() {
  const context = useContext(SyncContext)
  if (context === undefined) {
    throw new Error('useSync must be used within a SyncProvider')
  }
  return context
}