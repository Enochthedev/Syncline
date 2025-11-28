import React from 'react';
import { View, Text, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { theme } from '../../src/theme';

export interface BadgeProps {
    children: React.ReactNode;
    variant?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'secondary';
    size?: 'sm' | 'md' | 'lg';
    style?: StyleProp<ViewStyle>;
}

export const Badge: React.FC<BadgeProps> = ({
    children,
    variant = 'primary',
    size = 'md',
    style,
}) => {
    const getVariantStyle = () => {
        switch (variant) {
            case 'primary':
                return { backgroundColor: theme.colors.primaryLighter, color: theme.colors.primaryDark };
            case 'success':
                return { backgroundColor: theme.colors.successLight, color: theme.colors.success };
            case 'warning':
                return { backgroundColor: theme.colors.warningLight, color: theme.colors.warning };
            case 'error':
                return { backgroundColor: theme.colors.errorLight, color: theme.colors.error };
            case 'info':
                return { backgroundColor: theme.colors.infoLight, color: theme.colors.info };
            case 'secondary':
                return { backgroundColor: theme.colors.surface, color: theme.colors.text };
            default:
                return { backgroundColor: theme.colors.primaryLighter, color: theme.colors.primaryDark };
        }
    };

    const getSizeStyle = () => {
        switch (size) {
            case 'sm':
                return { paddingHorizontal: 8, paddingVertical: 2, fontSize: 10 };
            case 'md':
                return { paddingHorizontal: 10, paddingVertical: 4, fontSize: 12 };
            case 'lg':
                return { paddingHorizontal: 12, paddingVertical: 6, fontSize: 14 };
            default:
                return { paddingHorizontal: 10, paddingVertical: 4, fontSize: 12 };
        }
    };

    const variantStyle = getVariantStyle();
    const sizeStyle = getSizeStyle();

    return (
        <View
            style={[
                styles.badge,
                { backgroundColor: variantStyle.backgroundColor },
                { paddingHorizontal: sizeStyle.paddingHorizontal, paddingVertical: sizeStyle.paddingVertical },
                style,
            ]}
        >
            <Text style={[styles.text, { color: variantStyle.color, fontSize: sizeStyle.fontSize }]}>
                {children}
            </Text>
        </View>
    );
};

const styles = StyleSheet.create({
    badge: {
        borderRadius: theme.borderRadius.full,
        alignSelf: 'flex-start',
    },
    text: {
        fontWeight: '600',
    },
});
