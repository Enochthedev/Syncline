/**
 * Custom hook for error handling with retry logic and user feedback
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Alert } from 'react-native';
import ErrorHandler from '../services/errorHandler';
import {
    AppError,
    ErrorType,
    ErrorResolution,
    RecoveryAction,
    RetryConfig
} from '../types/errors';

interface UseErrorHandlerOptions {
    showUserFeedback?: boolean;
    autoRetry?: boolean;
    maxRetries?: number;
    onError?: (error: AppError) => void;
    onResolution?: (resolution: ErrorResolution) => void;
}

interface UseErrorHandlerReturn {
    error: AppError | null;
    isRetrying: boolean;
    retryCount: number;
    handleError: (error: Error, context?: any) => Promise<ErrorResolution>;
    retryLastOperation: () => Promise<void>;
    clearError: () => void;
    executeWithRetry: <T>(
        operation: () => Promise<T>,
        errorType: ErrorType,
        config?: Partial<RetryConfig>
    ) => Promise<T>;
}

export const useErrorHandler = (
    options: UseErrorHandlerOptions = {}
): UseErrorHandlerReturn => {
    const [error, setError] = useState<AppError | null>(null);
    const [isRetrying, setIsRetrying] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    const errorHandler = useRef(ErrorHandler.getInstance());
    const lastOperation = useRef<(() => Promise<any>) | null>(null);
    const lastErrorType = useRef<ErrorType | null>(null);

    const {
        showUserFeedback = true,
        autoRetry = false,
        maxRetries = 3,
        onError,
        onResolution
    } = options;

    useEffect(() => {
        // Cleanup on unmount
        return () => {
            setError(null);
            setIsRetrying(false);
            setRetryCount(0);
        };
    }, []);

    const handleError = useCallback(async (
        error: Error,
        context?: any
    ): Promise<ErrorResolution> => {
        try {
            const resolution = await errorHandler.current.handleError(error, context);
            const appError = await errorHandler.current.handleError(error, context);

            setError(appError as AppError);

            // Call error callback
            if (onError) {
                onError(appError as AppError);
            }

            // Handle resolution based on action
            await handleResolution(resolution, appError as AppError);

            // Call resolution callback
            if (onResolution) {
                onResolution(resolution);
            }

            return resolution;
        } catch (handlingError) {
            console.error('Error in useErrorHandler:', handlingError);

            const fallbackResolution: ErrorResolution = {
                resolved: false,
                action: RecoveryAction.CONTACT_SUPPORT,
                message: 'An unexpected error occurred. Please contact support.'
            };

            if (showUserFeedback) {
                Alert.alert('Error', fallbackResolution.message);
            }

            return fallbackResolution;
        }
    }, [onError, onResolution, showUserFeedback]);

    const handleResolution = async (
        resolution: ErrorResolution,
        appError: AppError
    ): Promise<void> => {
        switch (resolution.action) {
            case RecoveryAction.RETRY:
                if (autoRetry && retryCount < maxRetries) {
                    await performRetry();
                } else if (showUserFeedback) {
                    showRetryPrompt(appError);
                }
                break;

            case RecoveryAction.FALLBACK:
                if (showUserFeedback && resolution.message) {
                    Alert.alert('Notice', resolution.message);
                }
                break;

            case RecoveryAction.USER_ACTION:
                if (showUserFeedback) {
                    showUserActionPrompt(appError);
                }
                break;

            case RecoveryAction.CONTACT_SUPPORT:
                if (showUserFeedback) {
                    showSupportPrompt(appError);
                }
                break;

            default:
                if (showUserFeedback && resolution.message) {
                    Alert.alert('Error', resolution.message);
                }
        }
    };

    const performRetry = async (): Promise<void> => {
        if (!lastOperation.current) return;

        setIsRetrying(true);
        setRetryCount(prev => prev + 1);

        try {
            await lastOperation.current();
            setError(null);
            setRetryCount(0);
        } catch (retryError) {
            await handleError(retryError as Error);
        } finally {
            setIsRetrying(false);
        }
    };

    const retryLastOperation = useCallback(async (): Promise<void> => {
        await performRetry();
    }, []);

    const clearError = useCallback((): void => {
        setError(null);
        setRetryCount(0);
        setIsRetrying(false);
    }, []);

    const executeWithRetry = useCallback(async <T>(
        operation: () => Promise<T>,
        errorType: ErrorType,
        config?: Partial<RetryConfig>
    ): Promise<T> => {
        lastOperation.current = operation;
        lastErrorType.current = errorType;

        try {
            return await errorHandler.current.retryOperation(operation, errorType, config);
        } catch (error) {
            await handleError(error as Error);
            throw error;
        }
    }, [handleError]);

    const showRetryPrompt = (appError: AppError): void => {
        Alert.alert(
            'Retry Operation',
            appError.userMessage,
            [
                {
                    text: 'Cancel',
                    style: 'cancel'
                },
                {
                    text: 'Retry',
                    onPress: retryLastOperation
                }
            ]
        );
    };

    const showUserActionPrompt = (appError: AppError): void => {
        const actions = appError.suggestedActions.slice(0, 3); // Limit to 3 actions for alert

        const alertButtons = actions.map(action => ({
            text: action.title,
            onPress: () => handleSuggestedAction(action)
        }));

        alertButtons.push({
            text: 'Cancel',
            style: 'cancel' as const
        });

        Alert.alert(
            'Action Required',
            appError.userMessage,
            alertButtons
        );
    };

    const showSupportPrompt = (appError: AppError): void => {
        Alert.alert(
            'Contact Support',
            `${appError.userMessage}\n\nError ID: ${appError.id}`,
            [
                {
                    text: 'Copy Error ID',
                    onPress: () => {
                        // Copy to clipboard functionality would go here
                        console.log('Copy error ID:', appError.id);
                    }
                },
                {
                    text: 'Report Issue',
                    onPress: () => {
                        // Open error feedback modal
                        console.log('Open error feedback for:', appError.id);
                    }
                },
                {
                    text: 'OK',
                    style: 'cancel'
                }
            ]
        );
    };

    const handleSuggestedAction = (action: any): void => {
        switch (action.actionType) {
            case 'navigation':
                // Handle navigation - would integrate with navigation service
                console.log('Navigate to:', action.actionData?.screen);
                break;
            case 'button':
                // Handle button action
                console.log('Execute action:', action.actionData?.action);
                if (action.actionData?.action === 'clearCache') {
                    // Clear cache implementation
                }
                break;
            case 'setting':
                // Handle settings action
                console.log('Open setting:', action.actionData?.setting);
                break;
            default:
                console.log('Unknown action type:', action.actionType);
        }
    };

    return {
        error,
        isRetrying,
        retryCount,
        handleError,
        retryLastOperation,
        clearError,
        executeWithRetry
    };
};

export default useErrorHandler;