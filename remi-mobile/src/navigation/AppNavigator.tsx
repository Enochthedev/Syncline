import React from 'react'
import { createStackNavigator } from '@react-navigation/stack'
import { useAuth } from '@/hooks/useAuth'
import { AuthNavigator } from './AuthNavigator'
import { MainNavigator } from './MainNavigator'
import { RootStackParamList } from '@/types'
import { LoadingScreen } from '@/screens/LoadingScreen'

const Stack = createStackNavigator<RootStackParamList>()

export function AppNavigator() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {isAuthenticated ? (
        <Stack.Screen name="Main" component={MainNavigator} />
      ) : (
        <Stack.Screen name="Auth" component={AuthNavigator} />
      )}
    </Stack.Navigator>
  )
}