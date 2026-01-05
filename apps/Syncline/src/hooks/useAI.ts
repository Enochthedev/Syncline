/**
 * AI Features Hooks
 * 
 * React hooks for AI-powered features:
 * - Semantic search across messages and memories
 * - Entity extraction and analysis
 * - Summary generation
 * - AI insights and pattern analysis
 */

import { useState, useCallback, useMemo } from 'react';
import { aiAPI, platformAI } from '../api/endpoints/ai';
import {
    SemanticSearchResult,
    SearchResults,
    SearchFilters,
    EntityExtraction,
    AIInsight,
    Platform,
} from '../types';

// =============================================================================
// Semantic Search Hook
// =============================================================================

export const useSemanticSearch = () => {
    const [results, setResults] = useState<SemanticSearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const search = useCallback(async (
        query: string,
        filters?: SearchFilters,
        limit: number = 20
    ) => {
        if (!query.trim()) {
            setResults([]);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const searchResults = await aiAPI.semanticSearch(query, filters, limit);
            setResults(searchResults);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Search failed');
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const clearResults = useCallback(() => {
        setResults([]);
        setError(null);
    }, []);

    return {
        results,
        loading,
        error,
        search,
        clearResults,
    };
};

// =============================================================================
// Unified Search Hook
// =============================================================================

export const useUnifiedSearch = () => {
    const [results, setResults] = useState<SearchResults | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const search = useCallback(async (
        query: string,
        filters?: SearchFilters,
        limit: number = 20
    ) => {
        if (!query.trim()) {
            setResults(null);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const searchResults = await aiAPI.unifiedSearch(query, filters, limit);
            setResults(searchResults);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Search failed');
            setResults(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const clearResults = useCallback(() => {
        setResults(null);
        setError(null);
    }, []);

    return {
        results,
        loading,
        error,
        search,
        clearResults,
    };
};

// =============================================================================
// Entity Extraction Hook
// =============================================================================

export const useEntityExtraction = () => {
    const [entities, setEntities] = useState<EntityExtraction[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const extractEntities = useCallback(async (text: string) => {
        if (!text.trim()) {
            setEntities([]);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const extractedEntities = await aiAPI.extractEntities(text);
            setEntities(extractedEntities);
            return extractedEntities;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Entity extraction failed');
            setEntities([]);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const clearEntities = useCallback(() => {
        setEntities([]);
        setError(null);
    }, []);

    return {
        entities,
        loading,
        error,
        extractEntities,
        clearEntities,
    };
};

// =============================================================================
// Summary Generation Hook
// =============================================================================

export const useSummaryGeneration = () => {
    const [summary, setSummary] = useState<{
        content: string;
        type: string;
        confidence: number;
        key_topics: string[];
    } | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const generateSummary = useCallback(async (
        threadId: string,
        summaryType: 'brief' | 'detailed' | 'insight' = 'brief'
    ) => {
        setLoading(true);
        setError(null);

        try {
            const generatedSummary = await aiAPI.generateSummary(threadId, summaryType);
            setSummary(generatedSummary);
            return generatedSummary;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Summary generation failed');
            setSummary(null);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const clearSummary = useCallback(() => {
        setSummary(null);
        setError(null);
    }, []);

    return {
        summary,
        loading,
        error,
        generateSummary,
        clearSummary,
    };
};

// =============================================================================
// Contact Insights Hook
// =============================================================================

export const useContactInsights = (contactId?: string) => {
    const [insights, setInsights] = useState<AIInsight[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const generateInsights = useCallback(async (targetContactId?: string) => {
        const id = targetContactId || contactId;
        if (!id) return;

        setLoading(true);
        setError(null);

        try {
            const contactInsights = await aiAPI.generateContactInsights(id);
            setInsights(contactInsights);
            return contactInsights;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Insights generation failed');
            setInsights([]);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [contactId]);

    const clearInsights = useCallback(() => {
        setInsights([]);
        setError(null);
    }, []);

    return {
        insights,
        loading,
        error,
        generateInsights,
        clearInsights,
    };
};

// =============================================================================
// Pattern Analysis Hook
// =============================================================================

export const usePatternAnalysis = () => {
    const [analysis, setAnalysis] = useState<{
        communication_frequency: Record<string, number>;
        topic_trends: Array<{
            topic: string;
            frequency: number;
            trend: 'increasing' | 'decreasing' | 'stable';
        }>;
        sentiment_analysis: {
            overall_sentiment: 'positive' | 'neutral' | 'negative';
            sentiment_over_time: Array<{
                date: string;
                sentiment: number;
            }>;
        };
        response_patterns: {
            avg_response_time: number;
            response_rate: number;
        };
    } | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const analyzePatterns = useCallback(async (options?: {
        contact_id?: string;
        platform?: string;
        date_range?: {
            start: string;
            end: string;
        };
    }) => {
        setLoading(true);
        setError(null);

        try {
            const patternAnalysis = await aiAPI.analyzePatterns(options);
            setAnalysis(patternAnalysis);
            return patternAnalysis;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Pattern analysis failed');
            setAnalysis(null);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const clearAnalysis = useCallback(() => {
        setAnalysis(null);
        setError(null);
    }, []);

    return {
        analysis,
        loading,
        error,
        analyzePatterns,
        clearAnalysis,
    };
};

// =============================================================================
// AI Processing Status Hook
// =============================================================================

export const useAIProcessingStatus = () => {
    const [status, setStatus] = useState<{
        status: 'active' | 'inactive' | 'error';
        models_available: string[];
        current_model: string;
        processing_queue: number;
        last_processing: string;
    } | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStatus = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const processingStatus = await aiAPI.getProcessingStatus();
            setStatus(processingStatus);
            return processingStatus;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch AI status');
            setStatus(null);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const triggerProcessing = useCallback(async (options?: {
        platform?: string;
        contact_id?: string;
        since?: string;
        force_reprocess?: boolean;
    }) => {
        try {
            const result = await aiAPI.triggerProcessing(options);
            return result;
        } catch (err) {
            throw err;
        }
    }, []);

    return {
        status,
        loading,
        error,
        fetchStatus,
        triggerProcessing,
    };
};

// =============================================================================
// Platform-Specific AI Insights Hooks
// =============================================================================

export const usePlatformInsights = (platform: Platform, connectionId?: string) => {
    const [insights, setInsights] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchInsights = useCallback(async (targetConnectionId?: string) => {
        const id = targetConnectionId || connectionId;
        if (!id) return;

        setLoading(true);
        setError(null);

        try {
            let platformInsights;

            switch (platform) {
                case 'slack':
                    platformInsights = await platformAI.getSlackInsights(id);
                    break;
                case 'discord':
                    platformInsights = await platformAI.getDiscordInsights(id);
                    break;
                case 'gmail':
                    platformInsights = await platformAI.getGmailInsights(id);
                    break;
                case 'whatsapp':
                    platformInsights = await platformAI.getWhatsAppInsights(id);
                    break;
                default:
                    throw new Error(`Insights not available for platform: ${platform}`);
            }

            setInsights(platformInsights);
            return platformInsights;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch platform insights');
            setInsights(null);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [platform, connectionId]);

    const clearInsights = useCallback(() => {
        setInsights(null);
        setError(null);
    }, []);

    return {
        insights,
        loading,
        error,
        fetchInsights,
        clearInsights,
    };
};

// =============================================================================
// Combined AI Hook (Main Export)
// =============================================================================

export const useAI = () => {
    const semanticSearch = useSemanticSearch();
    const unifiedSearch = useUnifiedSearch();
    const entityExtraction = useEntityExtraction();
    const summaryGeneration = useSummaryGeneration();
    const patternAnalysis = usePatternAnalysis();
    const processingStatus = useAIProcessingStatus();

    // Convenience methods that combine multiple operations
    const searchWithEntities = useCallback(async (
        query: string,
        filters?: SearchFilters,
        limit: number = 20
    ) => {
        const [searchResults, entities] = await Promise.all([
            aiAPI.unifiedSearch(query, filters, limit),
            aiAPI.extractEntities(query),
        ]);

        return {
            results: searchResults,
            queryEntities: entities,
        };
    }, []);

    const analyzeText = useCallback(async (text: string) => {
        const entities = await aiAPI.extractEntities(text);

        return {
            entities,
            entityTypes: [...new Set(entities.map(e => e.type))],
            highConfidenceEntities: entities.filter(e => e.confidence > 0.8),
        };
    }, []);

    return {
        // Individual hooks
        semanticSearch: semanticSearch.search,
        unifiedSearch: unifiedSearch.search,
        extractEntities: entityExtraction.extractEntities,
        generateSummary: summaryGeneration.generateSummary,
        analyzePatterns: patternAnalysis.analyzePatterns,
        getProcessingStatus: processingStatus.fetchStatus,
        triggerProcessing: processingStatus.triggerProcessing,

        // Combined operations
        searchWithEntities,
        analyzeText,

        // Loading states
        loading: semanticSearch.loading || unifiedSearch.loading || entityExtraction.loading ||
            summaryGeneration.loading || patternAnalysis.loading || processingStatus.loading,

        // Error states
        error: semanticSearch.error || unifiedSearch.error || entityExtraction.error ||
            summaryGeneration.error || patternAnalysis.error || processingStatus.error,

        // Results
        semanticResults: semanticSearch.results,
        unifiedResults: unifiedSearch.results,
        entities: entityExtraction.entities,
        summary: summaryGeneration.summary,
        patterns: patternAnalysis.analysis,
        aiStatus: processingStatus.status,

        // Clear methods
        clearSemanticResults: semanticSearch.clearResults,
        clearUnifiedResults: unifiedSearch.clearResults,
        clearEntities: entityExtraction.clearEntities,
        clearSummary: summaryGeneration.clearSummary,
        clearPatterns: patternAnalysis.clearAnalysis,
    };
};