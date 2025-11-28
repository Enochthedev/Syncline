export interface User {
    id: string;
    email: string;
    full_name?: string;
}

export type Platform = 'gmail' | 'slack' | 'discord' | 'telegram' | 'twitter' | 'whatsapp';

export interface Connection {
    id: string;
    platform: Platform;
    status: 'active' | 'pending' | 'error' | 'disconnected';
    connected_at?: string;
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
