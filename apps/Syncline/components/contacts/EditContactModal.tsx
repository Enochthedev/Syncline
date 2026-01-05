import React, { useState, useEffect, useCallback } from 'react';
import {
    StyleSheet,
    View,
    Text,
    Modal,
    TouchableOpacity,
    TextInput,
    ScrollView,
    Alert,
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Contacts from 'expo-contacts';
import { theme } from '../../src/theme';
import { contactsAPI } from '../../src/api/endpoints/contacts';

// Available platforms for linking
const PLATFORMS = [
    { id: 'whatsapp', name: 'WhatsApp', icon: 'logo-whatsapp', color: '#25D366', placeholder: 'Phone number (+1234567890)', socialService: 'whatsapp' },
    { id: 'linkedin', name: 'LinkedIn', icon: 'logo-linkedin', color: '#0A66C2', placeholder: 'Username or profile URL', socialService: 'linkedin' },
    { id: 'twitter', name: 'Twitter/X', icon: 'logo-twitter', color: '#1DA1F2', placeholder: '@username', socialService: 'twitter' },
    { id: 'instagram', name: 'Instagram', icon: 'logo-instagram', color: '#E4405F', placeholder: '@username', socialService: 'instagram' },
    { id: 'facebook', name: 'Facebook', icon: 'logo-facebook', color: '#1877F2', placeholder: 'Username or profile URL', socialService: 'facebook' },
    { id: 'telegram', name: 'Telegram', icon: 'paper-plane', color: '#0088CC', placeholder: '@username or phone', socialService: 'telegram' },
    { id: 'discord', name: 'Discord', icon: 'logo-discord', color: '#5865F2', placeholder: 'username#1234', socialService: 'discord' },
    { id: 'slack', name: 'Slack', icon: 'logo-slack', color: '#4A154B', placeholder: '@username', socialService: 'slack' },
    { id: 'google_chat', name: 'Google Chat', icon: 'chatbubbles', color: '#4285F4', placeholder: 'Email address', socialService: 'googlechat' },
];

interface EditContactModalProps {
    visible: boolean;
    onClose: () => void;
    contact: {
        id: string;
        name: string;
        firstName?: string;
        lastName?: string;
        company?: string;
        jobTitle?: string;
        platforms: Array<{ platform: string; handle: string }>;
        deviceContactId?: string; // ID from expo-contacts
        backendContactId?: string; // ID from backend
    } | null;
    onSave: (updatedContact: any) => void;
    isDeviceOnly?: boolean; // True if this is a device-only contact
}

export default function EditContactModal({
    visible,
    onClose,
    contact,
    onSave,
    isDeviceOnly = false,
}: EditContactModalProps) {
    const [name, setName] = useState('');
    const [company, setCompany] = useState('');
    const [jobTitle, setJobTitle] = useState('');
    const [platformLinks, setPlatformLinks] = useState<Record<string, string>>({});
    const [saving, setSaving] = useState(false);
    const [showPlatformPicker, setShowPlatformPicker] = useState(false);

    // Initialize form when contact changes
    useEffect(() => {
        if (contact) {
            setName(contact.name || '');
            setCompany(contact.company || '');
            setJobTitle(contact.jobTitle || '');

            // Convert platforms array to Record
            const links: Record<string, string> = {};
            contact.platforms?.forEach(p => {
                links[p.platform.toLowerCase()] = p.handle;
            });
            setPlatformLinks(links);
        }
    }, [contact]);

    // Update device contact with changes
    const updateDeviceContact = useCallback(async (
        deviceContactId: string,
        updates: {
            firstName?: string;
            lastName?: string;
            name?: string;
            company?: string;
            jobTitle?: string;
            platformLinks?: Record<string, string>;
        }
    ) => {
        try {
            // First, get the existing contact to preserve other data
            const existingContact = await Contacts.getContactByIdAsync(deviceContactId, [
                Contacts.Fields.ID,
                Contacts.Fields.Name,
                Contacts.Fields.FirstName,
                Contacts.Fields.LastName,
                Contacts.Fields.PhoneNumbers,
                Contacts.Fields.Emails,
                Contacts.Fields.Company,
                Contacts.Fields.JobTitle,
                Contacts.Fields.SocialProfiles,
            ]);

            if (!existingContact || !existingContact.id) {
                console.warn('Device contact not found:', deviceContactId);
                return false;
            }

            // Build the update - start with existing contact data
            const contactUpdate: any = {
                id: existingContact.id,
                name: existingContact.name,
                firstName: existingContact.firstName,
                lastName: existingContact.lastName,
                company: existingContact.company,
                jobTitle: existingContact.jobTitle,
                phoneNumbers: existingContact.phoneNumbers,
                emails: existingContact.emails,
            };

            // Update name if changed
            if (updates.name) {
                const nameParts = updates.name.trim().split(' ');
                if (nameParts.length > 1) {
                    contactUpdate.firstName = nameParts[0];
                    contactUpdate.lastName = nameParts.slice(1).join(' ');
                } else {
                    contactUpdate.firstName = nameParts[0];
                    contactUpdate.lastName = '';
                }
                contactUpdate.name = updates.name.trim();
            }

            // Update company if changed
            if (updates.company !== undefined) {
                contactUpdate.company = updates.company;
            }

            // Update job title if changed
            if (updates.jobTitle !== undefined) {
                contactUpdate.jobTitle = updates.jobTitle;
            }

            // Build social profiles from platform links
            if (updates.platformLinks) {
                const socialProfiles = Object.entries(updates.platformLinks)
                    .filter(([_, value]) => value.trim() !== '')
                    .map(([platformId, username]) => {
                        const platform = PLATFORMS.find(p => p.id === platformId);
                        return {
                            service: platform?.socialService || platformId,
                            username: username.trim(),
                            label: platform?.name || platformId,
                        };
                    });

                // Merge with existing social profiles (keeping ones we don't manage)
                const existingProfiles = (existingContact as any).socialProfiles || [];
                const managedServices = PLATFORMS.map(p => p.socialService);
                const unmanagedProfiles = existingProfiles.filter(
                    (sp: any) => !managedServices.includes(sp.service?.toLowerCase())
                );

                contactUpdate.socialProfiles = [...unmanagedProfiles, ...socialProfiles];
            }

            // Update the contact on the device
            await Contacts.updateContactAsync(contactUpdate as { id: string } & Partial<Contacts.Contact>);
            console.log('Device contact updated successfully:', deviceContactId);
            return true;
        } catch (error) {
            console.error('Error updating device contact:', error);
            return false;
        }
    }, []);

    const handleSave = useCallback(async () => {
        if (!contact) return;

        try {
            setSaving(true);

            // Filter out empty platform links
            const cleanedPlatformLinks = Object.fromEntries(
                Object.entries(platformLinks).filter(([_, value]) => value.trim() !== '')
            );

            // Always try to update device contact first if we have a deviceContactId
            if (contact.deviceContactId) {
                const deviceUpdateSuccess = await updateDeviceContact(contact.deviceContactId, {
                    name: name.trim(),
                    company: company.trim(),
                    jobTitle: jobTitle.trim(),
                    platformLinks: cleanedPlatformLinks,
                });

                if (deviceUpdateSuccess) {
                    console.log('Device contact synced successfully');
                }
            }

            // Then update or create backend record
            if (contact.backendContactId) {
                // Update existing backend contact
                const updatedContact = await contactsAPI.updateContact(contact.backendContactId, {
                    canonical_name: name.trim() || contact.name,
                    platform_identities: cleanedPlatformLinks,
                    contact_metadata: {
                        company: company.trim(),
                        role: jobTitle.trim(),
                    },
                });

                onSave(updatedContact);
            } else {
                // Return data for parent to handle (device-only or new contact)
                onSave({
                    name: name.trim(),
                    company: company.trim(),
                    jobTitle: jobTitle.trim(),
                    platform_identities: cleanedPlatformLinks,
                    deviceContactId: contact.deviceContactId,
                });
            }

            onClose();
        } catch (error) {
            console.error('Error saving contact:', error);
            Alert.alert('Error', 'Failed to save contact. Please try again.');
        } finally {
            setSaving(false);
        }
    }, [contact, name, company, jobTitle, platformLinks, updateDeviceContact, onSave, onClose]);

    const handleAddPlatform = useCallback((platformId: string) => {
        if (!platformLinks[platformId]) {
            setPlatformLinks(prev => ({ ...prev, [platformId]: '' }));
        }
        setShowPlatformPicker(false);
    }, [platformLinks]);

    const handleRemovePlatform = useCallback((platformId: string) => {
        setPlatformLinks(prev => {
            const newLinks = { ...prev };
            delete newLinks[platformId];
            return newLinks;
        });
    }, []);

    const handlePlatformValueChange = useCallback((platformId: string, value: string) => {
        setPlatformLinks(prev => ({ ...prev, [platformId]: value }));
    }, []);

    // Get platforms not yet added
    const availablePlatforms = PLATFORMS.filter(p => !platformLinks.hasOwnProperty(p.id));

    if (!contact) return null;

    return (
        <Modal
            visible={visible}
            animationType="slide"
            presentationStyle="pageSheet"
            onRequestClose={onClose}
        >
            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.container}
            >
                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={onClose} style={styles.headerButton}>
                        <Text style={styles.cancelText}>Cancel</Text>
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>Edit Contact</Text>
                    <TouchableOpacity
                        onPress={handleSave}
                        style={styles.headerButton}
                        disabled={saving}
                    >
                        {saving ? (
                            <ActivityIndicator size="small" color={theme.colors.primary} />
                        ) : (
                            <Text style={styles.saveText}>Save</Text>
                        )}
                    </TouchableOpacity>
                </View>

                <ScrollView
                    style={styles.content}
                    showsVerticalScrollIndicator={false}
                    keyboardShouldPersistTaps="handled"
                >
                    {/* Basic Info Section */}
                    <View style={styles.section}>
                        <Text style={styles.sectionTitle}>Basic Info</Text>
                        <View style={styles.inputCard}>
                            <View style={styles.inputRow}>
                                <Ionicons name="person-outline" size={20} color={theme.colors.textSecondary} />
                                <TextInput
                                    style={styles.input}
                                    value={name}
                                    onChangeText={setName}
                                    placeholder="Name"
                                    placeholderTextColor={theme.colors.textTertiary}
                                />
                            </View>
                            <View style={styles.inputDivider} />
                            <View style={styles.inputRow}>
                                <Ionicons name="business-outline" size={20} color={theme.colors.textSecondary} />
                                <TextInput
                                    style={styles.input}
                                    value={company}
                                    onChangeText={setCompany}
                                    placeholder="Company"
                                    placeholderTextColor={theme.colors.textTertiary}
                                />
                            </View>
                            <View style={styles.inputDivider} />
                            <View style={styles.inputRow}>
                                <Ionicons name="briefcase-outline" size={20} color={theme.colors.textSecondary} />
                                <TextInput
                                    style={styles.input}
                                    value={jobTitle}
                                    onChangeText={setJobTitle}
                                    placeholder="Job Title"
                                    placeholderTextColor={theme.colors.textTertiary}
                                />
                            </View>
                        </View>
                    </View>

                    {/* Platform Links Section */}
                    <View style={styles.section}>
                        <View style={styles.sectionHeader}>
                            <Text style={styles.sectionTitle}>Platform Links</Text>
                            <Text style={styles.sectionSubtitle}>
                                Add usernames to link conversations
                            </Text>
                        </View>

                        {/* Existing platform links */}
                        {Object.keys(platformLinks).map(platformId => {
                            const platform = PLATFORMS.find(p => p.id === platformId);
                            if (!platform) return null;

                            return (
                                <View key={platformId} style={styles.platformCard}>
                                    <View style={[styles.platformIcon, { backgroundColor: platform.color + '20' }]}>
                                        <Ionicons name={platform.icon as any} size={20} color={platform.color} />
                                    </View>
                                    <View style={styles.platformInputContainer}>
                                        <Text style={styles.platformLabel}>{platform.name}</Text>
                                        <TextInput
                                            style={styles.platformInput}
                                            value={platformLinks[platformId]}
                                            onChangeText={(value) => handlePlatformValueChange(platformId, value)}
                                            placeholder={platform.placeholder}
                                            placeholderTextColor={theme.colors.textTertiary}
                                            autoCapitalize="none"
                                            autoCorrect={false}
                                        />
                                    </View>
                                    <TouchableOpacity
                                        onPress={() => handleRemovePlatform(platformId)}
                                        style={styles.removeButton}
                                    >
                                        <Ionicons name="close-circle" size={24} color={theme.colors.textTertiary} />
                                    </TouchableOpacity>
                                </View>
                            );
                        })}

                        {/* Add Platform Button */}
                        {availablePlatforms.length > 0 && (
                            <TouchableOpacity
                                style={styles.addPlatformButton}
                                onPress={() => setShowPlatformPicker(true)}
                            >
                                <Ionicons name="add-circle" size={24} color={theme.colors.primary} />
                                <Text style={styles.addPlatformText}>Add Platform Link</Text>
                            </TouchableOpacity>
                        )}

                        {/* Platform Picker */}
                        {showPlatformPicker && (
                            <View style={styles.platformPicker}>
                                <View style={styles.platformPickerHeader}>
                                    <Text style={styles.platformPickerTitle}>Select Platform</Text>
                                    <TouchableOpacity onPress={() => setShowPlatformPicker(false)}>
                                        <Ionicons name="close" size={24} color={theme.colors.text} />
                                    </TouchableOpacity>
                                </View>
                                <View style={styles.platformGrid}>
                                    {availablePlatforms.map(platform => (
                                        <TouchableOpacity
                                            key={platform.id}
                                            style={styles.platformPickerItem}
                                            onPress={() => handleAddPlatform(platform.id)}
                                        >
                                            <View style={[styles.platformIcon, { backgroundColor: platform.color + '20' }]}>
                                                <Ionicons name={platform.icon as any} size={24} color={platform.color} />
                                            </View>
                                            <Text style={styles.platformPickerName}>{platform.name}</Text>
                                        </TouchableOpacity>
                                    ))}
                                </View>
                            </View>
                        )}
                    </View>

                    {/* Info note for device-only contacts */}
                    {isDeviceOnly && (
                        <View style={styles.infoNote}>
                            <Ionicons name="information-circle-outline" size={20} color={theme.colors.primary} />
                            <Text style={styles.infoNoteText}>
                                This contact is from your device. Adding platform links will allow Syncline to find their conversations across your connected platforms.
                            </Text>
                        </View>
                    )}

                    <View style={{ height: 40 }} />
                </ScrollView>
            </KeyboardAvoidingView>
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
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 16,
        backgroundColor: theme.colors.background,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    headerButton: {
        minWidth: 60,
    },
    headerTitle: {
        fontSize: 17,
        fontWeight: '600',
        color: theme.colors.text,
    },
    cancelText: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    saveText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.primary,
        textAlign: 'right',
    },
    content: {
        flex: 1,
        paddingTop: 24,
    },
    section: {
        paddingHorizontal: 20,
        marginBottom: 32,
    },
    sectionHeader: {
        marginBottom: 16,
    },
    sectionTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
        marginBottom: 4,
    },
    sectionSubtitle: {
        fontSize: 13,
        color: theme.colors.textTertiary,
    },
    inputCard: {
        backgroundColor: theme.colors.background,
        borderRadius: 12,
        overflow: 'hidden',
        marginTop: 12,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 14,
        gap: 12,
    },
    inputDivider: {
        height: 1,
        backgroundColor: theme.colors.borderLight,
        marginLeft: 48,
    },
    input: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
    },
    platformCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.background,
        borderRadius: 12,
        padding: 12,
        marginBottom: 12,
        gap: 12,
    },
    platformIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
    },
    platformInputContainer: {
        flex: 1,
    },
    platformLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    platformInput: {
        fontSize: 15,
        color: theme.colors.text,
        padding: 0,
    },
    removeButton: {
        padding: 4,
    },
    addPlatformButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: theme.colors.primaryLighter,
        borderRadius: 12,
        paddingVertical: 14,
        borderWidth: 1,
        borderColor: theme.colors.primary + '30',
        borderStyle: 'dashed',
    },
    addPlatformText: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    platformPicker: {
        backgroundColor: theme.colors.background,
        borderRadius: 16,
        padding: 16,
        marginTop: 12,
    },
    platformPickerHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
    },
    platformPickerTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    platformGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
    },
    platformPickerItem: {
        width: '30%',
        alignItems: 'center',
        padding: 12,
        borderRadius: 12,
        backgroundColor: theme.colors.surface,
    },
    platformPickerName: {
        fontSize: 12,
        fontWeight: '500',
        color: theme.colors.text,
        marginTop: 8,
        textAlign: 'center',
    },
    infoNote: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: 12,
        backgroundColor: theme.colors.primaryLighter,
        borderRadius: 12,
        padding: 16,
        marginHorizontal: 20,
    },
    infoNoteText: {
        flex: 1,
        fontSize: 13,
        color: theme.colors.primary,
        lineHeight: 18,
    },
});
