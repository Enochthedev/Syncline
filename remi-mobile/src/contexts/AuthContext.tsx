import React, { createContext, useContext, useReducer, useEffect } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { authService } from '@/services/authService'

interface User {
  id: string
  email: string
  name: string
  avatar?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_USER'; payload: { user: User; token: string } }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'CLEAR_ERROR' }

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
}

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }
    case 'SET_USER':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      }
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
      }
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        error: null,
      }
    case 'CLEAR_ERROR':
      return { ...state, error: null }
    default:
      return state
  }
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  useEffect(() => {
    checkAuthState()
  }, [])

  const checkAuthState = async () => {
    try {
      const token = await AsyncStorage.getItem('auth_token')
      const userData = await AsyncStorage.getItem('user_data')

      if (token && userData) {
        const user = JSON.parse(userData)
        dispatch({ type: 'SET_USER', payload: { user, token } })
      } else {
        dispatch({ type: 'SET_LOADING', payload: false })
      }
    } catch (error) {
      console.error('Error checking auth state:', error)
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }

  const login = async (email: string, password: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true })
      const response = await authService.login(email, password)
      
      await AsyncStorage.setItem('auth_token', response.token)
      await AsyncStorage.setItem('user_data', JSON.stringify(response.user))
      
      dispatch({ type: 'SET_USER', payload: response })
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Login failed' })
    }
  }

  const register = async (email: string, password: string, name: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true })
      const response = await authService.register(email, password, name)
      
      await AsyncStorage.setItem('auth_token', response.token)
      await AsyncStorage.setItem('user_data', JSON.stringify(response.user))
      
      dispatch({ type: 'SET_USER', payload: response })
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Registration failed' })
    }
  }

  const logout = async () => {
    try {
      await AsyncStorage.removeItem('auth_token')
      await AsyncStorage.removeItem('user_data')
      dispatch({ type: 'LOGOUT' })
    } catch (error) {
      console.error('Error during logout:', error)
    }
  }

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' })
  }

  const value: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}