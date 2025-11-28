import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import React from 'react';
import { Platform, View } from 'react-native';
import { theme } from '../../src/theme';

// Separate component to avoid "Cannot call a class as a function" issues
const TabIcon = ({ name, color }: { name: keyof typeof Ionicons.glyphMap; color: string }) => (
    <View style={{ alignItems: 'center', justifyContent: 'center', width: 30, height: 30 }}>
        <Ionicons name={name} size={24} color={color} />
    </View>
);

export default function TabLayout() {
    return (
        <Tabs
            screenOptions={{
                headerShown: true,
                tabBarActiveTintColor: theme.colors.primary,
                tabBarInactiveTintColor: theme.colors.textSecondary,
                tabBarStyle: Platform.select({
                    ios: {
                        height: 85,
                        paddingBottom: 20,
                    },
                    default: {
                        height: 60,
                        paddingBottom: 10,
                    },
                }),
                headerStyle: {
                    backgroundColor: theme.colors.background,
                },
                headerTitleStyle: {
                    fontWeight: 'bold',
                    fontSize: 18,
                },
            }}>
            <Tabs.Screen
                name="index"
                options={{
                    title: 'Home',
                    tabBarLabel: 'Home',
                    tabBarIcon: ({ color }) => <TabIcon name="home" color={color} />,
                }}
            />
            <Tabs.Screen
                name="messages"
                options={{
                    title: 'Messages',
                    tabBarLabel: 'Messages',
                    tabBarIcon: ({ color }) => <TabIcon name="chatbubbles" color={color} />,
                }}
            />
            <Tabs.Screen
                name="search"
                options={{
                    title: 'Search',
                    tabBarLabel: 'Search',
                    tabBarIcon: ({ color }) => <TabIcon name="search" color={color} />,
                }}
            />

            {/* Hidden Tabs */}
            <Tabs.Screen
                name="connections"
                options={{
                    title: 'Connections',
                    href: null,
                }}
            />
            <Tabs.Screen
                name="settings"
                options={{
                    title: 'Settings',
                    href: null,
                }}
            />
        </Tabs>
    );
}
