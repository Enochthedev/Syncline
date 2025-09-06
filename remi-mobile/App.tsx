import React, { useEffect, useState } from 'react'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { NavigationContainer } from '@react-navigation/native'
import { AppNavigator } from '@/navigation/AppNavigator'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { SyncProvider } from '@/contexts/SyncContext'
import { NotificationProvider } from '@/contexts/NotificationContext'
import { PerformanceProvider } from '@/contexts/PerformanceContext'
import PerformanceConfig from '@/utils/performanceConfig'
import NetworkOptimizer from '@/services/networkOptimizer'

// Create a client with performance-optimized settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors except 408, 429
        if (error?.status >= 400 && error?.status < 500) {
          return error?.status === 408 || error?.status === 429
        }
        return failureCount < 3
      },
      networkMode: 'offlineFirst',
    },
    mutations: {
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors except 408, 429
        if (error?.status >= 400 && error?.status < 500) {
          return error?.status === 408 || error?.status === 429
        }
        return failureCount < 2
      },
      networkMode: 'offlineFirst',
    },
  },
})

// Initialize network optimizer
const networkOptimizer = NetworkOptimizer.getInstance(queryClient)

export default function App() {
  const [isPerformanceInitialized, setIsPerformanceInitialized] = useState(false)

  useEffect(() => {
    const initializePerformance = async () => {
      try {
        // Initialize performance configuration
        const performanceConfig = PerformanceConfig.getInstance()
        await performanceConfig.initialize()
        
        console.log('Performance optimization initialized')
        setIsPerformanceInitialized(true)
      } catch (error) {
        console.error('Failed to initialize performance optimization:', error)
        // Continue without performance optimization
        setIsPerformanceInitialized(true)
      }
    }

    initializePerformance()
  }, [])

  if (!isPerformanceInitialized) {
    // Show loading screen while performance is being initialized
    return null // You could show a splash screen here
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <PerformanceProvider>
            <ThemeProvider>
              <AuthProvider>
                <SyncProvider>
                  <NotificationProvider>
                    <NavigationContainer>
                      <AppNavigator />
                      <StatusBar style="auto" />
                    </NavigationContainer>
                  </NotificationProvider>
                </SyncProvider>
              </AuthProvider>
            </ThemeProvider>
          </PerformanceProvider>
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}