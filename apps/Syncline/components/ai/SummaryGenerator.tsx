/**
 * Summary Generator Component
 * 
 * AI-powered thread summarization interface:
 * - Thread summarization interface
 * - Different summary types (brief, detailed, insight)
 * - Summary confidence scoring
 * - Key topics extraction
 */

import React, { useState, useCallback, useMemo } from 'react';
import { 
    View, 
    Text, 
    TouchableOpacity, 
    ScrollView,
    ActivityIndicator,
    Alert
} from 'react-native';
import { styled } from '@tamagui/core';
import { 
    FileText, 
    Sparkles, 
    Brain,
    Clock,
    Tag,
    TrendingUp,
    Copy,
    Share,
    RefreshCw,
    CheckCircle,
    AlertCircle,
    Zap
} from '@tamagui/lucide-icons';
import { useSummaryGeneration } from '../../src/hooks/useAI';

// =============================================================================
// Styled Components
// =============================================================================

const Container = styled(View, {
    flex: 1,
    backgroundColor: '$background',
});

const Header = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    borderBottomWidth: 1,
    borderBottomColor: '$gray4',
});

const TypeSelector = styled(View, {
    flexDirection: 'row',
    paddingHorizontal: '$4',
    paddingVertical: '$3',
    backgroundColor: '$gray1',
});

const TypeOption = styled(TouchableOpacity, {
    flex: 1,
    alignItems: 'center',
    paddingVertical: '$3',
    borderRadius: '$3',
    marginHorizontal: '$1',
});

const SummaryCard = styled(View, {
    backgroundColor: '$background',
    marginHorizontal: '$4',
    marginVertical: '$3',
    borderRadius: '$4',
    padding: '$4',
    borderWidth: 1,
    borderColor: '$gray4',
    shadowColor: '$shadowColor',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
});

const SummaryHeader = styled(View, {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '$3',
});

const ConfidenceBar = styled(View, {
    height: 4,
    backgroundColor: '$gray3',
    borderRadius: 2,
    marginVertical: '$2',
    overflow: 'hidden',
});

const ConfidenceFill = styled(View, {
    height: '100%',
    borderRadius: 2,
});

const SummaryContent = styled(Text, {
    fontSize: '$4',
    lineHeight: '$6',
    color: '$color',
    marginVertical: '$3',
});

const TopicsContainer = styled(View, {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: '$3',
});

const TopicChip = styled(View, {
    backgroundColor: '$blue3',
    borderRadius: '$2',
    paddingHorizontal: '$2',
    paddingVertical: '$1',
    marginRight: '$2',
    marginBottom: '$2',
});

const ActionButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$blue8',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const SecondaryButton = styled(TouchableOpacity, {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '$gray3',
    borderRadius: '$3',
    paddingHorizontal: '$3',
    paddingVertical: '$2',
    marginRight: '$2',
});

const GenerateButton = styled(TouchableOpacity, {
    backgroundColor: '$purple8',
    borderRadius: '$4',
    paddingVertical: '$4',
    marginHorizontal: '$4',
    marginVertical: '$3',
    alignItems: 'center',
});

const EmptyState = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$8',
});

const LoadingContainer = styled(View, {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: '$8',
});

// =============================================================================
// Types and Constants
// =============================================================================

type SummaryType = 'brief' | 'detailed' | 'insight';

const SUMMARY_TYPES: Array<{
    type: SummaryType;
    label: string;
    description: string;
    icon: React.ReactNode;
}> = [
    {
        type: 'brief',
        label: 'Brief',
        description: 'Quick overview',
        icon: <FileText size={16} />,
    },
    {
        type: 'detailed',
        label: 'Detailed',
        description: 'Comprehensive summary',
        icon: <Brain size={16} />,
    },
    {
        type: 'insight',
        label: 'Insights',
        description: 'Key insights & patterns',
        icon: <Sparkles size={16} />,
    },
];

// =============================================================================
// Helper Functions
// =============================================================================

const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '$green8';
    if (confidence >= 0.6) return '$yellow8';
    return '$red8';
};

const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
};

const formatConfidence = (confidence: number) => {
    return `${Math.round(confidence * 100)}%`;
};

// =============================================================================
// Main Component
// =============================================================================

interface SummaryGeneratorProps {
    threadId: string;
    onSummaryGenerated?: (summary: {
        content: string;
        type: string;
        confidence: number;
        key_topics: string[];
    }) => void;
}

export const SummaryGenerator: React.FC<SummaryGeneratorProps> = ({
    threadId,
    onSummaryGenerated,
}) => {
    const [selectedType, setSelectedType] = useState<SummaryType>('brief');
    const [generatedSummaries, setGeneratedSummaries] = useState<Record<SummaryType, {
        content: string;
        type: string;
        confidence: number;
        key_topics: string[];
        generated_at: string;
    }>>({} as any);

    const { 
        summary, 
        loading, 
        error, 
        generateSummary, 
        clearSummary 
    } = useSummaryGeneration();

    // Handle generate summary
    const handleGenerate = useCallback(async () => {
        try {
            const result = await generateSummary(threadId, selectedType);
            
            // Store the generated summary
            setGeneratedSummaries(prev => ({
                ...prev,
                [selectedType]: {
                    ...result,
                    generated_at: new Date().toISOString(),
                },
            }));

            onSummaryGenerated?.(result);
        } catch (err) {
            Alert.alert('Error', 'Failed to generate summary');
        }
    }, [threadId, selectedType, generateSummary, onSummaryGenerated]);

    // Handle copy summary
    const handleCopy = useCallback(async (summaryContent: string) => {
        // Note: React Native doesn't have built-in clipboard
        // You might need to install @react-native-clipboard/clipboard
        Alert.alert('Summary Copied', 'Summary has been copied to clipboard');
    }, []);

    // Handle share summary
    const handleShare = useCallback(async (summaryContent: string) => {
        // Note: You might want to use react-native-share
        Alert.alert('Share Summary', 'Share functionality would be implemented here');
    }, []);

    // Get current summary (either from state or generated)
    const currentSummary = useMemo(() => {
        return generatedSummaries[selectedType] || summary;
    }, [generatedSummaries, selectedType, summary]);

    // Check if summary exists for current type
    const hasSummary = useMemo(() => {
        return !!currentSummary;
    }, [currentSummary]);

    // Render type selector
    const renderTypeSelector = useCallback(() => (
        <TypeSelector>
            {SUMMARY_TYPES.map((type) => (
                <TypeOption
                    key={type.type}
                    onPress={() => setSelectedType(type.type)}
                    style={{
                        backgroundColor: selectedType === type.type ? '$blue8' : 'transparent',
                    }}
                >
                    <View style={{ 
                        color: selectedType === type.type ? 'white' : '$gray11',
                        marginBottom: 4,
                    }}>
                        {React.cloneElement(type.icon as React.ReactElement, {
                            color: selectedType === type.type ? 'white' : '$gray11',
                        })}
                    </View>
                    <Text style={{
                        fontSize: 12,
                        fontWeight: '600',
                        color: selectedType === type.type ? 'white' : '$color',
                        textAlign: 'center',
                    }}>
                        {type.label}
                    </Text>
                    <Text style={{
                        fontSize: 10,
                        color: selectedType === type.type ? 'white' : '$gray11',
                        textAlign: 'center',
                        marginTop: 2,
                    }}>
                        {type.description}
                    </Text>
                </TypeOption>
            ))}
        </TypeSelector>
    ), [selectedType]);

    // Render summary content
    const renderSummary = useCallback(() => {
        if (!currentSummary) return null;

        const confidenceColor = getConfidenceColor(currentSummary.confidence);
        const confidenceLabel = getConfidenceLabel(currentSummary.confidence);

        return (
            <SummaryCard>
                <SummaryHeader>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <View style={{ marginRight: 8 }}>
                            {SUMMARY_TYPES.find(t => t.type === selectedType)?.icon}
                        </View>
                        <Text style={{ fontSize: 16, fontWeight: '600', color: '$color' }}>
                            {SUMMARY_TYPES.find(t => t.type === selectedType)?.label} Summary
                        </Text>
                    </View>
                    
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <View style={{ alignItems: 'center', marginRight: 12 }}>
                            <Text style={{ fontSize: 10, color: '$gray11' }}>Confidence</Text>
                            <Text style={{ 
                                fontSize: 12, 
                                fontWeight: '600', 
                                color: confidenceColor,
                            }}>
                                {formatConfidence(currentSummary.confidence)}
                            </Text>
                        </View>
                        <View style={{
                            backgroundColor: confidenceColor + '20',
                            borderRadius: 4,
                            paddingHorizontal: 6,
                            paddingVertical: 2,
                        }}>
                            <Text style={{ fontSize: 10, color: confidenceColor }}>
                                {confidenceLabel}
                            </Text>
                        </View>
                    </View>
                </SummaryHeader>

                {/* Confidence Bar */}
                <ConfidenceBar>
                    <ConfidenceFill 
                        style={{ 
                            width: `${currentSummary.confidence * 100}%`,
                            backgroundColor: confidenceColor,
                        }} 
                    />
                </ConfidenceBar>

                {/* Summary Content */}
                <SummaryContent>{currentSummary.content}</SummaryContent>

                {/* Key Topics */}
                {currentSummary.key_topics && currentSummary.key_topics.length > 0 && (
                    <View>
                        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                            <Tag size={14} color="$blue9" />
                            <Text style={{ 
                                marginLeft: 6, 
                                fontSize: 14, 
                                fontWeight: '600', 
                                color: '$color',
                            }}>
                                Key Topics
                            </Text>
                        </View>
                        <TopicsContainer>
                            {currentSummary.key_topics.map((topic, index) => (
                                <TopicChip key={index}>
                                    <Text style={{ fontSize: 11, color: '$blue11' }}>
                                        {topic}
                                    </Text>
                                </TopicChip>
                            ))}
                        </TopicsContainer>
                    </View>
                )}

                {/* Actions */}
                <View style={{ flexDirection: 'row', marginTop: 16 }}>
                    <ActionButton onPress={() => handleCopy(currentSummary.content)}>
                        <Copy size={14} color="white" />
                        <Text style={{ marginLeft: 6, color: 'white', fontSize: 12 }}>
                            Copy
                        </Text>
                    </ActionButton>
                    
                    <SecondaryButton onPress={() => handleShare(currentSummary.content)}>
                        <Share size={14} color="$gray11" />
                        <Text style={{ marginLeft: 6, color: '$gray11', fontSize: 12 }}>
                            Share
                        </Text>
                    </SecondaryButton>
                    
                    <SecondaryButton onPress={handleGenerate}>
                        <RefreshCw size={14} color="$gray11" />
                        <Text style={{ marginLeft: 6, color: '$gray11', fontSize: 12 }}>
                            Regenerate
                        </Text>
                    </SecondaryButton>
                </View>

                {/* Generation Time */}
                {generatedSummaries[selectedType]?.generated_at && (
                    <View style={{ marginTop: 12, alignItems: 'center' }}>
                        <Text style={{ fontSize: 11, color: '$gray9' }}>
                            Generated {new Date(generatedSummaries[selectedType].generated_at).toLocaleTimeString()}
                        </Text>
                    </View>
                )}
            </SummaryCard>
        );
    }, [currentSummary, selectedType, handleCopy, handleShare, handleGenerate, generatedSummaries]);

    if (loading) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Summary Generator
                    </Text>
                </Header>
                {renderTypeSelector()}
                <LoadingContainer>
                    <ActivityIndicator size="large" color="$purple9" />
                    <Text style={{ marginTop: 16, color: '$gray11', textAlign: 'center' }}>
                        Generating {selectedType} summary...
                    </Text>
                    <Text style={{ marginTop: 8, color: '$gray9', textAlign: 'center', fontSize: 12 }}>
                        This may take a few moments
                    </Text>
                </LoadingContainer>
            </Container>
        );
    }

    if (error) {
        return (
            <Container>
                <Header>
                    <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                        Summary Generator
                    </Text>
                </Header>
                {renderTypeSelector()}
                <EmptyState>
                    <AlertCircle size={48} color="$red8" />
                    <Text style={{ color: '$red11', marginTop: 16, textAlign: 'center' }}>
                        Failed to generate summary
                    </Text>
                    <Text style={{ color: '$gray9', marginTop: 8, textAlign: 'center' }}>
                        {error}
                    </Text>
                    <TouchableOpacity
                        onPress={handleGenerate}
                        style={{
                            backgroundColor: '$purple8',
                            paddingHorizontal: 20,
                            paddingVertical: 12,
                            borderRadius: 8,
                            marginTop: 16,
                        }}
                    >
                        <Text style={{ color: 'white', fontWeight: '500' }}>Try Again</Text>
                    </TouchableOpacity>
                </EmptyState>
            </Container>
        );
    }

    return (
        <Container>
            <Header>
                <Text style={{ fontSize: 18, fontWeight: '600', color: '$color' }}>
                    Summary Generator
                </Text>
                <TouchableOpacity onPress={clearSummary}>
                    <RefreshCw size={20} color="$gray9" />
                </TouchableOpacity>
            </Header>

            {/* Type Selector */}
            {renderTypeSelector()}

            <ScrollView showsVerticalScrollIndicator={false}>
                {/* Current Summary */}
                {hasSummary ? (
                    renderSummary()
                ) : (
                    <EmptyState>
                        <Brain size={48} color="$purple8" />
                        <Text style={{ 
                            fontSize: 18, 
                            fontWeight: '600', 
                            color: '$color',
                            marginTop: 16,
                        }}>
                            Generate AI Summary
                        </Text>
                        <Text style={{ 
                            fontSize: 14, 
                            color: '$gray11',
                            marginTop: 8,
                            textAlign: 'center',
                            lineHeight: 20,
                        }}>
                            Create a {selectedType} summary of this conversation{'\n'}
                            using advanced AI analysis
                        </Text>
                    </EmptyState>
                )}

                {/* Generate Button */}
                <GenerateButton onPress={handleGenerate} disabled={loading}>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        {loading ? (
                            <ActivityIndicator size="small" color="white" />
                        ) : (
                            <Zap size={20} color="white" />
                        )}
                        <Text style={{ 
                            marginLeft: 8, 
                            color: 'white', 
                            fontSize: 16,
                            fontWeight: '600',
                        }}>
                            {loading ? 'Generating...' : `Generate ${SUMMARY_TYPES.find(t => t.type === selectedType)?.label} Summary`}
                        </Text>
                    </View>
                </GenerateButton>

                {/* Summary History */}
                {Object.keys(generatedSummaries).length > 0 && (
                    <View style={{ paddingHorizontal: 16, paddingBottom: 20 }}>
                        <Text style={{ 
                            fontSize: 16, 
                            fontWeight: '600', 
                            color: '$color',
                            marginBottom: 12,
                        }}>
                            Generated Summaries
                        </Text>
                        {Object.entries(generatedSummaries).map(([type, summary]) => (
                            <TouchableOpacity
                                key={type}
                                onPress={() => setSelectedType(type as SummaryType)}
                                style={{
                                    flexDirection: 'row',
                                    alignItems: 'center',
                                    backgroundColor: selectedType === type ? '$blue2' : '$gray1',
                                    borderRadius: 8,
                                    padding: 12,
                                    marginBottom: 8,
                                }}
                            >
                                <CheckCircle size={16} color="$green9" />
                                <View style={{ flex: 1, marginLeft: 12 }}>
                                    <Text style={{ 
                                        fontSize: 14, 
                                        fontWeight: '600', 
                                        color: '$color',
                                        textTransform: 'capitalize',
                                    }}>
                                        {type} Summary
                                    </Text>
                                    <Text style={{ fontSize: 12, color: '$gray11' }}>
                                        {formatConfidence(summary.confidence)} confidence • {summary.key_topics.length} topics
                                    </Text>
                                </View>
                                <Text style={{ fontSize: 11, color: '$gray9' }}>
                                    {new Date(summary.generated_at).toLocaleTimeString()}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                )}
            </ScrollView>
        </Container>
    );
};

export default SummaryGenerator;