/**
 * Message with Memory Component
 * 
 * Enhanced message display with AI memory context:
 * - Message display with related memories
 * - Proactive memory suggestions
 * - Quick memory creation from messages
 * - Memory extraction results
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    ScrollView,
    Alert
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Brain, 
    Plus, 
    Star, 
    User, 
    Clock,
    MessageCircle,
    Lightbulb,
    ChevronDown,
    ChevronUp,
    Sparkles,
    Eye,
    Edit3
} from '@tamagui/lucide-icons';
import { useMemory, useMemoryExtraction } from '../../src/hooks/useMemory';
import { useAI } from '../../src/hooks/useAI';
import { 
    ChatMessage, 
    Memory, 
    MemoryExtractionResult,
    MemoryType,
    MemoryImportance 
} from '../../src/types';
import { PLATFORM_COLORS } from '../../src/types';
import MemoryEditor from '../memory/MemoryEditor';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    backgroundColor: '$background',
    borderRadius: '$4',
    marginVertical: '$2',
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
});

const MessageContainer = styled(View, {
    padding: '$4',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const MessageHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$2',
});

const SenderInfo = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
});

const PlatformBadge = styled(View, {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: '$2',
});

const MessageContent = styled(Text, {
    fontSize: '$4',
    lineHeight: '$5',
    color: '$color',
    marginVertical: '$2',
});

const MemorySection = styled(View, {
    backgroundColor: '$gray1',
    borderBottomLeftRadius: '$4',
    borderBottomRightRadius: '$4',
});

const MemorySectionHeader = styled(TouchableOpacity, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const MemoryItem = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const MemoryContent = styled(View, {
    flex: 1,
    marginLeft: '$3',
});

const MemoryTypeChip = styled(View, {
    backgroundColor: '$blue3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    alignSelf: 'flex-start',
});

const SuggestionItem = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const ActionButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    margin: '$2',
});

const SecondaryButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    margin: '$2',
});

const ImportanceStars = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: '$1',
});

// =============================================================================
// Helper Functions
// =============================================================================

const getMemoryTypeColor = (type: MemoryType) => {
    const colors: Record<MemoryType, string> = {
        fact: '$blue8',
        commitment: '$red8',
        preference: '$purple8',
        relationship: '$pink8',
        personal: '$green8',
        task: '$orange8',
        event: '$cyan8',
        insight: '$yellow8',
    };
    return colors[type] || '$gray8';
};

const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffTime / (1000 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`;
    return date.toLocaleDateString();
};

// =============================================================================
// Main Component
// =============================================================================

interface MessageWithMemoryProps {
    message: ChatMessage;
    relatedMemories?: Memory[];
    onMemorySelect?: (memory: Memory) => void;
    onMemoryCreate?: (memory: Partial<Memory>) => void;
    showMemoryExtraction?: boolean;
}

export const MessageWithMemory: React.FC<MessageWithMemoryProps> = ({
    message,
    relatedMemories = [],
    onMemorySelect,
    onMemoryCreate,
    showMemoryExtraction = true,
}) => {
    const [showMemories, setShowMemories] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [showMemoryEditor, setShowMemoryEditor] = useState(false);
    const [extracting, setExtracting] = useState(false);

    const { createMemory } = useMemory();
    const { extractFromMessage, extractionResult, loading: extractionLoading } = useMemoryExtraction();
    const { extractEntities } = useAI();

    // Auto-extract memories when component mounts if enabled
    useEffect(() => {
        if (showMemoryExtraction && message.content.length > 50) {
            handleExtractMemories();
        }
    }, [message.id, showMemoryExtraction]);

    // Handle memory extraction
    const handleExtractMemories = useCallback(async () => {
        if (extracting) return;
        
        setExtracting(true);
        try {
            await extractFromMessage(message.id);
        } catch (err) {
            console.error('Memory extraction failed:', err);
        } finally {
            setExtracting(false);
        }
    }, [message.id, extractFromMessage, extracting]);

    // Handle create memory from suggestion
    const handleCreateFromSuggestion = useCallback(async (suggestion: {
        type: MemoryType;
        content: string;
        importance: MemoryImportance;
        metadata?: Record<string, any>;
    }) => {
        try {
            const newMemory = await createMemory({
                ...suggestion,
                thread_id: message.thread_id,
                platform: message.platform,
                metadata: {
                    ...suggestion.metadata,
                    source_message_id: message.id,
                    extracted_automatically: true,
                },
            });
            
            onMemoryCreate?.(newMemory);
            Alert.alert('Success', 'Memory created successfully');
        } catch (err) {
            Alert.alert('Error', 'Failed to create memory');
        }
    }, [message, createMemory, onMemoryCreate]);

    // Handle manual memory creation
    const handleManualMemoryCreate = useCallback((memory: Memory) => {
        onMemoryCreate?.(memory);
        setShowMemoryEditor(false);
    }, [onMemoryCreate]);

    // Render importance stars
    const renderImportanceStars = useCallback((importance: MemoryImportance) => {
        return (
            <ImportanceStars>
                {Array.from({ length: 5 }, (_, i) => (
                    <Star
                        key={i}
                        size={10}
                        color={i < importance ? '$yellow9' : '$gray6'}
                        fill={i < importance ? '$yellow9' : 'transparent'}
                    />
                ))}
            </ImportanceStars>
        );
    }, []);

    // Render related memory
    const renderRelatedMemory = useCallback((memory: Memory) => (
        <MemoryItem
            key={memory.id}
            onPress={() => onMemorySelect?.(memory)}
        >
            <View style={{
                width: 4,
                height: 40,
                backgroundColor: getMemoryTypeColor(memory.type),
                borderRadius: 2,
            }} />
            <MemoryContent>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <MemoryTypeChip>
                        <Text style={{ fontSize: 10, color: '$blue11', textTransform: 'capitalize' }}>
                            {memory.type}
                        </Text>
                    </MemoryTypeChip>
                    <Text style={{ fontSize: 11, color: '$gray9' }}>
                        {formatDate(memory.created_at)}
                    </Text>
                </View>
                <Text style={{ 
                    fontSize: 13, 
                    color: '$color', 
                    marginTop: 4,
                    numberOfLines: 2,
                }}>
                    {memory.content}
                </Text>
                {renderImportanceStars(memory.importance)}
            </MemoryContent>
        </MemoryItem>
    ), [onMemorySelect, renderImportanceStars]);

    // Render memory suggestion
    const renderMemorySuggestion = useCallback((suggestion: {
        type: MemoryType;
        content: string;
        importance: MemoryImportance;
        metadata?: Record<string, any>;
    }, index: number) => (
        <SuggestionItem
            key={index}
            onPress={() => handleCreateFromSuggestion(suggestion)}
        >
            <Lightbulb size={16} color={getMemoryTypeColor(suggestion.type)} />
            <View style={{ flex: 1, marginLeft: 12 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <MemoryTypeChip style={{ backgroundColor: getMemoryTypeColor(suggestion.type) + '20' }}>
                        <Text style={{ 
                            fontSize: 10, 
                            color: getMemoryTypeColor(suggestion.type),
                            textTransform: 'capitalize',
                        }}>
                            {suggestion.type}
                        </Text>
                    </MemoryTypeChip>
                    {renderImportanceStars(suggestion.importance)}
                </View>
                <Text style={{ 
                    fontSize: 13, 
                    color: '$color', 
                    marginTop: 4,
                    lineHeight: 18,
                }}>
                    {suggestion.content}
                </Text>
            </View>
        </SuggestionItem>
    ), [handleCreateFromSuggestion, renderImportanceStars]);

    // Memory suggestions from extraction
    const memorySuggestions = useMemo(() => {
        return extractionResult?.memories || [];
    }, [extractionResult]);

    // Total memory count
    const totalMemories = relatedMemories.length + memorySuggestions.length;

    return (
        <Container>
            {/* Original Message */}
            <MessageContainer>
                <MessageHeader>
                    <SenderInfo>
                        <PlatformBadge style={{ backgroundColor: PLATFORM_COLORS[message.platform] }} />
                        <Text style={{ fontSize: 14, fontWeight: '600', color: '$color' }}>
                            {message.sender_name}
                        </Text>
                        <Text style={{ fontSize: 12, color: '$gray11', marginLeft: 8 }}>
                            {formatDate(message.timestamp)}
                        </Text>
                    </SenderInfo>
                    
                    {message.has_attachments && (
                        <View style={{ 
                            backgroundColor: '$blue3', 
                            borderRadius: 4, 
                            paddingHorizontal: 6, 
                            paddingVertical: 2,
                        }}>
                            <Text style={{ fontSize: 10, color: '$blue11' }}>📎</Text>
                        </View>
                    )}
                </MessageHeader>

                <MessageContent>{message.content}</MessageContent>

                {/* Quick Actions */}
                <View style={{ flexDirection: 'row', marginTop: 8 }}>
                    <SecondaryButton onPress={() => setShowMemoryEditor(true)}>
                        <Plus size={14} color="$gray11" />
                        <Text style={{ marginLeft: 4, color: '$gray11', fontSize: 12 }}>
                            Add Memory
                        </Text>
                    </SecondaryButton>
                    
                    {showMemoryExtraction && (
                        <SecondaryButton 
                            onPress={handleExtractMemories}
                            disabled={extracting || extractionLoading}
                        >
                            <Brain size={14} color="$purple9" />
                            <Text style={{ marginLeft: 4, color: '$purple9', fontSize: 12 }}>
                                {extracting || extractionLoading ? 'Extracting...' : 'Extract'}
                            </Text>
                        </SecondaryButton>
                    )}
                </View>
            </MessageContainer>

            {/* Memory Section */}
            {totalMemories > 0 && (
                <MemorySection>
                    {/* Related Memories */}
                    {relatedMemories.length > 0 && (
                        <>
                            <MemorySectionHeader onPress={() => setShowMemories(!showMemories)}>
                                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                    <Brain size={16} color="$blue9" />
                                    <Text style={{ marginLeft: 8, fontSize: 14, fontWeight: '600', color: '$color' }}>
                                        Related Memories ({relatedMemories.length})
                                    </Text>
                                </View>
                                {showMemories ? (
                                    <ChevronUp size={16} color="$gray9" />
                                ) : (
                                    <ChevronDown size={16} color="$gray9" />
                                )}
                            </MemorySectionHeader>
                            
                            {showMemories && relatedMemories.map(renderRelatedMemory)}
                        </>
                    )}

                    {/* Memory Suggestions */}
                    {memorySuggestions.length > 0 && (
                        <>
                            <MemorySectionHeader onPress={() => setShowSuggestions(!showSuggestions)}>
                                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                    <Sparkles size={16} color="$purple9" />
                                    <Text style={{ marginLeft: 8, fontSize: 14, fontWeight: '600', color: '$color' }}>
                                        Memory Suggestions ({memorySuggestions.length})
                                    </Text>
                                </View>
                                {showSuggestions ? (
                                    <ChevronUp size={16} color="$gray9" />
                                ) : (
                                    <ChevronDown size={16} color="$gray9" />
                                )}
                            </MemorySectionHeader>
                            
                            {showSuggestions && memorySuggestions.map(renderMemorySuggestion)}
                        </>
                    )}

                    {/* Extraction Results Summary */}
                    {extractionResult && (
                        <View style={{ padding: 12, backgroundColor: '$gray2' }}>
                            <Text style={{ fontSize: 12, color: '$gray11', textAlign: 'center' }}>
                                Found {extractionResult.memories.length} memories, {extractionResult.entities_found.length} entities, {extractionResult.commitments_found.length} commitments
                            </Text>
                        </View>
                    )}
                </MemorySection>
            )}

            {/* Memory Editor Modal */}
            <MemoryEditor
                visible={showMemoryEditor}
                onClose={() => setShowMemoryEditor(false)}
                onSave={handleManualMemoryCreate}
                threadId={message.thread_id}
                platform={message.platform}
                sourceMessageId={message.id}
            />
        </Container>
    );
};

export default MessageWithMemory;