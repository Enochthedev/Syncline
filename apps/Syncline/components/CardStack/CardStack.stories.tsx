import React from 'react';
import { View, Text } from 'react-native';
import { CardStack } from './CardStack';
import { LinearGradient } from 'expo-linear-gradient';
import { theme } from '../../src/theme';

export default {
    title: 'UI/CardStack',
    component: CardStack,
    decorators: [
        (Story: any) => (
            <View style={{ padding: 16, flex: 1, backgroundColor: theme.colors.backgroundSecondary }}>
                <Story />
            </View>
        ),
    ],
};

const sampleCards = [
    {
        id: '1',
        title: 'Favorites',
        subtitle: '12 records',
        gradient: ['#8B5CF6', '#6D28D9'],
        content: (
            <LinearGradient
                colors={['#8B5CF6', '#6D28D9']}
                style={{ flex: 1, padding: 24, justifyContent: 'center' }}
            >
                <Text style={{ fontSize: 24, fontWeight: 'bold', color: 'white' }}>FAVORITES</Text>
                <Text style={{ fontSize: 16, color: 'rgba(255,255,255,0.8)', marginTop: 8 }}>
                    12 RECORDS • 5.5 HOURS
                </Text>
            </LinearGradient>
        ),
    },
    {
        id: '2',
        title: 'Recent',
        subtitle: '8 records',
        gradient: ['#EF4444', '#DC2626'],
        content: (
            <LinearGradient
                colors={['#EF4444', '#DC2626']}
                style={{ flex: 1, padding: 24, justifyContent: 'center' }}
            >
                <Text style={{ fontSize: 24, fontWeight: 'bold', color: 'white' }}>RECENT</Text>
                <Text style={{ fontSize: 16, color: 'rgba(255,255,255,0.8)', marginTop: 8 }}>
                    8 RECORDS • 3.2 HOURS
                </Text>
            </LinearGradient>
        ),
    },
    {
        id: '3',
        title: 'Popular',
        subtitle: '20 records',
        gradient: ['#10B981', '#059669'],
        content: (
            <LinearGradient
                colors={['#10B981', '#059669']}
                style={{ flex: 1, padding: 24, justifyContent: 'center' }}
            >
                <Text style={{ fontSize: 24, fontWeight: 'bold', color: 'white' }}>POPULAR</Text>
                <Text style={{ fontSize: 16, color: 'rgba(255,255,255,0.8)', marginTop: 8 }}>
                    20 RECORDS • 8.7 HOURS
                </Text>
            </LinearGradient>
        ),
    },
];

export const Default = {
    args: {
        cards: sampleCards,
        onCardPress: (id: string) => console.log('Card pressed:', id),
    },
};

export const MessagingStack = () => {
    const messagingCards = [
        {
            id: 'gmail',
            title: 'Gmail',
            content: (
                <LinearGradient
                    colors={['#EA4335', '#C5221F']}
                    style={{ flex: 1, padding: 24 }}
                >
                    <Text style={{ fontSize: 20, fontWeight: '600', color: 'white' }}>Gmail</Text>
                    <Text style={{ fontSize: 48, fontWeight: 'bold', color: 'white', marginTop: 20 }}>
                        24
                    </Text>
                    <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
                        Unread messages
                    </Text>
                </LinearGradient>
            ),
        },
        {
            id: 'slack',
            title: 'Slack',
            content: (
                <LinearGradient
                    colors={['#4A154B', '#611f69']}
                    style={{ flex: 1, padding: 24 }}
                >
                    <Text style={{ fontSize: 20, fontWeight: '600', color: 'white' }}>Slack</Text>
                    <Text style={{ fontSize: 48, fontWeight: 'bold', color: 'white', marginTop: 20 }}>
                        12
                    </Text>
                    <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
                        Unread channels
                    </Text>
                </LinearGradient>
            ),
        },
        {
            id: 'discord',
            title: 'Discord',
            content: (
                <LinearGradient
                    colors={['#5865F2', '#404EBC']}
                    style={{ flex: 1, padding: 24 }}
                >
                    <Text style={{ fontSize: 20, fontWeight: '600', color: 'white' }}>Discord</Text>
                    <Text style={{ fontSize: 48, fontWeight: 'bold', color: 'white', marginTop: 20 }}>
                        8
                    </Text>
                    <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)' }}>
                        Unread servers
                    </Text>
                </LinearGradient>
            ),
        },
    ];

    return <CardStack cards={messagingCards} />;
};
