import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    TextInput,
    ActivityIndicator,
    RefreshControl,
    SectionList,
    Alert,
    Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { theme } from '../../src/theme';
import { useAuth } from '../../src/contexts/AuthContext';
import { contactsAPI } from '../../src/api/endpoints/contacts';
import { usePhoneContacts } from '../../src/hooks/usePhoneContacts';
import { PhoneContact } from '../../src/services/phoneContacts';

// =============================================================================
// Types
// =============================================================================

interface BackendContact {
    id: string;
    canonical_name: string;
    emails: string[] | null;
    phones: string[] | null;
    platform_identities: Record<string, string> | null;
    contact_metadata: Record<string, any> | null;
    avatar_url?: string;
    participant_count: number;
    thread_count: number;
    created_at: string;
    updated_at: string;
}

interface UnifiedContact {
    id: string;
    name: string;
    phones: string[];
    emails: string[];
    imageUri?: string;
    source: 'device' | 'backend' | 'merged';
    deviceContact?: PhoneContact;
    backendContact?: BackendContact;
    threadCount?: number;
    company?: string;
    jobTitle?: string;
}

interface ContactSection {
    title: string;
    data: UnifiedContact[];
}

// =============================================================================
// Contact Item Component (Memoized for performance with large lists)
// =============================================================================

// Helper function outside component to prevent recreation
const getInitials = (name: string) => {
    return name
        .split(' ')
        .map(word => word[0])
        .filter(Boolean)
        .join('')
        .toUpperCase()
        .slice(0, 2) || '?';
};

// Helper to get relationship Strength
const getRelationshipStrength = (contact: UnifiedContact) => {
    // TODO: Get real strength from backend
    // For now, simulate based on thread count and name hash for consistency
    const baseStrength = (contact.threadCount || 0) * 5 + 30;
    const nameHash = contact.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return Math.min(Math.max((baseStrength + (nameHash % 40)), 10), 98);
};

const getFrequencyLabel = (strength: number) => {
    if (strength > 75) return { label: 'High', color: '#10B981', bg: '#D1FAE5' };
    if (strength > 40) return { label: 'Medium', color: '#F59E0B', bg: '#FEF3C7' };
    return { label: 'Low', color: '#9CA3AF', bg: '#F3F4F6' };
};

const getRelationshipColor = (strength: number) => {
    if (strength >= 80) return '#10B981';
    if (strength >= 50) return '#F59E0B';
    return '#9CA3AF';
};

interface ContactItemProps {
    contact: UnifiedContact;
    onPress: (contact: UnifiedContact) => void;
    onAvatarPress?: (contact: UnifiedContact) => void;
}

const ContactItem = React.memo(({ contact, onPress, onAvatarPress }: ContactItemProps) => {
    const strength = getRelationshipStrength(contact);
    const strengthColor = getRelationshipColor(strength);
    const freq = getFrequencyLabel(strength);
    const displayPhone = contact.phones?.[0] || null;
    const displayEmail = contact.emails?.[0] || null;

    const handleAvatarPress = useCallback(() => {
        if (onAvatarPress) {
            onAvatarPress(contact);
        } else {
            onPress(contact);
        }
    }, [contact, onAvatarPress, onPress]);

    return (
        <TouchableOpacity
            style={styles.contactItem}
            onPress={() => onPress(contact)}
            activeOpacity={0.7}
        >
            {/* Avatar with Strength Ring */}
            <TouchableOpacity onPress={handleAvatarPress} activeOpacity={0.8} style={styles.avatarContainer}>
                <View style={[styles.strengthRing, { borderColor: strengthColor }]}>
                    <View style={styles.avatar}>
                        {contact.imageUri ? (
                            <Image
                                source={{ uri: contact.imageUri }}
                                style={styles.avatarImage}
                            />
                        ) : (
                            <Text style={styles.avatarText}>
                                {getInitials(contact.name)}
                            </Text>
                        )}
                    </View>
                </View>
            </TouchableOpacity>

            {/* Contact Info */}
            <View style={styles.contactInfo}>
                <View style={styles.contactNameRow}>
                    <Text style={styles.contactName} numberOfLines={1}>
                        {contact.name}
                    </Text>
                    {/* Source Indicators */}
                    <View style={styles.platformsRow}>
                        {contact.source === 'device' && (
                            <View style={[styles.platformDot, { backgroundColor: theme.colors.textTertiary }]}>
                                <Ionicons name="phone-portrait" size={8} color="white" />
                            </View>
                        )}
                        {contact.phones.length > 0 && contact.source !== 'device' && (
                            <View style={[styles.platformDot, { backgroundColor: '#25D366' }]}>
                                <Ionicons name="logo-whatsapp" size={8} color="white" />
                            </View>
                        )}
                        {contact.emails.length > 0 && (
                            <View style={[styles.platformDot, { backgroundColor: '#EA4335' }]}>
                                <Ionicons name="mail" size={8} color="white" />
                            </View>
                        )}
                    </View>
                </View>

                {/* Meta details */}
                <View style={styles.detailsRow}>
                    {contact.company ? (
                        <Text style={styles.contactDetail} numberOfLines={1}>
                            {contact.jobTitle ? `${contact.jobTitle}, ` : ''}{contact.company}
                        </Text>
                    ) : (
                        <Text style={styles.contactDetail} numberOfLines={1}>
                            {displayPhone || displayEmail || 'No contact info'}
                        </Text>
                    )}
                </View>

                {/* Metrics Row */}
                <View style={styles.metricsRow}>
                    {/* Relationship Strength Bar */}
                    <View style={styles.metric}>
                        <View style={styles.strengthBar}>
                            <View style={[
                                styles.strengthFill,
                                { width: `${strength}%`, backgroundColor: strengthColor }
                            ]} />
                        </View>
                        <Text style={[styles.metricValue, { color: strengthColor }]}>
                            {strength}%
                        </Text>
                    </View>

                    {/* Message Count */}
                    {contact.threadCount ? (
                        <View style={styles.metric}>
                            <Ionicons name="chatbubble" size={10} color={theme.colors.textSecondary} />
                            <Text style={styles.metricText}>{contact.threadCount}</Text>
                        </View>
                    ) : null}

                    {/* Frequency Badge */}
                    <View style={[styles.frequencyBadge, { backgroundColor: freq.bg }]}>
                        <Text style={[styles.frequencyText, { color: freq.color }]}>
                            {freq.label}
                        </Text>
                    </View>
                </View>
            </View>

            <Ionicons name="chevron-forward" size={20} color={theme.colors.textTertiary} />
        </TouchableOpacity>
    );
});

// =============================================================================
// Contacts Screen
// =============================================================================

export default function ContactsScreen() {
    const router = useRouter();
    const { isAuthenticated } = useAuth();

    const [backendContacts, setBackendContacts] = useState<BackendContact[]>([]);
    const [backendLoading, setBackendLoading] = useState(false);
    const syncIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const lastSyncRef = useRef<number>(0);

    // Phone contacts hook
    const {
        contacts: phoneContacts,
        loading: phoneLoading,
        error: phoneError,
        hasPermission,
        canRequestPermission,
        isAvailable: phoneContactsAvailable,
        searchQuery,
        requestPermissions,
        fetchContacts: fetchPhoneContacts,
        searchContacts,
        setSearchQuery,
        refresh: refreshPhoneContacts,
        clearError,
    } = usePhoneContacts({
        autoFetch: true,
        enableSearch: true,
    });

    // Alphabet for quick scroll
    const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'.split('');

    // Auto resync contacts every 5 minutes
    const SYNC_INTERVAL = 5 * 60 * 1000; // 5 minutes

    const syncContacts = useCallback(async () => {
        const now = Date.now();
        // Prevent syncing more than once per minute
        if (now - lastSyncRef.current < 60000) {
            return;
        }
        lastSyncRef.current = now;

        console.log('[Contacts] Auto-syncing contacts...');
        await Promise.all([
            refreshPhoneContacts(),
            fetchBackendContacts(),
        ]);
    }, [refreshPhoneContacts]);

    // Set up auto resync interval
    useEffect(() => {
        // Initial fetch
        fetchBackendContacts();

        // Start auto-sync interval
        syncIntervalRef.current = setInterval(() => {
            syncContacts();
        }, SYNC_INTERVAL);

        return () => {
            if (syncIntervalRef.current) {
                clearInterval(syncIntervalRef.current);
            }
        };
    }, [syncContacts]);

    const fetchBackendContacts = async () => {
        // Only fetch if user is authenticated
        if (!isAuthenticated) {
            setBackendContacts([]);
            return;
        }

        try {
            setBackendLoading(true);
            const response = await contactsAPI.listContacts({
                limit: 1000, // Get all contacts
            });
            setBackendContacts(response.contacts || []);
        } catch (error: any) {
            // Silently handle - may not be logged in or backend unavailable
            if (error?.response?.status === 401) {
                // Auth expired, just clear contacts
                console.log('[Contacts] Auth expired, skipping backend contacts');
            } else {
                console.warn('[Contacts] Backend contacts unavailable:', error?.message || 'Unknown error');
            }
            setBackendContacts([]);
        } finally {
            setBackendLoading(false);
        }
    };

    // Merge phone and backend contacts
    const unifiedContacts = useMemo((): UnifiedContact[] => {
        const contactMap = new Map<string, UnifiedContact>();

        // Add phone contacts
        phoneContacts.forEach(phoneContact => {
            const unifiedContact: UnifiedContact = {
                id: `phone_${phoneContact.id}`,
                name: phoneContact.name,
                phones: phoneContact.phoneNumbers.map(p => p.number),
                emails: phoneContact.emails.map(e => e.email),
                imageUri: phoneContact.imageUri || phoneContact.thumbnailUri,
                source: 'device',
                deviceContact: phoneContact,
                company: phoneContact.company,
                jobTitle: phoneContact.jobTitle,
            };

            // Try to match with backend contacts by phone/email
            const matchingBackend = backendContacts.find(bc => {
                const phoneMatch = bc.phones?.some(p =>
                    phoneContact.phoneNumbers.some(pn => pn.number.includes(p) || p.includes(pn.number))
                );
                const emailMatch = bc.emails?.some(e =>
                    phoneContact.emails.some(pe => pe.email.toLowerCase() === e.toLowerCase())
                );
                return phoneMatch || emailMatch;
            });

            if (matchingBackend) {
                unifiedContact.source = 'merged';
                unifiedContact.backendContact = matchingBackend;
                unifiedContact.threadCount = matchingBackend.thread_count;
                unifiedContact.id = `merged_${phoneContact.id}_${matchingBackend.id}`;
            }

            contactMap.set(unifiedContact.id, unifiedContact);
        });

        // Add backend-only contacts
        backendContacts.forEach(backendContact => {
            // Check if already merged
            const alreadyMerged = Array.from(contactMap.values()).some(uc =>
                uc.backendContact?.id === backendContact.id
            );

            if (!alreadyMerged) {
                const unifiedContact: UnifiedContact = {
                    id: `backend_${backendContact.id}`,
                    name: backendContact.canonical_name,
                    phones: backendContact.phones || [],
                    emails: backendContact.emails || [],
                    imageUri: backendContact.avatar_url,
                    source: 'backend',
                    backendContact: backendContact,
                    threadCount: backendContact.thread_count,
                };

                contactMap.set(unifiedContact.id, unifiedContact);
            }
        });

        return Array.from(contactMap.values()).sort((a, b) => a.name.localeCompare(b.name));
    }, [phoneContacts, backendContacts]);

    const onRefresh = useCallback(async () => {
        await Promise.all([
            refreshPhoneContacts(),
            fetchBackendContacts(),
        ]);
    }, [refreshPhoneContacts]);

    // Handle search
    const handleSearch = useCallback((query: string) => {
        setSearchQuery(query);
        if (phoneContactsAvailable) {
            searchContacts(query);
        }
    }, [setSearchQuery, searchContacts, phoneContactsAvailable]);

    // Filter unified contacts by search (for backend contacts)
    const filteredContacts = useMemo(() => {
        if (!searchQuery.trim()) return unifiedContacts;

        const query = searchQuery.toLowerCase();
        return unifiedContacts.filter(contact => {
            const nameMatch = contact.name.toLowerCase().includes(query);
            const phoneMatch = contact.phones.some(p => p.includes(query));
            const emailMatch = contact.emails.some(e => e.toLowerCase().includes(query));
            const companyMatch = contact.company?.toLowerCase().includes(query);
            return nameMatch || phoneMatch || emailMatch || companyMatch;
        });
    }, [unifiedContacts, searchQuery]);

    // Group contacts by first letter
    const sections = useMemo(() => {
        const grouped: Record<string, UnifiedContact[]> = {};

        filteredContacts.forEach(contact => {
            const firstChar = contact.name.charAt(0).toUpperCase();
            const key = /[A-Z]/.test(firstChar) ? firstChar : '#';

            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(contact);
        });

        // Sort sections alphabetically
        return Object.keys(grouped)
            .sort((a, b) => {
                if (a === '#') return 1;
                if (b === '#') return -1;
                return a.localeCompare(b);
            })
            .map(key => ({
                title: key,
                data: grouped[key],
            }));
    }, [filteredContacts]);

    const handleContactPress = (contact: UnifiedContact) => {
        // Determine the primary ID for the route
        let primaryId = '';
        if (contact.backendContact) {
            primaryId = contact.backendContact.id;
        } else if (contact.deviceContact) {
            primaryId = contact.deviceContact.id;
        } else {
            primaryId = contact.id;
        }

        router.push({
            pathname: '/contact/[id]' as const,
            params: {
                id: primaryId,
                source: contact.source,
                deviceId: contact.deviceContact?.id || '',
            },
        });
    };

    // Handle avatar press - same as contact press for now
    const handleAvatarPress = (contact: UnifiedContact) => {
        handleContactPress(contact);
    };

    // Handle permission request
    const handleRequestPermissions = useCallback(async () => {
        const granted = await requestPermissions();
        if (granted) {
            fetchPhoneContacts();
        }
    }, [requestPermissions, fetchPhoneContacts]);

    // Render section header
    const renderSectionHeader = ({ section }: { section: ContactSection }) => (
        <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{section.title}</Text>
        </View>
    );

    // Render permission request
    const renderPermissionRequest = () => (
        <View style={styles.permissionContainer}>
            <Ionicons name="people" size={60} color={theme.colors.primary} />
            <Text style={styles.permissionTitle}>Access Your Contacts</Text>
            <Text style={styles.permissionSubtitle}>
                Allow access to your device contacts to see all your friends and easily start conversations.
            </Text>
            <TouchableOpacity
                style={styles.permissionButton}
                onPress={handleRequestPermissions}
            >
                <Text style={styles.permissionButtonText}>Allow Access</Text>
            </TouchableOpacity>
            {!canRequestPermission && (
                <TouchableOpacity
                    style={[styles.permissionButton, { backgroundColor: theme.colors.surface, marginTop: 12 }]}
                    onPress={() => {
                        Linking.openSettings();
                    }}
                >
                    <Text style={[styles.permissionButtonText, { color: theme.colors.primary }]}>
                        Open Settings
                    </Text>
                </TouchableOpacity>
            )}
        </View>
    );

    // Define loading state early so it can be used in renderEmptyState
    const loading = phoneLoading || backendLoading;
    const refreshing = loading;

    // Empty state - show permission prompt if no device contacts
    const renderEmptyState = () => {
        // Only show permission prompt if:
        // 1. Phone contacts are available on this platform
        // 2. User does NOT have permission granted
        // 3. We're not still loading
        const shouldPromptPermission = phoneContactsAvailable && !hasPermission && !loading;

        if (shouldPromptPermission) {
            return (
                <View style={styles.permissionContainer}>
                    <Ionicons name="people" size={60} color={theme.colors.primary} />
                    <Text style={styles.permissionTitle}>Access Your Contacts</Text>
                    <Text style={styles.permissionSubtitle}>
                        Grant permission to see your device contacts and easily start conversations.
                    </Text>
                    <TouchableOpacity
                        style={styles.permissionButton}
                        onPress={handleRequestPermissions}
                    >
                        <Text style={styles.permissionButtonText}>Grant Permission</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.permissionButton, { backgroundColor: theme.colors.surface, marginTop: 12 }]}
                        onPress={() => {
                            Linking.openSettings();
                        }}
                    >
                        <Text style={[styles.permissionButtonText, { color: theme.colors.primary }]}>
                            Open Settings
                        </Text>
                    </TouchableOpacity>
                </View>
            );
        }

        return (
            <View style={styles.emptyState}>
                <Ionicons name="people-outline" size={80} color={theme.colors.textTertiary} />
                <Text style={styles.emptyTitle}>No Contacts</Text>
                <Text style={styles.emptySubtitle}>
                    {searchQuery
                        ? "No contacts match your search."
                        : "Contacts from your conversations will appear here."
                    }
                </Text>
            </View>
        );
    };

    if (loading && unifiedContacts.length === 0) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
                <Text style={styles.loadingText}>Loading contacts...</Text>
            </View>
        );
    }

    // Show permission request ONLY if contacts are available but no permission granted
    // Don't show this if permission is granted but 0 contacts (that's handled by renderEmptyState)
    if (phoneContactsAvailable && !hasPermission && backendContacts.length === 0) {
        return (
            <View style={styles.container}>
                {renderPermissionRequest()}
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* Error Banner */}
            {phoneError && (
                <View style={styles.errorBanner}>
                    <Text style={styles.errorText}>{phoneError}</Text>
                    <TouchableOpacity onPress={clearError}>
                        <Ionicons name="close" size={20} color={theme.colors.error} />
                    </TouchableOpacity>
                </View>
            )}

            {/* Search Bar */}
            <View style={styles.searchContainer}>
                <Ionicons name="search" size={20} color={theme.colors.textSecondary} />
                <TextInput
                    style={styles.searchInput}
                    placeholder="Search contacts..."
                    placeholderTextColor={theme.colors.textTertiary}
                    value={searchQuery}
                    onChangeText={handleSearch}
                    autoCorrect={false}
                />
                {searchQuery.length > 0 && (
                    <TouchableOpacity onPress={() => handleSearch('')}>
                        <Ionicons name="close-circle" size={20} color={theme.colors.textSecondary} />
                    </TouchableOpacity>
                )}
            </View>

            {/* Contact count */}
            <View style={styles.countContainer}>
                <Text style={styles.countText}>
                    {filteredContacts.length} {filteredContacts.length === 1 ? 'contact' : 'contacts'}
                    {phoneContactsAvailable && (
                        <Text style={styles.sourceText}>
                            {' • '}
                            {phoneContacts.length} from device, {backendContacts.length} from conversations
                        </Text>
                    )}
                </Text>
            </View>

            {/* Contacts List */}
            {filteredContacts.length === 0 ? (
                renderEmptyState()
            ) : (
                <View style={styles.listContainer}>
                    <SectionList
                        sections={sections}
                        keyExtractor={(item) => item.id}
                        renderItem={({ item }) => (
                            <ContactItem
                                contact={item}
                                onPress={handleContactPress}
                                onAvatarPress={handleAvatarPress}
                            />
                        )}
                        renderSectionHeader={renderSectionHeader}
                        stickySectionHeadersEnabled={true}
                        refreshControl={
                            <RefreshControl
                                refreshing={refreshing}
                                onRefresh={onRefresh}
                                tintColor={theme.colors.primary}
                            />
                        }
                        showsVerticalScrollIndicator={false}
                        contentContainerStyle={styles.listContent}
                        // Performance optimizations for large lists
                        windowSize={10}
                        maxToRenderPerBatch={15}
                        initialNumToRender={20}
                        removeClippedSubviews={true}
                        updateCellsBatchingPeriod={50}
                    />

                    {/* Alphabet Index */}
                    <View style={styles.alphabetIndex}>
                        {ALPHABET.map(letter => (
                            <TouchableOpacity
                                key={letter}
                                style={styles.alphabetLetter}
                                onPress={() => {
                                    // TODO: Scroll to section
                                }}
                            >
                                <Text style={styles.alphabetText}>{letter}</Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                </View>
            )}
        </View>
    );
}

// =============================================================================
// Styles
// =============================================================================

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: theme.colors.background,
    },
    loadingText: {
        marginTop: 12,
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        marginHorizontal: 16,
        marginTop: 12,
        marginBottom: 8,
        paddingHorizontal: 14,
        paddingVertical: 10,
        borderRadius: 12,
        gap: 10,
        ...theme.shadows.sm,
    },
    searchInput: {
        flex: 1,
        fontSize: 15,
        color: theme.colors.text,
    },
    countContainer: {
        paddingHorizontal: 16,
        paddingVertical: 8,
    },
    countText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    listContainer: {
        flex: 1,
        flexDirection: 'row',
    },
    listContent: {
        paddingBottom: 100,
    },
    sectionHeader: {
        backgroundColor: theme.colors.backgroundSecondary,
        paddingHorizontal: 16,
        paddingVertical: 6,
    },
    sectionTitle: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    contactItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: theme.colors.background,
        marginBottom: 1,
        borderBottomWidth: 0,
    },
    avatarContainer: {
        marginRight: 14,
    },
    strengthRing: {
        width: 50,
        height: 50,
        borderRadius: 25,
        borderWidth: 2.5,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 2,
    },
    avatar: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: theme.colors.primary,
        justifyContent: 'center',
        alignItems: 'center',
    },
    avatarImage: {
        width: 40,
        height: 40,
        borderRadius: 20,
    },
    avatarText: {
        fontSize: 15,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    contactInfo: {
        flex: 1,
        justifyContent: 'center',
        marginRight: 8,
    },
    contactNameRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 4,
    },
    contactName: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginRight: 8,
    },
    platformsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    platformDot: {
        width: 14,
        height: 14,
        borderRadius: 7,
        alignItems: 'center',
        justifyContent: 'center',
    },
    detailsRow: {
        marginBottom: 6,
    },
    contactDetail: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    sourceText: {
        fontSize: 11,
        color: theme.colors.textTertiary,
    },
    metricsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    metric: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    strengthBar: {
        width: 30,
        height: 3,
        backgroundColor: theme.colors.surface,
        borderRadius: 1.5,
        overflow: 'hidden',
    },
    strengthFill: {
        height: '100%',
        borderRadius: 1.5,
    },
    metricValue: {
        fontSize: 10,
        fontWeight: '600',
    },
    metricText: {
        fontSize: 10,
        color: theme.colors.textSecondary,
    },
    frequencyBadge: {
        paddingHorizontal: 6,
        paddingVertical: 1.5,
        borderRadius: 8,
    },
    frequencyText: {
        fontSize: 9,
        fontWeight: '600',
    },
    permissionContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
        backgroundColor: theme.colors.background,
    },
    permissionTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 20,
        marginBottom: 12,
        textAlign: 'center',
    },
    permissionSubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
        marginBottom: 30,
    },
    permissionButton: {
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 30,
        paddingVertical: 12,
        borderRadius: 8,
    },
    permissionButtonText: {
        color: '#FFFFFF',
        fontSize: 16,
        fontWeight: '600',
    },
    errorBanner: {
        backgroundColor: '#FEF2F2',
        padding: 12,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottomWidth: 1,
        borderBottomColor: '#FECACA',
    },
    errorText: {
        color: theme.colors.error,
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
        marginRight: 8,
    },
    threadCount: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.primary,
        marginLeft: 4,
    },
    alphabetIndex: {
        position: 'absolute',
        right: 4,
        top: 0,
        bottom: 0,
        justifyContent: 'center',
        alignItems: 'center',
        paddingVertical: 10,
    },
    alphabetLetter: {
        paddingVertical: 1,
        paddingHorizontal: 4,
    },
    alphabetText: {
        fontSize: 10,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
        marginBottom: 8,
    },
    emptySubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
    },
});
