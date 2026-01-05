/**
 * Phone Contacts Service
 * 
 * Handles integration with device contacts:
 * - Request contacts permissions
 * - Fetch device contacts
 * - Sync with backend
 * - Merge contact data
 */

import * as Contacts from 'expo-contacts';
import { Platform, Alert } from 'react-native';

// =============================================================================
// Types
// =============================================================================

export interface PhoneContact {
    id: string;
    name: string;
    firstName?: string;
    lastName?: string;
    phoneNumbers: Array<{
        number: string;
        label?: string;
        isPrimary?: boolean;
    }>;
    emails: Array<{
        email: string;
        label?: string;
        isPrimary?: boolean;
    }>;
    imageUri?: string;
    thumbnailUri?: string;
    company?: string;
    jobTitle?: string;
    birthday?: {
        day?: number;
        month?: number;
        year?: number;
    };
    addresses: Array<{
        street?: string;
        city?: string;
        region?: string;
        postalCode?: string;
        country?: string;
        label?: string;
    }>;
    socialProfiles: Array<{
        service?: string;
        username?: string;
        url?: string;
    }>;
    note?: string;
}

export interface ContactsPermissionStatus {
    granted: boolean;
    canAskAgain: boolean;
    status: 'granted' | 'denied' | 'undetermined';
}

export interface ContactsSyncResult {
    totalContacts: number;
    newContacts: number;
    updatedContacts: number;
    errors: string[];
}

// =============================================================================
// Phone Contacts Service
// =============================================================================

class PhoneContactsService {
    private permissionStatus: ContactsPermissionStatus | null = null;

    /**
     * Check current contacts permission status
     */
    async checkPermissions(): Promise<ContactsPermissionStatus> {
        try {
            const { status, canAskAgain } = await Contacts.getPermissionsAsync();

            this.permissionStatus = {
                granted: status === 'granted',
                canAskAgain,
                status: status as 'granted' | 'denied' | 'undetermined',
            };

            return this.permissionStatus;
        } catch (error) {
            console.error('Error checking contacts permissions:', error);
            return {
                granted: false,
                canAskAgain: false,
                status: 'denied',
            };
        }
    }

    /**
     * Request contacts permissions
     */
    async requestPermissions(): Promise<ContactsPermissionStatus> {
        try {
            const { status, canAskAgain } = await Contacts.requestPermissionsAsync();

            this.permissionStatus = {
                granted: status === 'granted',
                canAskAgain,
                status: status as 'granted' | 'denied' | 'undetermined',
            };

            return this.permissionStatus;
        } catch (error) {
            console.error('Error requesting contacts permissions:', error);
            return {
                granted: false,
                canAskAgain: false,
                status: 'denied',
            };
        }
    }

    /**
     * Show permission explanation dialog
     */
    async showPermissionDialog(): Promise<boolean> {
        return new Promise((resolve) => {
            Alert.alert(
                'Contacts Permission',
                'This app needs access to your contacts to help you find and message your friends. Your contact information is kept private and secure.',
                [
                    {
                        text: 'Not Now',
                        style: 'cancel',
                        onPress: () => resolve(false),
                    },
                    {
                        text: 'Allow Access',
                        onPress: () => resolve(true),
                    },
                ],
                { cancelable: false }
            );
        });
    }

    /**
     * Get all device contacts
     */
    async getDeviceContacts(): Promise<PhoneContact[]> {
        try {
            // Check permissions first
            const permissions = await this.checkPermissions();
            console.log('[Contacts] Permission status:', permissions);

            if (!permissions.granted) {
                console.warn('[Contacts] Permission not granted');
                throw new Error('Contacts permission not granted');
            }

            console.log('[Contacts] Fetching contacts from device...');

            // First try with basic fields (more reliable)
            let result = await Contacts.getContactsAsync({
                fields: [
                    Contacts.Fields.ID,
                    Contacts.Fields.Name,
                    Contacts.Fields.FirstName,
                    Contacts.Fields.LastName,
                    Contacts.Fields.PhoneNumbers,
                    Contacts.Fields.Emails,
                ],
                sort: Contacts.SortTypes.FirstName,
            });

            console.log('[Contacts] Raw result:', result);
            console.log('[Contacts] Raw result type:', typeof result);
            console.log('[Contacts] Raw result.data:', result?.data);
            console.log('[Contacts] Raw result.data length:', result?.data?.length);

            // If null result, try without specifying fields (default behavior)
            if (!result || result.data === undefined || result.data === null) {
                console.log('[Contacts] First attempt returned null, trying fallback...');
                result = await Contacts.getContactsAsync({});
                console.log('[Contacts] Fallback result:', result);
            }

            // Handle null or undefined result
            if (!result || !result.data) {
                console.warn('[Contacts] No contacts data returned after fallback - device may have no contacts');
                return [];
            }

            if (result.data.length === 0) {
                console.log('[Contacts] Device has no contacts. Add contacts in the Contacts app to see them here.');
                return [];
            }

            console.log(`[Contacts] Found ${result.data.length} contacts, fetching full details...`);

            // Now fetch with more fields for the contacts we found
            const detailedResult = await Contacts.getContactsAsync({
                fields: [
                    Contacts.Fields.ID,
                    Contacts.Fields.Name,
                    Contacts.Fields.FirstName,
                    Contacts.Fields.LastName,
                    Contacts.Fields.PhoneNumbers,
                    Contacts.Fields.Emails,
                    Contacts.Fields.Image,
                    Contacts.Fields.Company,
                    Contacts.Fields.JobTitle,
                ],
                sort: Contacts.SortTypes.FirstName,
            });

            const contactsToTransform = detailedResult?.data || result.data;

            // Transform to our format
            const transformed = contactsToTransform.map(this.transformContact);
            console.log(`[Contacts] Successfully fetched ${transformed.length} contacts`);
            return transformed;
        } catch (error) {
            console.error('[Contacts] Error fetching device contacts:', error);
            throw error;
        }
    }

    /**
     * Get contacts with pagination
     */
    async getDeviceContactsPaginated(
        pageSize: number = 50,
        pageOffset: number = 0
    ): Promise<{ contacts: PhoneContact[]; hasNextPage: boolean }> {
        try {
            const permissions = await this.checkPermissions();
            if (!permissions.granted) {
                throw new Error('Contacts permission not granted');
            }

            const { data, hasNextPage } = await Contacts.getContactsAsync({
                fields: [
                    Contacts.Fields.ID,
                    Contacts.Fields.Name,
                    Contacts.Fields.FirstName,
                    Contacts.Fields.LastName,
                    Contacts.Fields.PhoneNumbers,
                    Contacts.Fields.Emails,
                    Contacts.Fields.Image,
                ],
                sort: Contacts.SortTypes.FirstName,
                pageSize,
                pageOffset,
            });

            return {
                contacts: data.map(this.transformContact),
                hasNextPage: hasNextPage || false,
            };
        } catch (error) {
            console.error('Error fetching paginated contacts:', error);
            throw error;
        }
    }

    /**
     * Search device contacts
     */
    async searchDeviceContacts(query: string): Promise<PhoneContact[]> {
        try {
            const permissions = await this.checkPermissions();
            if (!permissions.granted) {
                throw new Error('Contacts permission not granted');
            }

            const { data } = await Contacts.getContactsAsync({
                fields: [
                    Contacts.Fields.ID,
                    Contacts.Fields.Name,
                    Contacts.Fields.FirstName,
                    Contacts.Fields.LastName,
                    Contacts.Fields.PhoneNumbers,
                    Contacts.Fields.Emails,
                ],
                sort: Contacts.SortTypes.FirstName,
                name: query, // This filters by name
            });

            return data.map(this.transformContact);
        } catch (error) {
            console.error('Error searching device contacts:', error);
            throw error;
        }
    }

    /**
     * Get contact by ID
     */
    async getContactById(contactId: string): Promise<PhoneContact | null> {
        try {
            const permissions = await this.checkPermissions();
            if (!permissions.granted) {
                throw new Error('Contacts permission not granted');
            }

            const contact = await Contacts.getContactByIdAsync(contactId, [
                Contacts.Fields.ID,
                Contacts.Fields.Name,
                Contacts.Fields.FirstName,
                Contacts.Fields.LastName,
                Contacts.Fields.PhoneNumbers,
                Contacts.Fields.Emails,
                Contacts.Fields.Image,
                Contacts.Fields.Company,
                Contacts.Fields.JobTitle,
                Contacts.Fields.Birthday,
                Contacts.Fields.Addresses,
                Contacts.Fields.SocialProfiles,
                Contacts.Fields.Note,
            ]);

            return contact ? this.transformContact(contact) : null;
        } catch (error) {
            console.error('Error fetching contact by ID:', error);
            return null;
        }
    }

    /**
     * Transform Expo contact to our format
     */
    private transformContact = (contact: any): PhoneContact => {
        // Generate a better name for contacts without names
        let displayName = contact.name || `${contact.firstName || ''} ${contact.lastName || ''}`.trim();

        // If still no name, try to use phone number or email as fallback
        if (!displayName || displayName === 'Unknown') {
            if (contact.phoneNumbers && contact.phoneNumbers.length > 0) {
                displayName = contact.phoneNumbers[0].number || 'Unknown Contact';
            } else if (contact.emails && contact.emails.length > 0) {
                displayName = contact.emails[0].email || 'Unknown Contact';
            } else {
                displayName = 'Unknown Contact';
            }
        }

        return {
            id: contact.id || contact.contactId || '',
            name: displayName,
            firstName: contact.firstName,
            lastName: contact.lastName,
            phoneNumbers: (contact.phoneNumbers || []).map((phone: any) => ({
                number: this.normalizePhoneNumber(phone.number || ''),
                label: phone.label,
                isPrimary: phone.isPrimary,
            })),
            emails: (contact.emails || []).map((email: any) => ({
                email: email.email || '',
                label: email.label,
                isPrimary: email.isPrimary,
            })),
            imageUri: contact.image?.uri,
            thumbnailUri: contact.imageUri, // Use imageUri as thumbnail fallback
            company: contact.company,
            jobTitle: contact.jobTitle,
            birthday: contact.birthday ? {
                day: contact.birthday.day,
                month: contact.birthday.month,
                year: contact.birthday.year,
            } : undefined,
            addresses: (contact.addresses || []).map((address: any) => ({
                street: address.street,
                city: address.city,
                region: address.region,
                postalCode: address.postalCode,
                country: address.country,
                label: address.label,
            })),
            socialProfiles: (contact.socialProfiles || []).map((profile: any) => ({
                service: profile.service,
                username: profile.username,
                url: profile.url,
            })),
            note: contact.note,
        };
    };

    /**
     * Normalize phone number for consistent formatting
     */
    private normalizePhoneNumber(phoneNumber: string): string {
        // Remove all non-digit characters except +
        const cleaned = phoneNumber.replace(/[^\d+]/g, '');

        // If it starts with +, keep it
        if (cleaned.startsWith('+')) {
            return cleaned;
        }

        // If it's a US number (10 digits), add +1
        if (cleaned.length === 10) {
            return `+1${cleaned}`;
        }

        // If it's 11 digits and starts with 1, add +
        if (cleaned.length === 11 && cleaned.startsWith('1')) {
            return `+${cleaned}`;
        }

        return cleaned;
    }

    /**
     * Check if contacts access is available on this platform
     */
    isContactsAvailable(): boolean {
        return Platform.OS === 'ios' || Platform.OS === 'android';
    }

    /**
     * Get permission status without requesting
     */
    getPermissionStatus(): ContactsPermissionStatus | null {
        return this.permissionStatus;
    }
}

// =============================================================================
// Export singleton instance
// =============================================================================

export const phoneContactsService = new PhoneContactsService();
export default phoneContactsService;