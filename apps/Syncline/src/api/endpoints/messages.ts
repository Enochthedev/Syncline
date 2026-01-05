import { apiClient } from '../client';
import { Message } from '../../types';

export interface ChatThread {
    id: string;
    platform: string;
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
    platform: string;
    sender_name: string;
    content: string;
    timestamp: string;
    is_from_me: boolean;
    has_attachments: boolean;
}

export const messagesAPI = {
    // Get active chat threads (replaces listMessages for live chat view)
    getChatThreads: async (filters?: {
        platform?: string;
        limit?: number;
    }): Promise<{ threads: ChatThread[]; total: number }> => {
        const { data } = await apiClient.get('/chats/threads', { 
            params: {
                ...filters,
                // Convert lowercase platform to uppercase for backend
                platform: filters?.platform?.toUpperCase()
            }
        });
        
        // Data already comes with lowercase platform from backend
        return data;
    },

    // Get messages for a specific chat thread
    getChatMessages: async (
        threadId: string,
        platform: string,
        options?: {
            limit?: number;
            before?: string;
        }
    ): Promise<{ messages: ChatMessage[]; has_more: boolean }> => {
        const { data } = await apiClient.get(`/chats/threads/${threadId}/messages`, {
            params: { 
                platform: platform.toUpperCase(), // Convert to uppercase for backend
                ...options 
            }
        });
        return data;
    },

    // Link chat thread to a contact
    linkChatToContact: async (
        threadId: string,
        platform: string,
        contactId: string
    ): Promise<{ success: boolean; message: string }> => {
        const { data } = await apiClient.post(`/chats/threads/${threadId}/link`, {
            contact_id: contactId
        }, {
            params: { platform }
        });
        return data;
    },

    // Send message to chat thread
    sendMessage: async (
        threadId: string,
        platform: string,
        content: string,
        replyTo?: string
    ): Promise<{ success: boolean; message_id?: string; message: string }> => {
        const { data } = await apiClient.post(`/chats/threads/${threadId}/messages`, {
            content,
            reply_to: replyTo
        }, {
            params: { platform }
        });
        return data;
    },

    // Legacy methods for backward compatibility
    listMessages: async (filters?: {
        platform?: string;
        contact_id?: string;
        start_date?: string;
        end_date?: string;
        limit?: number;
        skip?: number;
    }): Promise<{ messages: Message[]; total: number }> => {
        const { data } = await apiClient.get('/messages', { params: filters });
        const messages = data.messages.map((msg: any) => ({
            id: msg.id,
            platform: msg.platform,
            content: msg.content?.text || '',
            sender: msg.sender?.name || 'Unknown',
            timestamp: msg.timestamp,
            thread_id: msg.thread_id,
            has_attachments: (msg.attachment_count || 0) > 0,
        }));
        return { messages, total: data.total };
    },

    searchMessages: async (query: string): Promise<{ results: Message[]; total: number }> => {
        const { data } = await apiClient.get('/messages/search', {
            params: { query }
        });
        const results = data.results.map((msg: any) => ({
            id: msg.id,
            platform: msg.platform,
            content: msg.content?.text || '',
            sender: msg.sender?.name || 'Unknown',
            timestamp: msg.timestamp,
            thread_id: msg.thread_id,
            has_attachments: (msg.attachment_count || 0) > 0,
        }));
        return { results, total: data.total };
    },

    getMessage: async (messageId: string): Promise<Message> => {
        const { data } = await apiClient.get(`/messages/${messageId}`);
        return {
            id: data.id,
            platform: data.platform,
            content: data.content?.text || '',
            sender: data.sender?.name || 'Unknown',
            timestamp: data.timestamp,
            thread_id: data.thread_id,
            has_attachments: (data.attachment_count || 0) > 0,
        };
    },
};
