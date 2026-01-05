
import { apiClient } from '../client';

export interface PlatformIdentity {
    [key: string]: string;
}

export interface Contact {
    id: string;
    canonical_name: string;
    emails: string[] | null;
    phones: string[] | null;
    platform_identities: PlatformIdentity | null;
    contact_metadata: any | null;
    participant_count: number;
    thread_count: number;
    created_at: string;
    updated_at: string;
}

export interface ContactListResponse {
    contacts: Contact[];
    total: number;
    skip: number;
    limit: number;
}

export interface ThreadSummary {
    id: string;
    platform: string;
    platform_thread_id: string;
    title: string | null;
    message_count: number;
    first_message_at: string | null;
    last_message_at: string | null;
}

export interface ContactThreadsResponse {
    contact_id: string;
    contact_name: string;
    threads: ThreadSummary[];
    total: number;
}

export interface Message {
    id: string;
    platform: string;
    content: string;
    sender: string;
    timestamp: string;
    thread_id: string | null;
    has_attachments: boolean;
}

export interface ContactMessagesResponse {
    messages: Message[];
    total: number;
    skip: number;
    limit: number;
}

export const contactsAPI = {
    /**
     * List all contacts with optional filtering
     */
    listContacts: async (filters?: {
        user_id?: string;
        search?: string;
        platform?: string;
        limit?: number;
        skip?: number;
    }): Promise<ContactListResponse> => {
        const { data } = await apiClient.get('/contacts', { params: filters });
        return data;
    },

    /**
     * Get inbox - contacts sorted by last message time
     * Optimized for messaging UI with message previews
     */
    getInbox: async (options?: {
        user_id?: string;
        platform?: string;
        search?: string;
        limit?: number;
        skip?: number;
    }): Promise<{
        contacts: Array<{
            id: string;
            canonical_name: string;
            emails: string[] | null;
            phones: string[] | null;
            platform_identities: Record<string, string> | null;
            avatar_url: string | null;
            last_message: {
                message_id: string | null;
                content: string | null;
                platform: string | null;
                timestamp: string | null;
                sender_name: string | null;
                is_from_me: boolean;
            } | null;
            unread_count: number;
            platforms: string[];
        }>;
        total: number;
        skip: number;
        limit: number;
    }> => {
        const { data } = await apiClient.get('/contacts/inbox', { params: options });
        return data;
    },

    /**
     * Get detailed contact information
     */
    getContact: async (contactId: string): Promise<Contact> => {
        const { data } = await apiClient.get(`/contacts/${contactId}`);
        return data;
    },

    /**
     * Get all threads for a specific contact
     */
    getContactThreads: async (
        contactId: string,
        platform?: string
    ): Promise<ContactThreadsResponse> => {
        const { data } = await apiClient.get(`/contacts/${contactId}/threads`, {
            params: platform ? { platform } : undefined,
        });
        return data;
    },

    /**
     * Get messages for a specific contact
     * Uses the messages API with contact_id filter
     */
    getContactMessages: async (
        contactId: string,
        options?: {
            platform?: string;
            start_date?: string;
            end_date?: string;
            limit?: number;
            skip?: number;
        }
    ): Promise<ContactMessagesResponse> => {
        const { data } = await apiClient.get('/messages', {
            params: {
                contact_id: contactId,
                ...options,
            },
        });
        // Transform response to match our Message interface
        const messages = data.messages.map((msg: any) => ({
            id: msg.id,
            platform: msg.platform,
            content: msg.content?.text || '',
            sender: msg.sender?.name || 'Unknown',
            timestamp: msg.timestamp,
            thread_id: msg.thread_id,
            has_attachments: (msg.attachment_count || 0) > 0,
        }));
        return {
            messages,
            total: data.total,
            skip: data.skip,
            limit: data.limit,
        };
    },

    /**
     * Search messages for a specific contact
     */
    searchContactMessages: async (
        contactId: string,
        query: string,
        options?: {
            limit?: number;
            skip?: number;
        }
    ): Promise<{ results: Message[]; total: number }> => {
        const { data } = await apiClient.get('/messages/search', {
            params: {
                query,
                contact_ids: contactId,
                ...options,
            },
        });
        const results = data.results.map((msg: any) => ({
            id: msg.id,
            platform: msg.platform,
            content: msg.content || msg.highlighted_content || '',
            sender: msg.sender?.name || 'Unknown',
            timestamp: msg.timestamp,
            thread_id: msg.thread_id,
            has_attachments: (msg.attachment_count || 0) > 0,
        }));
        return { results, total: data.total };
    },

    /**
     * Sync device contacts with backend (handles deduplication)
     */
    syncContacts: async (
        userId: string,
        contacts: { name: string; emails?: string[]; phones?: string[] }[]
    ): Promise<{
        created: number;
        updated: number;
        duplicates_skipped: number;
        total_processed: number;
    }> => {
        const { data } = await apiClient.post(
            '/contacts/sync',
            { contacts },
            { params: { user_id: userId } }
        );
        return data;
    },

    /**
     * Update contact details
     */
    updateContact: async (
        contactId: string,
        updates: {
            canonical_name?: string;
            emails?: string[];
            phones?: string[];
            platform_identities?: Record<string, string>;
            contact_metadata?: Record<string, any>;
        }
    ): Promise<Contact> => {
        const { data } = await apiClient.patch(`/contacts/${contactId}`, updates);
        return data;
    },

    /**
     * Merge multiple contacts into one
     */
    mergeContacts: async (
        sourceContactIds: string[],
        targetContactId: string
    ): Promise<Contact> => {
        const { data } = await apiClient.post('/contacts/merge', {
            source_contact_ids: sourceContactIds,
            target_contact_id: targetContactId,
        });
        return data;
    },

    /**
     * Delete a contact
     */
    deleteContact: async (contactId: string): Promise<void> => {
        await apiClient.delete(`/contacts/${contactId}`);
    },
};
