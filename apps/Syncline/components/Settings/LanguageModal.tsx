import React, { useState } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../src/theme';

interface Language {
    code: string;
    name: string;
    nativeName: string;
}

interface LanguageModalProps {
    visible: boolean;
    onClose: () => void;
    selectedLanguage: string;
    onSelectLanguage: (code: string) => void;
}

const LANGUAGES: Language[] = [
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'es', name: 'Spanish', nativeName: 'Español' },
    { code: 'fr', name: 'French', nativeName: 'Français' },
    { code: 'de', name: 'German', nativeName: 'Deutsch' },
    { code: 'it', name: 'Italian', nativeName: 'Italiano' },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
    { code: 'ru', name: 'Russian', nativeName: 'Русский' },
    { code: 'zh', name: 'Chinese', nativeName: '中文' },
    { code: 'ja', name: 'Japanese', nativeName: '日本語' },
    { code: 'ko', name: 'Korean', nativeName: '한국어' },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
    { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
];

export const LanguageModal: React.FC<LanguageModalProps> = ({
    visible,
    onClose,
    selectedLanguage,
    onSelectLanguage,
}) => {
    const handleSelectLanguage = (code: string) => {
        onSelectLanguage(code);
        onClose();
    };

    return (
        <Modal
            visible={visible}
            animationType="slide"
            transparent
            onRequestClose={onClose}
        >
            <View style={styles.overlay}>
                <View style={styles.container}>
                    <View style={styles.header}>
                        <Text style={styles.title}>Select Language</Text>
                        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                            <Ionicons name="close" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                    </View>

                    <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                        {LANGUAGES.map((language) => {
                            const isSelected = language.code === selectedLanguage;
                            return (
                                <TouchableOpacity
                                    key={language.code}
                                    style={[
                                        styles.languageItem,
                                        isSelected && styles.languageItemSelected,
                                    ]}
                                    onPress={() => handleSelectLanguage(language.code)}
                                    activeOpacity={0.7}
                                >
                                    <View style={styles.languageInfo}>
                                        <Text style={[
                                            styles.languageName,
                                            isSelected && styles.languageNameSelected
                                        ]}>
                                            {language.name}
                                        </Text>
                                        <Text style={[
                                            styles.nativeName,
                                            isSelected && styles.nativeNameSelected
                                        ]}>
                                            {language.nativeName}
                                        </Text>
                                    </View>
                                    {isSelected && (
                                        <View style={styles.checkIcon}>
                                            <Ionicons
                                                name="checkmark-circle"
                                                size={24}
                                                color={theme.colors.primary}
                                            />
                                        </View>
                                    )}
                                </TouchableOpacity>
                            );
                        })}
                        <View style={{ height: 20 }} />
                    </ScrollView>
                </View>
            </View>
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        justifyContent: 'flex-end',
    },
    container: {
        backgroundColor: 'white',
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        paddingBottom: 40,
        maxHeight: '70%',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 20,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderLight,
    },
    title: {
        fontSize: 20,
        fontWeight: 'bold',
        color: theme.colors.text,
    },
    closeButton: {
        padding: 4,
    },
    content: {
        padding: 20,
    },
    languageItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 16,
        paddingHorizontal: 16,
        backgroundColor: 'white',
        borderRadius: 12,
        marginBottom: 8,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    languageItemSelected: {
        backgroundColor: theme.colors.primary + '10',
        borderColor: theme.colors.primary,
    },
    languageInfo: {
        flex: 1,
    },
    languageName: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    languageNameSelected: {
        color: theme.colors.primary,
    },
    nativeName: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    nativeNameSelected: {
        color: theme.colors.primary,
    },
    checkIcon: {
        marginLeft: 12,
    },
});
