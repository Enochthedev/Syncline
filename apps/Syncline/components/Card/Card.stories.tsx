import React from 'react';
import { View, Text } from 'react-native';
import { Card } from './Card';
import { theme } from '../../src/theme';

export default {
    title: 'UI/Card',
    component: Card,
    decorators: [
        (Story: any) => (
            <View style={{ padding: 16, flex: 1, backgroundColor: theme.colors.backgroundSecondary }}>
                <Story />
            </View>
        ),
    ],
};

export const Elevated = {
    args: {
        children: (
            <View>
                <Text style={theme.typography.h3}>Elevated Card</Text>
                <Text style={theme.typography.bodySmall}>This card has a shadow</Text>
            </View>
        ),
    },
};

export const Outlined = {
    args: {
        variant: 'outlined',
        children: (
            <View>
                <Text style={theme.typography.h3}>Outlined Card</Text>
                <Text style={theme.typography.bodySmall}>This card has a border</Text>
            </View>
        ),
    },
};

export const Flat = {
    args: {
        variant: 'flat',
        children: (
            <View>
                <Text style={theme.typography.h3}>Flat Card</Text>
                <Text style={theme.typography.bodySmall}>This card has no shadow or border</Text>
            </View>
        ),
    },
};

export const CustomShadow = {
    args: {
        shadow: 'xl',
        children: (
            <View>
                <Text style={theme.typography.h3}>Extra Large Shadow</Text>
                <Text style={theme.typography.bodySmall}>This card has xl shadow</Text>
            </View>
        ),
    },
};

export const Stack = () => (
    <View style={{ gap: 16 }}>
        <Card>
            <Text style={theme.typography.h4}>Card 1</Text>
            <Text style={theme.typography.bodySmall}>First card in stack</Text>
        </Card>
        <Card>
            <Text style={theme.typography.h4}>Card 2</Text>
            <Text style={theme.typography.bodySmall}>Second card in stack</Text>
        </Card>
        <Card>
            <Text style={theme.typography.h4}>Card 3</Text>
            <Text style={theme.typography.bodySmall}>Third card in stack</Text>
        </Card>
    </View>
);
