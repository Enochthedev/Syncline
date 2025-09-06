import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Animated,
  Dimensions
} from 'react-native';
import { useSecurity } from '../contexts/SecurityContext';
import { biometricService } from '../services/biometricService';

interface SecurityLockScreenProps {
  onUnlock?: () => void;
  showAppName?: boolean;
  customMessage?: string;
}

export const SecurityLockScreen: React.FC<SecurityLockScreenProps> = ({
  onUnlock,
  showAppName = true,
  customMessage
}) => {
  const { 
    biometricCapabilities, 
    unlockApp, 
    authenticateWithBiometric 
  } = useSecurity();
  
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [biometryTypeName, setBiometryTypeName] = useState('Biometric Authentication');
  const [fadeAnim] = useState(new Animated.Value(0));
  const [pulseAnim] = useState(new Animated.Value(1));

  useEffect(() => {
    // Fade in animation
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();

    // Get biometry type name
    biometricService.getBiometryTypeName().then(setBiometryTypeName);

    // Start pulse animation for biometric icon
    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    );
    pulseAnimation.start();

    return () => pulseAnimation.stop();
  }, []);

  const handleBiometricAuth = async () => {
    if (isAuthenticating) return;

    setIsAuthenticating(true);
    try {
      const success = await unlockApp();
      if (success) {
        onUnlock?.();
      } else {
        Alert.alert(
          'Authentication Failed',
          'Please try again or use your device passcode.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      Alert.alert(
        'Authentication Error',
        'An error occurred during authentication. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handlePasscodeAuth = () => {
    Alert.alert(
      'Passcode Authentication',
      'Please use your device passcode to unlock the app.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Use Passcode',
          onPress: async () => {
            try {
              const success = await authenticateWithBiometric('unlock the app');
              if (success) {
                onUnlock?.();
              }
            } catch (error) {
              console.error('Passcode authentication error:', error);
            }
          }
        }
      ]
    );
  };

  const getBiometricIcon = () => {
    if (!biometricCapabilities?.biometryType) return '🔒';
    
    switch (biometricCapabilities.biometryType) {
      case 'TouchID':
      case 'Fingerprint':
        return '👆';
      case 'FaceID':
      case 'Face':
        return '👤';
      case 'Iris':
        return '👁️';
      default:
        return '🔒';
    }
  };

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      <View style={styles.content}>
        {showAppName && (
          <Text style={styles.appName}>R.E.M.I</Text>
        )}
        
        <Animated.View 
          style={[
            styles.biometricIconContainer,
            { transform: [{ scale: pulseAnim }] }
          ]}
        >
          <Text style={styles.biometricIcon}>{getBiometricIcon()}</Text>
        </Animated.View>

        <Text style={styles.title}>App Locked</Text>
        
        <Text style={styles.message}>
          {customMessage || `Use ${biometryTypeName} to unlock and access your data securely.`}
        </Text>

        {biometricCapabilities?.isAvailable && (
          <TouchableOpacity
            style={[styles.unlockButton, isAuthenticating && styles.unlockButtonDisabled]}
            onPress={handleBiometricAuth}
            disabled={isAuthenticating}
          >
            <Text style={styles.unlockButtonText}>
              {isAuthenticating ? 'Authenticating...' : `Unlock with ${biometryTypeName}`}
            </Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.passcodeButton}
          onPress={handlePasscodeAuth}
        >
          <Text style={styles.passcodeButtonText}>Use Passcode</Text>
        </TouchableOpacity>

        <View style={styles.securityInfo}>
          <Text style={styles.securityInfoText}>
            🔐 Your data is protected with end-to-end encryption
          </Text>
        </View>
      </View>
    </Animated.View>
  );
};

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
    paddingHorizontal: 40,
    width: '100%',
  },
  appName: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 40,
    letterSpacing: 2,
  },
  biometricIconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 30,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  biometricIcon: {
    fontSize: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 16,
  },
  message: {
    fontSize: 16,
    color: '#cccccc',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 40,
  },
  unlockButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 25,
    marginBottom: 16,
    minWidth: 200,
  },
  unlockButtonDisabled: {
    backgroundColor: '#555555',
  },
  unlockButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  passcodeButton: {
    paddingHorizontal: 32,
    paddingVertical: 12,
    marginBottom: 40,
  },
  passcodeButtonText: {
    color: '#007AFF',
    fontSize: 16,
    textAlign: 'center',
  },
  securityInfo: {
    position: 'absolute',
    bottom: 50,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  securityInfoText: {
    fontSize: 14,
    color: '#888888',
    textAlign: 'center',
  },
});