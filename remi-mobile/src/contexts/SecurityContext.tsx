import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Alert, AppState, AppStateStatus } from 'react-native';
import { securityService, SecurityConfig, SecurityEvent, DeviceSecurityStatus } from '../services/securityService';
import { privacyService, PrivacyConfig, ConsentType } from '../services/privacyService';
import { biometricService, BiometricCapabilities } from '../services/biometricService';

interface SecurityContextType {
  // Security status
  isSecurityInitialized: boolean;
  deviceSecurity: DeviceSecurityStatus | null;
  biometricCapabilities: BiometricCapabilities | null;
  
  // Configuration
  securityConfig: SecurityConfig | null;
  privacyConfig: PrivacyConfig | null;
  
  // Security operations
  initializeSecurity: () => Promise<void>;
  checkDeviceSecurity: () => Promise<DeviceSecurityStatus>;
  authenticateWithBiometric: (purpose?: string) => Promise<boolean>;
  
  // Privacy operations
  recordConsent: (consentType: ConsentType, granted: boolean) => Promise<void>;
  hasConsent: (consentType: ConsentType) => Promise<boolean>;
  requestDataExport: (format?: 'json' | 'csv' | 'xml') => Promise<string>;
  requestDataDeletion: (type?: 'partial' | 'complete') => Promise<void>;
  
  // Secure storage
  storeSecurely: (key: string, value: any) => Promise<void>;
  retrieveSecurely: (key: string) => Promise<any>;
  
  // Security events
  recentSecurityEvents: SecurityEvent[];
  refreshSecurityEvents: () => Promise<void>;
  
  // App state security
  isAppSecured: boolean;
  lockApp: () => void;
  unlockApp: () => Promise<boolean>;
}

const SecurityContext = createContext<SecurityContextType | undefined>(undefined);

interface SecurityProviderProps {
  children: ReactNode;
  requireBiometricOnStart?: boolean;
  autoLockTimeoutMs?: number;
}

export const SecurityProvider: React.FC<SecurityProviderProps> = ({
  children,
  requireBiometricOnStart = true,
  autoLockTimeoutMs = 300000 // 5 minutes
}) => {
  const [isSecurityInitialized, setIsSecurityInitialized] = useState(false);
  const [deviceSecurity, setDeviceSecurity] = useState<DeviceSecurityStatus | null>(null);
  const [biometricCapabilities, setBiometricCapabilities] = useState<BiometricCapabilities | null>(null);
  const [securityConfig, setSecurityConfig] = useState<SecurityConfig | null>(null);
  const [privacyConfig, setPrivacyConfig] = useState<PrivacyConfig | null>(null);
  const [recentSecurityEvents, setRecentSecurityEvents] = useState<SecurityEvent[]>([]);
  const [isAppSecured, setIsAppSecured] = useState(false);
  const [lastActiveTime, setLastActiveTime] = useState(Date.now());

  // Initialize security services
  const initializeSecurity = async (): Promise<void> => {
    try {
      // Initialize encryption
      await securityService.initializeEncryption();
      
      // Load configurations
      const [secConfig, privConfig] = await Promise.all([
        securityService.getSecurityConfig(),
        privacyService.getPrivacyConfig()
      ]);
      
      setSecurityConfig(secConfig);
      setPrivacyConfig(privConfig);
      
      // Check device security
      const deviceSecStatus = await securityService.checkDeviceSecurity();
      setDeviceSecurity(deviceSecStatus);
      
      // Check biometric capabilities
      const biometricCaps = await biometricService.checkBiometricCapabilities();
      setBiometricCapabilities(biometricCaps);
      
      // Load recent security events
      await refreshSecurityEvents();
      
      // Handle device security violations
      if (!deviceSecStatus.isSecure && secConfig.deviceSecurityRequired) {
        Alert.alert(
          'Security Warning',
          `Device security violations detected:\n${deviceSecStatus.violations.join('\n')}\n\nSome features may be limited.`,
          [{ text: 'OK' }]
        );
      }
      
      setIsSecurityInitialized(true);
      
      // Require biometric authentication on start if enabled
      if (requireBiometricOnStart && biometricCaps.isAvailable) {
        setIsAppSecured(true);
      }
    } catch (error) {
      console.error('Failed to initialize security:', error);
      Alert.alert(
        'Security Error',
        'Failed to initialize security services. Some features may not work properly.',
        [{ text: 'OK' }]
      );
    }
  };

  // Check device security
  const checkDeviceSecurity = async (): Promise<DeviceSecurityStatus> => {
    const status = await securityService.checkDeviceSecurity();
    setDeviceSecurity(status);
    return status;
  };

  // Biometric authentication
  const authenticateWithBiometric = async (purpose: string = 'access the app'): Promise<boolean> => {
    try {
      if (!biometricCapabilities?.isAvailable) {
        Alert.alert('Biometric Not Available', 'Biometric authentication is not available on this device.');
        return false;
      }

      const config = await biometricService.createOptimalConfig(purpose);
      const result = await biometricService.authenticate(config);
      
      if (result.success) {
        setIsAppSecured(false);
        setLastActiveTime(Date.now());
      }
      
      return result.success;
    } catch (error) {
      console.error('Biometric authentication error:', error);
      return false;
    }
  };

  // Privacy operations
  const recordConsent = async (consentType: ConsentType, granted: boolean): Promise<void> => {
    // In a real app, you'd get the actual user ID
    const userId = 'current_user';
    await privacyService.recordConsent(userId, consentType, granted);
  };

  const hasConsent = async (consentType: ConsentType): Promise<boolean> => {
    const userId = 'current_user';
    return await privacyService.hasValidConsent(userId, consentType);
  };

  const requestDataExport = async (format: 'json' | 'csv' | 'xml' = 'json'): Promise<string> => {
    const userId = 'current_user';
    const request = await privacyService.requestDataExport(userId, format);
    
    Alert.alert(
      'Data Export Requested',
      `Your data export request has been submitted. Request ID: ${request.id}`,
      [{ text: 'OK' }]
    );
    
    return request.id;
  };

  const requestDataDeletion = async (type: 'partial' | 'complete' = 'complete'): Promise<void> => {
    const userId = 'current_user';
    
    Alert.alert(
      'Confirm Data Deletion',
      `Are you sure you want to ${type === 'complete' ? 'permanently delete all' : 'delete selected'} data? This action cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            const request = await privacyService.requestDataDeletion(userId, type);
            Alert.alert(
              'Data Deletion Requested',
              `Your data deletion request has been submitted. Request ID: ${request.id}`,
              [{ text: 'OK' }]
            );
          }
        }
      ]
    );
  };

  // Secure storage operations
  const storeSecurely = async (key: string, value: any): Promise<void> => {
    await securityService.storeSecurely(key, value);
  };

  const retrieveSecurely = async (key: string): Promise<any> => {
    return await securityService.retrieveSecurely(key);
  };

  // Security events
  const refreshSecurityEvents = async (): Promise<void> => {
    const events = await securityService.getAuditEvents(20);
    setRecentSecurityEvents(events);
  };

  // App locking
  const lockApp = (): void => {
    setIsAppSecured(true);
  };

  const unlockApp = async (): Promise<boolean> => {
    if (biometricCapabilities?.isAvailable) {
      return await authenticateWithBiometric('unlock the app');
    } else {
      // Fallback to other authentication methods
      setIsAppSecured(false);
      return true;
    }
  };

  // App state monitoring for auto-lock
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (nextAppState === 'active') {
        setLastActiveTime(Date.now());
        
        // Check if app should be locked due to inactivity
        const timeSinceLastActive = Date.now() - lastActiveTime;
        if (timeSinceLastActive > autoLockTimeoutMs && biometricCapabilities?.isAvailable) {
          setIsAppSecured(true);
        }
      } else if (nextAppState === 'background' || nextAppState === 'inactive') {
        // Lock app when going to background if biometrics are available
        if (biometricCapabilities?.isAvailable && securityConfig?.biometricEnabled) {
          setIsAppSecured(true);
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription?.remove();
  }, [lastActiveTime, autoLockTimeoutMs, biometricCapabilities, securityConfig]);

  // Auto-lock timer
  useEffect(() => {
    if (!autoLockTimeoutMs || !biometricCapabilities?.isAvailable) return;

    const interval = setInterval(() => {
      const timeSinceLastActive = Date.now() - lastActiveTime;
      if (timeSinceLastActive > autoLockTimeoutMs && !isAppSecured) {
        setIsAppSecured(true);
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [lastActiveTime, autoLockTimeoutMs, isAppSecured, biometricCapabilities]);

  // Initialize security on mount
  useEffect(() => {
    initializeSecurity();
  }, []);

  const contextValue: SecurityContextType = {
    isSecurityInitialized,
    deviceSecurity,
    biometricCapabilities,
    securityConfig,
    privacyConfig,
    initializeSecurity,
    checkDeviceSecurity,
    authenticateWithBiometric,
    recordConsent,
    hasConsent,
    requestDataExport,
    requestDataDeletion,
    storeSecurely,
    retrieveSecurely,
    recentSecurityEvents,
    refreshSecurityEvents,
    isAppSecured,
    lockApp,
    unlockApp
  };

  return (
    <SecurityContext.Provider value={contextValue}>
      {children}
    </SecurityContext.Provider>
  );
};

export const useSecurity = (): SecurityContextType => {
  const context = useContext(SecurityContext);
  if (context === undefined) {
    throw new Error('useSecurity must be used within a SecurityProvider');
  }
  return context;
};