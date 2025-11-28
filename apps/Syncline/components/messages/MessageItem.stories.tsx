import React from 'react';
import { View } from 'react-native';
import { MessageItem } from './MessageItem';

export default {
    title: 'Messages/MessageItem',
    component: MessageItem,
    decorators: [
        (Story: any) => (
            <View style={{ flex: 1, backgroundColor: '#f5f5f5' }}>
                <Story />
            </View>
        ),
    ],
};

const mockMessage = {
    id: '1',
    platform: 'slack' as const,
    content: 'Hey team, can we review the Q4 roadmap tomorrow?',
    sender: 'Alice Johnson',
    timestamp: new Date().toISOString(),
    has_attachments: false,
};

export const Default = {
    args: {
        message: mockMessage,
        onPress: () => console.log('Message pressed'),
    },
};

export const WithAttachment = {
    args: {
        message: {
            ...mockMessage,
            platform: 'gmail' as const,
            content: 'Please find attached the financial report for November.',
            has_attachments: true,
        },
        onPress: () => console.log('Message pressed'),
    },
};

export const LongContent = {
    args: {
        message: {
            ...mockMessage,
            platform: 'discord' as const,
            content: 'I was looking into the bug report #123 and it seems like we have a race condition in the websocket handler. I have pushed a fix to the branch fix/websocket-race-condition. Can someone review it?',
        },
        onPress: () => console.log('Message pressed'),
    },
};
