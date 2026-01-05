import React, { useEffect, useState, useCallback } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    Image,
    Alert,
    ActivityIndicator,
    Clipboard,
    Platform,
    Dimensions,
} from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Linking from 'expo-linking';
import * as Contacts from 'expo-contacts';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';
import { contactsAPI } from '../../src/api/endpoints/contacts';
import { messagesAPI } from '../../src/api/endpoints/messages';
import EditContactModal from '../../components/contacts/EditContactModal';

// Platform configuration
const PLATFORM_CONFIG: Record<string, { icon: string; color: string; name: string }> = {
    whatsapp: { icon: 'logo-whatsapp', color: '#25D366', name: 'WhatsApp' },
    linkedin: { icon: 'logo-linkedin', color: '#0A66C2', name: 'LinkedIn' },
    google_chat: { icon: 'chatbubbles', color: '#4285F4', name: 'Google Chat' },
    slack: { icon: 'logo-slack', color: '#4A154B', name: 'Slack' },
    discord: { icon: 'logo-discord', color: '#5865F2', name: 'Discord' },
    twitter: { icon: 'logo-twitter', color: '#1DA1F2', name: 'Twitter' },
    instagram: { icon: 'logo-instagram', color: '#E4405F', name: 'Instagram' },
    facebook: { icon: 'logo-facebook', color: '#1877F2', name: 'Facebook' },
    telegram: { icon: 'paper-plane', color: '#0088CC', name: 'Telegram' },
};

interface ContactInfo {
    id: string;
    name: string;
    firstName?: string;
    lastName?: string;
    phones: Array<{ number: string; label?: string }>;
    emails: Array<{ email: string; label?: string }>;
    company?: string;
    jobTitle?: string;
    imageUri?: string;
    location?: string;
    platforms: Array<{ platform: string; handle: string; icon: string; color: string }>;
    source: 'device' | 'backend' | 'merged';
    deviceContactId?: string;
    backendContactId?: string;
}

interface Message {
    id: string;
    platform: string;
    sender: string;
    content: string;
    timestamp: string;
}

// Generate a consistent color based on name
const getAvatarColor = (name: string) => {
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
    ];
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
};

export default function ContactProfileScreen() {
    const params = useLocalSearchParams();
    const router = useRouter();
    const [contact, setContact] = useState<ContactInfo | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [showEditModal, setShowEditModal] = useState(false);

    // Extract params - can be backend ID, device ID, or both
    const backendId = params.id as string;
    const deviceId = params.deviceId as string;
    const source = params.source as 'device' | 'backend' | 'merged';

    useEffect(() => {
        fetchData();
    }, [backendId, deviceId]);

    const fetchData = async () => {
        try {
            setLoading(true);
            let contactInfo: ContactInfo | null = null;
            let fetchedMessages: Message[] = [];

            // Fetch from backend if we have a backend ID
            if (backendId && source !== 'device') {
                try {
                    const contactData = await contactsAPI.getContact(backendId);

                    contactInfo = {
                        id: contactData.id,
                        name: contactData.canonical_name,
                        phones: (contactData.phones || []).map((p: string) => ({ number: p })),
                        emails: (contactData.emails || []).map((e: string) => ({ email: e })),
                        company: contactData.contact_metadata?.company,
                        jobTitle: contactData.contact_metadata?.role,
                        imageUri: contactData.contact_metadata?.avatar_url,
                        location: contactData.contact_metadata?.location,
                        platforms: Object.entries(contactData.platform_identities || {}).map(([key, val]) => ({
                            platform: key,
                            handle: val as string,
                            icon: PLATFORM_CONFIG[key.toLowerCase()]?.icon || 'albums',
                            color: PLATFORM_CONFIG[key.toLowerCase()]?.color || '#666',
                        })),
                        source: source || 'backend',
                        backendContactId: contactData.id,
                    };

                    // Fetch messages for this contact
                    const messagesData = await messagesAPI.listMessages({ contact_id: backendId, limit: 20 });
                    fetchedMessages = messagesData.messages || [];
                } catch (error) {
                    console.error('Error fetching backend contact:', error);
                }
            }

            // Determine effective device ID - for device contacts, id might be the device ID
            const effectiveDeviceId = deviceId || (source === 'device' ? backendId : '');

            // Fetch from device if we have a device ID
            if (effectiveDeviceId) {
                try {
                    const deviceContact = await Contacts.getContactByIdAsync(effectiveDeviceId, [
                        Contacts.Fields.ID,
                        Contacts.Fields.Name,
                        Contacts.Fields.FirstName,
                        Contacts.Fields.LastName,
                        Contacts.Fields.PhoneNumbers,
                        Contacts.Fields.Emails,
                        Contacts.Fields.Image,
                        Contacts.Fields.Company,
                        Contacts.Fields.JobTitle,
                        Contacts.Fields.Addresses,
                        Contacts.Fields.SocialProfiles,
                    ]);

                    if (deviceContact) {
                        const deviceInfo: ContactInfo = {
                            id: deviceContact.id || effectiveDeviceId,
                            name: deviceContact.name || `${deviceContact.firstName || ''} ${deviceContact.lastName || ''}`.trim() || 'Unknown',
                            firstName: deviceContact.firstName,
                            lastName: deviceContact.lastName,
                            phones: (deviceContact.phoneNumbers || []).map((p: any) => ({
                                number: p.number || '',
                                label: p.label
                            })),
                            emails: (deviceContact.emails || []).map((e: any) => ({
                                email: e.email || '',
                                label: e.label
                            })),
                            company: deviceContact.company,
                            jobTitle: deviceContact.jobTitle,
                            imageUri: deviceContact.image?.uri,
                            location: (deviceContact as any).addresses?.[0]?.city,
                            platforms: (deviceContact as any).socialProfiles?.map((sp: any) => ({
                                platform: sp.service || 'unknown',
                                handle: sp.username || sp.url || '',
                                icon: PLATFORM_CONFIG[sp.service?.toLowerCase()]?.icon || 'globe',
                                color: PLATFORM_CONFIG[sp.service?.toLowerCase()]?.color || '#666',
                            })) || [],
                            source: source || 'device',
                            deviceContactId: deviceContact.id,
                        };

                        // Merge with backend info if available
                        if (contactInfo) {
                            contactInfo = {
                                ...contactInfo,
                                // Prefer device data for personal info
                                name: deviceInfo.name || contactInfo.name,
                                firstName: deviceInfo.firstName,
                                lastName: deviceInfo.lastName,
                                imageUri: deviceInfo.imageUri || contactInfo.imageUri,
                                company: deviceInfo.company || contactInfo.company,
                                jobTitle: deviceInfo.jobTitle || contactInfo.jobTitle,
                                // Merge phones and emails (dedupe)
                                phones: [...new Map([...deviceInfo.phones, ...contactInfo.phones]
                                    .filter(p => p.number)
                                    .map(p => [p.number.replace(/\D/g, ''), p]))
                                    .values()],
                                emails: [...new Map([...deviceInfo.emails, ...contactInfo.emails]
                                    .filter(e => e.email)
                                    .map(e => [e.email.toLowerCase(), e]))
                                    .values()],
                                // Merge platforms
                                platforms: [...contactInfo.platforms, ...deviceInfo.platforms],
                                source: 'merged',
                                deviceContactId: deviceInfo.id,
                            };
                        } else {
                            contactInfo = deviceInfo;
                        }
                    }
                } catch (error) {
                    console.error('Error fetching device contact:', error);
                }
            }

            setContact(contactInfo);
            setMessages(fetchedMessages);
        } catch (error) {
            console.error('Error fetching contact details:', error);
            Alert.alert('Error', 'Failed to load contact details');
        } finally {
            setLoading(false);
        }
    };

    const handleCall = useCallback((phone: string) => {
        Linking.openURL(`tel:${phone}`);
    }, []);

    const handleEmail = useCallback((email: string) => {
        Linking.openURL(`mailto:${email}`);
    }, []);

    const handleCopy = useCallback((text: string, label: string) => {
        Clipboard.setString(text);
        Alert.alert('Copied', `${label} copied to clipboard`);
    }, []);

    const handleOpenPlatform = useCallback((platform: string, handle: string) => {
        // Try to open the platform app or website
        let url = '';
        switch (platform.toLowerCase()) {
            case 'whatsapp':
                url = `whatsapp://send?phone=${handle.replace(/\D/g, '')}`;
                break;
            case 'linkedin':
                url = `linkedin://profile/${handle}`;
                break;
            case 'twitter':
                url = `twitter://user?screen_name=${handle}`;
                break;
            case 'instagram':
                url = `instagram://user?username=${handle}`;
                break;
            default:
                Alert.alert('Open', `Opening ${platform} for ${handle}...`);
                return;
        }

        Linking.canOpenURL(url).then(canOpen => {
            if (canOpen) {
                Linking.openURL(url);
            } else {
                Alert.alert('Cannot Open', `${platform} app is not installed`);
            }
        });
    }, []);

    const handleViewConversation = useCallback(() => {
        if (contact?.backendContactId) {
            router.push({
                pathname: '/contact/conversation',
                params: {
                    contactId: contact.backendContactId,
                    contactName: contact.name,
                }
            });
        } else {
            Alert.alert(
                'No Conversations',
                'No conversations found for this contact. Connect a messaging platform to start syncing.',
                [{ text: 'OK' }]
            );
        }
    }, [contact, router]);

    if (loading) {
        return (
            <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
            </View>
        );
    }

    if (!contact) {
        return (
            <View style={styles.container}>
                <Stack.Screen options={{ title: 'Contact Not Found' }} />
                <Text style={styles.errorText}>Contact not found</Text>
            </View>
        );
    }

    const initials = contact.name
        ? contact.name.split(' ').map((n: string) => n[0]).filter(Boolean).join('').toUpperCase().slice(0, 2)
        : '??';
    const avatarColor = getAvatarColor(contact.name);

    // Computed Metrics (Simulated + Real)
    const threadCount = messages.length; // Approximate
    const nameHash = contact.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const strength = (threadCount * 5 + 30 + (nameHash % 30));
    const clampedStrength = Math.min(Math.max(strength, 10), 98);

    let strengthColor = '#9CA3AF';
    if (clampedStrength > 75) strengthColor = '#10B981';
    else if (clampedStrength > 40) strengthColor = '#F59E0B';

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    headerShown: false
                }}
            />

            {/* Custom Header with Gradient Background */}
            <View style={styles.navHeader}>
                <TouchableOpacity
                    onPress={() => router.back()}
                    style={styles.navButton}
                >
                    <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                </TouchableOpacity>
                <TouchableOpacity
                    onPress={() => setShowEditModal(true)}
                    style={styles.navButton}
                >
                    <Ionicons name="create-outline" size={22} color={theme.colors.primary} />
                </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
                {/* Profile Header */}
                <View style={styles.header}>
                    <View style={styles.avatarContainer}>
                        {/* Strength Ring */}
                        <View style={[styles.strengthRing, { borderColor: strengthColor }]}>
                            <View style={[styles.avatar, { backgroundColor: avatarColor }]}>
                                {contact.imageUri ? (
                                    <Image source={{ uri: contact.imageUri }} style={styles.avatarImage} />
                                ) : (
                                    <Text style={styles.avatarText}>{initials}</Text>
                                )}
                            </View>
                        </View>

                        {/* Source indicator badge */}
                        <View style={[styles.sourceBadge, {
                            backgroundColor: contact.source === 'merged' ? '#E8F5E9' :
                                contact.source === 'device' ? theme.colors.primaryLighter : '#E3F2FD'
                        }]}>
                            <Ionicons
                                name={contact.source === 'merged' ? 'link' :
                                    contact.source === 'device' ? 'phone-portrait' : 'chatbubbles'}
                                size={14}
                                color={contact.source === 'merged' ? theme.colors.success :
                                    contact.source === 'device' ? theme.colors.primary : '#1976D2'}
                            />
                        </View>
                    </View>

                    <Text style={styles.name}>{contact.name}</Text>
                    {(contact.jobTitle || contact.company) && (
                        <Text style={styles.role}>
                            {contact.jobTitle}{contact.jobTitle && contact.company ? ' • ' : ''}{contact.company}
                        </Text>
                    )}

                    {/* Metrics Row */}
                    <View style={styles.metricsRow}>
                        <View style={styles.metricItem}>
                            <Text style={[styles.metricValue, { color: strengthColor }]}>{clampedStrength}%</Text>
                            <Text style={styles.metricLabel}>Relationship</Text>
                        </View>
                        <View style={styles.metricDivider} />
                        <View style={styles.metricItem}>
                            <Text style={styles.metricValue}>{threadCount}</Text>
                            <Text style={styles.metricLabel}>Interactions</Text>
                        </View>
                        <View style={styles.metricDivider} />
                        <View style={styles.metricItem}>
                            <Text style={styles.metricValue}>
                                {messages.length > 0 ? 'Today' : 'Never'}
                            </Text>
                            <Text style={styles.metricLabel}>Last Seen</Text>
                        </View>
                    </View>

                    {/* Action Buttons Grid */}
                    <View style={styles.actionGrid}>
                        <TouchableOpacity
                            style={styles.actionGridItem}
                            onPress={handleViewConversation}
                        >
                            <View style={[styles.actionIconCircle, { backgroundColor: theme.colors.primary }]}>
                                <Ionicons name="chatbubbles" size={22} color="white" />
                            </View>
                            <Text style={styles.actionGridLabel}>Message</Text>
                        </TouchableOpacity>

                        {contact.phones.length > 0 && (
                            <TouchableOpacity
                                style={styles.actionGridItem}
                                onPress={() => handleCall(contact.phones[0].number)}
                            >
                                <View style={[styles.actionIconCircle, { backgroundColor: '#34C759' }]}>
                                    <Ionicons name="call" size={22} color="white" />
                                </View>
                                <Text style={styles.actionGridLabel}>Call</Text>
                            </TouchableOpacity>
                        )}

                        {contact.emails.length > 0 && (
                            <TouchableOpacity
                                style={styles.actionGridItem}
                                onPress={() => handleEmail(contact.emails[0].email)}
                            >
                                <View style={[styles.actionIconCircle, { backgroundColor: '#FF9500' }]}>
                                    <Ionicons name="mail" size={22} color="white" />
                                </View>
                                <Text style={styles.actionGridLabel}>Email</Text>
                            </TouchableOpacity>
                        )}

                        <TouchableOpacity
                            style={styles.actionGridItem}
                            onPress={() => setShowEditModal(true)}
                        >
                            <View style={[styles.actionIconCircle, { backgroundColor: '#8E8E93' }]}>
                                <Ionicons name="create" size={22} color="white" />
                            </View>
                            <Text style={styles.actionGridLabel}>Edit</Text>
                        </TouchableOpacity>
                    </View>
                </View>

                {/* Phone Numbers */}
                {contact.phones.length > 0 && (
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Phone Numbers</Text>
                        <Card style={styles.infoCard} shadow="sm">
                            {contact.phones.map((phone, index) => (
                                <React.Fragment key={phone.number + index}>
                                    {index > 0 && <View style={styles.divider} />}
                                    <TouchableOpacity
                                        style={styles.infoRow}
                                        onPress={() => handleCall(phone.number)}
                                    >
                                        <View style={styles.infoIcon}>
                                            <Ionicons name="call-outline" size={20} color={theme.colors.textSecondary} />
                                        </View>
                                        <View style={styles.infoContent}>
                                            <Text style={styles.infoLabel}>{phone.label || 'Phone'}</Text>
                                            <Text style={styles.infoValue}>{phone.number}</Text>
                                        </View>
                                        <TouchableOpacity onPress={() => handleCopy(phone.number, 'Phone number')}>
                                            <Ionicons name="copy-outline" size={18} color={theme.colors.textTertiary} />
                                        </TouchableOpacity>
                                    </TouchableOpacity>
                                </React.Fragment>
                            ))}
                        </Card>
                    </View>
                )}

                {/* Email Addresses */}
                {contact.emails.length > 0 && (
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Email Addresses</Text>
                        <Card style={styles.infoCard} shadow="sm">
                            {contact.emails.map((email, index) => (
                                <React.Fragment key={email.email + index}>
                                    {index > 0 && <View style={styles.divider} />}
                                    <TouchableOpacity
                                        style={styles.infoRow}
                                        onPress={() => handleEmail(email.email)}
                                    >
                                        <View style={styles.infoIcon}>
                                            <Ionicons name="mail-outline" size={20} color={theme.colors.textSecondary} />
                                        </View>
                                        <View style={styles.infoContent}>
                                            <Text style={styles.infoLabel}>{email.label || 'Email'}</Text>
                                            <Text style={styles.infoValue}>{email.email}</Text>
                                        </View>
                                        <TouchableOpacity onPress={() => handleCopy(email.email, 'Email')}>
                                            <Ionicons name="copy-outline" size={18} color={theme.colors.textTertiary} />
                                        </TouchableOpacity>
                                    </TouchableOpacity>
                                </React.Fragment>
                            ))}
                        </Card>
                    </View>
                )}

                {/* Connected Platforms */}
                {contact.platforms.length > 0 && (
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Connected Platforms</Text>
                        {contact.platforms.map((platform, index) => (
                            <Card key={platform.platform + index} style={styles.platformCard} shadow="sm">
                                <View style={styles.platformHeader}>
                                    <View style={[styles.platformIcon, { backgroundColor: platform.color + '20' }]}>
                                        <Ionicons name={platform.icon as any} size={20} color={platform.color} />
                                    </View>
                                    <View style={styles.platformInfo}>
                                        <Text style={styles.platformName}>
                                            {PLATFORM_CONFIG[platform.platform.toLowerCase()]?.name || platform.platform}
                                        </Text>
                                        <Text style={styles.platformHandle}>{platform.handle}</Text>
                                    </View>
                                    <TouchableOpacity
                                        style={[styles.platformAction, { borderColor: platform.color }]}
                                        onPress={() => handleOpenPlatform(platform.platform, platform.handle)}
                                    >
                                        <Text style={[styles.platformActionText, { color: platform.color }]}>Open</Text>
                                    </TouchableOpacity>
                                </View>
                            </Card>
                        ))}
                    </View>
                )}

                {/* Recent Messages Preview */}
                {messages.length > 0 && (
                    <View style={styles.section}>
                        <View style={styles.sectionHeader}>
                            <Text style={styles.sectionTitle}>Recent Activity</Text>
                            <TouchableOpacity onPress={handleViewConversation}>
                                <Text style={styles.seeAllText}>See All</Text>
                            </TouchableOpacity>
                        </View>
                        {messages.slice(0, 3).map((msg, index) => (
                            <Card key={msg.id || index} style={styles.activityCard} shadow="sm">
                                <View style={styles.activityHeader}>
                                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                                        <View style={[styles.platformDot, {
                                            backgroundColor: PLATFORM_CONFIG[msg.platform?.toLowerCase()]?.color || '#666'
                                        }]} />
                                        <Text style={styles.activityPlatform}>
                                            {PLATFORM_CONFIG[msg.platform?.toLowerCase()]?.name || msg.platform}
                                        </Text>
                                    </View>
                                    <Text style={styles.activityTime}>
                                        {msg.timestamp ? new Date(msg.timestamp).toLocaleString([], {
                                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                        }) : ''}
                                    </Text>
                                </View>
                                <Text style={styles.activityText} numberOfLines={2}>{msg.content}</Text>
                            </Card>
                        ))}
                        <TouchableOpacity style={styles.viewAllButton} onPress={handleViewConversation}>
                            <Text style={styles.viewAllButtonText}>View Full Conversation</Text>
                            <Ionicons name="arrow-forward" size={16} color={theme.colors.primary} />
                        </TouchableOpacity>
                    </View>
                )}

                {/* No messages state */}
                {messages.length === 0 && contact.source !== 'device' && (
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Messages</Text>
                        <Card style={styles.emptyCard} shadow="sm">
                            <Ionicons name="chatbubbles-outline" size={40} color={theme.colors.textTertiary} />
                            <Text style={styles.emptyText}>No messages yet</Text>
                            <Text style={styles.emptySubtext}>
                                Messages from connected platforms will appear here
                            </Text>
                        </Card>
                    </View>
                )}

                <View style={{ height: 40 }} />
            </ScrollView>

            {/* Edit Contact Modal */}
            <EditContactModal
                visible={showEditModal}
                onClose={() => setShowEditModal(false)}
                contact={contact ? {
                    id: contact.id,
                    name: contact.name,
                    firstName: contact.firstName,
                    lastName: contact.lastName,
                    company: contact.company,
                    jobTitle: contact.jobTitle,
                    platforms: contact.platforms.map(p => ({
                        platform: p.platform,
                        handle: p.handle,
                    })),
                    deviceContactId: contact.deviceContactId,
                    backendContactId: contact.backendContactId,
                } : null}
                onSave={(updatedContact) => {
                    console.log('Contact saved:', updatedContact);
                    // Refresh contact data
                    fetchData();
                }}
                isDeviceOnly={contact?.source === 'device'}
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    navHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingTop: 60,
        paddingBottom: 16,
        backgroundColor: theme.colors.backgroundSecondary,
        zIndex: 10,
    },
    navButton: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: 'white',
        alignItems: 'center',
        justifyContent: 'center',
        ...theme.shadows.sm,
    },
    errorText: {
        textAlign: 'center',
        marginTop: 100,
        fontSize: 18,
        color: theme.colors.textSecondary,
    },
    scrollContent: {
        paddingTop: 0,
        paddingBottom: 40,
    },
    header: {
        alignItems: 'center',
        paddingHorizontal: 24,
        marginBottom: 32,
    },
    avatarContainer: {
        marginBottom: 16,
        position: 'relative',
        alignItems: 'center',
        justifyContent: 'center',
    },
    strengthRing: {
        width: 110,
        height: 110,
        borderRadius: 55,
        borderWidth: 4,
        alignItems: 'center',
        justifyContent: 'center',
        // Drop shadow/glow for premium feel
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
        elevation: 5,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    avatar: {
        width: 96,
        height: 96,
        borderRadius: 48,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarImage: {
        width: 96,
        height: 96,
        borderRadius: 48,
    },
    avatarText: {
        fontSize: 32,
        fontWeight: 'bold',
        color: 'white',
    },
    sourceBadge: {
        position: 'absolute',
        bottom: 0,
        right: 0,
        width: 32,
        height: 32,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 2,
        borderColor: 'white',
        elevation: 2,
    },
    name: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 4,
        textAlign: 'center',
    },
    role: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginBottom: 20,
        textAlign: 'center',
    },
    metricsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'white',
        paddingVertical: 12,
        paddingHorizontal: 20,
        borderRadius: 16,
        marginBottom: 24,
        width: '100%',
        ...theme.shadows.sm,
    },
    metricItem: {
        alignItems: 'center',
        flex: 1,
    },
    metricValue: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 2,
    },
    metricLabel: {
        fontSize: 11,
        color: theme.colors.textTertiary,
        textTransform: 'uppercase',
    },
    metricDivider: {
        width: 1,
        height: 24,
        backgroundColor: theme.colors.borderLight,
    },
    actionGrid: {
        flexDirection: 'row',
        justifyContent: 'center',
        gap: 24,
    },
    actionGridItem: {
        alignItems: 'center',
        gap: 8,
    },
    actionIconCircle: {
        width: 52,
        height: 52,
        borderRadius: 26,
        alignItems: 'center',
        justifyContent: 'center',
        ...theme.shadows.sm,
    },
    actionGridLabel: {
        fontSize: 12,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    section: {
        paddingHorizontal: 24,
        marginBottom: 24,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 16,
    },
    seeAllText: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    platformCard: {
        marginBottom: 12,
        padding: 16,
    },
    platformHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
    },
    platformIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformInfo: {
        flex: 1,
    },
    platformName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    platformHandle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    platformAction: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
        borderWidth: 1,
    },
    platformActionText: {
        fontSize: 12,
        fontWeight: '600',
    },
    infoCard: {
        padding: 0,
        overflow: 'hidden',
    },
    infoRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        gap: 16,
    },
    infoIcon: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
    },
    infoContent: {
        flex: 1,
    },
    infoLabel: {
        fontSize: 12,
        color: theme.colors.textTertiary,
        marginBottom: 2,
        textTransform: 'capitalize',
    },
    infoValue: {
        fontSize: 16,
        color: theme.colors.text,
    },
    divider: {
        height: 1,
        backgroundColor: theme.colors.borderLight,
        marginLeft: 64,
    },
    activityCard: {
        marginBottom: 12,
        padding: 16,
    },
    activityHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 8,
    },
    platformDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    activityPlatform: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    activityTime: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    activityText: {
        fontSize: 14,
        color: theme.colors.text,
        lineHeight: 20,
    },
    viewAllButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 12,
        backgroundColor: theme.colors.primaryLighter,
        borderRadius: 12,
        marginTop: 8,
    },
    viewAllButtonText: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    emptyCard: {
        padding: 32,
        alignItems: 'center',
    },
    emptyText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginTop: 12,
    },
    emptySubtext: {
        fontSize: 14,
        color: theme.colors.textTertiary,
        textAlign: 'center',
        marginTop: 4,
    },
});
