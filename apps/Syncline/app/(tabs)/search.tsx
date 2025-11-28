import React, { useState } from 'react';
import { StyleSheet, View, TextInput, FlatList, TouchableOpacity, Text } from 'react-native';
import { MessageItem } from '../../components/messages/MessageItem';
import { aiAPI } from '../../src/api/endpoints/ai';
import { Message } from '../../src/types';

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
            <View style={styles.header}>
                <TextInput
                    style={styles.input}
                    placeholder="Search messages..."
                    value={query}
                    onChangeText={setQuery}
                    onSubmitEditing={handleSearch}
                    returnKeyType="search"
                />

                <View style={styles.toggles}>
                    <TouchableOpacity
                        style={[styles.chip, mode === 'semantic' && styles.activeChip]}
                        onPress={() => setMode('semantic')}
                    >
                        <Text style={[styles.chipText, mode === 'semantic' && styles.activeChipText]}>
                            ✨ AI Semantic
                        </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.chip, mode === 'keyword' && styles.activeChip]}
                        onPress={() => setMode('keyword')}
                    >
                        <Text style={[styles.chipText, mode === 'keyword' && styles.activeChipText]}>
                            🔤 Keyword
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
        backgroundColor: '#fff',
    },
    header: {
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
    },
    input: {
        backgroundColor: '#f5f5f5',
        padding: 12,
        borderRadius: 8,
        fontSize: 16,
        marginBottom: 12,
    },
    toggles: {
        flexDirection: 'row',
        gap: 8,
    },
    chip: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
        backgroundColor: '#f0f0f0',
    },
    activeChip: {
        backgroundColor: '#007AFF',
    },
    chipText: {
        fontSize: 14,
        color: '#666',
    },
    activeChipText: {
        color: 'white',
        fontWeight: '600',
    },
    list: {
        paddingBottom: 20,
    },
});
