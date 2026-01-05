import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Modal,
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ActivityIndicator,
    Image,
    TextInput,
    ScrollView,
    Dimensions,
    FlatList,
    Clipboard,
    Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import QRCode from 'react-native-qrcode-svg';
import * as Contacts from 'expo-contacts';
import { WhatsAppIcon } from '../WhatsAppIcon/WhatsAppIcon';
import { theme } from '../../src/theme';
import { Card } from '../Card/Card';
import { connectionsAPI } from '../../src/api/endpoints/connections';
import { whatsappAPI, WhatsAppStatusResponse } from '../../src/api/endpoints/whatsapp';
import { useAuth } from '../../src/contexts/AuthContext';

const { height: screenHeight } = Dimensions.get('window');

// Popular country codes
const COUNTRY_CODES = [
    { code: '+1', country: 'US/CA', flag: '🇺🇸' },
    { code: '+44', country: 'UK', flag: '🇬🇧' },
    { code: '+234', country: 'Nigeria', flag: '🇳🇬' },
    { code: '+91', country: 'India', flag: '🇮🇳' },
    { code: '+49', country: 'Germany', flag: '🇩🇪' },
    { code: '+33', country: 'France', flag: '🇫🇷' },
    { code: '+61', country: 'Australia', flag: '🇦🇺' },
    { code: '+81', country: 'Japan', flag: '🇯🇵' },
    { code: '+86', country: 'China', flag: '🇨🇳' },
    { code: '+55', country: 'Brazil', flag: '🇧🇷' },
    { code: '+27', country: 'South Africa', flag: '🇿🇦' },
    { code: '+254', country: 'Kenya', flag: '🇰🇪' },
    { code: '+971', country: 'UAE', flag: '🇦🇪' },
    { code: '+966', country: 'Saudi Arabia', flag: '🇸🇦' },
    { code: '+52', country: 'Mexico', flag: '🇲🇽' },
];

type ConnectionStep = 'init' | 'qr' | 'phone_input' | 'pairing_code' | 'scanning' | 'success' | 'error';

interface WhatsAppConnectModalProps {
    visible: boolean;
    userId: string;
    onClose: () => void;
    onConnected: (connectionId: string) => void;
}

export const WhatsAppConnectModal: React.FC<WhatsAppConnectModalProps> = ({
    visible,
    userId,
    onClose,
    onConnected,
}) => {
    const { isAuthenticated, user } = useAuth();
    const [step, setStep] = useState<ConnectionStep>('init');
    const [connectionId, setConnectionId] = useState<string | null>(null);
    const [qrCode, setQrCode] = useState<string | null>(null);
    const [pairingCode, setPairingCode] = useState<string | null>(null);
    const [phoneNumber, setPhoneNumber] = useState('');
    const [selectedCountryCode, setSelectedCountryCode] = useState(COUNTRY_CODES[2]); // Default Nigeria
    const [showCountryPicker, setShowCountryPicker] = useState(false);
    const [status, setStatus] = useState<WhatsAppStatusResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [pollingActive, setPollingActive] = useState(false);
    const [contactsPermission, setContactsPermission] = useState<string | null>(null);
    const [contactsCount, setContactsCount] = useState(0);

    const qrRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Cleanup timers
    const clearTimers = useCallback(() => {
        if (qrRefreshRef.current) {
            clearInterval(qrRefreshRef.current);
            qrRefreshRef.current = null;
        }
        if (countdownRef.current) {
            clearInterval(countdownRef.current);
            countdownRef.current = null;
        }
    }, []);

    // Request contact permissions
    const requestContactPermissions = async () => {
        try {
            const { status } = await Contacts.requestPermissionsAsync();
            setContactsPermission(status);

            if (status === 'granted') {
                const { data } = await Contacts.getContactsAsync({
                    fields: [Contacts.Fields.PhoneNumbers, Contacts.Fields.Name],
                });
                setContactsCount(data.length);
                console.log(`Found ${data.length} contacts`);
            }
            return status;
        } catch (err) {
            console.error('Contact permission error:', err);
            return 'denied';
        }
    };

    // Reset state when modal opens
    useEffect(() => {
        if (visible) {
            // Check authentication first
            if (!isAuthenticated || !user) {
                setError('Please login first to connect WhatsApp');
                setStep('error');
                return;
            }

            setStep('init');
            setConnectionId(null);
            setQrCode(null);
            setPairingCode(null);
            setPhoneNumber('');
            setStatus(null);
            setError(null);
            initializeConnection();
        } else {
            setPollingActive(false);
            clearTimers();
        }
        return clearTimers;
    }, [visible, clearTimers, isAuthenticated, user]);

    // Initialize connection and get QR code
    const initializeConnection = async () => {
        try {
            setStep('init');
            setError(null);

            // Request contact permissions first
            await requestContactPermissions();

            // STEP 1: Check for existing WhatsApp connection FIRST
            console.log('Checking for existing WhatsApp connection...');
            const existingCheck = await whatsappAPI.checkExistingConnection();

            if (existingCheck.is_existing && existingCheck.connection_id) {
                console.log('Found existing connection:', existingCheck.connection_id);
                setConnectionId(existingCheck.connection_id);

                if (existingCheck.is_logged_in) {
                    // Already logged in - show success immediately
                    console.log('Already logged in with phone:', existingCheck.phone);
                    setStep('success');
                    onConnected(existingCheck.connection_id);
                    return;
                } else {
                    // Connection exists but not logged in - go to phone input (default)
                    console.log('Connection exists but not logged in, showing phone input...');
                    setStep('phone_input');
                    return;
                }
            }

            // STEP 2: No existing connection - create new one
            console.log('No existing connection found, creating new one...');
            const response = await connectionsAPI.initiateConnection(
                'whatsapp',
                userId,
                'syncline://oauth/callback'
            );

            console.log('Connected:', response.connection_id);
            setConnectionId(response.connection_id);

            // Default to phone input for pairing code (simpler for users)
            setStep('phone_input');

        } catch (err: any) {
            console.error('WhatsApp init error:', err);
            let errorMessage = 'Failed to initialize WhatsApp connection';
            if (err.response?.data?.detail) {
                errorMessage = typeof err.response.data.detail === 'string'
                    ? err.response.data.detail
                    : JSON.stringify(err.response.data.detail);
            } else if (err.message) {
                errorMessage = err.message;
            }
            setError(errorMessage);
            setStep('error');
        }
    };

    // Fetch QR code and start refresh cycle
    const fetchQRCode = useCallback(async (connId: string) => {
        try {
            setStep('qr');
            const loginResponse = await whatsappAPI.getLoginQR(connId);

            if (loginResponse.already_logged_in) {
                setStep('success');
                onConnected(connId);
                return;
            }

            if (loginResponse.qr_code && loginResponse.qr_code.length > 20) {
                setQrCode(loginResponse.qr_code);
                startQrRefresh(connId);
                startPolling(connId);
            } else {
                throw new Error('No QR code received from server');
            }
        } catch (err: any) {
            console.error('QR code fetch error:', err);
            const errorMessage = err.response?.data?.detail || err.message || 'Failed to get QR code';
            setError(errorMessage);
            setStep('error');
        }
    }, [onConnected, startQrRefresh, startPolling]);

    // Auto-refresh QR code
    const startQrRefresh = useCallback((connId: string) => {
        clearTimers();

        qrRefreshRef.current = setInterval(async () => {
            try {
                const loginResponse = await whatsappAPI.getLoginQR(connId);
                if (loginResponse.qr_code && loginResponse.qr_code.length > 20 && !loginResponse.already_logged_in) {
                    setQrCode(loginResponse.qr_code);
                } else if (loginResponse.already_logged_in) {
                    setStep('success');
                    onConnected(connId);
                    clearTimers();
                }
            } catch (err) {
                console.log('QR refresh error:', err);
            }
        }, 15000);
    }, [clearTimers, onConnected]);

    // Handle Phone Login
    const handlePhoneSubmit = async () => {
        if (!connectionId || !phoneNumber || phoneNumber.length < 5) {
            setError('Please enter a valid phone number');
            return;
        }

        const fullNumber = `${selectedCountryCode.code}${phoneNumber.replace(/^0+/, '')}`;

        try {
            setStep('scanning');
            const response = await whatsappAPI.loginWithPhone(connectionId, fullNumber);

            // Handle response - either we got a code or check_phone flag
            if (response.pairing_code) {
                setPairingCode(response.pairing_code);
                setStep('pairing_code');
                startPolling(connectionId);
            } else if ((response as any).check_phone) {
                // Bridge sent pairing directly to WhatsApp
                setPairingCode(null);
                setStep('pairing_code');  // Show waiting screen
                startPolling(connectionId);
            } else {
                throw new Error('No pairing code received');
            }
        } catch (err: any) {
            console.error('Phone login error:', err);
            const errorMessage = err.response?.data?.detail || err.message || 'Failed to get pairing code';
            setError(errorMessage);
            setStep('error');
        }
    };

    // Poll for connection status
    const startPolling = useCallback(async (connId: string) => {
        setPollingActive(true);

        await whatsappAPI.pollStatus(
            connId,
            async (newStatus) => {
                setStatus(newStatus);
                if (newStatus.is_logged_in) {
                    // Update connection status in database
                    try {
                        await connectionsAPI.updateStatus(connId, 'active');
                    } catch (e) {
                        console.log('Failed to update status:', e);
                    }
                    setStep('success');
                    onConnected(connId);
                    clearTimers();
                }
            },
            2000,  // Poll every 2 seconds for faster response
            120    // Keep polling for 4 minutes (240 seconds)
        );

        setPollingActive(false);
    }, [onConnected, clearTimers]);

    const handleClose = () => {
        setPollingActive(false);
        clearTimers();
        onClose();
    };

    const handleRetry = () => {
        clearTimers();
        initializeConnection();
    };

    // Render QR code
    const renderQRCode = () => {
        if (!qrCode) return null;

        if (qrCode.startsWith('data:image')) {
            return (
                <Image
                    source={{ uri: qrCode }}
                    style={styles.qrImage}
                    resizeMode="contain"
                />
            );
        }

        return (
            <View style={styles.qrContainer}>
                <QRCode
                    value={qrCode}
                    size={180}
                    backgroundColor="white"
                    color="black"
                />
            </View>
        );
    };

    // Render country picker
    const renderCountryPicker = () => (
        <Modal visible={showCountryPicker} transparent animationType="fade">
            <TouchableOpacity
                style={styles.pickerOverlay}
                onPress={() => setShowCountryPicker(false)}
                activeOpacity={1}
            >
                <View style={styles.pickerContainer}>
                    <Text style={styles.pickerTitle}>Select Country</Text>
                    <FlatList
                        data={COUNTRY_CODES}
                        keyExtractor={(item) => item.code}
                        renderItem={({ item }) => (
                            <TouchableOpacity
                                style={styles.pickerItem}
                                onPress={() => {
                                    setSelectedCountryCode(item);
                                    setShowCountryPicker(false);
                                }}
                            >
                                <Text style={styles.pickerFlag}>{item.flag}</Text>
                                <Text style={styles.pickerCountry}>{item.country}</Text>
                                <Text style={styles.pickerCode}>{item.code}</Text>
                            </TouchableOpacity>
                        )}
                    />
                </View>
            </TouchableOpacity>
        </Modal>
    );

    return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={handleClose}
        >
            <View style={styles.overlay}>
                <View style={styles.modalContainer}>
                    {/* Header */}
                    <LinearGradient
                        colors={['#25D366', '#1DA851']}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={styles.header}
                    >
                        <TouchableOpacity onPress={handleClose} style={styles.closeButton}>
                            <Ionicons name="close" size={28} color="white" />
                        </TouchableOpacity>

                        <View style={styles.iconWrapper}>
                            <WhatsAppIcon size={48} color="white" />
                        </View>

                        <Text style={styles.modalTitle}>Connect WhatsApp</Text>
                        <Text style={styles.modalSubtitle}>
                            {step === 'init' && 'Setting up connection...'}
                            {step === 'qr' && 'Scan QR code with WhatsApp'}
                            {step === 'phone_input' && 'Enter your phone number'}
                            {step === 'pairing_code' && 'Enter code on your phone'}
                            {step === 'scanning' && 'Getting pairing code...'}
                            {step === 'success' && 'Successfully connected!'}
                            {step === 'error' && 'Connection failed'}
                        </Text>
                    </LinearGradient>

                    {/* Scrollable Content */}
                    <ScrollView
                        style={styles.scrollView}
                        contentContainerStyle={styles.scrollContent}
                        showsVerticalScrollIndicator={false}
                    >
                        {/* Loading State */}
                        {(step === 'init' || step === 'scanning') && (
                            <View style={styles.centerContent}>
                                <ActivityIndicator size="large" color="#25D366" />
                                <Text style={styles.statusText}>
                                    {step === 'init' ? 'Preparing connection...' : 'Getting pairing code...'}
                                </Text>
                            </View>
                        )}

                        {/* QR Code */}
                        {step === 'qr' && (
                            <View style={styles.qrSection}>
                                <View style={styles.altMethodBadge}>
                                    <Text style={styles.altMethodText}>Alternative Method</Text>
                                </View>

                                <Card padding="l" style={styles.qrCard}>
                                    {renderQRCode()}
                                </Card>

                                <TouchableOpacity
                                    style={styles.linkButton}
                                    onPress={() => setStep('phone_input')}
                                >
                                    <Text style={styles.linkButtonText}>← Back to pairing code</Text>
                                </TouchableOpacity>

                                <View style={styles.instructions}>
                                    <Text style={styles.instructionTitle}>How to connect:</Text>
                                    <Text style={styles.instructionStep}>1. Open WhatsApp on your phone</Text>
                                    <Text style={styles.instructionStep}>2. Go to Settings → Linked Devices</Text>
                                    <Text style={styles.instructionStep}>3. Tap "Link a Device" and scan this QR code</Text>
                                </View>
                            </View>
                        )}

                        {/* Phone Input with Country Selector */}
                        {step === 'phone_input' && (
                            <View style={styles.centerContent}>
                                <View style={styles.recommendedBadge}>
                                    <Text style={styles.recommendedText}>✓ Recommended Method</Text>
                                </View>

                                <Text style={styles.instructionTitle}>Enter Your Phone Number</Text>
                                <Text style={styles.instructionSubtitle}>We'll send a pairing code to your WhatsApp</Text>

                                <View style={styles.phoneInputRow}>
                                    <TouchableOpacity
                                        style={styles.countrySelector}
                                        onPress={() => setShowCountryPicker(true)}
                                    >
                                        <Text style={styles.countryFlag}>{selectedCountryCode.flag}</Text>
                                        <Text style={styles.countryCode}>{selectedCountryCode.code}</Text>
                                        <Ionicons name="chevron-down" size={16} color="#666" />
                                    </TouchableOpacity>

                                    <TextInput
                                        style={styles.phoneInput}
                                        placeholder="Phone number"
                                        value={phoneNumber}
                                        onChangeText={setPhoneNumber}
                                        keyboardType="phone-pad"
                                        placeholderTextColor="#999"
                                    />
                                </View>

                                <TouchableOpacity style={styles.primaryButton} onPress={handlePhoneSubmit}>
                                    <Text style={styles.primaryButtonText}>Get Pairing Code</Text>
                                </TouchableOpacity>

                                <TouchableOpacity style={styles.linkButton} onPress={() => fetchQRCode(connectionId!)}>
                                    <Text style={styles.linkButtonText}>Use QR Code instead</Text>
                                </TouchableOpacity>
                            </View>
                        )}

                        {/* Pairing Code */}
                        {step === 'pairing_code' && (
                            <View style={styles.centerContent}>
                                {pairingCode ? (
                                    <>
                                        <Text style={styles.instructionTitle}>Your Pairing Code</Text>
                                        <TouchableOpacity
                                            style={styles.pairingCodeBox}
                                            onPress={() => {
                                                Clipboard.setString(pairingCode.replace('-', ''));
                                                Alert.alert('Copied!', 'Pairing code copied to clipboard');
                                            }}
                                            activeOpacity={0.7}
                                        >
                                            <Text style={styles.pairingCodeText}>
                                                {pairingCode}
                                            </Text>
                                            <View style={styles.copyButton}>
                                                <Ionicons name="copy-outline" size={20} color="#25D366" />
                                                <Text style={styles.copyButtonText}>Tap to copy</Text>
                                            </View>
                                        </TouchableOpacity>
                                        <View style={styles.pairingInstructions}>
                                            <Text style={styles.instructionStep}>1. Open WhatsApp on your phone</Text>
                                            <Text style={styles.instructionStep}>2. Go to Settings → Linked Devices</Text>
                                            <Text style={styles.instructionStep}>3. Tap "Link with phone number"</Text>
                                            <Text style={styles.instructionStep}>4. Enter the code above</Text>
                                        </View>
                                    </>
                                ) : (
                                    <>
                                        <Text style={styles.instructionTitle}>Check Your WhatsApp!</Text>
                                        <View style={styles.pairingCodeBox}>
                                            <Ionicons name="phone-portrait-outline" size={50} color="#25D366" />
                                        </View>
                                        <Text style={styles.instructionSubtitle}>
                                            A pairing notification was sent to your WhatsApp.{'\n'}Open WhatsApp and follow the prompts.
                                        </Text>
                                    </>
                                )}
                                <View style={styles.waitingRow}>
                                    <ActivityIndicator size="small" color="#25D366" />
                                    <Text style={styles.waitingText}>Waiting for connection...</Text>
                                </View>
                            </View>
                        )}

                        {/* Success */}
                        {step === 'success' && (
                            <View style={styles.centerContent}>
                                <Ionicons name="checkmark-circle" size={80} color="#25D366" />
                                <Text style={styles.successTitle}>Connected!</Text>
                                <Text style={styles.successText}>
                                    Your WhatsApp is now linked to Syncline.
                                </Text>
                                {status?.bridge_status.phone && (
                                    <Text style={styles.phoneText}>📱 {status.bridge_status.phone}</Text>
                                )}
                                {contactsCount > 0 && (
                                    <Text style={styles.contactsText}>✓ {contactsCount} contacts synced</Text>
                                )}
                                <TouchableOpacity style={styles.primaryButton} onPress={handleClose}>
                                    <Text style={styles.primaryButtonText}>Done</Text>
                                </TouchableOpacity>
                            </View>
                        )}

                        {/* Error */}
                        {step === 'error' && (
                            <View style={styles.centerContent}>
                                <Ionicons name="close-circle" size={80} color={theme.colors.error} />
                                <Text style={styles.errorTitle}>Connection Failed</Text>
                                <Text style={styles.errorText}>{error}</Text>

                                {error?.includes('login') ? (
                                    <TouchableOpacity
                                        style={styles.primaryButton}
                                        onPress={handleClose}
                                    >
                                        <Text style={styles.primaryButtonText}>Go to Login</Text>
                                    </TouchableOpacity>
                                ) : (
                                    <>
                                        <TouchableOpacity style={styles.primaryButton} onPress={handleRetry}>
                                            <Text style={styles.primaryButtonText}>Try Again</Text>
                                        </TouchableOpacity>
                                        <TouchableOpacity style={styles.linkButton} onPress={() => setStep('phone_input')}>
                                            <Text style={styles.linkButtonText}>Try Phone Number</Text>
                                        </TouchableOpacity>
                                    </>
                                )}
                            </View>
                        )}
                    </ScrollView>
                </View>
            </View>

            {renderCountryPicker()}
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'flex-end',
    },
    modalContainer: {
        backgroundColor: theme.colors.background,
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        height: screenHeight * 0.85,
        overflow: 'hidden',
    },
    header: {
        padding: 24,
        paddingTop: 32,
        alignItems: 'center',
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
    },
    closeButton: {
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 10,
    },
    iconWrapper: {
        width: 80,
        height: 80,
        borderRadius: 20,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 12,
    },
    modalTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: 'white',
        marginBottom: 4,
    },
    modalSubtitle: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
        textAlign: 'center',
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        padding: 24,
        paddingBottom: 48,
    },
    centerContent: {
        alignItems: 'center',
        paddingVertical: 24,
    },
    statusText: {
        marginTop: 16,
        color: theme.colors.textSecondary,
    },
    qrSection: {
        alignItems: 'center',
    },
    recommendedBadge: {
        backgroundColor: '#E8F5E9',
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        marginBottom: 16,
    },
    recommendedText: {
        color: '#2E7D32',
        fontWeight: '600',
        fontSize: 14,
    },
    qrCard: {
        backgroundColor: 'white',
        padding: 16,
    },
    qrContainer: {
        padding: 8,
        backgroundColor: 'white',
    },
    qrImage: {
        width: 180,
        height: 180,
    },
    linkButton: {
        paddingVertical: 12,
        marginTop: 8,
    },
    linkButtonText: {
        color: '#25D366',
        fontWeight: '600',
    },
    instructions: {
        marginTop: 24,
        width: '100%',
    },
    instructionTitle: {
        fontSize: 18,
        fontWeight: '600',
        marginBottom: 12,
        color: theme.colors.text,
        textAlign: 'center',
    },
    instructionSubtitle: {
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 16,
        lineHeight: 20,
    },
    instructionStep: {
        color: theme.colors.textSecondary,
        marginBottom: 8,
        fontSize: 14,
    },
    // Phone input with country selector
    phoneInputRow: {
        flexDirection: 'row',
        width: '100%',
        marginBottom: 16,
        gap: 8,
    },
    countrySelector: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
        paddingHorizontal: 12,
        paddingVertical: 14,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: theme.colors.border,
        gap: 6,
    },
    countryFlag: {
        fontSize: 20,
    },
    countryCode: {
        fontSize: 16,
        fontWeight: '500',
        color: theme.colors.text,
    },
    phoneInput: {
        flex: 1,
        padding: 14,
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: 12,
        fontSize: 16,
        backgroundColor: 'white',
    },
    noticeBox: {
        backgroundColor: '#FFF3E0',
        padding: 12,
        borderRadius: 8,
        marginTop: 12,
        borderLeftWidth: 3,
        borderLeftColor: '#FF9800',
    },
    noticeText: {
        color: '#E65100',
        fontSize: 13,
        lineHeight: 18,
        textAlign: 'center',
    },
    primaryButton: {
        backgroundColor: '#25D366',
        paddingVertical: 14,
        paddingHorizontal: 32,
        borderRadius: 12,
        marginTop: 8,
        width: '100%',
        alignItems: 'center',
    },
    primaryButtonText: {
        color: 'white',
        fontWeight: '600',
        fontSize: 16,
    },
    pairingCodeBox: {
        backgroundColor: '#f0f2f5',
        paddingVertical: 20,
        paddingHorizontal: 32,
        borderRadius: 12,
        marginVertical: 16,
        borderWidth: 2,
        borderColor: '#25D366',
        borderStyle: 'dashed',
        alignItems: 'center',
    },
    pairingCodeText: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#333',
        letterSpacing: 6,
        textAlign: 'center',
    },
    copyButton: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 12,
        gap: 6,
    },
    copyButtonText: {
        fontSize: 14,
        color: '#25D366',
        fontWeight: '500',
    },
    pairingInstructions: {
        marginTop: 16,
        width: '100%',
    },
    altMethodBadge: {
        backgroundColor: '#f5f5f5',
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
        marginBottom: 16,
    },
    altMethodText: {
        color: '#666',
        fontWeight: '500',
        fontSize: 14,
    },
    waitingRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 16,
        gap: 8,
    },
    waitingText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    successTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#25D366',
        marginTop: 16,
        marginBottom: 8,
    },
    successText: {
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 16,
    },
    phoneText: {
        color: theme.colors.text,
        marginBottom: 8,
    },
    contactsText: {
        color: '#25D366',
        marginBottom: 24,
    },
    errorTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: theme.colors.error,
        marginTop: 16,
        marginBottom: 8,
    },
    errorText: {
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 24,
    },
    // Country picker modal
    pickerOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    pickerContainer: {
        backgroundColor: 'white',
        borderRadius: 16,
        width: '80%',
        maxHeight: '60%',
        padding: 16,
    },
    pickerTitle: {
        fontSize: 18,
        fontWeight: '600',
        textAlign: 'center',
        marginBottom: 16,
        color: theme.colors.text,
    },
    pickerItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#eee',
    },
    pickerFlag: {
        fontSize: 24,
        marginRight: 12,
    },
    pickerCountry: {
        flex: 1,
        fontSize: 16,
        color: theme.colors.text,
    },
    pickerCode: {
        fontSize: 16,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
});

export default WhatsAppConnectModal;
