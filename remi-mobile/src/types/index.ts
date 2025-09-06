// Core type definitions for R.E.M.I Mobile App

export interface UnifiedContact {
    id: string;
    primaryName: string;
    displayName: string;
    profilePhoto?: string;

    // Platform identities
    identities: ContactIdentity[];

    // Contact information
    emails: string[];
    phoneNumbers: string[];
    socialProfiles: SocialProfile[];

    // Communication metadata
    lastInteraction: Date;
    totalMessages: number;
    platforms: string[];
    preferredPlatform?: string;

    // AI-generated insights
    relationshipStrength: number; // 0-1 scale
    communicationFrequency: 'high' | 'medium' | 'low';
    responsePattern: ResponsePattern;
    topicAffinity: TopicAffinity[];

    // Shared content
    sharedFiles: SharedFile[];
    sharedLinks: SharedLink[];
    commonContacts: string[];

    // Metadata
    createdAt: Date;
    updatedAt: Date;
    lastSyncAt: Date;
}

export interface ContactIdentity {
    platform: string;
    platformUserId: string;
    displayName: string;
    handle?: string;
    profileUrl?: string;
    verified: boolean;
}

export interface SocialProfile {
    platform: string;
    url: string;
    handle: string;
}

export interface ResponsePattern {
    averageResponseTime: number; // in minutes
    responseRate: number; // 0-1 scale
    preferredTimes: string[]; // time ranges
    communicationStyle: 'formal' | 'casual' | 'mixed';
}

export interface TopicAffinity {
    topic: string;
    frequency: number;
    sentiment: 'positive' | 'neutral' | 'negative';
}

export interface SharedFile {
    id: string;
    name: string;
    type: string;
    size: number;
    url: string;
    sharedAt: Date;
    platform: string;
}

export interface SharedLink {
    id: string;
    url: string;
    title: string;
    description?: string;
    sharedAt: Date;
    platform: string;
}

// Search related types
export interface SearchFilters {
    participants?: string[];
    platforms?: string[];
    date_from?: Date;
    date_to?: Date;
    has_attachments?: boolean;
    entity_types?: string[];
    content_type?: string;
}

export interface SearchResult {
    id: string;
    type: 'message' | 'thread' | 'contact' | 'file' | 'commitment';
    title: string;
    snippet: string;
    content?: string;
    relevanceScore: number;
    timestamp: Date;

    // Context information
    contact?: UnifiedContact;
    platform?: string;
    thread?: ConversationThread;

    // Highlighting
    highlights: TextHighlight[];

    // Quick actions
    quickActions: QuickAction[];
}

export interface TextHighlight {
    start: number;
    end: number;
    text: string;
}

export interface QuickAction {
    id: string;
    label: string;
    icon: string;
    action: () => void;
}

export interface ConversationThread {
    id: string;
    platform: string;
    platformThreadId: string;

    // Thread metadata
    title?: string;
    participants: UnifiedContact[];
    messageCount: number;

    // Timing
    createdAt: Date;
    lastMessageAt: Date;
    lastReadAt?: Date;

    // AI Analysis
    summary: ThreadSummary;
    keyTopics: string[];
    relationshipDynamics: RelationshipDynamic[];

    // User preferences
    isMuted: boolean;
    isArchived: boolean;
    customLabel?: string;

    // Recent messages preview
    recentMessages: Message[];
}

export interface ThreadSummary {
    shortSummary: string;
    keyPoints: string[];
    actionItems: ActionItem[];
    decisions: Decision[];
    nextSteps: string[];
    generatedAt: Date;
}

export interface ActionItem {
    id: string;
    description: string;
    assignee?: string;
    dueDate?: Date;
    status: 'pending' | 'in_progress' | 'completed';
}

export interface Decision {
    id: string;
    description: string;
    decidedBy: string;
    decidedAt: Date;
    impact: 'low' | 'medium' | 'high';
}

export interface RelationshipDynamic {
    participantId: string;
    role: string;
    influence: number; // 0-1 scale
    engagement: number; // 0-1 scale
}

export interface Message {
    id: string;
    threadId: string;
    platform: string;
    platformMessageId: string;

    // Content
    content: MessageContent;
    attachments: Attachment[];

    // Participants
    sender: UnifiedContact;
    recipients: UnifiedContact[];

    // Metadata
    timestamp: Date;
    editedAt?: Date;
    isRead: boolean;
    isImportant: boolean;

    // AI Analysis
    entities: ExtractedEntity[];
    sentiment: SentimentScore;
    topics: string[];
    commitments: Commitment[];

    // Search and indexing
    searchableText: string;
    embedding?: number[];

    // Sync metadata
    lastSyncAt: Date;
    syncVersion: number;
}

export interface MessageContent {
    text?: string;
    html?: string;
    markdown?: string;
    richText?: RichTextElement[];
    mediaType?: 'text' | 'image' | 'video' | 'audio' | 'file';
}

export interface RichTextElement {
    type: 'text' | 'link' | 'mention' | 'emoji';
    content: string;
    attributes?: Record<string, any>;
}

export interface Attachment {
    id: string;
    name: string;
    type: string;
    size: number;
    url: string;
    thumbnailUrl?: string;
    metadata?: Record<string, any>;
}

export interface ExtractedEntity {
    id: string;
    type: string;
    text: string;
    confidence: number;
    startOffset: number;
    endOffset: number;
    metadata?: Record<string, any>;
}

export interface SentimentScore {
    overall: number; // -1 to 1
    confidence: number; // 0 to 1
    emotions: EmotionScore[];
}

export interface EmotionScore {
    emotion: string;
    score: number; // 0 to 1
}

export interface Commitment {
    id: string;
    description: string;
    assignee?: string;
    dueDate?: Date;
    status: 'pending' | 'in_progress' | 'completed' | 'overdue';
    priority: 'low' | 'medium' | 'high';
    extractedAt: Date;
    confidence: number;
}

// Navigation types
export type RootStackParamList = {
    Auth: undefined;
    Main: undefined;
    MainTabs: undefined;
    ContactProfile: { contactId: string };
    MessageThread: { threadId: string };
    Search: { query?: string };
    Settings: undefined;
    DemoWorkflow: undefined;
    ResponsiveUIDemo: undefined;
};

export type TabParamList = {
    Dashboard: undefined;
    Search: undefined;
    Contacts: undefined;
    Messages: undefined;
    Settings: undefined;
};

// API types
export interface ApiResponse<T> {
    data: T;
    message?: string;
    status: number;
    timestamp: string;
}

export interface PaginatedResponse<T> {
    data: T[];
    pagination: {
        page: number;
        limit: number;
        total: number;
        totalPages: number;
    };
}

export interface ApiError {
    message: string;
    code: string;
    details?: Record<string, any>;
}

// Sync types
export interface DataUpdate {
    type: 'contact' | 'message' | 'thread' | 'insight' | 'setting';
    action: 'create' | 'update' | 'delete';
    data: any;
    timestamp: Date;
    source: string;
}

export interface SyncResult {
    success: boolean;
    itemsProcessed: number;
    conflicts: DataConflict[];
    errors: SyncError[];
    lastSyncTime: Date;
}

export interface DataConflict {
    id: string;
    type: string;
    localData: any;
    serverData: any;
    conflictType: 'version' | 'content' | 'deletion';
    timestamp: Date;
}

export interface SyncError {
    id: string;
    type: string;
    message: string;
    data?: any;
    timestamp: Date;
    retryable: boolean;
}

// Notification types
export interface ProactiveInsight {
    id: string;
    type: InsightType;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';

    // Context
    relatedContacts: UnifiedContact[];
    relatedMessages: Message[];
    suggestedActions: SuggestedAction[];

    // Timing
    createdAt: Date;
    expiresAt?: Date;
    optimalDeliveryTime?: Date;

    // Interaction
    isRead: boolean;
    isActedUpon: boolean;
    userFeedback?: InsightFeedback;
}

export enum InsightType {
    FOLLOW_UP_REMINDER = 'follow_up_reminder',
    COMMITMENT_DEADLINE = 'commitment_deadline',
    RELATIONSHIP_OPPORTUNITY = 'relationship_opportunity',
    COMMUNICATION_PATTERN = 'communication_pattern',
    SHARED_INTEREST = 'shared_interest',
    RECONNECTION_SUGGESTION = 'reconnection_suggestion'
}

export interface SuggestedAction {
    id: string;
    label: string;
    description: string;
    actionType: 'message' | 'call' | 'email' | 'reminder' | 'note';
    data?: Record<string, any>;
}

export interface InsightFeedback {
    helpful: boolean;
    actionTaken: boolean;
    feedback?: string;
    timestamp: Date;
}

// New types for relationship insights
export interface RelationshipInsight {
    id: string;
    type: string;
    title: string;
    description: string;
    confidence: number;
    supporting_data: Record<string, any>;
    suggested_actions: string[];
    user_feedback?: 'helpful' | 'not_helpful' | 'incorrect';
    generated_at: Date;
}

export interface TimelineData {
    timeline: TimelinePoint[];
    trend_analysis: TrendAnalysis;
    summary: TimelineSummary;
    patterns: Record<string, any>;
}

export interface TimelinePoint {
    date: string;
    message_count: number;
    platform_count: number;
    avg_message_length: number;
    platforms: string[];
    platform_breakdown: Record<string, number>;
}

export interface TrendAnalysis {
    trend: 'increasing' | 'decreasing' | 'stable';
    slope: number;
    correlation: number;
    strength: number;
}

export interface TimelineSummary {
    total_days: number;
    active_days: number;
    total_messages: number;
    avg_daily_messages: number;
    peak_day: TimelinePoint | null;
}

export interface SentimentData {
    sentiment_timeline: SentimentPoint[];
    overall_sentiment: number;
    sentiment_trend: TrendAnalysis;
    sentiment_category: 'positive' | 'negative' | 'neutral';
    sentiment_distribution: {
        positive_avg: number;
        neutral_avg: number;
        negative_avg: number;
    };
}

export interface SentimentPoint {
    date: string;
    avg_sentiment_score: number;
    positive_ratio: number;
    neutral_ratio: number;
    negative_ratio: number;
    total_messages: number;
}

export interface NetworkData {
    network_graph: {
        nodes: NetworkNode[];
        edges: NetworkEdge[];
    };
    network_stats: {
        network_size: number;
        avg_shared_threads: number;
        network_strength_score: number;
        top_connections: MutualContact[];
    } | null;
    mutual_contacts_list: MutualContact[];
}

export interface NetworkNode {
    id: string;
    label: string;
    type: 'user' | 'main_contact' | 'mutual_contact';
}

export interface NetworkEdge {
    from: string;
    to: string;
    weight: number;
}

export interface MutualContact {
    platform: string;
    platform_user_id: string;
    display_name: string;
    shared_threads: number;
    shared_messages: number;
    unified_contact?: {
        id: string;
        primary_name: string;
        relationship_strength: number;
    };
}

export interface ComprehensiveAnalysis {
    timeline_analysis: TimelineData;
    sentiment_analysis: SentimentData;
    frequency_analysis: Record<string, any>;
    network_analysis: NetworkData;
    ai_insights: RelationshipInsight[];
    generated_at: string;
}