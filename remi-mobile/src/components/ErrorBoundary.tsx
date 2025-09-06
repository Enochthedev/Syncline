/**
 * React Error Boundary component with comprehensive error handling
 * and user feedback capabilities
 */

import React, { Component, ReactNode } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Dimensions
} from 'react-native';
import ErrorHandler from '../services/errorHandler';
import { AppError, ErrorType, ErrorSeverity } from '../types/errors';

interface Props {
  children: ReactNode;
  fallback?: (error: AppError, retry: () => void) => ReactNode;
  onError?: (error: AppError) => void;
}

interface State {
  hasError: boolean;
  error: AppError | null;
  errorId: string | null;
}

class ErrorBoundary extends Component<Props, State> {
  private errorHandler: ErrorHandler;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorId: null
    };
    this.errorHandler = ErrorHandler.getInstance();
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true
    };
  }

  async componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    try {
      const appError = await this.errorHandler.handleError(error, {
        screenName: 'ErrorBoundary',
        actionAttempted: 'component_render',
        additionalData: {
          componentStack: errorInfo.componentStack,
          errorBoundary: true
        }
      });

      this.setState({
        error: appError,
        errorId: appError.id
      });

      // Call optional error callback
      if (this.props.onError) {
        this.props.onError(appError);
      }

      console.error('ErrorBoundary caught error:', error, errorInfo);
    } catch (handlingError) {
      console.error('Error in ErrorBoundary:', handlingError);
      
      // Fallback error state
      const fallbackError: AppError = {
        id: `fallback_${Date.now()}`,
        type: ErrorType.COMPONENT_RENDER_ERROR,
        severity: ErrorSeverity.HIGH,
        message: error.message,
        userMessage: 'Something went wrong. Please try again.',
        context: {
          deviceId: 'unknown',
          platform: 'ios',
          appVersion: '1.0.0',
          timestamp: new Date()
        },
        recoveryActions: [],
        suggestedActions: [],
        retryable: true,
        reportable: true,
        timestamp: new Date(),
        stackTrace: error.stack,
        originalError: error
      };

      this.setState({
        error: fallbackError,
        errorId: fallbackError.id
      });
    }
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null
    });
  };

  private handleReportError = async () => {
    if (this.state.errorId) {
      Alert.prompt(
        'Report Error',
        'Please describe what you were doing when this error occurred:',
        [
          {
            text: 'Cancel',
            style: 'cancel'
          },
          {
            text: 'Send Report',
            onPress: async (feedback) => {
              try {
                await this.errorHandler.reportError(this.state.errorId!, feedback);
                Alert.alert('Thank You', 'Your error report has been sent.');
              } catch (reportError) {
                Alert.alert('Error', 'Failed to send error report. Please try again later.');
              }
            }
          }
        ],
        'plain-text'
      );
    }
  };

  private handleSuggestedAction = (actionData: any) => {
    switch (actionData.actionType) {
      case 'navigation':
        // Handle navigation action
        console.log('Navigate to:', actionData.actionData?.screen);
        break;
      case 'button':
        // Handle button action
        console.log('Execute action:', actionData.actionData?.action);
        break;
      case 'setting':
        // Handle settings action
        console.log('Open setting:', actionData.actionData?.setting);
        break;
      default:
        console.log('Unknown action type:', actionData.actionType);
    }
  };

  private renderErrorDetails = () => {
    const { error } = this.state;
    if (!error) return null;

    return (
      <View style={styles.errorDetails}>
        <Text style={styles.errorType}>
          Error Type: {error.type.replace(/_/g, ' ').toUpperCase()}
        </Text>
        <Text style={styles.errorId}>
          Error ID: {error.id}
        </Text>
        <Text style={styles.timestamp}>
          Time: {error.timestamp.toLocaleString()}
        </Text>
      </View>
    );
  };

  private renderSuggestedActions = () => {
    const { error } = this.state;
    if (!error || !error.suggestedActions.length) return null;

    return (
      <View style={styles.suggestedActions}>
        <Text style={styles.suggestedActionsTitle}>Suggested Actions:</Text>
        {error.suggestedActions
          .sort((a, b) => a.priority - b.priority)
          .map((action) => (
            <TouchableOpacity
              key={action.id}
              style={styles.actionButton}
              onPress={() => this.handleSuggestedAction(action)}
            >
              <Text style={styles.actionTitle}>{action.title}</Text>
              <Text style={styles.actionDescription}>{action.description}</Text>
            </TouchableOpacity>
          ))}
      </View>
    );
  };

  private renderDefaultErrorUI = () => {
    const { error } = this.state;
    if (!error) return null;

    const isHighSeverity = error.severity === ErrorSeverity.HIGH || 
                          error.severity === ErrorSeverity.CRITICAL;

    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.errorIcon}>
            <Text style={styles.errorIconText}>⚠️</Text>
          </View>
          
          <Text style={styles.title}>
            {isHighSeverity ? 'Something Went Wrong' : 'Minor Issue Detected'}
          </Text>
          
          <Text style={styles.message}>
            {error.userMessage}
          </Text>

          {this.renderSuggestedActions()}
          {this.renderErrorDetails()}

          <View style={styles.buttonContainer}>
            {error.retryable && (
              <TouchableOpacity
                style={[styles.button, styles.retryButton]}
                onPress={this.handleRetry}
              >
                <Text style={styles.buttonText}>Try Again</Text>
              </TouchableOpacity>
            )}

            {error.reportable && (
              <TouchableOpacity
                style={[styles.button, styles.reportButton]}
                onPress={this.handleReportError}
              >
                <Text style={styles.buttonText}>Report Issue</Text>
              </TouchableOpacity>
            )}
          </View>

          <TouchableOpacity
            style={styles.detailsToggle}
            onPress={() => {
              // Toggle technical details visibility
              Alert.alert(
                'Technical Details',
                `Error: ${error.message}\n\nStack: ${error.stackTrace?.substring(0, 500)}...`,
                [{ text: 'OK' }]
              );
            }}
          >
            <Text style={styles.detailsToggleText}>View Technical Details</Text>
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback && this.state.error) {
        return this.props.fallback(this.state.error, this.handleRetry);
      }

      // Use default error UI
      return this.renderDefaultErrorUI();
    }

    return this.props.children;
  }
}

const { width, height } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
    maxWidth: width - 40
  },
  errorIcon: {
    marginBottom: 20
  },
  errorIconText: {
    fontSize: 64,
    textAlign: 'center'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
    marginBottom: 16
  },
  message: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24
  },
  errorDetails: {
    backgroundColor: '#f1f3f4',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    width: '100%'
  },
  errorType: {
    fontSize: 14,
    color: '#5f6368',
    marginBottom: 4
  },
  errorId: {
    fontSize: 12,
    color: '#5f6368',
    fontFamily: 'monospace',
    marginBottom: 4
  },
  timestamp: {
    fontSize: 12,
    color: '#5f6368'
  },
  suggestedActions: {
    width: '100%',
    marginBottom: 24
  },
  suggestedActionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12
  },
  actionButton: {
    backgroundColor: '#e8f0fe',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#1976d2'
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1976d2',
    marginBottom: 4
  },
  actionDescription: {
    fontSize: 12,
    color: '#5f6368'
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 24
  },
  button: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    minWidth: 120
  },
  retryButton: {
    backgroundColor: '#1976d2'
  },
  reportButton: {
    backgroundColor: '#d32f2f'
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center'
  },
  detailsToggle: {
    padding: 8
  },
  detailsToggleText: {
    fontSize: 14,
    color: '#1976d2',
    textDecorationLine: 'underline'
  }
});

export default ErrorBoundary;