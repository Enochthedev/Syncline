import React from 'react';
import { View, Text } from 'react-native';
import { GlassCard } from './GlassCard';
import { theme } from '../../src/theme';

export default {
    title: 'UI/GlassCard',
    component: GlassCard,
    decorators: [
        (Story: any) => (
            <View style={{
                padding: 16,
                flex: 1,
                backgroundColor: '#8B5CF6',
                justifyContent: 'center',
            }}>
                <Story />
            </View>
        ),
    ],
};

export const LightGlass = {
    args: {
        variant: 'light',
        intensity: 80,
        children: (
            <View>
                <Text style={{ fontSize: 24, fontWeight: 'bold', color: theme.colors.text }}>
                    Account Balance
                </Text>
                <Text style={{ fontSize: 48, fontWeight: 'bold', color: theme.colors.text, marginTop: 16 }}>
                    $1,560.00
                </Text>
                <Text style={{ fontSize: 14, color: theme.colors.textSecondary, marginTop: 8 }}>
                    Available balance
                </Text>
            </View>
        ),
    },
};

export const DarkGlass = {
    args: {
        variant: 'dark',
        intensity: 60,
        children: (
            <View>
                <Text style={{ fontSize: 20, fontWeight: '600', color: 'white' }}>
                    STQ 2 Account
                </Text>
                <Text style={{ fontSize: 36, fontWeight: 'bold', color: 'white', marginTop: 12 }}>
                    429,200.00 STQ
                </Text>
                <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 8 }}>
                    $2.72
                </Text>
            </View>
        ),
    },
};

export const GradientGlass = {
    args: {
        gradient: ['#0EA5E9', '#0284C7'],
        intensity: 40,
        children: (
            <View>
                <Text style={{ fontSize: 20, fontWeight: '600', color: 'white' }}>
                    Premium Account
                </Text>
                <Text style={{ fontSize: 36, fontWeight: 'bold', color: 'white', marginTop: 12 }}>
                    ✨ Active
                </Text>
                <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.9)', marginTop: 8 }}>
                    Valid until Dec 2025
                </Text>
            </View>
        ),
    },
};
