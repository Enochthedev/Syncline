import React, { createContext, useContext, useState, useEffect } from 'react'
import { useColorScheme } from 'react-native'
import AsyncStorage from '@react-native-async-storage/async-storage'

type ThemeMode = 'light' | 'dark' | 'system'

interface Colors {
  primary: string
  primaryDark: string
  secondary: string
  background: string
  surface: string
  text: string
  textSecondary: string
  border: string
  error: string
  success: string
  warning: string
}

const lightColors: Colors = {
  primary: '#3b82f6',
  primaryDark: '#1d4ed8',
  secondary: '#64748b',
  background: '#ffffff',
  surface: '#f8fafc',
  text: '#0f172a',
  textSecondary: '#64748b',
  border: '#e2e8f0',
  error: '#ef4444',
  success: '#22c55e',
  warning: '#f59e0b',
}

const darkColors: Colors = {
  primary: '#60a5fa',
  primaryDark: '#3b82f6',
  secondary: '#94a3b8',
  background: '#0f172a',
  surface: '#1e293b',
  text: '#f8fafc',
  textSecondary: '#94a3b8',
  border: '#334155',
  error: '#f87171',
  success: '#4ade80',
  warning: '#fbbf24',
}

interface ThemeContextType {
  mode: ThemeMode
  colors: Colors
  isDark: boolean
  setTheme: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemColorScheme = useColorScheme()
  const [mode, setMode] = useState<ThemeMode>('system')

  useEffect(() => {
    loadTheme()
  }, [])

  const loadTheme = async () => {
    try {
      const savedTheme = await AsyncStorage.getItem('theme_mode')
      if (savedTheme && ['light', 'dark', 'system'].includes(savedTheme)) {
        setMode(savedTheme as ThemeMode)
      }
    } catch (error) {
      console.error('Error loading theme:', error)
    }
  }

  const setTheme = async (newMode: ThemeMode) => {
    try {
      setMode(newMode)
      await AsyncStorage.setItem('theme_mode', newMode)
    } catch (error) {
      console.error('Error saving theme:', error)
    }
  }

  const isDark = mode === 'dark' || (mode === 'system' && systemColorScheme === 'dark')
  const colors = isDark ? darkColors : lightColors

  const value: ThemeContextType = {
    mode,
    colors,
    isDark,
    setTheme,
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}