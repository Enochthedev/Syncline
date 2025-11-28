import React from 'react';
import { View } from 'react-native';
import { PlatformCard } from './PlatformCard';

export default {
    title: 'Connections/PlatformCard',
    component: PlatformCard,
    decorators: [
        (Story: any) => (
            <View style={{ padding: 16, flex: 1, backgroundColor: '#f5f5f5' }}>
                <Story />
            </View>
        ),
    ],
};

export const Disconnected = {
    args: {
        platform: 'gmail',
        onConnect: () => console.log('Connect pressed'),
        onDisconnect: () => console.log('Disconnect pressed'),
    },
};

export const Connected = {
    args: {
        platform: 'slack',
        connection: {
            id: '123',
            platform: 'slack',
            status: 'active',
            connected_at: '2025-11-28T10:00:00Z',
        },
        onConnect: () => console.log('Connect pressed'),
        onDisconnect: () => console.log('Disconnect pressed'),
    },
};

export const AllPlatforms = () => (
    <View>
        <PlatformCard platform="gmail" onConnect={() => { }} onDisconnect={() => { }} />
        <PlatformCard platform="slack" onConnect={() => { }} onDisconnect={() => { }} />
        <PlatformCard platform="discord" onConnect={() => { }} onDisconnect={() => { }} />
        <PlatformCard platform="telegram" onConnect={() => { }} onDisconnect={() => { }} />
        <PlatformCard platform="twitter" onConnect={() => { }} onDisconnect={() => { }} />
        <PlatformCard platform="whatsapp" onConnect={() => { }} onDisconnect={() => { }} />
    </View>
);
