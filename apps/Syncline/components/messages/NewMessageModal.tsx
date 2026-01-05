import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    FlatList,
    TouchableOpacity,
    TextInput,
    Modal,
    Alert,
    ActivityIndicator,
    Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Contacts from 'expo-contacts';
import { theme } from '../../src/theme';
import { Card } from '../Card/Card';

interface PhoneContact {
    id: string;
    name: string;
    phoneNumbers: string[];
    emails: string[];
    imageUri?: string;
}

interface NewMessageModalProps {
    visible: boolean;
    onClose: () => void;
    onSelectContact: (contact: PhoneContact) => void;
}

export function NewMessageModal({ visible, onClose, onSelectContact }: NewMessageModalProps) {
    const [contacts, setContacts] = useState<PhoneContact[]>([]);
    const [filteredContacts, setFilteredContacts] = useState<PhoneContact[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [hasPermission, setHasPermission] = useState(false);

    useEffect(() => {
        if (visible) {
            checkPermissionAndLoadContacts();
        }
    }, [visible]);

    useEffect(() => {
        // Filter contacts based on search query
        if (!searchQuery.trim()) {
            setFilteredContacts(contacts);
        } else {
            const query = searchQuery.toLowerCase();
            const filtered = contacts.filter(contact => 
                contact.name.toLowerCase().includes(query) ||
                contact.phoneNumbers.some(phone => phone.includes(query)) ||
                contact.emails.some(email => email.toLowerCase().includes(query))
            );
            setFilteredContacts(filtered);
        }
    }, [searchQuery, contacts]);

    const checkPermissionAndLoadContacts = async () => {
        try {
            setLoading(true);
            
            // Check current permission status
            const { status: currentStatus } = await Contacts.getPermissionsAsync();
            
            if (currentStatus === 'granted') {
                setHasPermission(true);
                await loadContacts();
            } else {
                // Request permission
                const { status: newStatus } = await Contacts.requestPermissionsAsync();
                
                if (newStatus === 'granted') {
                    setHasPermission(true);
                    await loadContacts();
                } else {
                    setHasPermission(false);
                    Alert.alert(
                        'Permission Required',
                        'Contact access is needed to start new conversations with your contacts.',
                        [
                            { text: 'Cancel', onPress: onClose },
                            { text: 'Settings', onPress: () => {
                                // TODO: Open app settings
                                onClose();
                            }}
                        ]
                    );
                }
            }
        } catch (error) {
            console.error('Error checking contacts permission:', error);
            Alert.alert('Error', 'Failed to access contacts');
        } finally {
            setLoading(false);
        }
    };

    const loadContacts = async () => {
        try {
            const { data } = await Contacts.getContactsAsync({
                fields: [
                    Contacts.Fields.Name,
                    Contacts.Fields.PhoneNumbers,
                    Contacts.Fields.Emails,
                    Contacts.Fields.Image,
                ],
                sort: Contacts.SortTypes.FirstName,
            });

            const phoneContacts: PhoneContact[] = data
                .filter(contact => contact.name && contact.phoneNumbers?.length > 0)
                .map(contact => ({
                    id: contact.id || Math.random().toString(),
                    name: contact.name || 'Unknown',
                    phoneNumbers: contact.phoneNumbers?.map(p => p.number || '').filter(Boolean) || [],
                    emails: contact.emails?.map(e => e.email || '').filter(Boolean) || [],
                    imageUri: contact.imageAvailable ? contact.image?.uri : undefined,
                }))
                .sort((a, b) => a.name.localeCompare(b.name));

            setContacts(phoneContacts);
            setFilteredContacts(phoneContacts);
        } catch (error) {
            console.error('Error loading contacts:', error);
            Alert.alert('Error', 'Failed to load contacts');
        }
    };

    const handleContactSelect = (contact: PhoneContact) => {
        onSelectContact(contact);
        onClose();
        setSearchQuery('');
    };

    const renderContactItem = ({ item }: { item: PhoneContact }) => (
        <TouchableOpacity onPress={() => handleContactSelect(item)}>
            <Card style={styles.contactCard}>
                <View style={styles.contactContent}>
                    {/* Avatar */}
                    <View style={styles.avatarContainer}>
                        {item.imageUri ? (
                            <Image source={{ uri: item.imageUri }} style={styles.avatar} />
                        ) : (
                            <View style={[styles.avatar, styles.avatarPlaceholder]}>
                                <Text style={styles.avatarText}>
                                    {item.name
                                        .split(' ')
                                        .map(n => n[0])
                                        .join('')
                                        .toUpperCase()
                                        .slice(0, 2)}
                                </Text>
                            </View>
                        )}
                    </View>

                    {/* Contact Info */}
                    <View style={styles.contactInfo}>
                        <Text style={styles.contactName} numberOfLines={1}>
                            {item.name}
                        </Text>
                        
                        {/* Primary phone number */}
                        {item.phoneNumbers[0] && (
                            <Text style={styles.contactPhone} numberOfLines={1}>
                                {item.phoneNumbers[0]}
                            </Text>
                        )}
                        
                        {/* Additional info */}
                        {item.phoneNumbers.length > 1 && (
                            <Text style={styles.contactExtra}>
                                +{item.phoneNumbers.length - 1} more number{item.phoneNumbers.length > 2 ? 's' : ''}
                            </Text>
                        )}
                    </View>

                    {/* WhatsApp indicator if phone number exists */}
                    <View style={styles.platformIndicator}>
                        <Ionicons name="logo-whatsapp" size={20} color="#25D366" />
                    </View>
                </View>
            </Card>
        </TouchableOpacity>
    );

    const renderEmptyState = () => (
        <View style={styles.emptyState}>
            <Ionicons name="people-outline" size={64} color={theme.colors.textTertiary} />
            <Text style={styles.emptyTitle}>No contacts found</Text>
            <Text style={styles.emptySubtitle}>
                {searchQuery ? 'Try a different search term' : 'No contacts with phone numbers available'}
            </Text>
        </View>
    );

    const renderPermissionDenied = () => (
        <View style={styles.emptyState}>
            <Ionicons name="lock-closed-outline" size={64} color={theme.colors.textTertiary} />
            <Text style={styles.emptyTitle}>Contact Access Required</Text>
            <Text style={styles.emptySubtitle}>
                Grant contact permission to start conversations with your contacts
            </Text>
            <TouchableOpacity 
                style={styles.permissionButton}
                onPress={checkPermissionAndLoadContacts}
            >
                <Text style={styles.permissionButtonText}>Grant Permission</Text>
            </TouchableOpacity>
        </View>
    );

    return (
        <Modal
            visible={visible}
            animationType="slide"
            presentationStyle="pageSheet"
            onRequestClose={onClose}
        >
            <View style={styles.container}>
                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                        <Ionicons name="close" size={24} color={theme.colors.text} />
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>New Message</Text>
                    <View style={styles.headerSpacer} />
                </View>

                {/* Search Bar */}
                <View style={styles.searchContainer}>
                    <View style={styles.searchBar}>
                        <Ionicons name="search" size={20} color={theme.colors.textTertiary} />
                        <TextInput
                            style={styles.searchInput}
                            placeholder="Search contacts..."
                            placeholderTextColor={theme.colors.textTertiary}
                            value={searchQuery}
                            onChangeText={setSearchQuery}
                            autoCapitalize="words"
                        />
                        {searchQuery.length > 0 && (
                            <TouchableOpacity onPress={() => setSearchQuery('')}>
                                <Ionicons name="close-circle" size={20} color={theme.colors.textTertiary} />
                            </TouchableOpacity>
                        )}
                    </View>
                </View>

                {/* Content */}
                {loading ? (
                    <View style={styles.loadingContainer}>
                        <ActivityIndicator size="large" color={theme.colors.primary} />
                        <Text style={styles.loadingText}>Loading contacts...</Text>
                    </View>
                ) : !hasPermission ? (
                    renderPermissionDenied()
                ) : filteredContacts.length === 0 ? (
                    renderEmptyState()
                ) : (
                    <FlatList
                        data={filteredContacts}
                        keyExtractor={(item) => item.id}
                        renderItem={renderContactItem}
                        contentContainerStyle={styles.listContent}
                        showsVerticalScrollIndicator={false}
                    />
                )}
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        backgroundColor: theme.colors.background,
    },
    closeButton: {
        padding: 4,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
    },
    headerSpacer: {
        width: 32,
    },
    searchContainer: {
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: theme.colors.background,
    },
    searchBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 12,
        paddingVertical: 10,
        gap: 8,
    },
    searchInput: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
    },
    loadingText: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    listContent: {
        padding: 16,
        gap: 8,
    },
    contactCard: {
        padding: 0,
        backgroundColor: 'white',
    },
    contactContent: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        gap: 12,
    },
    avatarContainer: {
        position: 'relative',
    },
    avatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
    },
    avatarPlaceholder: {
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
    },
    avatarText: {
        fontSize: 16,
        fontWeight: 'bold',
        color: theme.colors.textSecondary,
    },
    contactInfo: {
        flex: 1,
        gap: 2,
    },
    contactName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    contactPhone: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    contactExtra: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    platformIndicator: {
        padding: 8,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 32,
        gap: 16,
    },
    emptyTitle: {
        fontSize: 20,
        fontWeight: '600',
        color: theme.colors.text,
    },
    emptySubtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
    },
    permissionButton: {
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 12,
        marginTop: 8,
    },
    permissionButtonText: {
        color: 'white',
        fontSize: 16,
        fontWeight: '600',
    },
});