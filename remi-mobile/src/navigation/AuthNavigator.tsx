import React from 'react'
import { createStackNavigator } from '@react-navigation/stack'
import { LoginScreen } from '@/screens/auth/LoginScreen'
import { RegisterScreen } from '@/screens/auth/RegisterScreen'
import { ForgotPasswordScreen } from '@/screens/auth/ForgotPasswordScreen'
import { OnboardingScreen } from '@/screens/auth/OnboardingScreen'
import { useTheme } from '@/hooks/useTheme'

type AuthStackParamList = {
  Onboarding: undefined
  Login: undefined
  Register: undefined
  ForgotPassword: undefined
}

const Stack = createStackNavigator<AuthStackParamList>()

export function AuthNavigator() {
  const { colors } = useTheme()

  return (
    <Stack.Navigator
      initialRouteName="Onboarding"
      screenOptions={{
        headerStyle: {
          backgroundColor: colors.surface,
        },
        headerTintColor: colors.text,
        headerTitleStyle: {
          fontWeight: '600',
        },
      }}
    >
      <Stack.Screen 
        name="Onboarding" 
        component={OnboardingScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen 
        name="Login" 
        component={LoginScreen}
        options={{ title: 'Sign In' }}
      />
      <Stack.Screen 
        name="Register" 
        component={RegisterScreen}
        options={{ title: 'Create Account' }}
      />
      <Stack.Screen 
        name="ForgotPassword" 
        component={ForgotPasswordScreen}
        options={{ title: 'Reset Password' }}
      />
    </Stack.Navigator>
  )
}