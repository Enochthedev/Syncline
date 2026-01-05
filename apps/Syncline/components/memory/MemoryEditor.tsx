/**
 * Memory Editor Component
 * 
 * Modal for creating and editing memories with:
 * - Memory type selection
 * - Content input with rich text support
 * - Importance level setting
 * - Contact and thread linking
 * - Metadata and tags management
 */

import React, { useState, useCallback, useEffect } from 'react';
import { 
    View, 
    Text, 
    TextInput, 
    TouchableOpacity, 
    Modal, 
    ScrollView, 
    Alert,
    KeyboardAvoidingView,
    Platform
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    X, 
    Save, 
    Star, 
    User, 
    MessageCircle, 
    Tag,
    Calendar,
    Plus,
    Check
} from '@tamagui/lucide-icons';
import { useMemory } from '../../src/hooks/useMemory';
import { Memory, MemoryType, MemoryImportance, Platform as PlatformType } from '../../src/types';
import { PLATFORM_NAMES, PLATFORM_COLORS } from '../../src/types';

// =============================================================================
// Styled Components
// =============================================================================

const ModalOverlay = styled(View, {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
});

const ModalContainer = styled(View, {
    backgroundColor: '$background',
    borderRadius: '$4',
    width: '90%',
    maxWidth: 500,
    maxHeight: '80%',
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
});

const ModalHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
});

const CloseButton = styled(TouchableOpacity, {
    padding: '$2',
});

const SaveButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
});

const FormSection = styled(View, {
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray3',
});

const SectionTitle = styled(Text, {
    fontSize: '$4',
    fontWeight: '600',
    color: '$color',
    marginBottom: '$3',
});

const ContentInput = styled(TextInput, {
    fontSize: '$4',
    color: '$color',
    lineHeight: '$5',
    minHeight: 120,
    textAlignVertical: 'top',
    backgroundColor: '$gray1',
    borderRadius: '$3',
    padding: '$3',
    borderWidth: 1,
    borderColor: '$gray6',
});

const TypeSelector = styled(View, {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: '$2',
});

const TypeOption = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
    marginBottom: '$2',
    borderWidth: 1,
    borderColor: 'transparent',
});

const ImportanceSelector = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: '$2',
});

const ImportanceStar = styled(TouchableOpacity, {
    marginRight: '$1',
});

const PlatformSelector = styled(View, {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: '$2',
});

const PlatformOption = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray2',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
    marginBottom: '$2',
    borderWidth: 1,
    borderColor: 'transparent',
});

const TagInput = styled(TextInput, {
    flex: 1,
    fontSize: '$4',
    color: '$color',
    backgroundColor: '$gray1',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    borderWidth: 1,
    borderColor: '$gray6',
});

const TagContainer = styled(View, {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: '$2',
});

const TagChip = styled(View, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
    marginBottom: '$2',
});

const RemoveTagButton = styled(TouchableOpacity, {
    marginLeft: '$1',
});

// =============================================================================
// Memory Type Configuration
// =============================================================================

const MEMORY_TYPES: Array<{
    type: MemoryType;
    label: string;
    description: string;
    color: string;
    icon: React.ReactNode;
}> = [
    {
        type: 'fact',
        label: 'Fact',
        description: 'Factual information',
        color: '$blue8',
        icon: <MessageCircle size={16} color="$blue8" />,
    },
    {
        type: 'commitment',
        label: 'Commitment',
        description: 'Promises and deadlines',
        color: '$red8',
        icon: <Calendar size={16} color="$red8" />,
    },
    {
        type: 'preference',
        label: 'Preference',
        description: 'Personal preferences',
        color: '$purple8',
        icon: <Star size={16} color="$purple8" />,
    },
    {
        type: 'relationship',
        label: 'Relationship',
        description: 'Relationship information',
        color: '$pink8',
        icon: <User size={16} color="$pink8" />,
    },
    {
        type: 'personal',
        label: 'Personal',
        description: 'Personal details',
        color: '$green8',
        icon: <User size={16} color="$green8" />,
    },
    {
        type: 'task',
        label: 'Task',
        description: 'Action items',
        color: '$orange8',
        icon: <Check size={16} color="$orange8" />,
    },
    {
        type: 'event',
        label: 'Event',
        description: 'Events and meetings',
        color: '$cyan8',
        icon: <Calendar size={16} color="$cyan8" />,
    },
    {
        type: 'insight',
        label: 'Insight',
        description: 'AI-generated insights',
        color: '$yellow8',
        icon: <Star size={16} color="$yellow8" />,
    },
];

// =============================================================================
// Main Component
// =============================================================================

interface MemoryEditorProps {
    visible: boolean;
    onClose: () => void;
    onSave?: (memory: Memory) => void;
    initialMemory?: Partial<Memory>;
    contactId?: string;
    threadId?: string;
    platform?: PlatformType;
    sourceMessageId?: string;
}

export const MemoryEditor: React.FC<MemoryEditorProps> = ({
    visible,
    onClose,
    onSave,
    initialMemory,
    contactId,
    threadId,
    platform,
    sourceMessageId,
}) => {
    const [content, setContent] = useState('');
    const [memoryType, setMemoryType] = useState<MemoryType>('fact');
    const [importance, setImportance] = useState<MemoryImportance>(3);
    const [selectedPlatform, setSelectedPlatform] = useState<PlatformType | undefined>(platform);
    const [tags, setTags] = useState<string[]>([]);
    const [newTag, setNewTag] = useState('');
    const [saving, setSaving] = useState(false);

    const { createMemory, updateMemory } = useMemory();

    // Initialize form when modal opens or initial memory changes
    useEffect(() => {
        if (visible) {
            if (initialMemory) {
                setContent(initialMemory.content || '');
                setMemoryType(initialMemory.type || 'fact');
                setImportance(initialMemory.importance || 3);
                setSelectedPlatform(initialMemory.platform || platform);
                // Extract tags from metadata if available
                const memoryTags = initialMemory.memory_metadata?.tags || [];
                setTags(Array.isArray(memoryTags) ? memoryTags : []);
            } else {
                // Reset form for new memory
                setContent('');
                setMemoryType('fact');
                setImportance(3);
                setSelectedPlatform(platform);
                setTags([]);
            }
            setNewTag('');
            setSaving(false);
        }
    }, [visible, initialMemory, platform]);

    // Handle save
    const handleSave = useCallback(async () => {
        if (!content.trim()) {
            Alert.alert('Error', 'Please enter memory content');
            return;
        }

        setSaving(true);

        try {
            const memoryData = {
                type: memoryType,
                content: content.trim(),
                importance,
                contact_id: contactId,
                thread_id: threadId,
                platform: selectedPlatform,
                metadata: {
                    tags,
                    source_message_id: sourceMessageId,
                    created_via: 'manual',
                },
            };

            let savedMemory: Memory;

            if (initialMemory?.id) {
                // Update existing memory
                savedMemory = await updateMemory(initialMemory.id, {
                    content: content.trim(),
                    importance,
                    metadata: memoryData.metadata,
                });
            } else {
                // Create new memory
                savedMemory = await createMemory(memoryData);
            }

            onSave?.(savedMemory);
            onClose();
            
            Alert.alert(
                'Success', 
                initialMemory?.id ? 'Memory updated successfully' : 'Memory created successfully'
            );
        } catch (error) {
            Alert.alert('Error', 'Failed to save memory');
        } finally {
            setSaving(false);
        }
    }, [
        content,
        memoryType,
        importance,
        contactId,
        threadId,
        selectedPlatform,
        tags,
        sourceMessageId,
        initialMemory,
        createMemory,
        updateMemory,
        onSave,
        onClose,
    ]);

    // Handle add tag
    const handleAddTag = useCallback(() => {
        const trimmedTag = newTag.trim().toLowerCase();
        if (trimmedTag && !tags.includes(trimmedTag)) {
            setTags([...tags, trimmedTag]);
            setNewTag('');
        }
    }, [newTag, tags]);

    // Handle remove tag
    const handleRemoveTag = useCallback((tagToRemove: string) => {
        setTags(tags.filter(tag => tag !== tagToRemove));
    }, [tags]);

    // Render importance stars
    const renderImportanceStars = useCallback(() => {
        return (
            <ImportanceSelector>
                {Array.from({ length: 5 }, (_, i) => (
                    <ImportanceStar
                        key={i}
                        onPress={() => setImportance((i + 1) as MemoryImportance)}
                    >
                        <Star
                            size={24}
                            color={i < importance ? '$yellow9' : '$gray6'}
                            fill={i < importance ? '$yellow9' : 'transparent'}
                        />
                    </ImportanceStar>
                ))}
                <Text style={{ marginLeft: 12, color: '$gray11', fontSize: 14 }}>
                    {importance}/5 - {
                        importance === 1 ? 'Very Low' :
                        importance === 2 ? 'Low' :
                        importance === 3 ? 'Medium' :
                        importance === 4 ? 'High' : 'Very High'
                    }
                </Text>
            </ImportanceSelector>
        );
    }, [importance]);

    if (!visible) return null;

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={onClose}
        >
            <KeyboardAvoidingView 
                style={{ flex: 1 }} 
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                <ModalOverlay>
                    <ModalContainer>
                        {/* Header */}
                        <ModalHeader>
                            <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                                {initialMemory?.id ? 'Edit Memory' : 'Create Memory'}
                            </Text>
                            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                <SaveButton onPress={handleSave} disabled={saving}>
                                    <Save size={16} color="white" />
                                    <Text style={{ marginLeft: 6, color: 'white', fontWeight: '500' }}>
                                        {saving ? 'Saving...' : 'Save'}
                                    </Text>
                                </SaveButton>
                                <CloseButton onPress={onClose}>
                                    <X size={20} color="$gray11" />
                                </CloseButton>
                            </View>
                        </ModalHeader>

                        <ScrollView showsVerticalScrollIndicator={false}>
                            {/* Content */}
                            <FormSection>
                                <SectionTitle>Content</SectionTitle>
                                <ContentInput
                                    value={content}
                                    onChangeText={setContent}
                                    placeholder="Enter memory content..."
                                    placeholderTextColor="$gray9"
                                    multiline
                                    autoFocus
                                />
                            </FormSection>

                            {/* Memory Type */}
                            <FormSection>
                                <SectionTitle>Type</SectionTitle>
                                <TypeSelector>
                                    {MEMORY_TYPES.map((type) => (
                                        <TypeOption
                                            key={type.type}
                                            onPress={() => setMemoryType(type.type)}
                                            style={{
                                                backgroundColor: memoryType === type.type ? type.color + '20' : '$gray2',
                                                borderColor: memoryType === type.type ? type.color : 'transparent',
                                            }}
                                        >
                                            {type.icon}
                                            <Text style={{
                                                marginLeft: 6,
                                                color: memoryType === type.type ? type.color : '$gray11',
                                                fontWeight: memoryType === type.type ? '600' : 'normal',
                                                fontSize: 14,
                                            }}>
                                                {type.label}
                                            </Text>
                                        </TypeOption>
                                    ))}
                                </TypeSelector>
                                <Text style={{ 
                                    marginTop: 8, 
                                    fontSize: 12, 
                                    color: '$gray9',
                                    fontStyle: 'italic',
                                }}>
                                    {MEMORY_TYPES.find(t => t.type === memoryType)?.description}
                                </Text>
                            </FormSection>

                            {/* Importance */}
                            <FormSection>
                                <SectionTitle>Importance</SectionTitle>
                                {renderImportanceStars()}
                            </FormSection>

                            {/* Platform */}
                            <FormSection>
                                <SectionTitle>Platform (Optional)</SectionTitle>
                                <PlatformSelector>
                                    <PlatformOption
                                        onPress={() => setSelectedPlatform(undefined)}
                                        style={{
                                            backgroundColor: !selectedPlatform ? '$gray6' : '$gray2',
                                            borderColor: !selectedPlatform ? '$gray8' : 'transparent',
                                        }}
                                    >
                                        <Text style={{
                                            color: !selectedPlatform ? '$color' : '$gray11',
                                            fontWeight: !selectedPlatform ? '600' : 'normal',
                                            fontSize: 14,
                                        }}>
                                            None
                                        </Text>
                                    </PlatformOption>
                                    {Object.entries(PLATFORM_NAMES).map(([key, name]) => (
                                        <PlatformOption
                                            key={key}
                                            onPress={() => setSelectedPlatform(key as PlatformType)}
                                            style={{
                                                backgroundColor: selectedPlatform === key ? PLATFORM_COLORS[key as PlatformType] + '20' : '$gray2',
                                                borderColor: selectedPlatform === key ? PLATFORM_COLORS[key as PlatformType] : 'transparent',
                                            }}
                                        >
                                            <View style={{
                                                width: 12,
                                                height: 12,
                                                borderRadius: 6,
                                                backgroundColor: PLATFORM_COLORS[key as PlatformType],
                                                marginRight: 6,
                                            }} />
                                            <Text style={{
                                                color: selectedPlatform === key ? PLATFORM_COLORS[key as PlatformType] : '$gray11',
                                                fontWeight: selectedPlatform === key ? '600' : 'normal',
                                                fontSize: 14,
                                            }}>
                                                {name}
                                            </Text>
                                        </PlatformOption>
                                    ))}
                                </PlatformSelector>
                            </FormSection>

                            {/* Tags */}
                            <FormSection style={{ borderBottomWidth: 0 }}>
                                <SectionTitle>Tags (Optional)</SectionTitle>
                                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                                    <TagInput
                                        value={newTag}
                                        onChangeText={setNewTag}
                                        placeholder="Add a tag..."
                                        placeholderTextColor="$gray9"
                                        onSubmitEditing={handleAddTag}
                                        returnKeyType="done"
                                    />
                                    <TouchableOpacity
                                        onPress={handleAddTag}
                                        style={{
                                            backgroundColor: '$blue8',
                                            borderRadius: 6,
                                            padding: 8,
                                            marginLeft: 8,
                                        }}
                                    >
                                        <Plus size={16} color="white" />
                                    </TouchableOpacity>
                                </View>
                                
                                {tags.length > 0 && (
                                    <TagContainer>
                                        {tags.map((tag) => (
                                            <TagChip key={tag}>
                                                <Tag size={12} color="$blue11" />
                                                <Text style={{ 
                                                    marginLeft: 4, 
                                                    fontSize: 12, 
                                                    color: '$blue11',
                                                }}>
                                                    {tag}
                                                </Text>
                                                <RemoveTagButton onPress={() => handleRemoveTag(tag)}>
                                                    <X size={12} color="$blue11" />
                                                </RemoveTagButton>
                                            </TagChip>
                                        ))}
                                    </TagContainer>
                                )}
                            </FormSection>
                        </ScrollView>
                    </ModalContainer>
                </ModalOverlay>
            </KeyboardAvoidingView>
        </Modal>
    );
};

export default MemoryEditor;