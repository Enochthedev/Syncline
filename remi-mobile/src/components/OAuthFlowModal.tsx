/**
 * OAuth Flow Modal Component
 * 
 * Handles OAuth authentication flows for platform connections with
 * device-optimized UI and security features.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Linking,
  Platform,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { useTheme } from '../hooks/useTheme';
import { platformConnectionService } from '../services/platformConnectionService';
import { LoadingSpinner } from './LoadingSpinner';

interface OAuthFlowModalProps {
  visible: boolean;
  platform: string;
  onSuccess: (platform: string) => void;
  onCancel: () => void;
  onError: (error: string) => void;
}

export const OAuthFlowModal: React.FC<OAuthFlowModalProps> = ({
  visible,
  platform,
  onSuccess,
  onCancel,
  onError,
}) => {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [oauthState, setOauthState] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const webViewRef = useRef<WebView>(null);

  useEffect(() => {
    if (visible && platform) {
      initiateOAuthFlow();
    }
  }, [visible, platform]);

  const initiateOAuthFlow = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const oauthData = await platformConnectionService.initiateOAuthFlow(platform);
      setAuthUrl(oauthData.authUrl);
      setOauthState(oauthData.state);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start OAuth flow';
      setError(errorMessage);
      onError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigationStateChange = async (navState: any) => {
    const { url } = navState;
    
    // Check if this is a redirect URL with authorization code
    if (url.includes('code=') && url.includes('state=')) {
      try {
        const urlParams = new URLSearchParams(url.split('?')[1]);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        
        if (!code || !state) {
          throw new Error('Missing authorization code or state parameter');
        }
        
        if (state !== oauthState) {
          throw new Error('Invalid state parameter - possible CSRF attack');
        }
        
        setLoading(true);
        
        const connection = await platformConnectionService.completeOAuthFlow(platform, code, state);
        
        Alert.alert(
          'Connection Successful',
          `${connection.displayName} has been connected successfully!`,
          [{ text: 'OK', onPress: () => onSuccess(platform) }]
        );
        
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to complete OAuth flow';
        setError(errorMessage);
        onError(errorMessage);
      } finally {
        setLoading(false);
      }
    }
    
    // Check for OAuth errors
    if (url.includes('error=')) {
      const urlParams = new URLSearchParams(url.split('?')[1]);
      const error = urlParams.get('error');
      const errorDescription = urlParams.get('error_description');
      
      const errorMessage = errorDescription || error || 'OAuth authorization failed';
      setError(errorMessage);
      onError(errorMessage);
    }
  };

  const handleWebViewError = (syntheticEvent: any) => {
    const { nativeEvent } = syntheticEvent;
    const errorMessage = `Failed to load OAuth page: ${nativeEvent.description}`;
    setError(errorMessage);
    onError(errorMessage);
  };

  const handleOpenInBrowser = async () => {
    if (authUrl) {
      try {
        const supported = await Linking.canOpenURL(authUrl);
        if (supported) {
          await Linking.openURL(authUrl);
          Alert.alert(
            'Continue in Browser',
            'The OAuth flow will continue in your default browser. Please return to the app after completing the authorization.',
            [
              { text: 'Cancel', onPress: onCancel },
              { text: 'OK' }
            ]
          );
        } else {
          throw new Error('Cannot open URL in browser');
        }
      } catch (err) {
        onError('Failed to open OAuth URL in browser');
      }
    }
  };

  const getPlatformDisplayName = (platform: string) => {
    const names: Record<string, string> = {
      gmail: 'Gmail',
      slack: 'Slack',
      discord: 'Discord',
      whatsapp: 'WhatsApp',
      twitter: 'Twitter',
      linkedin: 'LinkedIn',
    };
    return names[platform] || platform;
  };

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, string> = {
      gmail: '📧',
      slack: '💬',
      discord: '🎮',
      whatsapp: '📱',
      twitter: '🐦',
      linkedin: '💼',
    };
    return icons[platform] || '🔗';
  };

  const styles = StyleSheet.create({
    modal: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 16,
      backgroundColor: theme.colors.surface,
      borderBottomWidth: 1,
      borderBottomColor: theme.colors.border,
      paddingTop: Platform.OS === 'ios' ? 50 : 16,
    },
    headerLeft: {
      flexDirection: 'row',
      alignItems: 'center',
      flex: 1,
    },
    platformIcon: {
      fontSize: 24,
      marginRight: 12,
    },
    headerTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.colors.text,
    },
    headerSubtitle: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      marginTop: 2,
    },
    cancelButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    cancelButtonText: {
      color: theme.colors.text,
      fontSize: 14,
      fontWeight: '500',
    },
    content: {
      flex: 1,
    },
    webView: {
      flex: 1,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    loadingText: {
      fontSize: 16,
      color: theme.colors.textSecondary,
      marginTop: 16,
      textAlign: 'center',
    },
    errorContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    errorIcon: {
      fontSize: 48,
      marginBottom: 16,
    },
    errorTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.colors.error,
      marginBottom: 8,
      textAlign: 'center',
    },
    errorMessage: {
      fontSize: 14,
      color: theme.colors.textSecondary,
      textAlign: 'center',
      marginBottom: 24,
      lineHeight: 20,
    },
    errorActions: {
      flexDirection: 'row',
      justifyContent: 'center',
    },
    errorButton: {
      paddingHorizontal: 20,
      paddingVertical: 10,
      borderRadius: 8,
      backgroundColor: theme.colors.primary,
      marginHorizontal: 8,
    },
    errorButtonSecondary: {
      backgroundColor: theme.colors.background,
      borderWidth: 1,
      borderColor: theme.colors.border,
    },
    errorButtonText: {
      color: theme.colors.surface,
      fontSize: 14,
      fontWeight: '500',
    },
    errorButtonTextSecondary: {
      color: theme.colors.text,
    },
    securityNotice: {
      backgroundColor: theme.colors.warningLight,
      padding: 12,
      margin: 16,
      borderRadius: 8,
      borderLeftWidth: 4,
      borderLeftColor: theme.colors.warning,
    },
    securityNoticeText: {
      fontSize: 12,
      color: theme.colors.text,
      lineHeight: 16,
    },
    footer: {
      padding: 16,
      backgroundColor: theme.colors.surface,
      borderTopWidth: 1,
      borderTopColor: theme.colors.border,
    },
    footerButton: {
      paddingVertical: 12,
      paddingHorizontal: 16,
      borderRadius: 8,
      backgroundColor: theme.colors.secondary,
      alignItems: 'center',
    },
    footerButtonText: {
      color: theme.colors.surface,
      fontSize: 14,
      fontWeight: '500',
    },
  });

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="fullScreen"
      onRequestClose={onCancel}
    >
      <View style={styles.modal}>
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={styles.platformIcon}>{getPlatformIcon(platform)}</Text>
            <View>
              <Text style={styles.headerTitle}>
                Connect {getPlatformDisplayName(platform)}
              </Text>
              <Text style={styles.headerSubtitle}>
                Authorize access to your account
              </Text>
            </View>
          </View>
          
          <TouchableOpacity style={styles.cancelButton} onPress={onCancel}>
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.securityNotice}>
          <Text style={styles.securityNoticeText}>
            🔒 Your login credentials are handled securely by {getPlatformDisplayName(platform)}. 
            We only receive permission to access your data as specified in the authorization scope.
          </Text>
        </View>

        <View style={styles.content}>
          {loading && !authUrl && (
            <View style={styles.loadingContainer}>
              <LoadingSpinner />
              <Text style={styles.loadingText}>
                Preparing secure connection to {getPlatformDisplayName(platform)}...
              </Text>
            </View>
          )}

          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorIcon}>⚠️</Text>
              <Text style={styles.errorTitle}>Connection Failed</Text>
              <Text style={styles.errorMessage}>{error}</Text>
              
              <View style={styles.errorActions}>
                <TouchableOpacity
                  style={styles.errorButton}
                  onPress={initiateOAuthFlow}
                >
                  <Text style={styles.errorButtonText}>Try Again</Text>
                </TouchableOpacity>
                
                <TouchableOpacity
                  style={[styles.errorButton, styles.errorButtonSecondary]}
                  onPress={onCancel}
                >
                  <Text style={[styles.errorButtonText, styles.errorButtonTextSecondary]}>
                    Cancel
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {authUrl && !error && (
            <>
              {loading && (
                <View style={styles.loadingContainer}>
                  <LoadingSpinner />
                  <Text style={styles.loadingText}>
                    Completing authorization...
                  </Text>
                </View>
              )}
              
              <WebView
                ref={webViewRef}
                source={{ uri: authUrl }}
                style={[styles.webView, loading && { display: 'none' }]}
                onNavigationStateChange={handleNavigationStateChange}
                onError={handleWebViewError}
                onLoadEnd={() => setLoading(false)}
                startInLoadingState={true}
                javaScriptEnabled={true}
                domStorageEnabled={true}
                sharedCookiesEnabled={true}
                thirdPartyCookiesEnabled={true}
                userAgent="Mozilla/5.0 (Mobile; rv:40.0) Gecko/40.0 Firefox/40.0"
              />
            </>
          )}
        </View>

        {authUrl && !loading && !error && (
          <View style={styles.footer}>
            <TouchableOpacity
              style={styles.footerButton}
              onPress={handleOpenInBrowser}
            >
              <Text style={styles.footerButtonText}>
                Open in Browser Instead
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
};