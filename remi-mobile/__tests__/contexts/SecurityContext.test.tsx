import React from 'react';
import { render, act, waitFor } from '@testing-library/react-native';
import { Alert, AppState } from 'react-native';
import { SecurityProvider, useSecurity } from '../../src/contexts/SecurityContext';
import { securityService } from '../../src/services/securityService';
import { privacyService, ConsentType } from '../../src/services/privacyService';
import { biometricService } from '../../src/services/biometricService';

// Mock dependencies
jest.mock('../../src/services/securityService');
jest.mock('../../src/services/privacyService');
jest.mock('../../src/services/biometricService');
jest.mock('react-native', () => ({
  Alert: {
    alert: jest.fn()
  },
  AppState: {
    addEventListener: jest.fn(() => ({ remove: jest.fn() }))
  }
}));

const mockSecurityService = securityService as jest.Mocked<typeof securityService>;
const mockPrivacyService = privacyService as jest.Mocked<typeof privacyService>;
const mockBiometricService = biometricService as jest.Mocked<typeof biometricService>;
const mockAlert = Alert.alert as jest.Mock;

// Test component to access context
const TestComponent: React.FC = () => {
  const security = useSecurity();
  return null;
};

describe('SecurityContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Setup default mocks
    mockSecurityService.initializeEncryption.mockResolvedValue();
    mockSecurityService.getSecurityConfig.mockResolvedValue({
      encryptionEnabled: true,
      biometricEnabled: true,
      deviceSecurityRequired: true,
      auditLoggingEnabled: true,
      piiRedactionLevel: 'basic'
    });
    mockSecurityService.checkDeviceSecurity.mockResolvedValue({
      isJailbroken: false,
      isRooted: false,
      isDebuggingEnabled: false,
      hasHooks: false,
      isSecure: true,
      violations: []
    });
    mockSecurityService.getAuditEvents.mockResolvedValue([]);
    mockSecurityService.storeSecurely.mockResolvedValue();
    mockSecurityService.retrieveSecurely.mockResolvedValue(null);
    
    mockPrivacyService.getPrivacyConfig.mockResolvedValue({
      piiRedactionEnabled: true,
      redactionLevel: 'basic',
      dataMinimizationEnabled: true,
      consentRequired: true,
      retentionPeriodDays: 365,
      allowDataExport: true,
      allowDataDeletion: true
    });
    mockPrivacyService.recordConsent.mockResolvedValue({
      id: 'consent_123',
      userId: 'user_123',
      consentType: ConsentType.DATA_PROCESSING,
      granted: true,
      timestamp: new Date(),
      version: '1.0'
    });
    mockPrivacyService.hasValidConsent.mockResolvedValue(true);
    mockPrivacyService.requestDataExport.mockResolvedValue({
      id: 'export_123',
      userId: 'user_123',
      requestedAt: new Date(),
      format: 'json',
      status: 'pending'
    });
    
    mockBiometricService.checkBiometricCapabilities.mockResolvedValue({
      isAvailable: true,
      biometryType: 'TouchID'
    });
    mockBiometricService.createOptimalConfig.mockResolvedValue({
      title: 'Authenticate',
      description: 'Use biometric to authenticate'
    });
    mockBiometricService.authenticate.mockResolvedValue({
      success: true,
      biometryType: 'TouchID',
      timestamp: new Date()
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Initialization', () => {
    it('should initialize security services on mount', async () => {
      render(
        <SecurityProvider>
          <TestComponent />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(mockSecurityService.initializeEncryption).toHaveBeenCalled();
        expect(mockSecurityService.getSecurityConfig).toHaveBeenCalled();
        expect(mockPrivacyService.getPrivacyConfig).toHaveBeenCalled();
        expect(mockSecurityService.checkDeviceSecurity).toHaveBeenCalled();
        expect(mockBiometricService.checkBiometricCapabilities).toHaveBeenCalled();
      });
    });

    it('should show security warning for insecure device', async () => {
      mockSecurityService.checkDeviceSecurity.mockResolvedValue({
        isJailbroken: true,
        isRooted: false,
        isDebuggingEnabled: false,
        hasHooks: false,
        isSecure: false,
        violations: ['Device is jailbroken']
      });

      render(
        <SecurityProvider>
          <TestComponent />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(mockAlert).toHaveBeenCalledWith(
          'Security Warning',
          expect.stringContaining('Device security violations detected'),
          [{ text: 'OK' }]
        );
      });
    });

    it('should handle initialization errors gracefully', async () => {
      mockSecurityService.initializeEncryption.mockRejectedValue(new Error('Init failed'));

      render(
        <SecurityProvider>
          <TestComponent />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(mockAlert).toHaveBeenCalledWith(
          'Security Error',
          expect.stringContaining('Failed to initialize security services'),
          [{ text: 'OK' }]
        );
      });
    });

    it('should lock app on start if biometric required', async () => {
      let contextValue: any;
      
      const TestConsumer: React.FC = () => {
        contextValue = useSecurity();
        return null;
      };

      render(
        <SecurityProvider requireBiometricOnStart={true}>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isAppSecured).toBe(true);
      });
    });
  });

  describe('Security Operations', () => {
    let contextValue: any;
    
    const TestConsumer: React.FC = () => {
      contextValue = useSecurity();
      return null;
    };

    beforeEach(async () => {
      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });
    });

    it('should check device security', async () => {
      const mockStatus = {
        isJailbroken: false,
        isRooted: false,
        isDebuggingEnabled: false,
        hasHooks: false,
        isSecure: true,
        violations: []
      };
      mockSecurityService.checkDeviceSecurity.mockResolvedValue(mockStatus);

      await act(async () => {
        const result = await contextValue.checkDeviceSecurity();
        expect(result).toEqual(mockStatus);
      });
    });

    it('should authenticate with biometric', async () => {
      await act(async () => {
        const result = await contextValue.authenticateWithBiometric('test purpose');
        expect(result).toBe(true);
      });

      expect(mockBiometricService.createOptimalConfig).toHaveBeenCalledWith('test purpose');
      expect(mockBiometricService.authenticate).toHaveBeenCalled();
    });

    it('should handle biometric authentication failure', async () => {
      mockBiometricService.authenticate.mockResolvedValue({
        success: false,
        error: 'Authentication failed',
        timestamp: new Date()
      });

      await act(async () => {
        const result = await contextValue.authenticateWithBiometric();
        expect(result).toBe(false);
      });
    });

    it('should store and retrieve data securely', async () => {
      const testData = { secret: 'value' };
      mockSecurityService.retrieveSecurely.mockResolvedValue(testData);

      await act(async () => {
        await contextValue.storeSecurely('test_key', testData);
        const retrieved = await contextValue.retrieveSecurely('test_key');
        
        expect(mockSecurityService.storeSecurely).toHaveBeenCalledWith('test_key', testData);
        expect(retrieved).toEqual(testData);
      });
    });
  });

  describe('Privacy Operations', () => {
    let contextValue: any;
    
    const TestConsumer: React.FC = () => {
      contextValue = useSecurity();
      return null;
    };

    beforeEach(async () => {
      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });
    });

    it('should record consent', async () => {
      await act(async () => {
        await contextValue.recordConsent(ConsentType.DATA_PROCESSING, true);
      });

      expect(mockPrivacyService.recordConsent).toHaveBeenCalledWith(
        'current_user',
        ConsentType.DATA_PROCESSING,
        true
      );
    });

    it('should check consent', async () => {
      await act(async () => {
        const hasConsent = await contextValue.hasConsent(ConsentType.AI_ANALYSIS);
        expect(hasConsent).toBe(true);
      });

      expect(mockPrivacyService.hasValidConsent).toHaveBeenCalledWith(
        'current_user',
        ConsentType.AI_ANALYSIS
      );
    });

    it('should request data export', async () => {
      await act(async () => {
        const requestId = await contextValue.requestDataExport('json');
        expect(requestId).toBe('export_123');
      });

      expect(mockPrivacyService.requestDataExport).toHaveBeenCalledWith('current_user', 'json');
      expect(mockAlert).toHaveBeenCalledWith(
        'Data Export Requested',
        expect.stringContaining('export_123'),
        [{ text: 'OK' }]
      );
    });

    it('should request data deletion with confirmation', async () => {
      mockAlert.mockImplementation((title, message, buttons) => {
        // Simulate user pressing "Delete" button
        const deleteButton = buttons?.find((b: any) => b.text === 'Delete');
        if (deleteButton) {
          deleteButton.onPress();
        }
      });

      mockPrivacyService.requestDataDeletion.mockResolvedValue({
        id: 'deletion_123',
        userId: 'current_user',
        requestedAt: new Date(),
        deletionType: 'complete',
        dataTypes: [],
        status: 'pending'
      });

      await act(async () => {
        await contextValue.requestDataDeletion('complete');
      });

      expect(mockAlert).toHaveBeenCalledWith(
        'Confirm Data Deletion',
        expect.stringContaining('permanently delete all'),
        expect.arrayContaining([
          { text: 'Cancel', style: 'cancel' },
          { text: 'Delete', style: 'destructive', onPress: expect.any(Function) }
        ])
      );
    });
  });

  describe('App State Security', () => {
    let contextValue: any;
    let appStateListener: (state: string) => void;
    
    const TestConsumer: React.FC = () => {
      contextValue = useSecurity();
      return null;
    };

    beforeEach(async () => {
      (AppState.addEventListener as jest.Mock).mockImplementation((event, listener) => {
        if (event === 'change') {
          appStateListener = listener;
        }
        return { remove: jest.fn() };
      });

      render(
        <SecurityProvider autoLockTimeoutMs={60000}>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });
    });

    it('should lock app when going to background', async () => {
      await act(async () => {
        appStateListener('background');
      });

      expect(contextValue.isAppSecured).toBe(true);
    });

    it('should check for auto-lock when becoming active', async () => {
      // Simulate app being inactive for longer than timeout
      jest.advanceTimersByTime(70000); // 70 seconds

      await act(async () => {
        appStateListener('active');
      });

      expect(contextValue.isAppSecured).toBe(true);
    });

    it('should not auto-lock if within timeout', async () => {
      // Simulate app being inactive for less than timeout
      jest.advanceTimersByTime(30000); // 30 seconds

      await act(async () => {
        appStateListener('active');
      });

      expect(contextValue.isAppSecured).toBe(false);
    });

    it('should manually lock app', async () => {
      await act(async () => {
        contextValue.lockApp();
      });

      expect(contextValue.isAppSecured).toBe(true);
    });

    it('should unlock app with biometric', async () => {
      // First lock the app
      await act(async () => {
        contextValue.lockApp();
      });

      expect(contextValue.isAppSecured).toBe(true);

      // Then unlock
      await act(async () => {
        const unlocked = await contextValue.unlockApp();
        expect(unlocked).toBe(true);
      });

      expect(contextValue.isAppSecured).toBe(false);
    });

    it('should unlock without biometric if not available', async () => {
      mockBiometricService.checkBiometricCapabilities.mockResolvedValue({
        isAvailable: false,
        biometryType: null
      });

      // Re-render with updated biometric capabilities
      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });

      await act(async () => {
        contextValue.lockApp();
      });

      await act(async () => {
        const unlocked = await contextValue.unlockApp();
        expect(unlocked).toBe(true);
      });

      expect(contextValue.isAppSecured).toBe(false);
    });
  });

  describe('Auto-Lock Timer', () => {
    let contextValue: any;
    
    const TestConsumer: React.FC = () => {
      contextValue = useSecurity();
      return null;
    };

    beforeEach(async () => {
      render(
        <SecurityProvider autoLockTimeoutMs={60000}>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });
    });

    it('should auto-lock after timeout', async () => {
      // Fast-forward time beyond the timeout
      act(() => {
        jest.advanceTimersByTime(70000); // 70 seconds
      });

      expect(contextValue.isAppSecured).toBe(true);
    });

    it('should not auto-lock if already secured', async () => {
      await act(async () => {
        contextValue.lockApp();
      });

      const initialSecuredState = contextValue.isAppSecured;

      act(() => {
        jest.advanceTimersByTime(70000);
      });

      expect(contextValue.isAppSecured).toBe(initialSecuredState);
    });

    it('should not auto-lock if biometric not available', async () => {
      mockBiometricService.checkBiometricCapabilities.mockResolvedValue({
        isAvailable: false,
        biometryType: null
      });

      render(
        <SecurityProvider autoLockTimeoutMs={60000}>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });

      act(() => {
        jest.advanceTimersByTime(70000);
      });

      expect(contextValue.isAppSecured).toBe(false);
    });
  });

  describe('Security Events', () => {
    let contextValue: any;
    
    const TestConsumer: React.FC = () => {
      contextValue = useSecurity();
      return null;
    };

    beforeEach(async () => {
      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });
    });

    it('should refresh security events', async () => {
      const mockEvents = [
        {
          id: 'event_1',
          type: 'login_success',
          timestamp: new Date(),
          deviceId: 'device_123',
          details: {},
          severity: 'low'
        }
      ];
      mockSecurityService.getAuditEvents.mockResolvedValue(mockEvents);

      await act(async () => {
        await contextValue.refreshSecurityEvents();
      });

      expect(contextValue.recentSecurityEvents).toEqual(mockEvents);
    });
  });

  describe('Error Handling', () => {
    it('should handle biometric authentication errors', async () => {
      let contextValue: any;
      
      const TestConsumer: React.FC = () => {
        contextValue = useSecurity();
        return null;
      };

      mockBiometricService.checkBiometricCapabilities.mockResolvedValue({
        isAvailable: false,
        biometryType: null,
        error: 'Biometric not supported'
      });

      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });

      await act(async () => {
        const result = await contextValue.authenticateWithBiometric();
        expect(result).toBe(false);
      });

      expect(mockAlert).toHaveBeenCalledWith(
        'Biometric Not Available',
        'Biometric authentication is not available on this device.'
      );
    });

    it('should handle secure storage errors', async () => {
      let contextValue: any;
      
      const TestConsumer: React.FC = () => {
        contextValue = useSecurity();
        return null;
      };

      render(
        <SecurityProvider>
          <TestConsumer />
        </SecurityProvider>
      );

      await waitFor(() => {
        expect(contextValue.isSecurityInitialized).toBe(true);
      });

      mockSecurityService.storeSecurely.mockRejectedValue(new Error('Storage failed'));

      await act(async () => {
        await expect(contextValue.storeSecurely('key', 'value'))
          .rejects.toThrow('Storage failed');
      });
    });
  });
});