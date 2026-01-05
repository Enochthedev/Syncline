import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { theme } from '../../src/theme';

export interface CardProps {
    children: React.ReactNode;
    style?: StyleProp<ViewStyle>;
    padding?: keyof typeof theme.spacing;
    shadow?: keyof typeof theme.shadows;
    variant?: 'elevated' | 'outlined' | 'flat';
}

export const Card: React.FC<CardProps> = ({
    children,
    style,
    padding = 'm',
    shadow = 'md',
    variant = 'elevated',
}) => {
    const getVariantStyle = () => {
        switch (variant) {
            case 'elevated':
                return [styles.elevated, theme.shadows[shadow]];
            case 'outlined':
                return styles.outlined;
            case 'flat':
                return styles.flat;
            default:
                return styles.elevated;
        }
    };

    return (
        <View
            style={[
                styles.card,
                padding && { padding: theme.spacing[padding] },
                getVariantStyle(),
                style,
            ]}
        >
            {children}
        </View>
    );
};

const styles = StyleSheet.create({
    card: {
        borderRadius: theme.borderRadius.l,
        overflow: 'hidden',
    },
    elevated: {
        backgroundColor: theme.colors.white,
    },
    outlined: {
        backgroundColor: theme.colors.white,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    flat: {
        backgroundColor: theme.colors.surface,
    },
});
