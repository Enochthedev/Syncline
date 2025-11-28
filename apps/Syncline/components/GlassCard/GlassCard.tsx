import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { theme } from '../../src/theme';

export interface GlassCardProps {
    children: React.ReactNode;
    style?: StyleProp<ViewStyle>;
    intensity?: number;
    gradient?: [string, string];
    variant?: 'light' | 'dark';
}

export const GlassCard: React.FC<GlassCardProps> = ({
    children,
    style,
    intensity = 80,
    gradient,
    variant = 'light',
}) => {
    if (gradient) {
        return (
            <View style={[styles.container, style]}>
                <LinearGradient
                    colors={[`${gradient[0]}E6`, `${gradient[1]}E6`]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 1 }}
                    style={styles.gradient}
                >
                    <BlurView intensity={intensity} style={styles.blur}>
                        <View style={styles.content}>
                            {children}
                        </View>
                    </BlurView>
                </LinearGradient>
            </View>
        );
    }

    return (
        <View style={[styles.container, style]}>
            <BlurView
                intensity={intensity}
                tint={variant}
                style={[styles.blur, styles.glassBorder]}
            >
                <View style={styles.content}>
                    {children}
                </View>
            </BlurView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        borderRadius: theme.borderRadius.l,
        overflow: 'hidden',
        ...theme.shadows.md,
    },
    gradient: {
        flex: 1,
    },
    blur: {
        flex: 1,
    },
    glassBorder: {
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    content: {
        flex: 1,
        padding: theme.spacing.l,
    },
});
