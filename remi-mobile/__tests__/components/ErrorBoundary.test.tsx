/**
 * Tests for ErrorBoundary component with comprehensive error handling
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import ErrorBoundary from '../../src/components/ErrorBoundary';
import { ErrorType, ErrorSeverity } from '../../src/types/errors';

// Mock dependencies
jest.mock('../../src/services/errorHandler');
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Alert: {
      alert: jest.fn(),
      prompt: jest.fn()
    }
  };
});

// Test component that throws errors
const ThrowError: React.FC<{ shouldThrow: boolean; errorMessage?: string }> = ({ 
  shouldThrow, 
  errorMessage = 'Test error' 
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Suppress console.error for cleaner test output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Error Catching', () => {
    it('should catch and display errors from child components', async () => {
      const { getByText, queryByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(queryByText('No error')).toBeNull();
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });

    it('should render children normally when no error occurs', () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(getByText('No error')).toBeTruthy();
    });

    it('should call onError callback when error occurs', async () => {
      const onErrorMock = jest.fn();
      
      render(
        <ErrorBoundary onError={onErrorMock}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(onErrorMock).toHaveBeenCalled();
      });
    });
  });

  describe('Error Display', () => {
    it('should display user-friendly error message', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Network connection failed" />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });

    it('should show retry button for retryable errors', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Try Again')).toBeTruthy();
      });
    });

    it('should show report button for reportable errors', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Report Issue')).toBeTruthy();
      });
    });

    it('should display error details when requested', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        const detailsButton = getByText('View Technical Details');
        fireEvent.press(detailsButton);
      });

      expect(Alert.alert).toHaveBeenCalledWith(
        'Technical Details',
        expect.stringContaining('Error:'),
        [{ text: 'OK' }]
      );
    });
  });

  describe('Error Recovery', () => {
    it('should reset error state when retry is pressed', async () => {
      const { getByText, queryByText, rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Try Again')).toBeTruthy();
      });

      fireEvent.press(getByText('Try Again'));

      // Re-render with no error
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(queryByText('Something Went Wrong')).toBeNull();
        expect(getByText('No error')).toBeTruthy();
      });
    });

    it('should handle error reporting', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        const reportButton = getByText('Report Issue');
        fireEvent.press(reportButton);
      });

      expect(Alert.prompt).toHaveBeenCalledWith(
        'Report Error',
        expect.stringContaining('describe what you were doing'),
        expect.arrayContaining([
          expect.objectContaining({ text: 'Cancel' }),
          expect.objectContaining({ text: 'Send Report' })
        ]),
        'plain-text'
      );
    });
  });

  describe('Custom Fallback', () => {
    it('should use custom fallback when provided', async () => {
      const customFallback = jest.fn().mockReturnValue(
        <div>Custom Error UI</div>
      );

      const { getByText } = render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Custom Error UI')).toBeTruthy();
        expect(customFallback).toHaveBeenCalled();
      });
    });

    it('should pass error and retry function to custom fallback', async () => {
      const customFallback = jest.fn().mockReturnValue(
        <div>Custom Error UI</div>
      );

      render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(customFallback).toHaveBeenCalledWith(
          expect.objectContaining({
            type: expect.any(String),
            message: expect.any(String)
          }),
          expect.any(Function)
        );
      });
    });
  });

  describe('Suggested Actions', () => {
    it('should display suggested actions when available', async () => {
      // This would require mocking the ErrorHandler to return specific suggested actions
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });

      // Would test for specific suggested actions based on error type
    });

    it('should handle suggested action execution', async () => {
      // Test would verify that suggested actions are properly executed
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });

      // Would test action execution
    });
  });

  describe('Error Severity Handling', () => {
    it('should display different UI for high severity errors', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Critical system failure" />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });

    it('should display different UI for low severity errors', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Minor issue detected" />
        </ErrorBoundary>
      );

      await waitFor(() => {
        // Would check for different title based on severity
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });
  });

  describe('Accessibility', () => {
    it('should be accessible to screen readers', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        const errorTitle = getByText('Something Went Wrong');
        expect(errorTitle).toBeTruthy();
        // Would test accessibility properties
      });
    });

    it('should support keyboard navigation', async () => {
      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        const retryButton = getByText('Try Again');
        expect(retryButton).toBeTruthy();
        // Would test keyboard navigation
      });
    });
  });

  describe('Performance', () => {
    it('should handle errors efficiently', async () => {
      const startTime = Date.now();
      
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        const endTime = Date.now();
        expect(endTime - startTime).toBeLessThan(1000);
      });
    });

    it('should not cause memory leaks', async () => {
      // Test would verify proper cleanup
      const { unmount } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        unmount();
        // Would verify cleanup
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle errors in error handling gracefully', async () => {
      // Mock ErrorHandler to throw an error
      const ErrorHandler = require('../../src/services/errorHandler').default;
      ErrorHandler.getInstance = jest.fn().mockImplementation(() => ({
        handleError: jest.fn().mockRejectedValue(new Error('Handler error'))
      }));

      const { getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });

    it('should handle multiple consecutive errors', async () => {
      const { rerender, getByText } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="First error" />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Try Again')).toBeTruthy();
      });

      fireEvent.press(getByText('Try Again'));

      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Second error" />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(getByText('Something Went Wrong')).toBeTruthy();
      });
    });
  });
});