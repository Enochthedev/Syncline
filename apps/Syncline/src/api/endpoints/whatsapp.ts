/**
 * WhatsApp API Endpoints
 * 
 * Handles WhatsApp-specific operations via Matrix bridge:
 * - Session management
 * - QR code login flow
 * - Connection status checking
 * - Message listing and sending
 */

import axios from 'axios';
import { apiClient, API_BASE_URL } from '../client';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Storage key for auth token
const AUTH_TOKEN_KEY = '@syncline/auth_token';

// Extended timeout for WhatsApp operations (90 seconds)
// Matrix bridge operations can be slow
const WHATSAPP_TIMEOUT = 90000;

// Create a separate client for slow WhatsApp operations
const getAuthHeader = async () => {
    const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
    return token ? { Authorization: `Bearer ${token}` } : {};
};

// =============================================================================
// Types
// =============================================================================

export interface WhatsAppLoginResponse {
    connection_id: string;
    qr_code: string | null;
    pairing_code?: string | null;
    already_logged_in: boolean;
    message: string;
}

export interface WhatsAppSessionResponse {
    connection_id: string;
    is_logged_in: boolean;
    phone_number?: string;
    session_age_seconds?: number;
}

export interface WhatsAppStatusResponse {
    connection_id: string;
    bridge_status: {
        connected: boolean;
        logged_in: boolean;
        phone?: string;
        battery_level?: number;
        platform?: string;
    };
    is_healthy: boolean;
}

export interface WhatsAppMessage {
    event_id: string;
    room_id: string;
    sender: string;
    content: string;
    timestamp: string;
    has_media: boolean;
}

export interface WhatsAppContact {
    jid: string;
    name: string;
    phone: string;
    room_id?: string;
}

export interface WhatsAppCleanupResponse {
    success: boolean;
    messages_deleted: number;
    sessions_cleared: number;
    message: string;
}

// =============================================================================
// API Functions
// =============================================================================


export const whatsappAPI = {
    /**
     * Check for existing WhatsApp connections
     * This should be called FIRST to prevent duplicate connections
     */
    checkExistingConnection: async (): Promise<{
        connection_id: string | null;
        is_existing: boolean;
        is_logged_in: boolean;
        phone: string | null;
        message: string;
        error: string | null;
    }> => {
        const { data } = await apiClient.get('/whatsapp/connections/check-existing');
        return data;
    },

    /**
     * Create a new WhatsApp session
     * This should be called first before any other operations
     * Uses extended timeout for Matrix bridge operations
     */
    createSession: async (connectionId: string): Promise<WhatsAppSessionResponse> => {
        const headers = await getAuthHeader();
        const { data } = await axios.post(
            `${API_BASE_URL}/whatsapp/${connectionId}/session/create`,
            {},
            { headers, timeout: WHATSAPP_TIMEOUT }
        );
        return data;
    },

    /**
     * Get current session status
     * Uses extended timeout for Matrix bridge operations
     */
    getSessionStatus: async (connectionId: string): Promise<WhatsAppSessionResponse> => {
        const headers = await getAuthHeader();
        const { data } = await axios.get(
            `${API_BASE_URL}/whatsapp/${connectionId}/session/status`,
            { headers, timeout: WHATSAPP_TIMEOUT }
        );
        return data;
    },

    /**
     * Clean up session and logout
     */
    cleanupSession: async (connectionId: string): Promise<{ success: boolean; logout_success: boolean; message: string }> => {
        const { data } = await apiClient.delete(`/whatsapp/${connectionId}/session`);
        return data;
    },

    /**
     * Get QR code for WhatsApp login
     * User needs to scan this with their WhatsApp mobile app
     * Uses extended timeout for Matrix bridge operations
     */
    getLoginQR: async (connectionId: string): Promise<WhatsAppLoginResponse> => {
        const headers = await getAuthHeader();
        const { data } = await axios.get(
            `${API_BASE_URL}/whatsapp/${connectionId}/login`,
            { headers, timeout: WHATSAPP_TIMEOUT }
        );
        return data;
    },

    /**
     * Login with phone number pairing
     * Uses extended timeout for Matrix bridge operations
     */
    loginWithPhone: async (connectionId: string, phone: string): Promise<WhatsAppLoginResponse> => {
        const headers = await getAuthHeader();
        const { data } = await axios.post(
            `${API_BASE_URL}/whatsapp/${connectionId}/login/phone`,
            { phone },
            { headers, timeout: WHATSAPP_TIMEOUT }
        );
        return data;
    },

    /**
     * Check WhatsApp connection status
     */
    getStatus: async (connectionId: string): Promise<WhatsAppStatusResponse> => {
        const { data } = await apiClient.get(`/whatsapp/${connectionId}/status`);
        return data;
    },

    /**
     * Logout from WhatsApp (keeps Matrix connection)
     */
    logout: async (connectionId: string): Promise<{ success: boolean; message: string }> => {
        const { data } = await apiClient.post(`/whatsapp/${connectionId}/logout`);
        return data;
    },

    /**
     * Clean up WhatsApp data for fresh start
     */
    cleanup: async (connectionId: string): Promise<WhatsAppCleanupResponse> => {
        const { data } = await apiClient.post(`/whatsapp/${connectionId}/cleanup`);
        return data;
    },

    /**
     * List WhatsApp messages
     */
    listMessages: async (
        connectionId: string,
        options?: {
            room_id?: string;
            limit?: number;
        }
    ): Promise<{ messages: WhatsAppMessage[]; total: number }> => {
        const { data } = await apiClient.get(`/whatsapp/${connectionId}/messages`, {
            params: options,
        });
        return data;
    },

    /**
     * Send a WhatsApp message
     */
    sendMessage: async (
        connectionId: string,
        roomId: string,
        content: string
    ): Promise<{ success: boolean; event_id?: string; message: string }> => {
        const { data } = await apiClient.post(`/whatsapp/${connectionId}/send`, {
            room_id: roomId,
            content,
        });
        return data;
    },

    /**
     * Collect WhatsApp messages from bridge
     */
    collectMessages: async (
        connectionId: string,
        limit?: number
    ): Promise<{ messages_collected: number; contacts_created: number; errors: number; message: string }> => {
        const { data } = await apiClient.post(`/whatsapp/${connectionId}/collect`, null, {
            params: { limit },
        });
        return data;
    },

    /**
     * List WhatsApp contacts
     */
    listContacts: async (
        connectionId: string
    ): Promise<{ contacts: WhatsAppContact[]; total: number }> => {
        const { data } = await apiClient.get(`/whatsapp/${connectionId}/contacts`);
        return data;
    },

    /**
     * Sync WhatsApp chats
     * Uses extended timeout for Matrix bridge operations
     */
    syncChats: async (connectionId: string): Promise<{ connection_id: string; sync_result: any; message: string }> => {
        const headers = await getAuthHeader();
        const { data } = await axios.post(
            `${API_BASE_URL}/whatsapp/${connectionId}/sync`,
            {},
            { headers, timeout: WHATSAPP_TIMEOUT }
        );
        return data;
    },

    /**
     * Enhanced WhatsApp session flow
     * Handles session creation, status checking, and login flow
     */
    initializeSession: async (connectionId: string): Promise<{
        session: WhatsAppSessionResponse;
        needsLogin: boolean;
        qrCode?: string;
    }> => {
        try {
            // Try to get existing session status
            let session: WhatsAppSessionResponse;
            try {
                session = await whatsappAPI.getSessionStatus(connectionId);
            } catch {
                // Create new session if none exists
                session = await whatsappAPI.createSession(connectionId);
            }

            // If already logged in, return session
            if (session.is_logged_in) {
                return {
                    session,
                    needsLogin: false,
                };
            }

            // Need to login - get QR code
            const loginResponse = await whatsappAPI.getLoginQR(connectionId);

            return {
                session,
                needsLogin: !loginResponse.already_logged_in,
                qrCode: loginResponse.qr_code || undefined,
            };

        } catch (error) {
            console.error('Failed to initialize WhatsApp session:', error);
            throw error;
        }
    },

    /**
     * Poll for WhatsApp connection status with session management
     * Useful during QR code scanning flow
     */
    pollStatus: async (
        connectionId: string,
        onStatusChange: (status: WhatsAppSessionResponse) => void,
        intervalMs: number = 2000,
        maxAttempts: number = 60
    ): Promise<boolean> => {
        let attempts = 0;

        return new Promise((resolve) => {
            const checkStatus = async () => {
                try {
                    const status = await whatsappAPI.getSessionStatus(connectionId);
                    onStatusChange(status);

                    if (status.is_logged_in) {
                        resolve(true);
                        return;
                    }

                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkStatus, intervalMs);
                    } else {
                        resolve(false);
                    }
                } catch (error) {
                    console.error('Status poll error:', error);
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkStatus, intervalMs);
                    } else {
                        resolve(false);
                    }
                }
            };

            checkStatus();
        });
    },
};
