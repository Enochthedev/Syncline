'use client';

import React, { useState } from 'react';
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');

  // Register page-specific keyboard shortcuts
  useKeyboardShortcuts([
    {
      id: 'analytics-export',
      key: 'e',
      ctrlKey: true,
      description: 'Export analytics data',
      category: 'Analytics',
      action: () => {
        // Trigger export functionality
        const event = new CustomEvent('analytics-export', { detail: { format: 'csv' } });
        window.dispatchEvent(event);
      },
    },
    {
      id: 'analytics-refresh',
      key: 'r',
      ctrlKey: true,
      shiftKey: true,
      description: 'Refresh analytics data',
      category: 'Analytics',
      action: () => {
        window.location.reload();
      },
    },
    {
      id: 'analytics-timerange-week',
      key: '1',
      description: 'Switch to 7-day view',
      category: 'Analytics',
      action: () => setTimeRange('7d'),
    },
    {
      id: 'analytics-timerange-month',
      key: '2',
      description: 'Switch to 30-day view',
      category: 'Analytics',
      action: () => setTimeRange('30d'),
    },
    {
      id: 'analytics-timerange-quarter',
      key: '3',
      description: 'Switch to 90-day view',
      category: 'Analytics',
      action: () => setTimeRange('90d'),
    },
    {
      id: 'analytics-timerange-year',
      key: '4',
      description: 'Switch to 1-year view',
      category: 'Analytics',
      action: () => setTimeRange('1y'),
    },
  ]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div id="main-content">
          <AnalyticsDashboard
            timeRange={timeRange}
            onTimeRangeChange={setTimeRange}
          />
        </div>
      </div>
    </div>
  );
}