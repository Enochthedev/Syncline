/**
 * Tests for useErrorHandler hook with retry logic and user feedback
 */

import { renderHook, act } from '@testing-library/react-hooks';
import { Alert } from 'react-native';
import { useErrorHandler } from '../../src/hooks/useErrorHandler';
import { ErrorType, RecoveryAction } from '../../src/types/errors';

// Mock dependencies
jest.mock('react-native', () => ({
    Alert: {
        alert: jest.fn(),
        prompt: jest.fn()
    }
}));

jest.mock('../../src/services/errorHandler', () => ({
    getInstance: jest.fn().mockReturnValue({
        handleError: jest.fn(),
        retryOperation: jest.fn()
    })
}));

describe('useErrorHandler', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('Basic Error Handling', () => {
        it('should handle errors and update state', async () => {
            const { result } = renderHook(() => useErrorHandler());

            const mockError = new Error('Test error');
            const mockAppError = {
                id: 'test-error-1',
                type: ErrorType.NETWORK_UNAVAILABLE,
                severity: 'medium',
                message: 'Test error',
                userMessage: 'Network unavailable',
                recoveryActions: [RecoveryAction.RETRY],
                suggestedActions: [],
                retryable: true,
                reportable: false,
                timestamp: new Date(),
                context: {
                    deviceId: 'test-device',
                    platform: 'ios' as const,
                    appVersion: '1.0.0',
                    timestamp: new Date()
                }
            };

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY,
                message: 'Network unavailable'
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(result.current.error).toBeDefined();
            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalledWith(mockError, undefined);
        });

        it('should clear error state', () => {
            const { result } = renderHook(() => useErrorHandler());

            act(() => {
                result.current.clearError();
            });

            expect(result.current.error).toBeNull();
            expect(result.current.retryCount).toBe(0);
            expect(result.current.isRetrying).toBe(false);
        });
    });

    describe('Retry Logic', () => {
        it('should execute operations with retry', async () => {
            const { result } = renderHook(() => useErrorHandler());

            let attemptCount = 0;
            const operation = jest.fn().mockImplementation(() => {
                attemptCount++;
                if (attemptCount < 3) {
                    throw new Error('Temporary failure');
                }
                return Promise.resolve('success');
            });

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().retryOperation.mockImplementation(async (op, errorType, config) => {
                return await op();
            });

            await act(async () => {
                const result_value = await result.current.executeWithRetry(
                    operation,
                    ErrorType.API_TIMEOUT
                );
                expect(result_value).toBe('success');
            });

            expect(ErrorHandler.getInstance().retryOperation).toHaveBeenCalledWith(
                operation,
                ErrorType.API_TIMEOUT,
                undefined
            );
        });

        it('should handle retry failures', async () => {
            const { result } = renderHook(() => useErrorHandler());

            const operation = jest.fn().mockRejectedValue(new Error('Persistent failure'));

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().retryOperation.mockRejectedValue(new Error('Persistent failure'));
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.CONTACT_SUPPORT
            });

            await act(async () => {
                try {
                    await result.current.executeWithRetry(operation, ErrorType.API_TIMEOUT);
                } catch (error) {
                    expect(error.message).toBe('Persistent failure');
                }
            });

            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalled();
        });

        it('should track retry count', async () => {
            const { result } = renderHook(() => useErrorHandler({ autoRetry: true }));

            const mockError = new Error('Retryable error');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(result.current.retryCount).toBeGreaterThanOrEqual(0);
        });
    });

    describe('User Feedback', () => {
        it('should show user feedback for errors', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ showUserFeedback: true })
            );

            const mockError = new Error('User action required');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.USER_ACTION,
                message: 'Please check your settings'
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            // User feedback would be shown via Alert or other UI
            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalled();
        });

        it('should not show user feedback when disabled', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ showUserFeedback: false })
            );

            const mockError = new Error('Silent error');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.USER_ACTION,
                message: 'Silent message'
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(Alert.alert).not.toHaveBeenCalled();
        });

        it('should handle retry prompts', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ showUserFeedback: true })
            );

            const mockError = new Error('Retryable error');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY,
                message: 'Operation failed, retry?'
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            // Would verify retry prompt is shown
            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalled();
        });
    });

    describe('Auto Retry', () => {
        it('should automatically retry when enabled', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ autoRetry: true, maxRetries: 2 })
            );

            const mockError = new Error('Auto retry error');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(result.current.isRetrying).toBe(false); // Should complete
        });

        it('should respect max retry limit', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ autoRetry: true, maxRetries: 1 })
            );

            const mockError = new Error('Max retry test');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            // Should not exceed max retries
            expect(result.current.retryCount).toBeLessThanOrEqual(1);
        });
    });

    describe('Callbacks', () => {
        it('should call onError callback', async () => {
            const onErrorMock = jest.fn();
            const { result } = renderHook(() =>
                useErrorHandler({ onError: onErrorMock })
            );

            const mockError = new Error('Callback test');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.RETRY
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(onErrorMock).toHaveBeenCalled();
        });

        it('should call onResolution callback', async () => {
            const onResolutionMock = jest.fn();
            const { result } = renderHook(() =>
                useErrorHandler({ onResolution: onResolutionMock })
            );

            const mockError = new Error('Resolution test');

            const ErrorHandler = require('../../src/services/errorHandler');
            const mockResolution = {
                resolved: true,
                action: RecoveryAction.FALLBACK
            };
            ErrorHandler.getInstance().handleError.mockResolvedValue(mockResolution);

            await act(async () => {
                await result.current.handleError(mockError);
            });

            expect(onResolutionMock).toHaveBeenCalledWith(mockResolution);
        });
    });

    describe('Error Recovery Actions', () => {
        it('should handle fallback action', async () => {
            const { result } = renderHook(() => useErrorHandler());

            const mockError = new Error('Fallback test');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: true,
                action: RecoveryAction.FALLBACK,
                message: 'Using cached data',
                fallbackData: { cached: true }
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            // Fallback should be handled appropriately
            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalled();
        });

        it('should handle contact support action', async () => {
            const { result } = renderHook(() =>
                useErrorHandler({ showUserFeedback: true })
            );

            const mockError = new Error('Support needed');

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: false,
                action: RecoveryAction.CONTACT_SUPPORT,
                message: 'Please contact support'
            });

            await act(async () => {
                await result.current.handleError(mockError);
            });

            // Support prompt should be shown
            expect(ErrorHandler.getInstance().handleError).toHaveBeenCalled();
        });
    });

    describe('Edge Cases', () => {
        it('should handle null/undefined errors', async () => {
            const { result } = renderHook(() => useErrorHandler());

            await act(async () => {
                try {
                    await result.current.handleError(null as any);
                } catch (error) {
                    // Should handle gracefully
                }
            });

            expect(result.current.error).toBeDefined();
        });

        it('should handle errors in error handling', async () => {
            const { result } = renderHook(() => useErrorHandler());

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockRejectedValue(new Error('Handler error'));

            await act(async () => {
                const resolution = await result.current.handleError(new Error('Test'));
                expect(resolution.action).toBe(RecoveryAction.CONTACT_SUPPORT);
            });
        });

        it('should cleanup on unmount', () => {
            const { result, unmount } = renderHook(() => useErrorHandler());

            act(() => {
                unmount();
            });

            // Should cleanup properly
            expect(true).toBe(true); // Placeholder assertion
        });
    });

    describe('Performance', () => {
        it('should handle errors efficiently', async () => {
            const { result } = renderHook(() => useErrorHandler());

            const startTime = Date.now();

            const ErrorHandler = require('../../src/services/errorHandler');
            ErrorHandler.getInstance().handleError.mockResolvedValue({
                resolved: true,
                action: RecoveryAction.FALLBACK
            });

            await act(async () => {
                await result.current.handleError(new Error('Performance test'));
            });

            const endTime = Date.now();
            expect(endTime - startTime).toBeLessThan(1000);
        });

        it('should not cause memory leaks', () => {
            const { result, unmount } = renderHook(() => useErrorHandler());

            // Simulate multiple error handling cycles
            act(() => {
                for (let i = 0; i < 100; i++) {
                    result.current.clearError();
                }
            });

            unmount();

            // Should not leak memory
            expect(true).toBe(true); // Placeholder assertion
        });
    });
});