/**
 * Memory Detail Component
 * 
 * Displays full memory content with:
 * - Complete memory information and metadata
 * - Edit memory importance and content
 * - Related memories and connections
 * - Memory access history and statistics
 */

import React, { useState, useCallback, useMemo } from 'react';
import { View, Text, ScrollView, TouchableOpacity, TextInput, Alert, Modal } from 'react-native';
import { styled } from '@tamagui/core';
import { 
    Edit3, 
    Save, 
    X, 
    Star, 
    Clock, 
    User, 
    MessageCircle, 
    Tag,
    Calendar,
    Eye,
    Link,
    Trash2,
    ArrowLeft
} from '@tamagui/lucide-icons';
import { useMemory, useContactMemories } from '../../src/hooks/useMemory';
import { Memory, MemoryType, MemoryImportance, Platform } from '../../src/types';
import { PLATFORM_COLORS, PLATFORM_NAMES } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '$background',
});

const Header = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
    backgroundColor: '$background',
});

const BackButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: '$2',
});

const ActionButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
});

const DeleteButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$red2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginLeft: '$2',
});

const ContentSection = styled(View, {
    padding: '$4',
});

const SectionTitle = styled(Text, {
    fontSize: '$5',
    fontWeight: '600',
    color: '$color',
    marginBottom: '$3',
});

const MemoryCard = styled(View, {
    backgroundColor: '$gray1',
    borderRadius: '$4',
    padding: '$4',
    marginBottom: '$4',
    borderLeftWidth: 4,
});

const MetadataGrid = styled(View, {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: '$3',
});

const MetadataItem = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
    marginBottom: '$2',
});

const ImportanceSelector = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: '$3',
});

const ImportanceStar = styled(TouchableOpacity, {
    marginRight: '$1',
});

const EditableContent = styled(TextInput, {
    fontSize: '$4',
    color: '$color',
    lineHeight: '$5',
    minHeight: 100,
    textAlignVertical: 'top',
    backgroundColor: '$gray1',
    borderRadius: '$3',
    padding: '$3',
    borderWidth: 1,
    borderColor: '$gray6',
});

const RelatedMemoryItem = styled(TouchableOpacity, {
    backgroundColor: '$gray1',
    borderRadius: '$3',
    padding: '$3',
    marginBottom: '$2',
    borderLeftWidth: 3,
});

const StatItem = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: '$2',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const LoadingContainer = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
});

const ErrorContainer = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: '$4',
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
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
};

const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
};

// =============================================================================
// Main Component
// =============================================================================

interface MemoryDetailProps {
    memoryId: string;
    onBack?: () => void;
    onMemoryUpdated?: (memory: Memory) => void;
    onMemoryDeleted?: () => void;
    onRelatedMemoryPress?: (memoryId: string) => void;
}

export const MemoryDetail: React.FC<MemoryDetailProps> = ({
    memoryId,
    onBack,
    onMemoryUpdated,
    onMemoryDeleted,
    onRelatedMemoryPress,
}) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [editImportance, setEditImportance] = useState<MemoryImportance>(1);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const { memory, loading, error, updateMemory, deleteMemory, refetch } = useMemory(memoryId);
    
    // Get related memories if we have a contact
    const { 
        memories: relatedMemories, 
        loading: relatedLoading 
    } = useContactMemories(
        memory?.contact_id || '',
        { limit: 5 }
    );

    // Initialize edit state when memory loads
    React.useEffect(() => {
        if (memory && !isEditing) {
            setEditContent(memory.content);
            setEditImportance(memory.importance);
        }
    }, [memory, isEditing]);

    // Handle edit mode toggle
    const handleEditToggle = useCallback(() => {
        if (isEditing) {
            // Reset to original values
            setEditContent(memory?.content || '');
            setEditImportance(memory?.importance || 1);
        }
        setIsEditing(!isEditing);
    }, [isEditing, memory]);

    // Handle save
    const handleSave = useCallback(async () => {
        if (!memory) return;

        try {
            const updatedMemory = await updateMemory(memory.id, {
                content: editContent,
                importance: editImportance,
            });
            
            setIsEditing(false);
            onMemoryUpdated?.(updatedMemory);
            
            Alert.alert('Success', 'Memory updated successfully');
        } catch (error) {
            Alert.alert('Error', 'Failed to update memory');
        }
    }, [memory, editContent, editImportance, updateMemory, onMemoryUpdated]);

    // Handle delete
    const handleDelete = useCallback(async () => {
        if (!memory) return;

        try {
            await deleteMemory(memory.id);
            onMemoryDeleted?.();
            Alert.alert('Success', 'Memory deleted successfully');
        } catch (error) {
            Alert.alert('Error', 'Failed to delete memory');
        }
    }, [memory, deleteMemory, onMemoryDeleted]);

    // Render importance stars
    const renderImportanceStars = useCallback((importance: MemoryImportance, editable = false) => {
        return (
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                {Array.from({ length: 5 }, (_, i) => (
                    <ImportanceStar
                        key={i}
                        onPress={editable ? () => setEditImportance((i + 1) as MemoryImportance) : undefined}
                        disabled={!editable}
                    >
                        <Star
                            size={20}
                            color={i < importance ? '$yellow9' : '$gray6'}
                            fill={i < importance ? '$yellow9' : 'transparent'}
                        />
                    </ImportanceStar>
                ))}
                <Text style={{ marginLeft: 8, color: '$gray11', fontSize: 14 }}>
                    {editable ? 'Tap to change' : `${importance}/5`}
                </Text>
            </View>
        );
    }, []);

    // Filter related memories (exclude current memory)
    const filteredRelatedMemories = useMemo(() => {
        return relatedMemories.filter(m => m.id !== memoryId).slice(0, 3);
    }, [relatedMemories, memoryId]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <BackButton onPress={onBack}>
                        <ArrowLeft size={20} color="$color" />
                        <Text style={{ marginLeft: 8, fontSize: 16, color: '$color' }}>Back</Text>
                    </BackButton>
                </Header>
                <LoadingContainer>
                    <Text style={{ color: '$gray11' }}>Loading memory...</Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error || !memory) {
        return (
            <Container>
                <Header>
                    <BackButton onPress={onBack}>
                        <ArrowLeft size={20} color="$color" />
                        <Text style={{ marginLeft: 8, fontSize: 16, color: '$color' }}>Back</Text>
                    </BackButton>
                </Header>
                <ErrorContainer>
                    <Text style={{ color: '$red11', textAlign: 'center', marginBottom: 16 }}>
                        {error || 'Memory not found'}
                    </Text>
                    <TouchableOpacity
                        onPress={refetch}
                        style={{
                            backgroundColor: '$blue8',
                            paddingHorizontal: 16,
                            paddingVertical: 8,
                            borderRadius: 6,
                        }}
                    >
                        <Text style={{ color: 'white' }}>Retry</Text>
                    </TouchableOpacity>
                </ErrorContainer>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <BackButton onPress={onBack}>
                    <ArrowLeft size={20} color="$color" />
                    <Text style={{ marginLeft: 8, fontSize: 16, color: '$color' }}>Back</Text>
                </BackButton>
                
                <View style={{ flexDirection: 'row' }}>
                    {isEditing ? (
                        <>
                            <ActionButton onPress={handleSave}>
                                <Save size={16} color="$blue11" />
                                <Text style={{ marginLeft: 6, color: '$blue11' }}>Save</Text>
                            </ActionButton>
                            <TouchableOpacity
                                onPress={handleEditToggle}
                                style={{
                                    marginLeft: 8,
                                    paddingHorizontal: 12,
                                    paddingVertical: 8,
                                }}
                            >
                                <X size={16} color="$gray11" />
                            </TouchableOpacity>
                        </>
                    ) : (
                        <>
                            <ActionButton onPress={handleEditToggle}>
                                <Edit3 size={16} color="$blue11" />
                                <Text style={{ marginLeft: 6, color: '$blue11' }}>Edit</Text>
                            </ActionButton>
                            <DeleteButton onPress={() => setShowDeleteConfirm(true)}>
                                <Trash2 size={16} color="$red11" />
                            </DeleteButton>
                        </>
                    )}
                </View>
            </Header>

            <ScrollView showsVerticalScrollIndicator={false}>
                <ContentSection>
                    {/* Memory Content */}
                    <MemoryCard style={{ borderLeftColor: getMemoryTypeColor(memory.type) }}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                <View style={{
                                    backgroundColor: getMemoryTypeColor(memory.type) + '20',
                                    borderRadius: 16,
                                    paddingHorizontal: 8,
                                    paddingVertical: 4,
                                }}>
                                    <Text style={{ 
                                        color: getMemoryTypeColor(memory.type),
                                        fontSize: 12,
                                        fontWeight: '600',
                                        textTransform: 'capitalize',
                                    }}>
                                        {memory.type}
                                    </Text>
                                </View>
                            </View>
                            
                            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                <Eye size={14} color="$gray9" />
                                <Text style={{ marginLeft: 4, color: '$gray9', fontSize: 12 }}>
                                    {memory.access_count}
                                </Text>
                            </View>
                        </View>

                        {isEditing ? (
                            <EditableContent
                                value={editContent}
                                onChangeText={setEditContent}
                                multiline
                                placeholder="Enter memory content..."
                                placeholderTextColor="$gray9"
                            />
                        ) : (
                            <Text style={{ 
                                fontSize: 16, 
                                lineHeight: 24, 
                                color: '$color',
                            }}>
                                {memory.content}
                            </Text>
                        )}

                        <View style={{ marginTop: 16 }}>
                            <Text style={{ fontSize: 14, color: '$gray11', marginBottom: 8 }}>
                                Importance
                            </Text>
                            {renderImportanceStars(isEditing ? editImportance : memory.importance, isEditing)}
                        </View>
                    </MemoryCard>

                    {/* Metadata */}
                    <SectionTitle>Details</SectionTitle>
                    <MetadataGrid>
                        <MetadataItem>
                            <Calendar size={14} color="$gray9" />
                            <Text style={{ marginLeft: 6, fontSize: 12, color: '$gray11' }}>
                                Created {formatRelativeTime(memory.created_at)}
                            </Text>
                        </MetadataItem>
                        
                        {memory.updated_at !== memory.created_at && (
                            <MetadataItem>
                                <Edit3 size={14} color="$gray9" />
                                <Text style={{ marginLeft: 6, fontSize: 12, color: '$gray11' }}>
                                    Updated {formatRelativeTime(memory.updated_at)}
                                </Text>
                            </MetadataItem>
                        )}
                        
                        <MetadataItem>
                            <Clock size={14} color="$gray9" />
                            <Text style={{ marginLeft: 6, fontSize: 12, color: '$gray11' }}>
                                Last accessed {formatRelativeTime(memory.last_accessed_at)}
                            </Text>
                        </MetadataItem>

                        {memory.platform && (
                            <MetadataItem>
                                <MessageCircle size={14} color={PLATFORM_COLORS[memory.platform]} />
                                <Text style={{ marginLeft: 6, fontSize: 12, color: '$gray11' }}>
                                    {PLATFORM_NAMES[memory.platform]}
                                </Text>
                            </MetadataItem>
                        )}
                    </MetadataGrid>

                    {/* Statistics */}
                    <SectionTitle style={{ marginTop: 24 }}>Statistics</SectionTitle>
                    <View style={{ backgroundColor: '$gray1', borderRadius: 8, padding: 16 }}>
                        <StatItem>
                            <Text style={{ color: '$gray11' }}>Access Count</Text>
                            <Text style={{ color: '$color', fontWeight: '500' }}>{memory.access_count}</Text>
                        </StatItem>
                        <StatItem>
                            <Text style={{ color: '$gray11' }}>Created</Text>
                            <Text style={{ color: '$color', fontWeight: '500' }}>{formatDate(memory.created_at)}</Text>
                        </StatItem>
                        <StatItem>
                            <Text style={{ color: '$gray11' }}>Last Updated</Text>
                            <Text style={{ color: '$color', fontWeight: '500' }}>{formatDate(memory.updated_at)}</Text>
                        </StatItem>
                        <StatItem style={{ borderBottomWidth: 0 }}>
                            <Text style={{ color: '$gray11' }}>Last Accessed</Text>
                            <Text style={{ color: '$color', fontWeight: '500' }}>{formatDate(memory.last_accessed_at)}</Text>
                        </StatItem>
                    </View>

                    {/* Related Memories */}
                    {filteredRelatedMemories.length > 0 && (
                        <>
                            <SectionTitle style={{ marginTop: 24 }}>Related Memories</SectionTitle>
                            {filteredRelatedMemories.map((relatedMemory) => (
                                <RelatedMemoryItem
                                    key={relatedMemory.id}
                                    onPress={() => onRelatedMemoryPress?.(relatedMemory.id)}
                                    style={{ borderLeftColor: getMemoryTypeColor(relatedMemory.type) }}
                                >
                                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                        <Text style={{ 
                                            fontSize: 12, 
                                            color: getMemoryTypeColor(relatedMemory.type),
                                            textTransform: 'capitalize',
                                            fontWeight: '600',
                                        }}>
                                            {relatedMemory.type}
                                        </Text>
                                        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                            {Array.from({ length: relatedMemory.importance }, (_, i) => (
                                                <Star key={i} size={10} color="$yellow9" fill="$yellow9" />
                                            ))}
                                        </View>
                                    </View>
                                    <Text style={{ 
                                        fontSize: 14, 
                                        color: '$color',
                                        numberOfLines: 2,
                                    }}>
                                        {relatedMemory.content}
                                    </Text>
                                </RelatedMemoryItem>
                            ))}
                        </>
                    )}
                </ContentSection>
            </ScrollView>

            {/* Delete Confirmation Modal */}
            <Modal
                visible={showDeleteConfirm}
                transparent
                animationType="fade"
                onRequestClose={() => setShowDeleteConfirm(false)}
            >
                <View style={{
                    flex: 1,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    justifyContent: 'center',
                    alignItems: 'center',
                    paddingHorizontal: 20,
                }}>
                    <View style={{
                        backgroundColor: '$background',
                        borderRadius: 12,
                        padding: 20,
                        width: '100%',
                        maxWidth: 400,
                    }}>
                        <Text style={{ 
                            fontSize: 18, 
                            fontWeight: '600', 
                            color: '$color',
                            marginBottom: 12,
                        }}>
                            Delete Memory
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            lineHeight: 20,
                            marginBottom: 20,
                        }}>
                            Are you sure you want to delete this memory? This action cannot be undone.
                        </Text>
                        <View style={{ flexDirection: 'row', justifyContent: 'flex-end' }}>
                            <TouchableOpacity
                                onPress={() => setShowDeleteConfirm(false)}
                                style={{
                                    paddingHorizontal: 16,
                                    paddingVertical: 8,
                                    marginRight: 12,
                                }}
                            >
                                <Text style={{ color: '$gray11' }}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                onPress={() => {
                                    setShowDeleteConfirm(false);
                                    handleDelete();
                                }}
                                style={{
                                    backgroundColor: '$red8',
                                    paddingHorizontal: 16,
                                    paddingVertical: 8,
                                    borderRadius: 6,
                                }}
                            >
                                <Text style={{ color: 'white', fontWeight: '500' }}>Delete</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </Modal>
        </Container>
    );
};

export default MemoryDetail;