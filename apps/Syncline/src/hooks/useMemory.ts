/**
 * Memory Management Hooks
 * 
 * React hooks for interacting with the memory system:
 * - Memory search and retrieval
 * - Proactive recommendations
 * - Memory CRUD operations
 * - Real-time memory updates
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { memoryAPI } from '../api/endpoints/ai';
import {
    Memory,
    MemorySearchResult,
    MemoryRecommendation,
    MemoryExtractionResult,
    MemoryStats,
    MemoryType,
    MemoryImportance,
} from '../types';

// =============================================================================
// Memory Search Hook
// =============================================================================

export const useMemorySearch = () => {
    const [results, setResults] = useState<MemorySearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const searchMemories = useCallback(async (
        query: string,
        options?: {
            contact_id?: string;
            memory_types?: MemoryType[];
            importance_min?: MemoryImportance;
            platform?: string;
            limit?: number;
        }
    ) => {
        if (!query.trim()) {
            setResults([]);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const searchResults = await memoryAPI.searchMemories(query, options);
            setResults(searchResults);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to search memories');
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
        searchMemories,
        clearResults,
    };
};

// =============================================================================
// Memory Recommendations Hook
// =============================================================================

export const useMemoryRecommendations = (
    context?: {
        current_contact?: string;
        current_thread?: string;
        current_platform?: string;
        keywords?: string[];
    }
) => {
    const [recommendations, setRecommendations] = useState<MemoryRecommendation[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchRecommendations = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const recs = await memoryAPI.getRecommendations(context);
            setRecommendations(recs);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch recommendations');
            setRecommendations([]);
        } finally {
            setLoading(false);
        }
    }, [context]);

    useEffect(() => {
        fetchRecommendations();
    }, [fetchRecommendations]);

    const refreshRecommendations = useCallback(() => {
        fetchRecommendations();
    }, [fetchRecommendations]);

    // Filter recommendations by priority
    const highPriorityRecommendations = useMemo(
        () => recommendations.filter(rec => rec.priority >= 0.7),
        [recommendations]
    );

    const mediumPriorityRecommendations = useMemo(
        () => recommendations.filter(rec => rec.priority >= 0.4 && rec.priority < 0.7),
        [recommendations]
    );

    const lowPriorityRecommendations = useMemo(
        () => recommendations.filter(rec => rec.priority < 0.4),
        [recommendations]
    );

    return {
        recommendations,
        highPriorityRecommendations,
        mediumPriorityRecommendations,
        lowPriorityRecommendations,
        loading,
        error,
        refreshRecommendations,
    };
};

// =============================================================================
// Memory CRUD Hook
// =============================================================================

export const useMemory = (memoryId?: string) => {
    const [memory, setMemory] = useState<Memory | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchMemory = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            const mem = await memoryAPI.getMemory(id);
            setMemory(mem);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch memory');
            setMemory(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const createMemory = useCallback(async (memoryData: {
        type: MemoryType;
        content: string;
        importance: MemoryImportance;
        contact_id?: string;
        thread_id?: string;
        platform?: string;
        metadata?: Record<string, any>;
    }) => {
        setLoading(true);
        setError(null);

        try {
            const newMemory = await memoryAPI.createMemory(memoryData);
            setMemory(newMemory);
            return newMemory;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create memory');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const updateMemory = useCallback(async (
        id: string,
        updates: {
            content?: string;
            importance?: MemoryImportance;
            metadata?: Record<string, any>;
        }
    ) => {
        setLoading(true);
        setError(null);

        try {
            const updatedMemory = await memoryAPI.updateMemory(id, updates);
            setMemory(updatedMemory);
            return updatedMemory;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update memory');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const deleteMemory = useCallback(async (id: string) => {
        setLoading(true);
        setError(null);

        try {
            await memoryAPI.deleteMemory(id);
            setMemory(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete memory');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (memoryId) {
            fetchMemory(memoryId);
        }
    }, [memoryId, fetchMemory]);

    return {
        memory,
        loading,
        error,
        createMemory,
        updateMemory,
        deleteMemory,
        refetch: memoryId ? () => fetchMemory(memoryId) : undefined,
    };
};

// =============================================================================
// Contact Memories Hook
// =============================================================================

export const useContactMemories = (
    contactId: string,
    options?: {
        memory_types?: MemoryType[];
        limit?: number;
    }
) => {
    const [memories, setMemories] = useState<Memory[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchMemories = useCallback(async () => {
        if (!contactId) return;

        setLoading(true);
        setError(null);

        try {
            const contactMemories = await memoryAPI.getContactMemories(contactId, options);
            setMemories(contactMemories);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch contact memories');
            setMemories([]);
        } finally {
            setLoading(false);
        }
    }, [contactId, options]);

    useEffect(() => {
        fetchMemories();
    }, [fetchMemories]);

    // Group memories by type
    const memoriesByType = useMemo(() => {
        const grouped: Record<MemoryType, Memory[]> = {
            fact: [],
            commitment: [],
            preference: [],
            relationship: [],
            personal: [],
            task: [],
            event: [],
            insight: [],
        };

        memories.forEach(memory => {
            grouped[memory.type].push(memory);
        });

        return grouped;
    }, [memories]);

    // Get important memories (importance >= 4)
    const importantMemories = useMemo(
        () => memories.filter(memory => memory.importance >= 4),
        [memories]
    );

    // Get recent memories (last 30 days)
    const recentMemories = useMemo(() => {
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        return memories.filter(memory => 
            new Date(memory.created_at) > thirtyDaysAgo
        );
    }, [memories]);

    return {
        memories,
        memoriesByType,
        importantMemories,
        recentMemories,
        loading,
        error,
        refetch: fetchMemories,
    };
};

// =============================================================================
// Memory Extraction Hook
// =============================================================================

export const useMemoryExtraction = () => {
    const [extractionResult, setExtractionResult] = useState<MemoryExtractionResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const extractFromMessage = useCallback(async (messageId: string) => {
        setLoading(true);
        setError(null);

        try {
            const result = await memoryAPI.extractFromMessage(messageId);
            setExtractionResult(result);
            return result;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to extract memories');
            setExtractionResult(null);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const clearResult = useCallback(() => {
        setExtractionResult(null);
        setError(null);
    }, []);

    return {
        extractionResult,
        loading,
        error,
        extractFromMessage,
        clearResult,
    };
};

// =============================================================================
// Memory Statistics Hook
// =============================================================================

export const useMemoryStats = () => {
    const [stats, setStats] = useState<MemoryStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStats = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const memoryStats = await memoryAPI.getStats();
            setStats(memoryStats);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch memory statistics');
            setStats(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    return {
        stats,
        loading,
        error,
        refetch: fetchStats,
    };
};