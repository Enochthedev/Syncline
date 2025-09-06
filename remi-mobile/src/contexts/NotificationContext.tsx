import React, { createContext, useContext, useState, useEffect } from 'react'
import { Platform, PermissionsAndroid } from 'react-native'
import messaging from '@react-native-firebase/messaging'
import { notificationService } from '@/services/notificationService'

interface NotificationState {
  hasPermission: boolean
  token: string | null
  isLoading: boolean
}

interface NotificationContextType extends NotificationState {
  requestPermission: () => Promise<boolean>
  registerForNotifications: () => Promise<void>
}

const initialState: NotificationState = {
  hasPermission: false,
  token: null,
  isLoading: true,
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<NotificationState>(initialState)

  useEffect(() => {
    checkPermission()
  }, [])

  const checkPermission = async () => {
    try {
      const authStatus = await messaging().hasPermission()
      const enabled = authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
                     authStatus === messaging.AuthorizationStatus.PROVISIONAL

      setState(prev => ({ ...prev, hasPermission: enabled, isLoading: false }))

      if (enabled) {
        await getToken()
      }
    } catch (error) {
      console.error('Error checking notification permission:', error)
      setState(prev => ({ ...prev, isLoading: false }))
    }
  }

  const requestPermission = async (): Promise<boolean> => {
    try {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS
        )
        if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
          return false
        }
      }

      const authStatus = await messaging().requestPermission()
      const enabled = authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
                     authStatus === messaging.AuthorizationStatus.PROVISIONAL

      setState(prev => ({ ...prev, hasPermission: enabled }))

      if (enabled) {
        await getToken()
      }

      return enabled
    } catch (error) {
      console.error('Error requesting notification permission:', error)
      return false
    }
  }

  const getToken = async () => {
    try {
      const token = await messaging().getToken()
      setState(prev => ({ ...prev, token }))
      return token
    } catch (error) {
      console.error('Error getting FCM token:', error)
      return null
    }
  }

  const registerForNotifications = async () => {
    if (!state.hasPermission) {
      const granted = await requestPermission()
      if (!granted) return
    }

    const token = await getToken()
    if (token) {
      await notificationService.registerToken(token)
    }
  }

  const value: NotificationContextType = {
    ...state,
    requestPermission,
    registerForNotifications,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}