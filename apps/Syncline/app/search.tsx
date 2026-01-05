import React, { useState } from 'react';
import { StyleSheet, View, TextInput, FlatList, TouchableOpacity, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Stack } from 'expo-router';
import { MessageItem } from '../components/messages/MessageItem';
import { aiAPI } from '../src/api/endpoints/ai';
import { Message } from '../src/types';
import { theme } from '../src/theme';

export default function SearchScreen() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState<'semantic' | 'keyword'>('semantic');

    const handleSearch = async () => {
        if (!query.trim()) return;

        setLoading(true);
        try {
            // Use semantic search by default as it's more powerful
            const data = await aiAPI.semanticSearch(query);
            setResults(data.results);
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <View style={styles.container}>
            <Stack.Screen options={{ title: 'Search', headerShown: true }} />
            <View style={styles.header}>
                <View style={styles.searchContainer}>
                    <Ionicons name="search" size={20} color={theme.colors.textTertiary} style={styles.searchIcon} />
                    <TextInput
                        style={styles.input}
                        placeholder="Search messages..."
                        placeholderTextColor={theme.colors.textTertiary}
                        value={query}
                        onChangeText={setQuery}
                        onSubmitEditing={handleSearch}
                        returnKeyType="search"
                    />
                </View>

                <View style={styles.toggles}>
                    <TouchableOpacity
                        style={[styles.chip, mode === 'semantic' && styles.activeChip]}
                        onPress={() => setMode('semantic')}
                        activeOpacity={0.8}
                    >
                        <Ionicons
                            name="sparkles"
                            size={16}
                            color={mode === 'semantic' ? 'white' : theme.colors.textSecondary}
                        />
                        <Text style={[styles.chipText, mode === 'semantic' && styles.activeChipText]}>
                            AI Semantic
                        </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.chip, mode === 'keyword' && styles.activeChip]}
                        onPress={() => setMode('keyword')}
                        activeOpacity={0.8}
                    >
                        <Ionicons
                            name="text"
                            size={16}
                            color={mode === 'keyword' ? 'white' : theme.colors.textSecondary}
                        />
                        <Text style={[styles.chipText, mode === 'keyword' && styles.activeChipText]}>
                            Keyword
                        </Text>
                    </TouchableOpacity>
                </View>
            </View>

            <FlatList
                data={results}
                keyExtractor={(item) => item.id}
                renderItem={({ item }) => (
                    <MessageItem
                        message={item}
                        onPress={() => console.log('Open message', item.id)}
                    />
                )}
                contentContainerStyle={styles.list}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        padding: 16,
        backgroundColor: 'white',
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 12,
        marginBottom: 16,
        height: 48,
    },
    searchIcon: {
        marginRight: 8,
    },
    input: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
        height: '100%',
    },
    toggles: {
        flexDirection: 'row',
        gap: 12,
    },
    chip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        backgroundColor: theme.colors.surface,
        borderWidth: 1,
        borderColor: theme.colors.borderLight,
    },
    activeChip: {
        backgroundColor: theme.colors.primary,
        borderColor: theme.colors.primary,
    },
    chipText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
    activeChipText: {
        color: 'white',
        fontWeight: '600',
    },
    list: {
        padding: 16,
    },
});
