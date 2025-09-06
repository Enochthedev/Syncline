/**
 * Error feedback and reporting component with user-friendly interface
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Modal,
  ScrollView,
  Alert,
  Switch,
  Dimensions
} from 'react-native';
import ErrorHandler from '../services/errorHandler';
import { AppError, ErrorMetrics, ErrorType } from '../types/errors';

interface ErrorFeedbackProps {
  visible: boolean;
  error?: AppError;
  onClose: () => void;
  onSubmit?: (feedback: string) => void;
}

interface ErrorReportData {
  description: string;
  reproductionSteps: string[];
  includeDeviceInfo: boolean;
  includeLogs: boolean;
  contactEmail?: string;
}

const ErrorFeedback: React.FC<ErrorFeedbackProps> = ({
  visible,
  error,
  onClose,
  onSubmit
}) => {
  const [reportData, setReportData] = useState<ErrorReportData>({
    description: '',
    reproductionSteps: [''],
    includeDeviceInfo: true,
    includeLogs: true
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMetrics, setErrorMetrics] = useState<Map<ErrorType, ErrorMetrics>>(new Map());

  const errorHandler = ErrorHandler.getInstance();

  useEffect(() => {
    if (visible) {
      loadErrorMetrics();
    }
  }, [visible]);

  const loadErrorMetrics = () => {
    const metrics = errorHandler.getErrorMetrics();
    setErrorMetrics(metrics);
  };

  const handleAddReproductionStep = () => {
    setReportData(prev => ({
      ...prev,
      reproductionSteps: [...prev.reproductionSteps, '']
    }));
  };

  const handleUpdateReproductionStep = (index: number, value: string) => {
    setReportData(prev => ({
      ...prev,
      reproductionSteps: prev.reproductionSteps.map((step, i) => 
        i === index ? value : step
      )
    }));
  };

  const handleRemoveReproductionStep = (index: number) => {
    if (reportData.reproductionSteps.length > 1) {
      setReportData(prev => ({
        ...prev,
        reproductionSteps: prev.reproductionSteps.filter((_, i) => i !== index)
      }));
    }
  };

  const handleSubmitReport = async () => {
    if (!reportData.description.trim()) {
      Alert.alert('Error', 'Please provide a description of the issue.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (error) {
        await errorHandler.reportError(error.id, reportData.description);
      }

      if (onSubmit) {
        onSubmit(reportData.description);
      }

      Alert.alert(
        'Thank You',
        'Your error report has been submitted. We\'ll investigate the issue.',
        [{ text: 'OK', onPress: onClose }]
      );

      // Reset form
      setReportData({
        description: '',
        reproductionSteps: [''],
        includeDeviceInfo: true,
        includeLogs: true
      });
    } catch (submitError) {
      Alert.alert(
        'Submission Failed',
        'Failed to submit error report. Please try again later.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderErrorSummary = () => {
    if (!error) return null;

    return (
      <View style={styles.errorSummary}>
        <Text style={styles.sectionTitle}>Error Summary</Text>
        <View style={styles.errorInfo}>
          <Text style={styles.errorLabel}>Type:</Text>
          <Text style={styles.errorValue}>
            {error.type.replace(/_/g, ' ').toUpperCase()}
          </Text>
        </View>
        <View style={styles.errorInfo}>
          <Text style={styles.errorLabel}>Severity:</Text>
          <Text style={[
            styles.errorValue,
            { color: getSeverityColor(error.severity) }
          ]}>
            {error.severity.toUpperCase()}
          </Text>
        </View>
        <View style={styles.errorInfo}>
          <Text style={styles.errorLabel}>Time:</Text>
          <Text style={styles.errorValue}>
            {error.timestamp.toLocaleString()}
          </Text>
        </View>
        <View style={styles.errorInfo}>
          <Text style={styles.errorLabel}>Message:</Text>
          <Text style={styles.errorValue}>{error.userMessage}</Text>
        </View>
      </View>
    );
  };

  const renderReproductionSteps = () => {
    return (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Steps to Reproduce (Optional)</Text>
        <Text style={styles.sectionDescription}>
          Help us understand how this error occurred by describing the steps you took.
        </Text>
        {reportData.reproductionSteps.map((step, index) => (
          <View key={index} style={styles.stepContainer}>
            <Text style={styles.stepNumber}>{index + 1}.</Text>
            <TextInput
              style={styles.stepInput}
              placeholder={`Step ${index + 1}`}
              value={step}
              onChangeText={(value) => handleUpdateReproductionStep(index, value)}
              multiline
            />
            {reportData.reproductionSteps.length > 1 && (
              <TouchableOpacity
                style={styles.removeStepButton}
                onPress={() => handleRemoveReproductionStep(index)}
              >
                <Text style={styles.removeStepText}>×</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}
        <TouchableOpacity
          style={styles.addStepButton}
          onPress={handleAddReproductionStep}
        >
          <Text style={styles.addStepText}>+ Add Step</Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderPrivacyOptions = () => {
    return (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Privacy & Data</Text>
        <View style={styles.privacyOption}>
          <View style={styles.privacyOptionText}>
            <Text style={styles.privacyOptionTitle}>Include Device Information</Text>
            <Text style={styles.privacyOptionDescription}>
              Device model, OS version, app version (helps with debugging)
            </Text>
          </View>
          <Switch
            value={reportData.includeDeviceInfo}
            onValueChange={(value) => 
              setReportData(prev => ({ ...prev, includeDeviceInfo: value }))
            }
          />
        </View>
        <View style={styles.privacyOption}>
          <View style={styles.privacyOptionText}>
            <Text style={styles.privacyOptionTitle}>Include Error Logs</Text>
            <Text style={styles.privacyOptionDescription}>
              Technical error details (no personal data included)
            </Text>
          </View>
          <Switch
            value={reportData.includeLogs}
            onValueChange={(value) => 
              setReportData(prev => ({ ...prev, includeLogs: value }))
            }
          />
        </View>
      </View>
    );
  };

  const renderErrorMetrics = () => {
    if (errorMetrics.size === 0) return null;

    const sortedMetrics = Array.from(errorMetrics.entries())
      .sort(([, a], [, b]) => b.count - a.count)
      .slice(0, 5);

    return (
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Recent Error Patterns</Text>
        <Text style={styles.sectionDescription}>
          Most common errors in this session:
        </Text>
        {sortedMetrics.map(([type, metrics]) => (
          <View key={type} style={styles.metricItem}>
            <Text style={styles.metricType}>
              {type.replace(/_/g, ' ').toUpperCase()}
            </Text>
            <Text style={styles.metricCount}>
              {metrics.count} occurrence{metrics.count !== 1 ? 's' : ''}
            </Text>
          </View>
        ))}
      </View>
    );
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return '#d32f2f';
      case 'high': return '#f57c00';
      case 'medium': return '#1976d2';
      case 'low': return '#388e3c';
      default: return '#666';
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>Cancel</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Report Issue</Text>
          <TouchableOpacity
            onPress={handleSubmitReport}
            style={[
              styles.submitButton,
              { opacity: isSubmitting ? 0.6 : 1 }
            ]}
            disabled={isSubmitting}
          >
            <Text style={styles.submitButtonText}>
              {isSubmitting ? 'Sending...' : 'Submit'}
            </Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {renderErrorSummary()}

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Describe the Issue</Text>
            <Text style={styles.sectionDescription}>
              Please describe what happened and what you expected to happen.
            </Text>
            <TextInput
              style={styles.descriptionInput}
              placeholder="Describe the issue you encountered..."
              value={reportData.description}
              onChangeText={(value) => 
                setReportData(prev => ({ ...prev, description: value }))
              }
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />
          </View>

          {renderReproductionSteps()}
          {renderPrivacyOptions()}
          {renderErrorMetrics()}

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Contact Information (Optional)</Text>
            <TextInput
              style={styles.emailInput}
              placeholder="your.email@example.com"
              value={reportData.contactEmail}
              onChangeText={(value) => 
                setReportData(prev => ({ ...prev, contactEmail: value }))
              }
              keyboardType="email-address"
              autoCapitalize="none"
            />
            <Text style={styles.emailDescription}>
              We'll only use this to follow up on your report if needed.
            </Text>
          </View>

          <View style={styles.bottomPadding} />
        </ScrollView>
      </View>
    </Modal>
  );
};

const { width } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff'
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    paddingTop: 50 // Account for status bar
  },
  closeButton: {
    padding: 8
  },
  closeButtonText: {
    fontSize: 16,
    color: '#666'
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333'
  },
  submitButton: {
    padding: 8
  },
  submitButtonText: {
    fontSize: 16,
    color: '#1976d2',
    fontWeight: '600'
  },
  content: {
    flex: 1,
    paddingHorizontal: 16
  },
  section: {
    marginTop: 24
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8
  },
  sectionDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    lineHeight: 20
  },
  errorSummary: {
    backgroundColor: '#f8f9fa',
    padding: 16,
    borderRadius: 8,
    marginTop: 16
  },
  errorInfo: {
    flexDirection: 'row',
    marginBottom: 8
  },
  errorLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    width: 80
  },
  errorValue: {
    fontSize: 14,
    color: '#666',
    flex: 1
  },
  descriptionInput: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    minHeight: 100,
    backgroundColor: '#fafafa'
  },
  stepContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12
  },
  stepNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    width: 24,
    marginTop: 12
  },
  stepInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fafafa',
    marginRight: 8
  },
  removeStepButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#f44336',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8
  },
  removeStepText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold'
  },
  addStepButton: {
    padding: 12,
    borderWidth: 1,
    borderColor: '#1976d2',
    borderRadius: 8,
    borderStyle: 'dashed',
    alignItems: 'center'
  },
  addStepText: {
    color: '#1976d2',
    fontSize: 16,
    fontWeight: '600'
  },
  privacyOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0'
  },
  privacyOptionText: {
    flex: 1,
    marginRight: 16
  },
  privacyOptionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4
  },
  privacyOptionDescription: {
    fontSize: 14,
    color: '#666',
    lineHeight: 18
  },
  metricItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0'
  },
  metricType: {
    fontSize: 14,
    color: '#333',
    flex: 1
  },
  metricCount: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600'
  },
  emailInput: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    backgroundColor: '#fafafa',
    marginBottom: 8
  },
  emailDescription: {
    fontSize: 12,
    color: '#666',
    fontStyle: 'italic'
  },
  bottomPadding: {
    height: 40
  }
});

export default ErrorFeedback;