import React from 'react'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { createStackNavigator } from '@react-navigation/stack'
import Icon from 'react-native-vector-icons/Ionicons'
import { TabParamList, RootStackParamList } from '@/types'
import { useTheme } from '@/hooks/useTheme'

// Screens
import { DashboardScreen } from '@/screens/DashboardScreen'
import { SearchScreen } from '@/screens/SearchScreen'
import { ContactsScreen } from '@/screens/ContactsScreen'
import { MessagesScreen } from '@/screens/MessagesScreen'
import { SettingsScreen } from '@/screens/SettingsScreen'
import { ContactProfileScreen } from '@/screens/ContactProfileScreen'
import { MessageThreadScreen } from '@/screens/MessageThreadScreen'
import { ResponsiveUIDemoScreen } from '@/screens/ResponsiveUIDemo'
import { DemoWorkflowScreen } from '@/screens/DemoWorkflowScreen'
import { PlatformConnectionsScreen } from '@/screens/PlatformConnectionsScreen'

const Tab = createBottomTabNavigator<TabParamList>()
const Stack = createStackNavigator<RootStackParamList>()

function TabNavigator() {
  const { colors } = useTheme()

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string

          switch (route.name) {
            case 'Dashboard':
              iconName = focused ? 'home' : 'home-outline'
              break
            case 'Search':
              iconName = focused ? 'search' : 'search-outline'
              break
            case 'Contacts':
              iconName = focused ? 'people' : 'people-outline'
              break
            case 'Messages':
              iconName = focused ? 'chatbubbles' : 'chatbubbles-outline'
              break
            case 'Settings':
              iconName = focused ? 'settings' : 'settings-outline'
              break
            default:
              iconName = 'circle'
          }

          return <Icon name={iconName} size={size} color={color} />
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
        },
        headerStyle: {
          backgroundColor: colors.surface,
        },
        headerTintColor: colors.text,
        headerTitleStyle: {
          fontWeight: '600',
        },
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardScreen}
        options={{ title: 'Dashboard' }}
      />
      <Tab.Screen 
        name="Search" 
        component={SearchScreen}
        options={{ title: 'Search' }}
      />
      <Tab.Screen 
        name="Contacts" 
        component={ContactsScreen}
        options={{ title: 'Contacts' }}
      />
      <Tab.Screen 
        name="Messages" 
        component={MessagesScreen}
        options={{ title: 'Messages' }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
    </Tab.Navigator>
  )
}

export function MainNavigator() {
  const { colors } = useTheme()

  return (
    <Stack.Navigator
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
        name="MainTabs" 
        component={TabNavigator}
        options={{ headerShown: false }}
      />
      <Stack.Screen 
        name="ContactProfile" 
        component={ContactProfileScreen}
        options={({ route }) => ({ 
          title: 'Contact Profile',
          headerBackTitleVisible: false,
        })}
      />
      <Stack.Screen 
        name="MessageThread" 
        component={MessageThreadScreen}
        options={({ route }) => ({ 
          title: 'Messages',
          headerBackTitleVisible: false,
        })}
      />
      <Stack.Screen 
        name="ResponsiveUIDemo" 
        component={ResponsiveUIDemoScreen}
        options={{ 
          title: 'Responsive UI Demo',
          headerBackTitleVisible: false,
        }}
      />
      <Stack.Screen 
        name="DemoWorkflow" 
        component={DemoWorkflowScreen}
        options={{ 
          title: 'Demo Workflow',
          headerShown: false,
        }}
      />
      <Stack.Screen 
        name="PlatformConnections" 
        component={PlatformConnectionsScreen}
        options={{ 
          title: 'Platform Connections',
          headerBackTitleVisible: false,
        }}
      />
    </Stack.Navigator>
  )
}