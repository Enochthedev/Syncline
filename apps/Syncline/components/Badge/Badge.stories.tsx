import React from 'react';
import { View } from 'react-native';
import { Badge } from './Badge';

export default {
    title: 'UI/Badge',
    component: Badge,
    decorators: [
        (Story: any) => (
            <View style={{ padding: 16, flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                <Story />
            </View>
        ),
    ],
};

export const Primary = {
    args: {
        children: 'Primary',
        variant: 'primary',
    },
};

export const Success = {
    args: {
        children: 'Success',
        variant: 'success',
    },
};

export const Warning = {
    args: {
        children: 'Warning',
        variant: 'warning',
    },
};

export const Error = {
    args: {
        children: 'Error',
        variant: 'error',
    },
};

export const AllVariants = () => (
    <View style={{ gap: 12 }}>
        <Badge variant="primary">Primary</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="warning">Warning</Badge>
        <Badge variant="error">Error</Badge>
        <Badge variant="info">Info</Badge>
        <Badge variant="secondary">Secondary</Badge>
    </View>
);

export const Sizes = () => (
    <View style={{ gap: 12 }}>
        <Badge size="sm">Small</Badge>
        <Badge size="md">Medium</Badge>
        <Badge size="lg">Large</Badge>
    </View>
);
