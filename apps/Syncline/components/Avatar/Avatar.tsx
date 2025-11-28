import React from 'react';
import { View, Image, StyleSheet } from 'react-native';
import { theme } from '../../src/theme';

interface AvatarProps {
    seed: string;
    size?: number;
    style?: any;
    variant?: 'personas' | 'initials' | 'bottts' | 'avataaars';
}

export const Avatar: React.FC<AvatarProps> = ({
    seed,
    size = 48,
    style,
    variant = 'personas'
}) => {
    // Generate Dicebear avatar URL
    const avatarUrl = `https://api.dicebear.com/7.x/${variant}/svg?seed=${encodeURIComponent(seed)}&backgroundColor=0ea5e9`;

    return (
        <View style={[styles.container, { width: size, height: size, borderRadius: size / 2 }, style]}>
            <Image
                source={{ uri: avatarUrl }}
                style={[styles.image, { width: size, height: size, borderRadius: size / 2 }]}
                resizeMode="cover"
            />
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        overflow: 'hidden',
        backgroundColor: theme.colors.surface,
    },
    image: {
        width: '100%',
        height: '100%',
    },
});
