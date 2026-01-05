export interface User {
    id: string;
    email: string;
    full_name?: string;
}

export type Platform = 'gmail' | 'slack' | 'discord' | 'telegram' | 'twitter' | 'whatsapp' | 'linkedin' | 'google_chat';

// Platform display names
export const PLATFORM_NAMES: Record<Platform, string> = {
    gmail: 'Gmail',
    slack: 'Slack',
    discord: 'Discord',
    telegram: 'Telegram',
    twitter: 'X',
    whatsapp: 'WhatsApp',
    linkedin: 'LinkedIn',
    google_chat: 'Google Chat',
};

// Platform colors
export const PLATFORM_COLORS: Record<Platform, string> = {
    gmail: '#EA4335',
    slack: '#4A154B',
    discord: '#5865F2',
    telegram: '#0088cc',
    twitter: '#000000',
    whatsapp: '#25D366',
    linkedin: '#0077B5',
    google_chat: '#00AC47',
};

export interface Connection {
    id: string;
    platform: Platform;
    status: 'active' | 'inactive' | 'revoked' | 'pending' | 'error' | 'disconnected';
    connected_at?: string;
    last_sync_at?: string;
    updated_at?: string;
    created_at?: string;
    platform_metadata?: Record<string, any>;
    metadata?: Record<string, any>;
}

export interface Message {
    id: string;
    platform: Platform;
    content: string;
    sender: string;
    timestamp: string;
    thread_id?: string;
    has_attachments?: boolean;
    sentiment_score?: number;
}

export interface ChatThread {
    id: string;
    platform: Platform;
    contact_id?: string;
    contact_name?: string;
    phone_number?: string;
    last_message?: string;
    last_message_time?: string;
    unread_count: number;
    platform_metadata?: Record<string, any>;
    is_linked: boolean;
}

export interface ChatMessage {
    id: string;
    thread_id: string;
    platform: Platform;
    sender_name: string;
    content: string;
    timestamp: string;
    is_from_me: boolean;
    has_attachments: boolean;
}

export interface ThreadSummary {
    thread_id: string;
    content: string;
    type: 'brief' | 'detailed' | 'bullet_points';
    generated_at: string;
}

export interface ContactInsight {
    type: 'frequency' | 'topics' | 'sentiment' | 'platforms';
    title: string;
    description: string;
    data: any;
    confidence: number;
}

// =============================================================================
// NEW: AI and Memory Types
// =============================================================================

export type MemoryType = 'fact' | 'commitment' | 'preference' | 'relationship' | 'personal' | 'task' | 'event' | 'insight';

export type MemoryImportance = 1 | 2 | 3 | 4 | 5;

export interface Memory {
    id: string;
    type: MemoryType;
    content: string;
    importance: MemoryImportance;
    contact_id?: string;
    thread_id?: string;
    platform?: Platform;
    source_message_id?: string;
    memory_metadata?: Record<string, any>;
    is_active: boolean;
    access_count: number;
    created_at: string;
    updated_at: string;
    last_accessed_at: string;
}

export interface MemorySearchResult {
    memory_id: string;
    memory_type: MemoryType;
    content: string;
    importance: MemoryImportance;
    relevance_score: number;
    snippet: string;
}

export interface MemoryRecommendation {
    type: string;
    title: string;
    description: string;
    priority: number;
    memory_ids: string[];
    suggested_action?: string;
    due_date?: string;
    contact_id?: string;
}

export interface MemoryExtractionResult {
    memories: Array<{
        type: MemoryType;
        content: string;
        importance: MemoryImportance;
        metadata?: Record<string, any>;
    }>;
    entities_found: string[];
    commitments_found: Array<{
        description: string;
        due_date?: string;
        priority: string;
    }>;
    topics: string[];
    confidence: number;
}

export interface AIInsight {
    id: string;
    type: 'summary' | 'pattern' | 'recommendation' | 'entity' | 'sentiment';
    title: string;
    content: string;
    confidence: number;
    source_messages?: string[];
    generated_at: string;
    metadata?: Record<string, any>;
}

export interface EntityExtraction {
    text: string;
    type: string;
    start_pos: number;
    end_pos: number;
    confidence: number;
    normalized_value?: string;
    context?: string;
}

export interface SemanticSearchResult {
    message_id: string;
    platform: Platform;
    content: string;
    sender: string;
    timestamp: string;
    similarity_score: number;
    snippet: string;
    thread_id?: string;
}

// =============================================================================
// NEW: Platform Connection Types
// =============================================================================

export interface SlackConnection extends Connection {
    platform: 'slack';
    platform_metadata?: {
        team_id?: string;
        team_name?: string;
        user_id?: string;
        bot_id?: string;
        channels_count?: number;
        last_message_sync?: string;
    };
}

export interface DiscordConnection extends Connection {
    platform: 'discord';
    platform_metadata?: {
        bot_id?: string;
        bot_username?: string;
        guilds_count?: number;
        channels_count?: number;
        last_message_sync?: string;
    };
}

export interface GmailConnection extends Connection {
    platform: 'gmail';
    platform_metadata?: {
        email?: string;
        labels_count?: number;
        last_history_id?: string;
        watch_expiration?: string;
    };
}

export interface WhatsAppConnection extends Connection {
    platform: 'whatsapp';
    platform_metadata?: {
        phone_number?: string;
        session_age_seconds?: number;
        bridge_status?: {
            connected: boolean;
            logged_in: boolean;
            phone?: string;
            battery_level?: number;
            platform?: string;
        };
    };
}

// Union type for all connection types
export type PlatformConnection = SlackConnection | DiscordConnection | GmailConnection | WhatsAppConnection;

// =============================================================================
// NEW: Search and Filter Types
// =============================================================================

export interface SearchFilters {
    platforms?: Platform[];
    contacts?: string[];
    date_range?: {
        start: string;
        end: string;
    };
    has_attachments?: boolean;
    sentiment?: 'positive' | 'neutral' | 'negative';
    memory_types?: MemoryType[];
    importance_min?: MemoryImportance;
}

export interface SearchResults {
    messages: SemanticSearchResult[];
    memories: MemorySearchResult[];
    total_messages: number;
    total_memories: number;
    query_time_ms: number;
}

// =============================================================================
// NEW: Analytics Types
// =============================================================================

export interface PlatformStats {
    platform: Platform;
    message_count: number;
    contact_count: number;
    thread_count: number;
    last_sync: string;
    health_status: 'healthy' | 'degraded' | 'unhealthy';
}

export interface MemoryStats {
    total_memories: number;
    memories_by_type: Record<MemoryType, number>;
    memories_by_importance: Record<MemoryImportance, number>;
    recent_memories: number;
    last_updated: string;
}

export interface SystemHealth {
    overall_status: 'healthy' | 'degraded' | 'unhealthy';
    platforms: PlatformStats[];
    memory_system: MemoryStats;
    ai_processing: {
        status: 'active' | 'inactive' | 'error';
        models_available: string[];
        last_processing: string;
    };
    last_check: string;
}
