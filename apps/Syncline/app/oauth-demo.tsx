/**
 * OAuth Authorization Flow Screen (Section 4.11.1, Figure 4.2)
 * 
 * Simulated Google OAuth consent screen for documentation screenshots.
 * Shows the standard OAuth flow with permission requests.
 */

import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../src/theme';
import { Card } from '../components/Card/Card';

export default function OAuthDemoScreen() {
    const [step, setStep] = useState<'consent' | 'success'>('consent');

    if (step === 'success') {
        return (
            <View style={styles.container}>
                <View style={styles.successContainer}>
                    <View style={styles.successIcon}>
                        <Ionicons name="checkmark-circle" size={72} color="#10B981" />
                    </View>
                    <Text style={styles.successTitle}>Successfully Connected!</Text>
                    <Text style={styles.successDescription}>
                        Your Gmail account has been connected to MESH.
                        We're now syncing your messages.
                    </Text>
                    <TouchableOpacity
                        style={styles.continueButton}
                        onPress={() => setStep('consent')}
                    >
                        <Text style={styles.continueButtonText}>Continue to MESH</Text>
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* Google OAuth Consent Screen */}
            <View style={styles.oauthContainer}>
                {/* Google Header */}
                <View style={styles.googleHeader}>
                    <View style={styles.googleLogo}>
                        <Text style={styles.googleLogoText}>G</Text>
                    </View>
                </View>

                {/* Main Content */}
                <Card style={styles.consentCard}>
                    <Text style={styles.signInTitle}>Sign in with Google</Text>

                    {/* User Account */}
                    <View style={styles.userAccount}>
                        <View style={styles.userAvatar}>
                            <Text style={styles.userAvatarText}>AW</Text>
                        </View>
                        <View style={styles.userInfo}>
                            <Text style={styles.userName}>Alex Wave</Text>
                            <Text style={styles.userEmail}>alex.wave@gmail.com</Text>
                        </View>
                        <Ionicons name="chevron-down" size={20} color={theme.colors.textSecondary} />
                    </View>

                    {/* App Info */}
                    <View style={styles.appSection}>
                        <View style={styles.appIcon}>
                            <Text style={styles.appIconText}>M</Text>
                        </View>
                        <Text style={styles.appRequestText}>
                            <Text style={styles.bold}>MESH</Text> wants to access your Google Account
                        </Text>
                    </View>

                    {/* Permissions */}
                    <View style={styles.permissionsSection}>
                        <Text style={styles.permissionsTitle}>This will allow MESH to:</Text>

                        <View style={styles.permissionItem}>
                            <View style={styles.permissionIcon}>
                                <Ionicons name="mail" size={20} color="#EA4335" />
                            </View>
                            <View style={styles.permissionContent}>
                                <Text style={styles.permissionText}>Read your email messages</Text>
                                <Text style={styles.permissionDescription}>
                                    View and search through your emails
                                </Text>
                            </View>
                        </View>

                        <View style={styles.permissionItem}>
                            <View style={styles.permissionIcon}>
                                <Ionicons name="people" size={20} color="#FBBC04" />
                            </View>
                            <View style={styles.permissionContent}>
                                <Text style={styles.permissionText}>View your contacts</Text>
                                <Text style={styles.permissionDescription}>
                                    See names and email addresses
                                </Text>
                            </View>
                        </View>

                        <View style={styles.permissionItem}>
                            <View style={styles.permissionIcon}>
                                <Ionicons name="calendar" size={20} color="#4285F4" />
                            </View>
                            <View style={styles.permissionContent}>
                                <Text style={styles.permissionText}>See your primary Google Account email address</Text>
                                <Text style={styles.permissionDescription}>
                                    For account identification
                                </Text>
                            </View>
                        </View>
                    </View>

                    {/* Privacy Notice */}
                    <View style={styles.privacyNotice}>
                        <Ionicons name="shield-checkmark" size={16} color={theme.colors.textSecondary} />
                        <Text style={styles.privacyText}>
                            MESH's use and transfer of information received from Google APIs will adhere to{' '}
                            <Text style={styles.link}>Google API Services User Data Policy</Text>, including the Limited Use requirements.
                        </Text>
                    </View>

                    {/* Action Buttons */}
                    <View style={styles.actionButtons}>
                        <TouchableOpacity style={styles.cancelButton}>
                            <Text style={styles.cancelButtonText}>Cancel</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.allowButton}
                            onPress={() => setStep('success')}
                        >
                            <Text style={styles.allowButtonText}>Allow</Text>
                        </TouchableOpacity>
                    </View>
                </Card>

                {/* Footer Links */}
                <View style={styles.footerLinks}>
                    <TouchableOpacity>
                        <Text style={styles.footerLink}>Privacy Policy</Text>
                    </TouchableOpacity>
                    <Text style={styles.footerDot}>•</Text>
                    <TouchableOpacity>
                        <Text style={styles.footerLink}>Terms of Service</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F1F3F4',
    },
    oauthContainer: {
        flex: 1,
        alignItems: 'center',
        paddingTop: 60,
        paddingHorizontal: 20,
    },
    googleHeader: {
        marginBottom: 24,
    },
    googleLogo: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: 'white',
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    googleLogoText: {
        fontSize: 28,
        fontWeight: '500',
        color: '#4285F4',
    },
    consentCard: {
        width: '100%',
        maxWidth: 400,
        backgroundColor: 'white',
        borderRadius: 16,
        padding: 24,
    },
    signInTitle: {
        fontSize: 22,
        fontWeight: '500',
        color: '#202124',
        textAlign: 'center',
        marginBottom: 24,
    },
    userAccount: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        backgroundColor: '#F8F9FA',
        borderRadius: 12,
        marginBottom: 24,
    },
    userAvatar: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#4285F4',
        alignItems: 'center',
        justifyContent: 'center',
    },
    userAvatarText: {
        fontSize: 16,
        fontWeight: '600',
        color: 'white',
    },
    userInfo: {
        flex: 1,
        marginLeft: 12,
    },
    userName: {
        fontSize: 14,
        fontWeight: '500',
        color: '#202124',
    },
    userEmail: {
        fontSize: 12,
        color: '#5F6368',
    },
    appSection: {
        alignItems: 'center',
        marginBottom: 24,
    },
    appIcon: {
        width: 48,
        height: 48,
        borderRadius: 12,
        backgroundColor: theme.colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 12,
    },
    appIconText: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
    },
    appRequestText: {
        fontSize: 14,
        color: '#5F6368',
        textAlign: 'center',
    },
    bold: {
        fontWeight: '600',
        color: '#202124',
    },
    permissionsSection: {
        marginBottom: 20,
    },
    permissionsTitle: {
        fontSize: 14,
        fontWeight: '500',
        color: '#202124',
        marginBottom: 16,
    },
    permissionItem: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        marginBottom: 16,
    },
    permissionIcon: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: '#F1F3F4',
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    permissionContent: {
        flex: 1,
    },
    permissionText: {
        fontSize: 14,
        fontWeight: '500',
        color: '#202124',
    },
    permissionDescription: {
        fontSize: 12,
        color: '#5F6368',
        marginTop: 2,
    },
    privacyNotice: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        backgroundColor: '#F8F9FA',
        padding: 12,
        borderRadius: 8,
        marginBottom: 24,
        gap: 10,
    },
    privacyText: {
        flex: 1,
        fontSize: 11,
        color: '#5F6368',
        lineHeight: 16,
    },
    link: {
        color: '#4285F4',
    },
    actionButtons: {
        flexDirection: 'row',
        justifyContent: 'flex-end',
        gap: 12,
    },
    cancelButton: {
        paddingVertical: 10,
        paddingHorizontal: 24,
    },
    cancelButtonText: {
        fontSize: 14,
        fontWeight: '500',
        color: '#4285F4',
    },
    allowButton: {
        backgroundColor: '#4285F4',
        paddingVertical: 10,
        paddingHorizontal: 24,
        borderRadius: 8,
    },
    allowButtonText: {
        fontSize: 14,
        fontWeight: '500',
        color: 'white',
    },
    footerLinks: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 24,
    },
    footerLink: {
        fontSize: 12,
        color: '#5F6368',
    },
    footerDot: {
        marginHorizontal: 8,
        color: '#5F6368',
    },
    successContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
    },
    successIcon: {
        marginBottom: 24,
    },
    successTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 12,
    },
    successDescription: {
        fontSize: 15,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 22,
        marginBottom: 32,
    },
    continueButton: {
        backgroundColor: theme.colors.primary,
        paddingVertical: 14,
        paddingHorizontal: 32,
        borderRadius: 12,
    },
    continueButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: 'white',
    },
});
