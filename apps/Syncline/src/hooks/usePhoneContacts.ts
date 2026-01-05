/**
 * Phone Contacts Hook
 * 
 * React hook for managing device contacts:
 * - Permission management
 * - Contact fetching and caching
 * - Search functionality
 * - Sync with backend
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Alert } from 'react-native';
import * as Linking from 'expo-linking';
import { phoneContactsService, PhoneContact, ContactsPermissionStatus } from '../services/phoneContacts';
import { contactsAPI } from '../api/endpoints/contacts';

// =============================================================================
// Types
// =============================================================================

interface UsePhoneContactsOptions {
    autoFetch?: boolean;
    pageSize?: number;
    enableSearch?: boolean;
}

interface ContactsState {
    contacts: PhoneContact[];
    loading: boolean;
    error: string | null;
    permissionStatus: ContactsPermissionStatus | null;
    hasNextPage: boolean;
    totalCount: number;
}

// =============================================================================
// Main Hook
// =============================================================================

export const usePhoneContacts = (options: UsePhoneContactsOptions = {}) => {
    const {
        autoFetch = true,
        pageSize = 50,
        enableSearch = true,
    } = options;

    const [state, setState] = useState<ContactsState>({
        contacts: [],
        loading: false,
        error: null,
        permissionStatus: null,
        hasNextPage: false,
        totalCount: 0,
    });

    const [searchQuery, setSearchQuery] = useState('');
    const [currentPage, setCurrentPage] = useState(0);

    // Check if contacts are available on this platform
    const isAvailable = useMemo(() => {
        return phoneContactsService.isContactsAvailable();
    }, []);

    // Initialize permissions check
    useEffect(() => {
        if (isAvailable) {
            checkPermissions();
        }
    }, [isAvailable]);

    // Auto-fetch contacts if enabled and permissions granted
    useEffect(() => {
        if (autoFetch && state.permissionStatus?.granted && state.contacts.length === 0) {
            fetchContacts();
        }
    }, [autoFetch, state.permissionStatus?.granted]);

    // Check permissions
    const checkPermissions = useCallback(async () => {
        try {
            const status = await phoneContactsService.checkPermissions();
            setState(prev => ({ ...prev, permissionStatus: status }));
            return status;
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: 'Failed to check permissions',
                permissionStatus: { granted: false, canAskAgain: false, status: 'denied' }
            }));
            return { granted: false, canAskAgain: false, status: 'denied' as const };
        }
    }, []);

    // Request permissions with user-friendly flow
    const requestPermissions = useCallback(async (): Promise<boolean> => {
        try {
            setState(prev => ({ ...prev, loading: true, error: null }));

            // Check current status first
            const currentStatus = await phoneContactsService.checkPermissions();

            if (currentStatus.granted) {
                setState(prev => ({ ...prev, permissionStatus: currentStatus, loading: false }));
                return true;
            }

            // If we can't ask again, show settings dialog
            if (!currentStatus.canAskAgain) {
                Alert.alert(
                    'Contacts Permission Required',
                    'Please enable contacts access in your device settings to use this feature.',
                    [
                        { text: 'Cancel', style: 'cancel' },
                        {
                            text: 'Open Settings', onPress: () => {
                                Linking.openSettings();
                            }
                        },
                    ]
                );
                setState(prev => ({ ...prev, loading: false }));
                return false;
            }

            // Show explanation dialog
            const userWantsToGrant = await phoneContactsService.showPermissionDialog();
            if (!userWantsToGrant) {
                setState(prev => ({ ...prev, loading: false }));
                return false;
            }

            // Request permission
            const newStatus = await phoneContactsService.requestPermissions();
            setState(prev => ({ ...prev, permissionStatus: newStatus, loading: false }));

            if (!newStatus.granted) {
                Alert.alert(
                    'Permission Denied',
                    'Contacts access is required to sync your contacts. You can enable it later in settings.',
                    [{ text: 'OK' }]
                );
            }

            return newStatus.granted;
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: 'Failed to request permissions',
                loading: false
            }));
            return false;
        }
    }, []);

    // Fetch contacts from device
    const fetchContacts = useCallback(async (reset: boolean = false) => {
        try {
            setState(prev => ({ ...prev, loading: true, error: null }));

            // Check permissions
            const permissions = await checkPermissions();
            if (!permissions.granted) {
                setState(prev => ({ ...prev, loading: false }));
                return;
            }

            // Fetch all contacts at once for better UX
            const allContacts = await phoneContactsService.getDeviceContacts();

            console.log(`📱 Fetched ${allContacts.length} contacts from device`);

            setState(prev => ({
                ...prev,
                contacts: allContacts,
                hasNextPage: false,
                totalCount: allContacts.length,
                loading: false,
            }));

            if (reset) {
                setCurrentPage(0);
            }
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: error instanceof Error ? error.message : 'Failed to fetch contacts',
                loading: false
            }));
        }
    }, [checkPermissions]);

    // Load more contacts (pagination)
    const loadMore = useCallback(async () => {
        if (state.loading || !state.hasNextPage) return;

        try {
            setState(prev => ({ ...prev, loading: true }));

            const nextPage = currentPage + 1;
            const result = await phoneContactsService.getDeviceContactsPaginated(pageSize, nextPage * pageSize);

            setState(prev => ({
                ...prev,
                contacts: [...prev.contacts, ...result.contacts],
                hasNextPage: result.hasNextPage,
                totalCount: prev.totalCount + result.contacts.length,
                loading: false,
            }));

            setCurrentPage(nextPage);
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: 'Failed to load more contacts',
                loading: false
            }));
        }
    }, [state.loading, state.hasNextPage, currentPage, pageSize]);

    // Search contacts
    const searchContacts = useCallback(async (query: string) => {
        if (!enableSearch) return;

        try {
            setSearchQuery(query);

            if (!query.trim()) {
                // Reset to full list
                await fetchContacts(true);
                return;
            }

            setState(prev => ({ ...prev, loading: true, error: null }));

            const permissions = await checkPermissions();
            if (!permissions.granted) {
                setState(prev => ({ ...prev, loading: false }));
                return;
            }

            const results = await phoneContactsService.searchDeviceContacts(query);

            setState(prev => ({
                ...prev,
                contacts: results,
                hasNextPage: false,
                totalCount: results.length,
                loading: false,
            }));
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: 'Failed to search contacts',
                loading: false
            }));
        }
    }, [enableSearch, fetchContacts, checkPermissions]);

    // Get contact by ID
    const getContactById = useCallback(async (contactId: string): Promise<PhoneContact | null> => {
        try {
            const permissions = await checkPermissions();
            if (!permissions.granted) {
                return null;
            }

            return await phoneContactsService.getContactById(contactId);
        } catch (error) {
            console.error('Failed to get contact by ID:', error);
            return null;
        }
    }, [checkPermissions]);

    // Refresh contacts
    const refresh = useCallback(async () => {
        await fetchContacts(true);
    }, [fetchContacts]);

    // Clear error
    const clearError = useCallback(() => {
        setState(prev => ({ ...prev, error: null }));
    }, []);

    // Sync with backend (optional)
    const syncWithBackend = useCallback(async () => {
        try {
            setState(prev => ({ ...prev, loading: true }));

            // This would sync device contacts with your backend
            // Implementation depends on your backend API
            const contactsToSync = state.contacts.map(contact => ({
                device_contact_id: contact.id,
                canonical_name: contact.name,
                phones: contact.phoneNumbers.map(p => p.number),
                emails: contact.emails.map(e => e.email),
                contact_metadata: {
                    firstName: contact.firstName,
                    lastName: contact.lastName,
                    company: contact.company,
                    jobTitle: contact.jobTitle,
                    imageUri: contact.imageUri,
                },
            }));

            // Call your backend API to sync contacts
            // await contactsAPI.syncDeviceContacts(contactsToSync);

            setState(prev => ({ ...prev, loading: false }));
        } catch (error) {
            setState(prev => ({
                ...prev,
                error: 'Failed to sync with backend',
                loading: false
            }));
        }
    }, [state.contacts]);

    // Filter contacts by search query (client-side)
    const filteredContacts = useMemo(() => {
        if (!searchQuery.trim()) return state.contacts;

        const query = searchQuery.toLowerCase();
        return state.contacts.filter(contact => {
            const nameMatch = contact.name.toLowerCase().includes(query);
            const phoneMatch = contact.phoneNumbers.some(p => p.number.includes(query));
            const emailMatch = contact.emails.some(e => e.email.toLowerCase().includes(query));
            return nameMatch || phoneMatch || emailMatch;
        });
    }, [state.contacts, searchQuery]);

    return {
        // State
        contacts: filteredContacts,
        allContacts: state.contacts,
        loading: state.loading,
        error: state.error,
        permissionStatus: state.permissionStatus,
        hasNextPage: state.hasNextPage,
        totalCount: state.totalCount,
        searchQuery,
        isAvailable,

        // Actions
        requestPermissions,
        checkPermissions,
        fetchContacts: () => fetchContacts(true),
        loadMore,
        searchContacts,
        setSearchQuery,
        getContactById,
        refresh,
        clearError,
        syncWithBackend,

        // Computed
        hasPermission: state.permissionStatus?.granted || false,
        canRequestPermission: state.permissionStatus?.canAskAgain !== false,
        isEmpty: filteredContacts.length === 0,
        isSearching: searchQuery.trim().length > 0,
    };
};

export default usePhoneContacts;