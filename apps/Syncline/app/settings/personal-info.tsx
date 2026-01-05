import React, { useState } from 'react';
import {
    StyleSheet,
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    TextInput,
    Alert,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';
import { Card } from '../../components/Card/Card';

export default function PersonalInfoScreen() {
    const router = useRouter();
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({
        fullName: 'Alex Morgan',
        email: 'alex.morgan@company.com',
        phone: '+1 (555) 123-4567',
    });

    const handleSave = () => {
        Alert.alert('Success', 'Personal information updated successfully');
        setIsEditing(false);
    };

    const renderField = (label: string, value: string, key: keyof typeof formData, icon: string) => (
        <View style={styles.fieldContainer}>
            <View style={styles.fieldHeader}>
                <Ionicons name={icon as any} size={20} color={theme.colors.textSecondary} />
                <Text style={styles.fieldLabel}>{label}</Text>
            </View>
            {isEditing ? (
                <TextInput
                    style={styles.fieldInput}
                    value={formData[key]}
                    onChangeText={(text) => setFormData({ ...formData, [key]: text })}
                    placeholder={label}
                />
            ) : (
                <Text style={styles.fieldValue}>{value}</Text>
            )}
        </View>
    );

    return (
        <View style={styles.container}>
            <Stack.Screen
                options={{
                    headerShown: true,
                    headerTitle: 'Personal Information',
                    headerLeft: () => (
                        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    ),
                    headerRight: () => (
                        <TouchableOpacity
                            onPress={() => isEditing ? handleSave() : setIsEditing(true)}
                            style={styles.editButton}
                        >
                            <Text style={styles.editButtonText}>
                                {isEditing ? 'Save' : 'Edit'}
                            </Text>
                        </TouchableOpacity>
                    ),
                }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Basic Information</Text>
                    {renderField('Full Name', formData.fullName, 'fullName', 'person')}
                    {renderField('Email Address', formData.email, 'email', 'mail')}
                    {renderField('Phone Number', formData.phone, 'phone', 'call')}
                </Card>

                <Card style={styles.section}>
                    <Text style={styles.sectionTitle}>Account Status</Text>
                    <View style={styles.statusRow}>
                        <Text style={styles.statusLabel}>Account Created</Text>
                        <Text style={styles.statusValue}>November 15, 2024</Text>
                    </View>
                    <View style={styles.statusRow}>
                        <Text style={styles.statusLabel}>Email Verified</Text>
                        <View style={styles.verifiedBadge}>
                            <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
                            <Text style={styles.verifiedText}>Verified</Text>
                        </View>
                    </View>
                    <View style={styles.statusRow}>
                        <Text style={styles.statusLabel}>Phone Verified</Text>
                        <View style={styles.verifiedBadge}>
                            <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} />
                            <Text style={styles.verifiedText}>Verified</Text>
                        </View>
                    </View>
                </Card>

                <TouchableOpacity style={styles.dangerButton}>
                    <Ionicons name="trash-outline" size={20} color={theme.colors.error} />
                    <Text style={styles.dangerButtonText}>Delete Account</Text>
                </TouchableOpacity>

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.backgroundSecondary,
    },
    backButton: {
        padding: 8,
        marginLeft: 8,
    },
    editButton: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        marginRight: 8,
    },
    editButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    content: {
        flex: 1,
    },
    section: {
        margin: 16,
        marginBottom: 0,
        padding: 20,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 20,
    },
    fieldContainer: {
        marginBottom: 20,
    },
    fieldHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 8,
    },
    fieldLabel: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    fieldValue: {
        fontSize: 16,
        color: theme.colors.text,
        paddingVertical: 8,
    },
    fieldInput: {
        fontSize: 16,
        color: theme.colors.text,
        paddingVertical: 12,
        paddingHorizontal: 16,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: theme.colors.borderLight,
    },
    statusRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    statusLabel: {
        fontSize: 15,
        color: theme.colors.textSecondary,
    },
    statusValue: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
    },
    verifiedBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    verifiedText: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.success,
    },
    dangerButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        backgroundColor: theme.colors.errorLight,
        padding: 16,
        borderRadius: 12,
        margin: 16,
    },
    dangerButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.error,
    },
});
