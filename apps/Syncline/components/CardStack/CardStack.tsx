import React, { useState } from 'react';
import { View, StyleSheet, Dimensions, TouchableOpacity, Text } from 'react-native';
import Animated, {
    useAnimatedStyle,
    useSharedValue,
    withSpring,
    interpolate,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { theme } from '../../src/theme';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width - 48;
const STACK_OFFSET = 8;
const ROTATION_DEGREES = 2;

export interface CardStackProps {
    cards: Array<{
        id: string;
        title: string;
        subtitle?: string;
        gradient?: [string, string];
        content: React.ReactNode;
    }>;
    onCardPress?: (id: string) => void;
}

export const CardStack: React.FC<CardStackProps> = ({ cards, onCardPress }) => {
    const [activeIndex, setActiveIndex] = useState(0);

    const renderCard = (card: typeof cards[0], index: number) => {
        const isActive = index === activeIndex;
        const offset = (index - activeIndex) * STACK_OFFSET;
        const rotation = (index - activeIndex) * ROTATION_DEGREES;
        const scale = 1 - (index - activeIndex) * 0.02;

        return (
            <TouchableOpacity
                key={card.id}
                activeOpacity={0.9}
                onPress={() => {
                    setActiveIndex(index);
                    onCardPress?.(card.id);
                }}
                style={[
                    styles.card,
                    {
                        transform: [
                            { translateY: offset },
                            { rotate: `${rotation}deg` },
                            { scale: Math.max(scale, 0.9) },
                        ],
                        zIndex: cards.length - index,
                        opacity: index < activeIndex + 3 ? 1 : 0,
                    },
                ]}
            >
                <View style={styles.cardContent}>
                    {card.content}
                </View>
            </TouchableOpacity>
        );
    };

    return (
        <View style={styles.container}>
            {cards.map((card, index) => renderCard(card, index))}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        height: 300,
        alignItems: 'center',
        justifyContent: 'center',
    },
    card: {
        position: 'absolute',
        width: CARD_WIDTH,
        height: 280,
        borderRadius: theme.borderRadius.xl,
        backgroundColor: theme.colors.white,
        ...theme.shadows.lg,
    },
    cardContent: {
        flex: 1,
        borderRadius: theme.borderRadius.xl,
        overflow: 'hidden',
    },
});
