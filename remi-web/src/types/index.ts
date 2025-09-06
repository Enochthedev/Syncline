// Core type definitions for R.E.M.I Web App

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

export interface SearchQuery {
    text: string;
    intent?: QueryIntent;
    filters?: SearchFilters;
    contactContext?: string;
    timeRange?: TimeRange;
    platforms?: string[];
    sortBy?: SortOption;
    limit?: number;
    offset?: number;
}

export interface SearchResponse {
    results: SearchResult[];
    totalCount: number;
    processingTime: number;
    suggestions?: string[];
    facets?: SearchFacet[];
    relatedContacts?: UnifiedContact[];
    queryInsights?: QueryInsights;
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

export interface SearchFacet {
    field: string;
    values: FacetValue[];
}

export interface FacetValue {
    value: string;
    count: number;
    selected: boolean;
}

export interface QueryInsights {
    intent: QueryIntent;
    confidence: number;
    suggestedFilters: SearchFilters;
    relatedQueries: string[];
}

export enum QueryIntent {
    PERSON_SEARCH = 'person_search',
    CONTENT_SEARCH = 'content_search',
    FILE_SEARCH = 'file_search',
    COMMITMENT_SEARCH = 'commitment_search',
    TEMPORAL_SEARCH = 'temporal_search'
}

export interface TimeRange {
    start: Date;
    end: Date;
    label?: string;
}

export enum SortOption {
    RELEVANCE = 'relevance',
    DATE_DESC = 'date_desc',
    DATE_ASC = 'date_asc',
    SENDER = 'sender',
    PLATFORM = 'platform'
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

// Web-specific types
export interface WebSocketMessage {
    type: string;
    data: any;
    timestamp: string;
}

export interface PWAInstallPrompt {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export interface ServiceWorkerMessage {
    type: 'SKIP_WAITING' | 'CACHE_UPDATE' | 'OFFLINE_READY';
    payload?: any;
}

// Analytics types
export interface AnalyticsEvent {
    name: string;
    properties?: Record<string, any>;
    timestamp: Date;
    userId?: string;
    sessionId: string;
}

export interface PerformanceMetrics {
    // Core Web Vitals
    largestContentfulPaint: number;
    firstInputDelay: number;
    cumulativeLayoutShift: number;

    // Additional metrics
    firstContentfulPaint: number;
    timeToInteractive: number;
    totalBlockingTime: number;

    // Custom metrics
    searchPerformance: number;
    contactLoadTime: number;
    syncLatency: number;
}

// Export all types
export * from './contacts';
export * from './messages';
export * from './search';
export * from './api';